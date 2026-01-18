"""
Tests for the code safety linter (tools/linter.py).
"""

from tools.linter import check_code_safety


class TestCheckCodeSafety:
    """Tests for check_code_safety function."""

    def test_safe_code_passes(self, safe_code):
        """Safe code should pass all checks."""
        result = check_code_safety(safe_code)
        
        assert result["safe"] is True
        assert result["reason"] is None
        assert result["blocked_imports"] == []

    def test_detects_os_import(self, unsafe_code_os):
        """Should detect blocked 'os' import."""
        result = check_code_safety(unsafe_code_os)
        
        assert result["safe"] is False
        assert "os" in result["blocked_imports"]
        assert "Blocked import" in result["reason"]

    def test_detects_eval(self, unsafe_code_eval):
        """Should detect dangerous eval() call."""
        result = check_code_safety(unsafe_code_eval)
        
        assert result["safe"] is False
        assert "eval()" in result["reason"]

    def test_detects_exec(self):
        """Should detect dangerous exec() call."""
        code = 'exec("print(1)")'
        result = check_code_safety(code)
        
        assert result["safe"] is False
        assert "exec()" in result["reason"]

    def test_detects_subprocess_import(self):
        """Should detect blocked subprocess import."""
        code = "import subprocess\nsubprocess.run(['ls'])"
        result = check_code_safety(code)
        
        assert result["safe"] is False
        assert "subprocess" in result["blocked_imports"]

    def test_detects_from_import(self):
        """Should detect blocked imports via 'from x import y' syntax."""
        code = "from os import path\nprint(path.exists('.'))"
        result = check_code_safety(code)
        
        assert result["safe"] is False
        assert "os" in result["blocked_imports"]

    def test_detects_dunder_import(self):
        """Should detect __import__ bypass attempts."""
        code = "os = __import__('os')\nos.getcwd()"
        result = check_code_safety(code)
        
        assert result["safe"] is False
        assert "os" in result["blocked_imports"]

    def test_allows_safe_imports(self):
        """Should allow safe standard library imports."""
        code = """
import math
import json
import datetime
from collections import defaultdict

print(math.pi)
"""
        result = check_code_safety(code)
        
        assert result["safe"] is True
        assert result["blocked_imports"] == []

    def test_handles_syntax_errors_gracefully(self, code_with_syntax_error):
        """Should not crash on code with syntax errors."""
        # Should still attempt regex-based detection
        result = check_code_safety(code_with_syntax_error)
        
        # Even with syntax error, should return a valid result structure
        assert "safe" in result
        assert "reason" in result
        assert "blocked_imports" in result

    def test_detects_compile_builtin(self):
        """Should detect compile() which can be used to bypass restrictions."""
        code = "code = compile('import os', '<string>', 'exec')"
        result = check_code_safety(code)
        
        assert result["safe"] is False
        assert "compile()" in result["reason"]

    def test_multiple_blocked_imports(self):
        """Should detect multiple blocked imports."""
        code = """
import os
import sys
import subprocess
"""
        result = check_code_safety(code)
        
        assert result["safe"] is False
        assert len(result["blocked_imports"]) >= 2
