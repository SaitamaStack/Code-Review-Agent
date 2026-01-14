"""
Reusable Streamlit UI components for the code review agent.

This module provides consistent, styled components for:
- Code display with syntax highlighting
- Review results visualization
- Execution output formatting
- Diff view between original and fixed code
"""

import streamlit as st
from models.schemas import CodeReview, ExecutionResult, FixedCode


def display_code(
    code: str,
    title: str = "Code",
    language: str = "python",
    show_line_numbers: bool = True,
) -> None:
    """
    Display code with syntax highlighting and optional title.
    
    Args:
        code: Source code to display
        title: Header text above the code block
        language: Language for syntax highlighting
        show_line_numbers: Whether to show line numbers
    """
    if title:
        st.subheader(title)
    
    # Add line numbers if requested
    if show_line_numbers and code:
        lines = code.split('\n')
        numbered_code = '\n'.join(
            f"{i+1:3d} | {line}" 
            for i, line in enumerate(lines)
        )
        st.code(numbered_code, language=language)
    else:
        st.code(code, language=language)


def display_review(review: CodeReview | dict | None) -> None:
    """
    Display code review results in a structured, readable format.
    
    Args:
        review: CodeReview object or dict with review data
    """
    if review is None:
        st.info("No review available yet.")
        return
    
    # Convert to dict if it's a Pydantic model
    if hasattr(review, 'model_dump'):
        review = review.model_dump()
    
    st.subheader("📋 Code Review")
    
    # Severity badge
    severity = review.get("severity", "unknown")
    severity_colors = {
        "low": "🟢",
        "medium": "🟡", 
        "high": "🔴",
    }
    severity_emoji = severity_colors.get(severity, "⚪")
    st.markdown(f"**Severity:** {severity_emoji} {severity.upper()}")
    
    # Summary
    if review.get("summary"):
        st.markdown(f"**Summary:** {review['summary']}")
    
    # Issues
    issues = review.get("issues", [])
    if issues:
        st.markdown("**Issues Found:**")
        for issue in issues:
            st.markdown(f"- ❌ {issue}")
    else:
        st.success("No issues found!")
    
    # Suggestions
    suggestions = review.get("suggestions", [])
    if suggestions:
        st.markdown("**Suggestions:**")
        for suggestion in suggestions:
            st.markdown(f"- 💡 {suggestion}")


def display_execution_result(result: ExecutionResult | dict | None) -> None:
    """
    Display execution results with appropriate styling.
    
    Args:
        result: ExecutionResult object or dict with execution data
    """
    if result is None:
        st.info("Code has not been executed yet.")
        return
    
    # Convert to dict if it's a Pydantic model
    if hasattr(result, 'model_dump'):
        result = result.model_dump()
    
    st.subheader("🚀 Execution Result")
    
    success = result.get("success", False)
    
    if success:
        st.success("✅ Code executed successfully!")
        
        output = result.get("output")
        if output:
            st.markdown("**Output:**")
            st.code(output, language="text")
        else:
            st.info("Code completed with no output.")
    else:
        st.error("❌ Execution failed!")
        
        error = result.get("error")
        if error:
            st.markdown("**Error:**")
            st.code(error, language="text")
    
    # Execution time
    exec_time = result.get("execution_time", 0)
    if exec_time > 0:
        st.caption(f"⏱️ Execution time: {exec_time:.3f}s")
    
    # Blocked import warning
    if result.get("blocked_import_detected"):
        st.warning("⚠️ Blocked import detected - code was not executed for security reasons.")


