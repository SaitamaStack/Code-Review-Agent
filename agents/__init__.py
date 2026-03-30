"""
Agents package containing the LangGraph state machine and prompts.

Provides:
- Two-pass code review agent workflow (broad review + verification)
- System prompts for LLM interactions
"""

from agents.graph import create_agent_graph, run_agent
from agents.prompts import (
    REVIEW_SYSTEM_PROMPT,
    VERIFICATION_SYSTEM_PROMPT,
    get_review_prompt,
    get_verification_prompt,
)

__all__ = [
    "create_agent_graph",
    "run_agent",
    "REVIEW_SYSTEM_PROMPT",
    "VERIFICATION_SYSTEM_PROMPT",
    "get_review_prompt",
    "get_verification_prompt",
]
