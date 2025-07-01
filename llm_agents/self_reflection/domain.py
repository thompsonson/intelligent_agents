"""Domain objects for self-reflection agent.

This module contains the enhanced domain entities for the self-reflection
agent with confidence-aware early stopping and probability distributions.
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..common.domain import LLMResponse


@dataclass(frozen=True)
class ReflectionResult:
    """Enhanced result with full probability distribution and confidence analysis."""
    final_answer: str
    consensus_confidence: float  # 0.0-1.0 confidence score
    answer_distribution: Dict[str, float]  # Normalized probabilities
    uncertainty_level: str  # "high", "medium", "low"
    early_stopping: bool  # Stopped early due to confidence?
    total_responses: int
    convergence_analysis: Dict[str, Any]  # Convergence metrics