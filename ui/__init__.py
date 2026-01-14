"""
UI package containing reusable Streamlit components.

Provides:
- Code display with syntax highlighting
- Review result visualization
- Execution output display
- Diff view components
"""

from ui.components import (
    display_code,
    display_review,
    display_execution_result,
    display_diff,
    display_agent_progress,
    code_input_area,
)

__all__ = [
    "display_code",
    "display_review",
    "display_execution_result",
    "display_diff",
    "display_agent_progress",
    "code_input_area",
]
