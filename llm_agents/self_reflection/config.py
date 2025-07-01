"""Configuration for self-reflection agent.

This module contains configuration classes for the self-reflection agent,
extending the patterns from self-consistency with confidence-aware parameters.
"""

from dataclasses import dataclass
from ..common.interfaces import LLMInterface


@dataclass
class ReflectionConfig:
    """Configuration for self-reflection agent."""
    llm_interface: LLMInterface
    target_responses: int = 10  # Higher default for exploration
    confidence_threshold: float = 0.8  # Early stopping threshold
    min_responses: int = 5  # Minimum before early stop
    prompt_template: str = ""