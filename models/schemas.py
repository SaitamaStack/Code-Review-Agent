"""
Pydantic models for structured LLM outputs and agent state.

These schemas ensure the LLM returns well-formed, validated responses
that can be reliably processed by the agent pipeline.
"""

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class CodeReview(BaseModel):
    """
    Structured output from the code review step.

    The LLM analyzes submitted code and returns this structured review
    containing identified issues, improvement suggestions, and severity.
    Used by both the broad review pass and the verification pass.
    """

    issues: list[str] = Field(
        default_factory=list,
        description="List of identified problems, bugs, or anti-patterns in the code",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations to improve the code",
    )
    severity: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Overall severity of issues found (low=minor style issues, high=critical bugs)",
    )
    summary: str = Field(
        default="", description="Brief summary of the code review findings"
    )


class ExecutionResult(BaseModel):
    """
    Result of executing Python code in the sandbox.

    Captures success/failure status along with stdout/stderr
    for display and error analysis. Used by the Execute Only path.
    """

    success: bool = Field(description="Whether the code executed without errors")
    output: str | None = Field(
        default=None, description="Standard output from code execution (stdout)"
    )
    error: str | None = Field(
        default=None,
        description="Error message if execution failed (stderr or exception)",
    )
    execution_time: float = Field(
        default=0.0, description="Time taken to execute the code in seconds"
    )
    blocked_import_detected: bool = Field(
        default=False,
        description="Whether a blocked import was detected before execution",
    )


class AgentState(TypedDict, total=False):
    """
    State schema for the LangGraph agent state machine.

    This TypedDict defines all state variables passed between
    nodes in the two-pass review graph.

    Attributes:
        original_code: The user's original submitted code (immutable)
        current_code: The current version of code being reviewed
        review: Accumulated review results (merged after both passes)
        messages: Chat history for the agent run
        status: Current status of the agent workflow
        parse_failures: Count of LLM response parse failures across both passes
    """

    original_code: str
    current_code: str
    review: CodeReview | None
    messages: list[dict]
    status: Literal["reviewing", "verifying", "success", "failed"]
    parse_failures: int
