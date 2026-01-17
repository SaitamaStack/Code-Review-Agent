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

REVIEW_SYSTEM_PROMPT = """You are a security-focused Python code auditor. Find BUGS that will CRASH the program or create SECURITY VULNERABILITIES.

ANALYZE LINE BY LINE. For each function ask:
1. What if the input is EMPTY? (empty list, empty string, None)
2. What if a number is ZERO? (division by zero)
3. Does it use dangerous functions like eval() or exec()?
4. Are all variables defined before use?

## CRITICAL ISSUES TO FIND:

### SECURITY (always severity: high)
- eval() or exec() = CRITICAL SECURITY RISK, always flag
- os.system(), subprocess with shell=True = command injection
- SQL with string formatting = SQL injection
- pickle.load() from untrusted source = code execution

### CRASH BUGS (severity: high)
- list[0] without checking empty = IndexError
- dict[key] without key check = KeyError  
- x / y without y != 0 check = ZeroDivisionError
- obj.method without None check = AttributeError
- int(string) without try/except = ValueError

### UNDEFINED VARIABLES (severity: high)
- Variable used before assignment
- Variable only defined in one if/else branch
- Typos in variable names

### LOGIC ERRORS (severity: medium)
- Off-by-one in loops (< vs <=)
- Wrong operators (< vs >, = vs ==)
- Dead code (functions never called)
- Files opened without closing

## OUTPUT FORMAT

Respond with JSON only:
{"issues": ["Line N: description"], "suggestions": ["fix"], "severity": "high", "summary": "text"}

RULES:
- Include line numbers: "Line 15: IndexError - words[0] on empty list"
- Security issues go FIRST
- Crash bugs go SECOND
- If eval/exec found, severity MUST be "high"
- Be SPECIFIC about what crashes and why"""


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
    return f"""Analyze this Python code for security vulnerabilities and crash bugs.

```python
{code}
```

CHECK EACH FUNCTION FOR:
1. SECURITY: Any eval(), exec(), os.system(), or SQL string formatting?
2. EMPTY INPUT: What happens if a list/string is empty? (IndexError on list[0]?)
3. ZERO DIVISION: Any division where denominator could be 0?
4. KEY ERRORS: Any dict[key] without checking key exists?
5. NONE ERRORS: Any method calls on potentially None objects?
6. UNDEFINED: Any variables used before definition?
7. DEAD CODE: Any functions defined but never called?

Respond with JSON: {{"issues": ["Line N: problem"], "suggestions": ["fix"], "severity": "low|medium|high", "summary": "text"}}

Be specific with line numbers. Security issues and crash bugs = severity "high"."""


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
