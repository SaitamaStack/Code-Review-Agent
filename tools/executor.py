"""
Safe code execution module using subprocess and tempfile.

This module provides sandboxed Python code execution with:
- Timeout protection against infinite loops
- Blocked import detection for dangerous modules
- Isolated execution via subprocess (not exec())
- Structured result capture
"""

import subprocess
import tempfile
import time
from pathlib import Path

from config import get_config
from models.schemas import ExecutionResult
from tools.linter import check_code_safety


def execute_code_safely(code: str) -> ExecutionResult:
    """
    Execute Python code in a sandboxed subprocess with safety checks.
    
    This function:
    1. Checks for blocked imports before execution
    2. Writes code to a temporary file
    3. Runs the code in a subprocess with timeout
    4. Captures and returns stdout/stderr
    
    Args:
        code: Python source code to execute
        
    Returns:
        ExecutionResult: Structured result with success status, output, and errors
        
    Example:
        result = execute_code_safely("print('Hello, World!')")
        if result.success:
            print(f"Output: {result.output}")
        else:
            print(f"Error: {result.error}")
    """
    config = get_config()
    
    # Step 1: Pre-execution safety check for blocked imports
    safety_result = check_code_safety(code)
    if not safety_result["safe"]:
        return ExecutionResult(
            success=False,
            output=None,
            error=f"Security Error: {safety_result['reason']}",
            execution_time=0.0,
            blocked_import_detected=True,
        )
    
    # Step 2: Write code to a temporary file for subprocess execution
    # Using tempfile ensures cleanup and isolation
    start_time = time.time()
    
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,  # Keep file until we explicitly remove it
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = Path(tmp_file.name)
        
        # Step 3: Execute in subprocess with timeout
        # SECURITY: Never use shell=True to prevent shell injection
        result = subprocess.run(
            ["python", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=config.execution_timeout,
            # Prevent any shell expansion or injection
            shell=False,
        )
        
        execution_time = time.time() - start_time
        
        # Step 4: Parse results
        if result.returncode == 0:
            return ExecutionResult(
                success=True,
                output=result.stdout.strip() if result.stdout else None,
                error=None,
                execution_time=execution_time,
                blocked_import_detected=False,
            )
        else:
            return ExecutionResult(
                success=False,
                output=result.stdout.strip() if result.stdout else None,
                error=result.stderr.strip() if result.stderr else "Unknown error",
                execution_time=execution_time,
                blocked_import_detected=False,
            )
            
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            output=None,
            error=f"Execution timed out after {config.execution_timeout} seconds",
            execution_time=execution_time,
            blocked_import_detected=False,
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            output=None,
            error=f"Execution failed: {str(e)}",
            execution_time=execution_time,
            blocked_import_detected=False,
        )
        
    finally:
        # Clean up temporary file
        try:
            if 'tmp_path' in locals():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass  # Ignore cleanup errors


def execute_code_with_input(code: str, stdin_input: str = "") -> ExecutionResult:
    """
    Execute Python code with optional stdin input.
    
    Useful for testing code that expects user input via input().
    
    Args:
        code: Python source code to execute
        stdin_input: String to provide as stdin (simulates user input)
        
    Returns:
        ExecutionResult: Structured result with success status, output, and errors
    """
    config = get_config()
    
    # Safety check first
    safety_result = check_code_safety(code)
    if not safety_result["safe"]:
        return ExecutionResult(
            success=False,
            output=None,
            error=f"Security Error: {safety_result['reason']}",
            execution_time=0.0,
            blocked_import_detected=True,
        )
    
    start_time = time.time()
    
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py", 
            delete=False,
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = Path(tmp_file.name)
        
        result = subprocess.run(
            ["python", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=config.execution_timeout,
            shell=False,
            input=stdin_input,  # Provide stdin input
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            return ExecutionResult(
                success=True,
                output=result.stdout.strip() if result.stdout else None,
                error=None,
                execution_time=execution_time,
                blocked_import_detected=False,
            )
        else:
            return ExecutionResult(
                success=False,
                output=result.stdout.strip() if result.stdout else None,
                error=result.stderr.strip() if result.stderr else "Unknown error",
                execution_time=execution_time,
                blocked_import_detected=False,
            )
            
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            output=None,
            error=f"Execution timed out after {config.execution_timeout} seconds",
            execution_time=execution_time,
            blocked_import_detected=False,
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return ExecutionResult(
            success=False,
            output=None,
            error=f"Execution failed: {str(e)}",
            execution_time=execution_time,
            blocked_import_detected=False,
        )
        
    finally:
        try:
            if 'tmp_path' in locals():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
