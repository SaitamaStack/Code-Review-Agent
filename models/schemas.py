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


class FixedCode(BaseModel):
    """
    Structured output from the code fixing step.

    Contains the corrected code along with explanations of what
    was changed and why, enabling transparency in the fix process.
    """

    code: str = Field(description="The corrected Python code")
    explanation: str = Field(
        default="", description="Human-readable explanation of the fixes applied"
    )
    changes_made: list[str] = Field(
        default_factory=list,
        description="List of specific changes made to the original code",
    )


class PatchResult(BaseModel):
    """
    A surgical line-range patch returned by the fix LLM.

    Instead of rewriting the entire file, the model specifies only which
    lines to replace and what to replace them with, limiting the blast
    radius of any single fix to the lines actually involved.
    """

    line_start: int = Field(description="1-indexed first line to replace (inclusive)")
    line_end: int = Field(description="1-indexed last line to replace (inclusive)")
    replacement: str = Field(
        description="New code to insert in place of line_start through line_end"
    )
    explanation: str = Field(
        default="", description="Brief description of the fix applied"
    )


class ExecutionResult(BaseModel):
    """
    Result of executing Python code in the sandbox.

    Captures success/failure status along with stdout/stderr
    for display and error analysis.
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
    nodes in the agent graph during the review-fix-execute cycle.

    Attributes:
        original_code: The user's original submitted code (immutable)
        current_code: The current version of code (updated after fixes)
        review: Latest code review results
        execution_result: Result from most recent execution attempt
        attempt: Current retry attempt number (starts at 0)
        messages: Chat history for multi-turn conversations
        error_history: List of errors from previous attempts (for context)
        status: Current status of the agent workflow
        parse_failures: Count of consecutive LLM response parse failures
        current_issue_index: Which issue in review.issues is currently being fixed
        patch_retry_count: Retry counter for patch failures per issue
        rejected_patches: Rejection messages from failed patch attempts
        fix_results: Success or failure record accumulated for each processed issue
    """

    original_code: str
    current_code: str
    review: CodeReview | None
    fixed_code: FixedCode | None
    execution_result: ExecutionResult | None
    attempt: int
    messages: list[dict]
    error_history: list[str]
    status: Literal["reviewing", "fixing", "executing", "success", "failed"]
    parse_failures: int
    current_issue_index: int
    patch_retry_count: int
    rejected_patches: list[str]
    fix_results: list[dict]
