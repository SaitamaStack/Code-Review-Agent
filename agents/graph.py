"""
LangGraph state machine for the code review and fix agent.

Implements the following workflow:
    START → review → fix → execute → evaluate
                              ↑          ↓
                              └── retry ←┘ (if error & attempts < max)
                                         ↓
                                       END (success or max retries)
"""

import json
import logging
import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from config import get_config
from models.schemas import AgentState, CodeReview, FixedCode, ExecutionResult
from tools.executor import execute_code_safely
from agents.prompts import (
    REVIEW_SYSTEM_PROMPT,
    FIX_SYSTEM_PROMPT,
    get_review_prompt,
    get_fix_prompt,
)

# Configure logging for debugging LLM responses
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_llm() -> ChatOllama:
    """
    Create and configure the Ollama LLM instance.
    
    Returns:
        ChatOllama: Configured LLM for code review/fix tasks
    """
    config = get_config()
    return ChatOllama(
        model=config.model_name,
        base_url=config.ollama_base_url,
        temperature=config.temperature,
        format="json",  # Request JSON output
    )


def _normalize_to_string_list(items: list) -> list[str]:
    """
    Convert a list of items (strings or dicts) to a list of strings.
    
    Some models return structured objects like {"line": 5, "description": "..."} 
    instead of plain strings. This normalizes them.
    """
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Extract meaningful text from dict
            if "description" in item:
                desc = item["description"]
                if "line" in item:
                    result.append(f"Line {item['line']}: {desc}")
                else:
                    result.append(desc)
            elif "message" in item:
                result.append(item["message"])
            elif "text" in item:
                result.append(item["text"])
            else:
                # Just stringify the dict
                result.append(str(item))
        else:
            result.append(str(item))
    return result


def _fix_duplicate_keys_json(json_str: str) -> str:
    """
    Attempt to fix JSON with duplicate keys by keeping only the last occurrence.
    
    Some models output duplicate keys when they "correct" themselves mid-generation.
    This is a best-effort repair.
    """
    # Remove duplicate consecutive key-value pairs
    # Pattern: "key": "value"\n  "key": "value" -> keep last one
    
    lines = json_str.split('\n')
    seen_keys = {}
    result_lines = []
    
    for i, line in enumerate(lines):
        # Check if this line starts a key
        key_match = re.match(r'\s*"(\w+)":', line)
        if key_match:
            key = key_match.group(1)
            # Check if next line has the same key (duplicate)
            if i + 1 < len(lines):
                next_key_match = re.match(r'\s*"(\w+)":', lines[i + 1])
                if next_key_match and next_key_match.group(1) == key:
                    # Skip this line, keep the next one
                    continue
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def _adapt_response_to_schema(data: dict, model_class: type) -> dict:
    """
    Adapt parsed JSON data to match the expected schema.
    
    Handles cases where the model returns a different structure than expected,
    like objects instead of strings for list fields.
    """
    from models.schemas import CodeReview, FixedCode
    
    if model_class == CodeReview:
        # Normalize issues and suggestions to string lists
        if "issues" in data and isinstance(data["issues"], list):
            data["issues"] = _normalize_to_string_list(data["issues"])
        if "suggestions" in data and isinstance(data["suggestions"], list):
            data["suggestions"] = _normalize_to_string_list(data["suggestions"])
        
        # Ensure severity is valid
        if "severity" in data:
            severity = str(data["severity"]).lower()
            if severity not in ("low", "medium", "high"):
                data["severity"] = "medium"
            else:
                data["severity"] = severity
        
        # Ensure summary is a string
        if "summary" in data and not isinstance(data["summary"], str):
            data["summary"] = str(data["summary"])
    
    elif model_class == FixedCode:
        # Normalize changes_made to string list
        if "changes_made" in data and isinstance(data["changes_made"], list):
            data["changes_made"] = _normalize_to_string_list(data["changes_made"])
        
        # Ensure code is a string
        if "code" in data and not isinstance(data["code"], str):
            data["code"] = str(data["code"])
    
    return data


