"""Configuration for self-reflection agent.

This module contains configuration classes for the self-reflection agent,
extending the patterns from self-consistency with confidence-aware parameters.
"""

from dataclasses import dataclass
from ..common.interfaces import LLMInterface


@dataclass
class ReflectionConfig:
    """Configuration for self-reflection agent with entropy-based intelligence."""
    llm_interface: LLMInterface
    target_responses: int = 10  # Higher default for exploration
    confidence_threshold: float = 0.8  # Early stopping threshold
    min_responses: int = 5  # Minimum before early stop
    prompt_template: str = ""
    
    # Entropy-based intelligence parameters
    entropy_threshold: float = 0.3  # Stop if entropy below this (0.0 = very concentrated)
    entropy_weight: float = 0.3  # Weight of entropy in combined stopping score (0.0-1.0)
    min_entropy_samples: int = 4  # Minimum samples before entropy influences stopping
    entropy_mode: str = "combined"  # "off", "confidence_only", "entropy_only", "combined"