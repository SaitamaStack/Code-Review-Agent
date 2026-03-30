"""
LangGraph state machine for the two-pass code review agent.

Implements the following workflow:
    START → broad_review → verification → END

broad_review: exhaustive general-purpose Python code audit
verification: targeted second pass for categories LLMs commonly miss
              (hardcoded credentials, bare except, O(n²) patterns,
               weak password hashing, timing attacks)

The verification node merges its findings into the broad review's output,
so the final state.review contains the combined results of both passes.
"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from agents.prompts import (
    REVIEW_SYSTEM_PROMPT,
    VERIFICATION_SYSTEM_PROMPT,
    get_review_prompt,
    get_verification_prompt,
)
from config import get_config
from models.schemas import AgentState, CodeReview

# Configure logging for debugging LLM responses
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_llm() -> ChatOllama:
    """
    Create and configure the Ollama LLM instance.

    Returns:
        ChatOllama: Configured LLM for code review tasks
    """
    config = get_config()
    return ChatOllama(
        model=config.model_name,
        base_url=config.ollama_base_url,
        temperature=config.temperature,
        format="json",  # Request JSON output
        timeout=180,  # 3 minute timeout for thorough analysis
        num_ctx=6144,  # 6K context window - optimal balance for code analysis
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

    lines = json_str.split("\n")
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

    return "\n".join(result_lines)


def _adapt_response_to_schema(data: dict, model_class: type) -> dict:
    """
    Adapt parsed JSON data to match the expected schema.

    Handles cases where the model returns a different structure than expected,
    like objects instead of strings for list fields.
    """
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
        r"```json\s*([\s\S]*?)```",
        r"```\s*([\s\S]*?)```",
        r"`([\s\S]*?)`",
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        for match in matches:
            result = try_parse_and_validate(
                match.strip(), f"code block ({pattern[:15]}...)"
            )
            if result:
                return result

    # Strategy 3: Find JSON object by looking for { ... } structure
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        potential_json = cleaned[first_brace : last_brace + 1]
        result = try_parse_and_validate(potential_json, "brace extraction")
        if result:
            return result

    # Strategy 4: Handle thinking tags
    thinking_patterns = [
        r"<think>[\s\S]*?</think>",
        r"<thinking>[\s\S]*?</thinking>",
        r"<reasoning>[\s\S]*?</reasoning>",
    ]

    cleaned_no_thinking = cleaned
    for pattern in thinking_patterns:
        cleaned_no_thinking = re.sub(
            pattern, "", cleaned_no_thinking, flags=re.IGNORECASE
        )

    if cleaned_no_thinking != cleaned:
        cleaned_no_thinking = cleaned_no_thinking.strip()

        result = try_parse_and_validate(
            cleaned_no_thinking, "after removing thinking tags"
        )
        if result:
            return result

        # Try brace extraction on cleaned content
        first_brace = cleaned_no_thinking.find("{")
        last_brace = cleaned_no_thinking.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            potential_json = cleaned_no_thinking[first_brace : last_brace + 1]
            result = try_parse_and_validate(
                potential_json, "braces after removing thinking"
            )
            if result:
                return result

    # All strategies failed
    logger.error(f"✗ ALL PARSING STRATEGIES FAILED for model {model_class.__name__}")
    logger.error(f"Response started with: {response[:200]}")
    logger.error(
        f"Response ended with: {response[-200:] if len(response) > 200 else response}"
    )
    return None


# =============================================================================
# GRAPH NODES
# =============================================================================


def broad_review_node(state: AgentState) -> AgentState:
    """
    First pass: exhaustive general-purpose code review.

    Sends the code to the LLM with a broad audit prompt covering all standard
    bug categories. Sets the baseline review that the verification node will
    then supplement with targeted checks.
    """
    config = get_config()
    llm = create_llm()

    logger.info(f"=== BROAD REVIEW NODE: Calling LLM ({config.model_name}) ===")

    messages = [
        SystemMessage(content=REVIEW_SYSTEM_PROMPT),
        HumanMessage(content=get_review_prompt(state["current_code"])),
    ]

    response = llm.invoke(messages)

    logger.info("=== BROAD REVIEW NODE: Got response, parsing... ===")

    review_data = parse_json_response(response.content, CodeReview)

    parse_failures = state.get("parse_failures", 0)

    if review_data:
        review = CodeReview(**review_data)
        logger.info(
            f"✓ Broad review parsed: {len(review.issues)} issue(s) — "
            f"{review.summary[:80] if review.summary else 'no summary'}"
        )
    else:
        parse_failures += 1
        logger.warning(f"✗ Broad review parsing failed (failure #{parse_failures})")
        review = CodeReview(
            issues=["Could not parse LLM response - check logs for raw output"],
            suggestions=[
                "The model may not be producing valid JSON. Try a different model."
            ],
            severity="medium",
            summary=f"Broad review parsing failed (attempt #{parse_failures})",
        )

    return {
        **state,
        "review": review,
        "status": "reviewing",
        "parse_failures": parse_failures,
        "messages": state.get("messages", [])
        + [{"role": "assistant", "content": f"Broad review: {review.summary}"}],
    }


def verification_node(state: AgentState) -> AgentState:
    """
    Second pass: targeted hunt for issues LLMs most commonly miss.

    Receives the broad review's findings and checks specifically for:
    - Hardcoded credentials
    - Bare except clauses
    - O(n²) string concatenation patterns
    - Wrong password hashing algorithms (MD5/SHA1/SHA256)
    - Timing attacks via non-constant-time comparisons

    Merges any new findings into the existing review so state.review
    reflects the complete picture from both passes.
    """
    config = get_config()
    llm = create_llm()

    prior_review = state["review"]

    logger.info(
        f"=== VERIFICATION NODE: Calling LLM ({config.model_name}) — "
        f"prior review has {len(prior_review.issues)} issue(s) ==="
    )

    messages = [
        SystemMessage(content=VERIFICATION_SYSTEM_PROMPT),
        HumanMessage(
            content=get_verification_prompt(state["current_code"], prior_review)
        ),
    ]

    response = llm.invoke(messages)

    logger.info("=== VERIFICATION NODE: Got response, parsing... ===")

    verification_data = parse_json_response(response.content, CodeReview)
    parse_failures = state.get("parse_failures", 0)

    if not verification_data:
        parse_failures += 1
        logger.warning(
            f"✗ Verification parsing failed (failure #{parse_failures}). "
            f"Using broad review only."
        )
        return {
            **state,
            "status": "success",
            "parse_failures": parse_failures,
            "messages": state.get("messages", [])
            + [
                {
                    "role": "assistant",
                    "content": "Verification pass: could not parse response, using broad review only.",
                }
            ],
        }

    verification = CodeReview(**verification_data)
    logger.info(
        f"✓ Verification parsed: {len(verification.issues)} additional issue(s) found"
    )

    # Merge verification findings into the prior review.
    # Dedup by checking if the new issue text is a substring of any existing issue
    # (catches rephrased duplicates as well as exact matches).
    existing_lower = "\n".join(prior_review.issues).lower()
    new_issues = [
        issue for issue in verification.issues if issue.lower() not in existing_lower
    ]
    new_suggestions = [
        s for s in verification.suggestions if s not in prior_review.suggestions
    ]

    merged_issues = prior_review.issues + new_issues
    merged_suggestions = prior_review.suggestions + new_suggestions

    # Take the higher of the two severity ratings
    severity_rank = {"low": 0, "medium": 1, "high": 2}
    merged_severity = max(
        prior_review.severity,
        verification.severity,
        key=lambda s: severity_rank.get(s, 0),
    )

    new_count = len(new_issues)
    verification_note = (
        f" Verification pass added {new_count} additional issue(s)."
        if new_count > 0
        else " Verification pass confirmed no additional issues."
    )

    merged_review = CodeReview(
        issues=merged_issues,
        suggestions=merged_suggestions,
        severity=merged_severity,
        summary=prior_review.summary + verification_note,
    )

    logger.info(
        f"✓ Merged review: {len(merged_issues)} total issue(s) "
        f"({new_count} new from verification)"
    )

    return {
        **state,
        "review": merged_review,
        "status": "success",
        "parse_failures": parse_failures,
        "messages": state.get("messages", [])
        + [
            {
                "role": "assistant",
                "content": (
                    f"Verification: {new_count} additional issue(s) found. "
                    f"Total: {len(merged_issues)} issue(s)."
                ),
            }
        ],
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph state machine for two-pass code review.

    Graph structure:
        START → broad_review → verification → END

    Returns:
        Compiled StateGraph ready for execution
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("broad_review", broad_review_node)
    workflow.add_node("verification", verification_node)

    # Set entry point and edges
    workflow.set_entry_point("broad_review")
    workflow.add_edge("broad_review", "verification")
    workflow.add_edge("verification", END)

    return workflow.compile()


def run_agent(code: str) -> AgentState:
    """
    Run the two-pass code review agent on the given code.

    This is the main entry point for using the agent.

    Args:
        code: Python source code to review

    Returns:
        Final AgentState with the merged review from both passes

    Example:
        result = run_agent("def foo(items=[]): pass")
        if result["status"] == "success":
            review = result["review"]
            for issue in review.issues:
                print(issue)
    """
    graph = create_agent_graph()

    initial_state: AgentState = {
        "original_code": code,
        "current_code": code,
        "review": None,
        "messages": [
            {
                "role": "user",
                "content": f"Please review this code:\n```python\n{code}\n```",
            }
        ],
        "status": "reviewing",
        "parse_failures": 0,
    }

    logger.info("=== STARTING AGENT RUN ===")
    logger.info(f"Code length: {len(code)} chars")

    final_state = graph.invoke(initial_state)

    logger.info("=== AGENT RUN COMPLETE ===")
    logger.info(f"Final status: {final_state.get('status')}")
    logger.info(f"Total parse failures: {final_state.get('parse_failures', 0)}")

    return final_state