def parse_json_response(response: str, model_class: type) -> dict | None:
    """
    Parse JSON from LLM response, handling common issues across different models.
    
    Args:
        response: Raw LLM response string
        model_class: Pydantic model class for validation
        
    Returns:
        Parsed dict or None if parsing fails
    """
    # Log the raw response for debugging
    logger.info(f"=== RAW LLM RESPONSE (first 1000 chars) ===")
    logger.info(response[:1000] if len(response) > 1000 else response)
    logger.info(f"=== END RAW RESPONSE (total length: {len(response)}) ===")
    
    # Clean the response - some models add thinking tags or extra whitespace
    cleaned = response.strip()
    
    # Pre-processing: Try to fix duplicate keys
    cleaned = _fix_duplicate_keys_json(cleaned)
    
    def try_parse_and_validate(json_str: str, source: str) -> dict | None:
        """Helper to parse JSON and validate against schema with adaptation."""
        try:
            data = json.loads(json_str)
            # Adapt the data structure to match expected schema
            adapted = _adapt_response_to_schema(data, model_class)
            validated = model_class(**adapted)
            logger.info(f"✓ Parsed successfully via {source}")
            return validated.model_dump()
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode failed ({source}): {e}")
        except Exception as e:
            logger.debug(f"Validation failed ({source}): {e}")
        return None
    
    # Strategy 1: Try direct JSON parsing
    result = try_parse_and_validate(cleaned, "direct parsing")
    if result:
        return result
    
    # Strategy 2: Extract JSON from markdown code blocks
    json_patterns = [
        r'```json\s*([\s\S]*?)```',
        r'```\s*([\s\S]*?)```',
        r'`([\s\S]*?)`',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        for match in matches:
            result = try_parse_and_validate(match.strip(), f"code block ({pattern[:15]}...)")
            if result:
                return result
    
    # Strategy 3: Find JSON object by looking for { ... } structure
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        potential_json = cleaned[first_brace:last_brace + 1]
        result = try_parse_and_validate(potential_json, "brace extraction")
        if result:
            return result
    
    # Strategy 4: Handle thinking tags
    thinking_patterns = [
        r'<think>[\s\S]*?</think>',
        r'<thinking>[\s\S]*?</thinking>',
        r'<reasoning>[\s\S]*?</reasoning>',
    ]
    
    cleaned_no_thinking = cleaned
    for pattern in thinking_patterns:
        cleaned_no_thinking = re.sub(pattern, '', cleaned_no_thinking, flags=re.IGNORECASE)
    
    if cleaned_no_thinking != cleaned:
        cleaned_no_thinking = cleaned_no_thinking.strip()
        
        result = try_parse_and_validate(cleaned_no_thinking, "after removing thinking tags")
        if result:
            return result
        
        # Try brace extraction on cleaned content
        first_brace = cleaned_no_thinking.find('{')
        last_brace = cleaned_no_thinking.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            potential_json = cleaned_no_thinking[first_brace:last_brace + 1]
            result = try_parse_and_validate(potential_json, "braces after removing thinking")
            if result:
                return result
    
    # All strategies failed
    logger.error(f"✗ ALL PARSING STRATEGIES FAILED for model {model_class.__name__}")
    logger.error(f"Response started with: {response[:200]}")
    logger.error(f"Response ended with: {response[-200:] if len(response) > 200 else response}")
    return None


# =============================================================================
# GRAPH NODES
# =============================================================================

def review_node(state: AgentState) -> AgentState:
    """
    Review the submitted code and identify issues.
    
    This node:
    1. Sends code to LLM for review
    2. Parses structured CodeReview response
    3. Updates state with review results
    """
    config = get_config()
    llm = create_llm()
    
    logger.info(f"=== REVIEW NODE: Calling LLM ({config.model_name}) ===")
    
    messages = [
        SystemMessage(content=REVIEW_SYSTEM_PROMPT),
        HumanMessage(content=get_review_prompt(state["current_code"])),
    ]
    
    response = llm.invoke(messages)
    
    logger.info(f"=== REVIEW NODE: Got response, parsing... ===")
    
    # Parse the response into CodeReview
    review_data = parse_json_response(response.content, CodeReview)
    
    # Track parse failures in state for detecting stuck loops
    parse_failures = state.get("parse_failures", 0)
    
    if review_data:
        review = CodeReview(**review_data)
        logger.info(f"✓ Review parsed successfully: {review.summary[:100] if review.summary else 'no summary'}")
    else:
        # Fallback if parsing fails
        parse_failures += 1
        logger.warning(f"✗ Review parsing failed (failure #{parse_failures})")
        review = CodeReview(
            issues=["Could not parse LLM response - check logs for raw output"],
            suggestions=["The model may not be producing valid JSON. Try a different model."],
            severity="medium",
            summary=f"Review parsing failed (attempt #{parse_failures})",
        )
    
    return {
        **state,
        "review": review,
        "status": "reviewing",
        "parse_failures": parse_failures,
        "messages": state.get("messages", []) + [
            {"role": "assistant", "content": f"Review: {review.summary}"}
        ],
    }


def fix_node(state: AgentState) -> AgentState:
    """
    Generate fixed code based on review feedback or execution errors.
    
    This node:
    1. Constructs prompt with review/error context
    2. Sends to LLM for code fixing
    3. Updates state with fixed code
    """
    config = get_config()
    llm = create_llm()
    
    attempt = state.get("attempt", 0)
    parse_failures = state.get("parse_failures", 0)
    
    logger.info(f"=== FIX NODE: Calling LLM ({config.model_name}) - Attempt {attempt + 1} ===")
    
    # Build context for the fix
    review_dict = state["review"].model_dump() if state.get("review") else None
    error = state["execution_result"].error if state.get("execution_result") else None
    previous_errors = state.get("error_history", [])
    
    messages = [
        SystemMessage(content=FIX_SYSTEM_PROMPT),
        HumanMessage(content=get_fix_prompt(
            code=state["current_code"],
            review=review_dict,
            error=error,
            previous_attempts=previous_errors if previous_errors else None,
        )),
    ]
    
    response = llm.invoke(messages)
    
    logger.info(f"=== FIX NODE: Got response, parsing... ===")
    
    # Parse the response into FixedCode
    fix_data = parse_json_response(response.content, FixedCode)
    
    if fix_data:
        fixed = FixedCode(**fix_data)
        new_code = fixed.code
        logger.info(f"✓ Fix parsed successfully: {fixed.explanation[:100] if fixed.explanation else 'no explanation'}")
    else:
        # Parsing failed - increment counter and try to extract code anyway
        parse_failures += 1
        logger.warning(f"✗ Fix parsing failed (failure #{parse_failures})")
        
        # Try harder to extract code from the response
        extracted_code = _extract_code_from_response(response.content)
        
        if extracted_code and extracted_code != state["current_code"]:
            logger.info(f"✓ Extracted code from response despite JSON parse failure")
            fixed = FixedCode(
                code=extracted_code,
                explanation="Code extracted from non-JSON response",
                changes_made=["Extracted from LLM response"],
            )
            new_code = extracted_code
        else:
            logger.warning(f"✗ Could not extract code, keeping original")
            fixed = FixedCode(
                code=state["current_code"],
                explanation=f"Could not parse LLM response (failure #{parse_failures})",
                changes_made=[],
            )
            new_code = state["current_code"]
    
    # Check for excessive parse failures - this indicates a stuck loop
    max_parse_failures = config.max_retries * 2  # Allow some failures but not infinite
    if parse_failures >= max_parse_failures:
        logger.error(f"✗ Too many parse failures ({parse_failures}), marking as failed")
        return {
            **state,
            "current_code": new_code,
            "fixed_code": fixed,
            "status": "failed",  # Force exit from the loop
            "parse_failures": parse_failures,
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"Fix failed: Too many parsing errors. The model may not be producing valid JSON."}
            ],
        }
    
    return {
        **state,
        "current_code": new_code,
        "fixed_code": fixed,
        "status": "fixing",
        "parse_failures": parse_failures,
        "messages": state.get("messages", []) + [
            {"role": "assistant", "content": f"Fix: {fixed.explanation}"}
        ],
    }


