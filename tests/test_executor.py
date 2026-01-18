"""
Tests for the safe code executor (tools/executor.py).
"""

from config import update_config
from tools.executor import execute_code_safely


class TestExecuteCodeSafely:
    """Tests for execute_code_safely function."""

    def test_successful_execution(self):
        """Should execute simple code and capture output."""
        code = "print('Hello, World!')"
        result = execute_code_safely(code)
        
        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.error is None
        assert result.execution_time > 0

    def test_captures_multiple_prints(self):
        """Should capture all stdout output."""
        code = """
print("line 1")
print("line 2")
print("line 3")
"""
        result = execute_code_safely(code)
        
        assert result.success is True
        assert "line 1" in result.output
        assert "line 2" in result.output
        assert "line 3" in result.output

    def test_captures_runtime_error(self):
        """Should capture runtime errors."""
        code = "x = 1 / 0"  # ZeroDivisionError
        result = execute_code_safely(code)
        
        assert result.success is False
        assert result.error is not None
        assert "ZeroDivisionError" in result.error

    def test_captures_name_error(self):
        """Should capture NameError for undefined variables."""
        code = "print(undefined_variable)"
        result = execute_code_safely(code)
        
        assert result.success is False
        assert "NameError" in result.error

    def test_blocks_os_import(self, unsafe_code_os):
        """Should block code with os import before execution."""
        result = execute_code_safely(unsafe_code_os)
        
        assert result.success is False
        assert result.blocked_import_detected is True
        assert "Security Error" in result.error

    def test_blocks_eval(self, unsafe_code_eval):
        """Should block code with eval() before execution."""
        result = execute_code_safely(unsafe_code_eval)
        
        assert result.success is False
        assert "eval()" in result.error

    def test_timeout_enforcement(self):
        """Should timeout on long-running code."""
        # Set a short timeout for testing
        update_config(execution_timeout=1)
        
        code = """
import time
time.sleep(10)
print("done")
"""
        result = execute_code_safely(code)
        
        assert result.success is False
        assert "timed out" in result.error.lower()

    def test_handles_empty_output(self):
        """Should handle code that produces no output."""
        code = "x = 1 + 1"  # No print statement
        result = execute_code_safely(code)
        
        assert result.success is True
        assert result.output is None or result.output == ""

    def test_execution_time_tracked(self):
        """Should track execution time."""
        code = "print('quick')"
        result = execute_code_safely(code)
        
        assert result.execution_time >= 0
        assert result.execution_time < 5  # Should be fast

    def test_allows_safe_imports(self):
        """Should allow safe standard library imports."""
        code = """
import math
import json
result = math.sqrt(16) + json.loads('{"x": 1}')["x"]
print(result)
"""
        result = execute_code_safely(code)
        
        assert result.success is True
        assert "5.0" in result.output

    def test_function_definition_and_call(self):
        """Should handle function definitions and calls."""
        code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(f"Result: {result}")
"""
        result = execute_code_safely(code)
        
        assert result.success is True
        assert "Result: 5" in result.output

    def test_class_definition_and_usage(self):
        """Should handle class definitions."""
        code = """
class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1
        return self.count

c = Counter()
print(c.increment())
print(c.increment())
"""
        result = execute_code_safely(code)
        
        assert result.success is True
        assert "1" in result.output
        assert "2" in result.output
