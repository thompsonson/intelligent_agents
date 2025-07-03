"""Domain objects for self-consistency agent.

This module contains the core domain entities and value objects for the self-consistency
Chain-of-Thought agent following the updated signatures specification.
"""

from dataclasses import dataclass
from typing import Dict
from ..common.domain import LLMResponse


@dataclass(frozen=True)
class ConsensusResult:
    """Immutable Value object for argmax results."""
    final_answer: str
    vote_count: int
    confidence: float