def _extract_code_from_response(response: str) -> str | None:
    """
    Try to extract Python code from a response even if JSON parsing failed.
    
    This handles cases where the model outputs code in markdown blocks
    but doesn't follow the expected JSON structure.
    """
    # Try to find Python code blocks
    patterns = [
        r'```python\s*([\s\S]*?)```',
        r'```py\s*([\s\S]*?)```',
        r'```\s*([\s\S]*?)```',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            code = match.strip()
            # Basic validation - should look like Python code
            if code and (
                'def ' in code or
                'class ' in code or
                'import ' in code or
                'print(' in code or
                '=' in code
            ):
                logger.info(f"Extracted code block ({len(code)} chars)")
                return code
    
    # Try to find code in a "code" field even if overall JSON is malformed
    code_field_match = re.search(r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"|\'code\'\s*:\s*\'((?:[^\'\\]|\\.)*)\'', response)
    if code_field_match:
        code = code_field_match.group(1) or code_field_match.group(2)
        if code:
            # Unescape the string
            try:
                code = code.encode().decode('unicode_escape')
                logger.info(f"Extracted code from 'code' field ({len(code)} chars)")
                return code
            except Exception:
                pass
    
    return None


def execute_node(state: AgentState) -> AgentState:
    """
    Execute the current code in a sandboxed environment.
    
    This node:
    1. Runs code through the safe executor
    2. Captures execution results
    3. Updates state with results
    """
    result = execute_code_safely(state["current_code"])
    
    # Track error history for context in retries
    error_history = state.get("error_history", [])
    if not result.success and result.error:
        error_history = error_history + [result.error]
    
    return {
        **state,
        "execution_result": result,
        "error_history": error_history,
        "status": "executing",
    }


def evaluate_node(state: AgentState) -> AgentState:
    """
    Evaluate execution results and determine next action.
    
    This node:
    1. Checks if execution was successful
    2. Updates attempt counter
    3. Sets final status
    """
    config = get_config()
    result = state.get("execution_result")
    attempt = state.get("attempt", 0)
    parse_failures = state.get("parse_failures", 0)
    
    logger.info(f"=== EVALUATE NODE ===")
    logger.info(f"Attempt: {attempt + 1}/{config.max_retries}")
    logger.info(f"Parse failures so far: {parse_failures}")
    logger.info(f"Execution success: {result.success if result else 'N/A'}")
    
    if result and result.success:
        logger.info(f"✓ Execution successful, ending workflow")
        return {
            **state,
            "status": "success",
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"✅ Code executed successfully! Output: {result.output}"}
            ],
        }
    
    # Execution failed
    new_attempt = attempt + 1
    
    # Check if we're in a stuck loop (parse failures but no progress)
    if parse_failures > 0 and new_attempt > 1:
        # Check if code hasn't changed - indicates we're stuck
        if state.get("current_code") == state.get("original_code"):
            logger.warning(f"✗ Detected stuck loop: code unchanged after {new_attempt} attempts with {parse_failures} parse failures")
            return {
                **state,
                "attempt": new_attempt,
                "status": "failed",
                "messages": state.get("messages", []) + [
                    {"role": "assistant", "content": f"❌ Stuck loop detected: LLM responses could not be parsed. Try a different model or check the logs."}
                ],
            }
    
    if new_attempt >= config.max_retries:
        logger.info(f"✗ Max retries reached ({config.max_retries}), marking as failed")
        return {
            **state,
            "attempt": new_attempt,
            "status": "failed",
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"❌ Max retries ({config.max_retries}) reached. Last error: {result.error if result else 'Unknown'}"}
            ],
        }
    
    logger.info(f"→ Will retry (attempt {new_attempt + 1})")
    return {
        **state,
        "attempt": new_attempt,
        "status": "fixing",  # Will trigger retry
    }


