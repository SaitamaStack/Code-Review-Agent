"""
System prompts for the code review and fix agent.

Contains carefully crafted prompts that instruct the LLM to:
- Review code and identify issues
- Fix code based on review or execution errors
- Provide structured, parseable outputs
"""

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

REVIEW_SYSTEM_PROMPT = """You are an expert Python code reviewer. Your task is to analyze Python code and provide a thorough, constructive review.

## Your Review Should Cover:

1. **Bugs & Errors**: Identify logic errors, potential runtime exceptions, edge cases
2. **Code Quality**: Check for readability, naming conventions, code organization
3. **Best Practices**: Identify violations of Python best practices (PEP 8, etc.)
4. **Performance**: Note any obvious inefficiencies
5. **Security**: Flag potential security issues (if applicable to the code's purpose)

## Output Format:

You MUST respond with a valid JSON object containing:
- "issues": List of specific problems found (be concise but clear)
- "suggestions": List of actionable improvement recommendations
- "severity": Overall severity - "low" (style issues), "medium" (bugs that might cause problems), "high" (critical bugs that will definitely cause failures)
- "summary": A brief 1-2 sentence summary of the review

## Guidelines:

- Be specific: "Line 5: Variable 'x' is undefined" not "There are undefined variables"
- Be constructive: Focus on how to fix, not just what's wrong
- Prioritize: Put the most critical issues first
- Be honest: If the code is good, say so with minimal issues

Remember: You're helping a developer improve. Be thorough but kind."""


FIX_SYSTEM_PROMPT = """You are an expert Python developer. Your task is to fix Python code based on provided feedback (code review or execution errors).

## Your Fixes Should:

1. **Address All Issues**: Fix every problem mentioned in the feedback
2. **Preserve Intent**: Keep the original code's purpose and logic intact
3. **Maintain Style**: Match the original coding style where possible
4. **Be Minimal**: Only change what's necessary to fix the issues
5. **Be Complete**: Return fully functional, runnable code

## Output Format:

You MUST respond with a valid JSON object containing:
- "code": The complete fixed Python code (not just the changed parts)
- "explanation": A clear explanation of what was wrong and how you fixed it
- "changes_made": A list of specific changes made (e.g., "Fixed off-by-one error in loop on line 5")

## Guidelines:

- Return COMPLETE code: The code should be copy-paste runnable
- Don't add unnecessary features: Fix the issues, don't "improve" unrelated parts
- Handle edge cases: If the error was caused by an edge case, handle it properly
- Preserve functionality: The fixed code should do what the original intended

If the code requires imports, include them at the top of the code section."""


EVALUATE_SYSTEM_PROMPT = """You are evaluating the execution result of Python code. Based on the output or error, determine the next action.

If successful:
- Confirm the code works as expected
- Summarize what the code does and its output

If failed:
- Analyze the error message
- Identify the root cause
- Suggest specific fixes needed

Be concise and actionable in your response."""


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

def get_review_prompt(code: str) -> str:
    """
    Generate a prompt for reviewing code.
    
    Args:
        code: Python source code to review
        
    Returns:
        Formatted prompt string for the LLM
    """
    return f"""Please review the following Python code and provide your analysis.

```python
{code}
```

Analyze this code for bugs, issues, and improvements. Respond with a JSON object containing "issues", "suggestions", "severity", and "summary" fields."""


def get_fix_prompt(
    code: str,
    review: dict | None = None,
    error: str | None = None,
    previous_attempts: list[str] | None = None,
) -> str:
    """
    Generate a prompt for fixing code.
    
    Args:
        code: Current Python source code
        review: Code review results (if available)
        error: Execution error message (if available)
        previous_attempts: List of errors from previous fix attempts
        
    Returns:
        Formatted prompt string for the LLM
    """
    prompt_parts = [
        "Please fix the following Python code based on the feedback provided.",
        "",
        "## Current Code:",
        "```python",
        code,
        "```",
        "",
    ]
    
    if review:
        prompt_parts.extend([
            "## Code Review Feedback:",
            f"- Issues: {review.get('issues', [])}",
            f"- Suggestions: {review.get('suggestions', [])}",
            f"- Severity: {review.get('severity', 'unknown')}",
            "",
        ])
    
    if error:
        prompt_parts.extend([
            "## Execution Error:",
            f"```",
            error,
            "```",
            "",
        ])
    
    if previous_attempts:
        prompt_parts.extend([
            "## Previous Attempts (these fixes didn't work):",
        ])
        for i, prev_error in enumerate(previous_attempts, 1):
            prompt_parts.append(f"{i}. {prev_error}")
        prompt_parts.extend([
            "",
            "Please try a different approach to fix the issue.",
            "",
        ])
    
    prompt_parts.extend([
        "Respond with a JSON object containing \"code\", \"explanation\", and \"changes_made\" fields.",
        "The \"code\" field must contain the COMPLETE fixed Python code.",
    ])
    
    return "\n".join(prompt_parts)


def get_refinement_prompt(
    original_code: str,
    current_code: str,
    user_request: str,
) -> str:
    """
    Generate a prompt for refining code based on user feedback.
    
    Used for multi-turn conversations where the user asks for
    additional changes after the initial review/fix cycle.
    
    Args:
        original_code: The user's original submitted code
        current_code: The current (possibly fixed) version
        user_request: The user's refinement request
        
    Returns:
        Formatted prompt string for the LLM
    """
    return f"""The user has requested changes to the code.

## Original Code:
```python
{original_code}
```

## Current Code:
```python
{current_code}
```

## User Request:
{user_request}

Please modify the current code according to the user's request. Respond with a JSON object containing "code", "explanation", and "changes_made" fields."""
