"""
Configuration settings for the Local Code Review Agent.

This module centralizes all configurable parameters including:
- LLM model settings (Ollama)
- Execution safety limits
- Retry policies
"""

from dataclasses import dataclass, field


@dataclass
class Config:
    """
    Application configuration with sensible defaults.
    
    Attributes:
        model_name: Ollama model to use for code review/fixing
        max_retries: Maximum attempts to fix code before giving up
        execution_timeout: Seconds before killing code execution
        blocked_imports: Modules that cannot be imported in user code
        ollama_base_url: Base URL for Ollama API
    """
    
    # LLM Settings
    model_name: str = "qwen2.5:0.5b"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.1  # Low temperature for more deterministic code generation
    
    # Execution Safety Settings
    max_retries: int = 3
    execution_timeout: int = 10  # seconds
    
    # Security: Modules that are blocked from being imported in user code
    # These could allow filesystem access, network calls, or system manipulation
    blocked_imports: list[str] = field(default_factory=lambda: [
        "os",
        "sys", 
        "subprocess",
        "shutil",
        "socket",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "telnetlib",
        "smtplib",
        "poplib",
        "imaplib",
        "pickle",
        "shelve",
        "marshal",
        "builtins",
        "__builtins__",
        "importlib",
        "ctypes",
        "multiprocessing",
    ])
    
    # UI Settings
    max_code_display_lines: int = 100
    enable_syntax_highlighting: bool = True


# Global config instance - import this in other modules
config = Config()


def get_config() -> Config:
    """
    Get the current configuration instance.
    
    Returns:
        Config: The global configuration object
    """
    return config


def update_config(**kwargs) -> Config:
    """
    Update configuration values at runtime.
    
    Args:
        **kwargs: Configuration attributes to update
        
    Returns:
        Config: Updated configuration object
        
    Example:
        update_config(max_retries=5, execution_timeout=15)
    """
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            raise ValueError(f"Unknown config key: {key}")
    return config
