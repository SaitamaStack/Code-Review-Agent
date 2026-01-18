"""
Code safety utilities using AST analysis.

Provides static analysis to:
- Detect blocked/dangerous imports before execution
- Basic syntax validation
"""

import ast
import re
from typing import Any

from config import get_config


def check_code_safety(code: str) -> dict[str, Any]:
    """
    Check if code contains blocked imports or dangerous patterns.
    
    Uses both AST parsing and regex patterns to detect:
    - Direct imports of blocked modules
    - Import aliases that might hide blocked modules
    - Dynamic imports via __import__ or importlib
    
    Args:
        code: Python source code to analyze
        
    Returns:
        dict with keys:
            - safe (bool): True if code passes safety checks
            - reason (str | None): Explanation if code is unsafe
            - blocked_imports (list[str]): List of blocked imports found
            
    Example:
        result = check_code_safety("import os\\nos.system('rm -rf /')")
        # result = {"safe": False, "reason": "Blocked import: os", "blocked_imports": ["os"]}
    """
    config = get_config()
    blocked = set(config.blocked_imports)
    found_blocked: list[str] = []
    
    # Step 1: Try AST-based detection (most reliable)
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            # Check "import x" statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]  # Get top-level module
                    if module_name in blocked:
                        found_blocked.append(module_name)
            
            # Check "from x import y" statements
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name in blocked:
                        found_blocked.append(module_name)
            
            # Check for __import__('module') calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        module_name = str(node.args[0].value).split('.')[0]
                        if module_name in blocked:
                            found_blocked.append(module_name)
                            
    except SyntaxError:
        # If AST parsing fails, fall back to regex (code may have syntax errors)
        pass
    
    # Step 2: Regex-based detection as backup
    # This catches cases AST might miss or when code has syntax errors
    for blocked_module in blocked:
        patterns = [
            rf'\bimport\s+{re.escape(blocked_module)}\b',
            rf'\bfrom\s+{re.escape(blocked_module)}\b',
            rf'__import__\s*\(\s*["\']({re.escape(blocked_module)})',
        ]
        for pattern in patterns:
            if re.search(pattern, code):
                if blocked_module not in found_blocked:
                    found_blocked.append(blocked_module)
    
    # Step 3: Check for eval/exec with dynamic strings (potential bypass)
    dangerous_patterns = [
        (r'\beval\s*\(', "eval() is not allowed"),
        (r'\bexec\s*\(', "exec() is not allowed"),
        (r'\bcompile\s*\(', "compile() is not allowed"),
    ]
    
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, code):
            return {
                "safe": False,
                "reason": reason,
                "blocked_imports": found_blocked,
            }
    
    # Return results
    if found_blocked:
        return {
            "safe": False,
            "reason": f"Blocked import(s) detected: {', '.join(found_blocked)}",
            "blocked_imports": found_blocked,
        }
    
    return {
        "safe": True,
        "reason": None,
        "blocked_imports": [],
    }