# =============================================================================
# GRAPH EDGES (Routing Logic)
# =============================================================================

def should_continue(state: AgentState) -> Literal["fix", "end"]:
    """
    Determine whether to retry fixing or end the workflow.
    
    Returns:
        "fix" to retry, "end" to finish
    """
    status = state.get("status", "")
    
    if status in ("success", "failed"):
        return "end"
    
    return "fix"


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph state machine for code review and fix.
    
    Graph structure:
        START → review → fix → execute → evaluate
                                  ↑          ↓
                                  └── retry ←┘
                                             ↓
                                            END
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("review", review_node)
    workflow.add_node("fix", fix_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("evaluate", evaluate_node)
    
    # Set entry point
    workflow.set_entry_point("review")
    
    # Add edges for the main flow
    workflow.add_edge("review", "fix")
    workflow.add_edge("fix", "execute")
    workflow.add_edge("execute", "evaluate")
    
    # Add conditional edge for retry logic
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "fix": "fix",  # Retry: go back to fix
            "end": END,    # Done: end workflow
        }
    )
    
    return workflow.compile()


def run_agent(code: str) -> AgentState:
    """
    Run the code review and fix agent on the given code.
    
    This is the main entry point for using the agent.
    
    Args:
        code: Python source code to review and fix
        
    Returns:
        Final AgentState with review, fixed code, and execution results
        
    Example:
        result = run_agent("print('Hello World')")
        if result["status"] == "success":
            print("Code works!")
            print(result["execution_result"].output)
        else:
            print("Failed to fix code")
            print(result["error_history"])
    """
    # Create the graph
    graph = create_agent_graph()
    
    # Initialize state
    initial_state: AgentState = {
        "original_code": code,
        "current_code": code,
        "review": None,
        "fixed_code": None,
        "execution_result": None,
        "attempt": 0,
        "messages": [{"role": "user", "content": f"Please review and fix this code:\n```python\n{code}\n```"}],
        "error_history": [],
        "status": "reviewing",
        "parse_failures": 0,
    }
    
    logger.info(f"=== STARTING AGENT RUN ===")
    logger.info(f"Code length: {len(code)} chars")
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    logger.info(f"=== AGENT RUN COMPLETE ===")
    logger.info(f"Final status: {final_state.get('status')}")
    logger.info(f"Total parse failures: {final_state.get('parse_failures', 0)}")
    logger.info(f"Total attempts: {final_state.get('attempt', 0)}")
    
    return final_state


def run_agent_stream(code: str):
    """
    Run the agent with streaming, yielding state updates.
    
    Useful for showing progress in the UI.
    
    Args:
        code: Python source code to review and fix
        
    Yields:
        AgentState updates after each node execution
    """
    graph = create_agent_graph()
    
    initial_state: AgentState = {
        "original_code": code,
        "current_code": code,
        "review": None,
        "fixed_code": None,
        "execution_result": None,
        "attempt": 0,
        "messages": [{"role": "user", "content": f"Please review and fix this code:\n```python\n{code}\n```"}],
        "error_history": [],
        "status": "reviewing",
        "parse_failures": 0,
    }
    
    logger.info(f"=== STARTING AGENT STREAM ===")
    
    # Stream through the graph
    for state_update in graph.stream(initial_state):
        yield state_update
