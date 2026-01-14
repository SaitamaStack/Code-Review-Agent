"""
Shared utility functions for the code review agent.

Contains helper functions used across multiple modules for:
- Code formatting and manipulation
- Output handling
- File operations
- Time utilities
"""

import re
from datetime import datetime
from typing import Any


def format_code(code: str, strip_empty_lines: bool = True) -> str:
    """
    Clean and format Python code.
    
    Args:
        code: Raw code string
        strip_empty_lines: Whether to remove leading/trailing empty lines
        
    Returns:
        Formatted code string
    """
    if not code:
        return ""
    
    # Normalize line endings
    code = code.replace('\r\n', '\n').replace('\r', '\n')
    
    if strip_empty_lines:
        # Remove leading/trailing blank lines but preserve internal structure
        lines = code.split('\n')
        
        # Find first non-empty line
        start = 0
        for i, line in enumerate(lines):
            if line.strip():
                start = i
                break
        
        # Find last non-empty line
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                end = i + 1
                break
        
        code = '\n'.join(lines[start:end])
    
    return code


def truncate_output(
    output: str,
    max_lines: int = 50,
    max_length: int = 5000,
) -> str:
    """
    Truncate long output for display.
    
    Args:
        output: Output string to truncate
        max_lines: Maximum number of lines to keep
        max_length: Maximum character length
        
    Returns:
        Truncated output with indicator if truncation occurred
    """
    if not output:
        return ""
    
    # Truncate by character length first
    if len(output) > max_length:
        output = output[:max_length] + "\n... (output truncated)"
    
    # Then truncate by lines
    lines = output.split('\n')
    if len(lines) > max_lines:
        output = '\n'.join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    
    return output


def extract_code_from_markdown(text: str) -> str:
    """
    Extract Python code from markdown code blocks.
    
    Handles:
    - ```python ... ``` blocks
    - ``` ... ``` blocks
    - Plain code without markers
    
    Args:
        text: Text potentially containing markdown code blocks
        
    Returns:
        Extracted code or original text if no code block found
    """
    if not text:
        return ""
    
    # Try to find Python code block
    python_match = re.search(
        r'```python\s*([\s\S]*?)```',
        text,
        re.IGNORECASE
    )
    if python_match:
        return python_match.group(1).strip()
    
    # Try generic code block
    generic_match = re.search(
        r'```\s*([\s\S]*?)```',
        text
    )
    if generic_match:
        return generic_match.group(1).strip()
    
    # Return original if no code block found
    return text.strip()


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """
    Create a safe filename from a string.
    
    Args:
        name: Original string to convert
        max_length: Maximum length for filename
        
    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe_name = re.sub(r'\s+', '_', safe_name)
    safe_name = re.sub(r'_+', '_', safe_name)
    safe_name = safe_name.strip('_')
    
    # Truncate if needed
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length]
    
    return safe_name or "unnamed"


def get_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Get current timestamp as formatted string.
    
    Args:
        format_str: strftime format string
        
    Returns:
        Formatted timestamp
    """
    return datetime.now().strftime(format_str)


def dict_to_markdown(data: dict[str, Any], indent: int = 0) -> str:
    """
    Convert a dictionary to a markdown-formatted string.
    
    Args:
        data: Dictionary to convert
        indent: Indentation level
        
    Returns:
        Markdown-formatted string
    """
    lines = []
    prefix = "  " * indent
    
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}**{key}:**")
            lines.append(dict_to_markdown(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}**{key}:**")
            for item in value:
                if isinstance(item, dict):
                    lines.append(dict_to_markdown(item, indent + 1))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}**{key}:** {value}")
    
    return '\n'.join(lines)


def count_lines(code: str) -> int:
    """
    Count the number of lines in code.
    
    Args:
        code: Code string
        
    Returns:
        Number of lines
    """
    if not code:
        return 0
    return len(code.split('\n'))


def get_code_preview(code: str, max_lines: int = 5) -> str:
    """
    Get a short preview of code (first N lines).
    
    Args:
        code: Full code string
        max_lines: Maximum lines to include in preview
        
    Returns:
        Code preview string
    """
    if not code:
        return "(empty)"
    
    lines = code.split('\n')
    if len(lines) <= max_lines:
        return code
    
    preview = '\n'.join(lines[:max_lines])
    return f"{preview}\n# ... ({len(lines) - max_lines} more lines)"


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count for text.
    
    This is a simple approximation (1 token ≈ 4 characters).
    Actual token count depends on the specific tokenizer.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // 4
