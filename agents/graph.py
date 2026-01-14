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


def parse_json_response(response: str, model_class: type) -> dict | None:
    """
    Parse JSON from LLM response, handling common issues.
    
    Args:
        response: Raw LLM response string
        model_class: Pydantic model class for validation
        
    Returns:
        Parsed dict or None if parsing fails
    """
    try:
        # Try direct JSON parsing
        data = json.loads(response)
        # Validate with Pydantic
        validated = model_class(**data)
        return validated.model_dump()
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                validated = model_class(**data)
                return validated.model_dump()
            except (json.JSONDecodeError, Exception):
                pass
    except Exception:
        pass
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
    llm = create_llm()
    
    messages = [
        SystemMessage(content=REVIEW_SYSTEM_PROMPT),
        HumanMessage(content=get_review_prompt(state["current_code"])),
    ]
    
    response = llm.invoke(messages)
    
    # Parse the response into CodeReview
    review_data = parse_json_response(response.content, CodeReview)
    
    if review_data:
        review = CodeReview(**review_data)
    else:
        # Fallback if parsing fails
        review = CodeReview(
            issues=["Could not parse LLM response"],
            suggestions=["Please try again"],
            severity="medium",
            summary="Review parsing failed",
        )
    
    return {
        **state,
        "review": review,
        "status": "reviewing",
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
    llm = create_llm()
    
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
    
    # Parse the response into FixedCode
    fix_data = parse_json_response(response.content, FixedCode)
    
    if fix_data:
        fixed = FixedCode(**fix_data)
        new_code = fixed.code
    else:
        # Fallback: try to extract code from response
        fixed = FixedCode(
            code=state["current_code"],
            explanation="Could not parse LLM response",
            changes_made=[],
        )
        new_code = state["current_code"]
    
    return {
        **state,
        "current_code": new_code,
        "fixed_code": fixed,
        "status": "fixing",
        "messages": state.get("messages", []) + [
            {"role": "assistant", "content": f"Fix: {fixed.explanation}"}
        ],
    }


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
    
    if result and result.success:
        return {
            **state,
            "status": "success",
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"✅ Code executed successfully! Output: {result.output}"}
            ],
        }
    
    # Execution failed
    new_attempt = attempt + 1
    
    if new_attempt >= config.max_retries:
        return {
            **state,
            "attempt": new_attempt,
            "status": "failed",
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"❌ Max retries ({config.max_retries}) reached. Last error: {result.error if result else 'Unknown'}"}
            ],
        }
    
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
    }
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
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
    }
    
    # Stream through the graph
    for state_update in graph.stream(initial_state):
        yield state_update
