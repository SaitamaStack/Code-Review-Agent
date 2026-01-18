"""
Pytest configuration and shared fixtures.
"""

import pytest

from config import Config, update_config


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config to defaults before each test."""
    # Store original values
    original = Config()
    
    yield
    
    # Restore defaults after test
    update_config(
        model_name=original.model_name,
        ollama_base_url=original.ollama_base_url,
        temperature=original.temperature,
        max_retries=original.max_retries,
        execution_timeout=original.execution_timeout,
    )


@pytest.fixture
def safe_code():
    """Example of safe Python code."""
    return '''
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
'''


@pytest.fixture
def unsafe_code_os():
    """Code with blocked os import."""
    return '''
import os
os.system("echo hello")
'''


@pytest.fixture
def unsafe_code_eval():
    """Code with dangerous eval()."""
    return '''
user_input = "2 + 2"
result = eval(user_input)
print(result)
'''


@pytest.fixture
def code_with_syntax_error():
    """Code with syntax error."""
    return '''
def broken(
    print("missing closing paren"
'''
