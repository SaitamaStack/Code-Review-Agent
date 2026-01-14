"""
Code safety and linting utilities using AST analysis.

Provides static analysis to:
- Detect blocked/dangerous imports before execution
- Basic syntax validation
- Optional style checks
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


def lint_code(code: str) -> dict[str, Any]:
    """
    Perform basic linting and syntax validation on Python code.
    
    Checks for:
    - Syntax errors
    - Common issues detectable via AST
    
    Args:
        code: Python source code to lint
        
    Returns:
        dict with keys:
            - valid (bool): True if code is syntactically valid
            - errors (list[str]): List of error messages
            - warnings (list[str]): List of warning messages
    """
    errors: list[str] = []
    warnings: list[str] = []
    
    # Step 1: Check for syntax errors
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "valid": False,
            "errors": [f"Syntax error at line {e.lineno}: {e.msg}"],
            "warnings": [],
        }
    
    # Step 2: Basic AST analysis for common issues
    for node in ast.walk(tree):
        # Warn about bare except clauses
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                warnings.append(
                    f"Line {node.lineno}: Bare 'except:' clause - consider catching specific exceptions"
                )
        
        # Warn about mutable default arguments
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    warnings.append(
                        f"Line {node.lineno}: Function '{node.name}' has mutable default argument"
                    )
        
        # Warn about unused variables (basic check - variables assigned but never used)
        # This is a simplified check; full analysis would require scope tracking
        
    return {
        "valid": True,
        "errors": errors,
        "warnings": warnings,
    }


def get_syntax_error_details(code: str) -> dict[str, Any] | None:
    """
    Get detailed information about a syntax error in code.
    
    Args:
        code: Python source code with potential syntax error
        
    Returns:
        dict with error details or None if no syntax error
    """
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return {
            "line": e.lineno,
            "column": e.offset,
            "message": e.msg,
            "text": e.text,
        }