def display_diff(
    original: str,
    fixed: str,
    title: str = "Changes Made",
) -> None:
    """
    Display a side-by-side or inline diff between original and fixed code.
    
    Args:
        original: Original source code
        fixed: Fixed source code
        title: Header text for the diff section
    """
    st.subheader(f"🔄 {title}")
    
    if original == fixed:
        st.info("No changes were made to the code.")
        return
    
    # Use columns for side-by-side comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Original Code:**")
        st.code(original, language="python")
    
    with col2:
        st.markdown("**Fixed Code:**")
        st.code(fixed, language="python")
    
    # Simple line-by-line diff
    original_lines = original.split('\n')
    fixed_lines = fixed.split('\n')
    
    # Show changes summary
    changes = []
    max_lines = max(len(original_lines), len(fixed_lines))
    
    for i in range(max_lines):
        orig = original_lines[i] if i < len(original_lines) else ""
        fix = fixed_lines[i] if i < len(fixed_lines) else ""
        
        if orig != fix:
            if i >= len(original_lines):
                changes.append(f"Line {i+1}: Added `{fix[:50]}...`" if len(fix) > 50 else f"Line {i+1}: Added `{fix}`")
            elif i >= len(fixed_lines):
                changes.append(f"Line {i+1}: Removed")
            else:
                changes.append(f"Line {i+1}: Modified")
    
    if changes:
        with st.expander("View change summary"):
            for change in changes[:20]:  # Limit to first 20 changes
                st.text(change)
            if len(changes) > 20:
                st.text(f"... and {len(changes) - 20} more changes")


def display_fixed_code(fixed: FixedCode | dict | None) -> None:
    """
    Display the fixed code with explanation and changes.
    
    Args:
        fixed: FixedCode object or dict with fix data
    """
    if fixed is None:
        st.info("No fixes applied yet.")
        return
    
    # Convert to dict if it's a Pydantic model
    if hasattr(fixed, 'model_dump'):
        fixed = fixed.model_dump()
    
    st.subheader("🔧 Fixed Code")
    
    # Explanation
    explanation = fixed.get("explanation", "")
    if explanation:
        st.markdown(f"**Explanation:** {explanation}")
    
    # Changes made
    changes = fixed.get("changes_made", [])
    if changes:
        st.markdown("**Changes Made:**")
        for change in changes:
            st.markdown(f"- ✏️ {change}")
    
    # The fixed code
    code = fixed.get("code", "")
    if code:
        st.code(code, language="python")


def display_agent_progress(
    current_step: str,
    attempt: int,
    max_attempts: int,
) -> None:
    """
    Display the current agent progress and retry status.
    
    Args:
        current_step: Name of the current step (review, fix, execute, etc.)
        attempt: Current attempt number
        max_attempts: Maximum allowed attempts
    """
    steps = ["review", "fix", "execute", "evaluate"]
    
    # Progress indicator
    if current_step in steps:
        progress = (steps.index(current_step) + 1) / len(steps)
    else:
        progress = 1.0
    
    st.progress(progress, text=f"Step: {current_step.capitalize()}")
    
    # Attempt counter
    if attempt > 0:
        st.caption(f"🔄 Attempt {attempt} of {max_attempts}")


def code_input_area(
    key: str = "code_input",
    default_code: str = "",
    height: int = 300,
) -> str:
    """
    Create a code input area with helpful placeholder.
    
    Args:
        key: Unique key for the Streamlit widget
        default_code: Default code to show in the input
        height: Height of the text area in pixels
        
    Returns:
        The code entered by the user
    """
    placeholder = '''# Enter your Python code here
# Example:
def greet(name):
    print(f"Hello, {name}!")

greet("World")
'''
    
    code = st.text_area(
        "Enter Python Code",
        value=default_code or placeholder,
        height=height,
        key=key,
        help="Paste or type your Python code here. The agent will review, fix, and execute it.",
    )
    
    return code


def display_chat_message(
    role: str,
    content: str,
    avatar: str | None = None,
) -> None:
    """
    Display a chat message in the conversation.
    
    Args:
        role: 'user' or 'assistant'
        content: Message content
        avatar: Optional avatar emoji/image
    """
    if avatar is None:
        avatar = "👤" if role == "user" else "🤖"
    
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def display_status_badge(status: str) -> None:
    """
    Display a status badge for the current workflow state.
    
    Args:
        status: Current status (reviewing, fixing, executing, success, failed)
    """
    badges = {
        "reviewing": ("🔍", "Reviewing...", "info"),
        "fixing": ("🔧", "Fixing...", "info"),
        "executing": ("🚀", "Executing...", "info"),
        "success": ("✅", "Success!", "success"),
        "failed": ("❌", "Failed", "error"),
    }
    
    emoji, text, msg_type = badges.get(status, ("⏳", status, "info"))
    
    if msg_type == "success":
        st.success(f"{emoji} {text}")
    elif msg_type == "error":
        st.error(f"{emoji} {text}")
    else:
        st.info(f"{emoji} {text}")
