"""
Shared utility functions for the code review agent.

Contains helper functions used across multiple modules for:
- Code formatting and manipulation
- Time utilities
"""

from datetime import datetime


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


def get_timestamp(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Get current timestamp as formatted string.
    
    Args:
        format_str: strftime format string
        
    Returns:
        Formatted timestamp
    """
    return datetime.now().strftime(format_str)
