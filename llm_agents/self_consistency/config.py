"""Configuration for self-consistency agent.

This module contains configuration classes for the self-consistency agent,
following the established patterns from the maze solver configuration.
"""

from dataclasses import dataclass
from ..common.interfaces import LLMInterface


@dataclass
class AgentConfig:
    """Configuration for self-consistency agent."""
    llm_interface: LLMInterface
    target_responses: int = 5
    prompt_template: str = ""