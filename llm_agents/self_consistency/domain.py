"""Domain objects for self-consistency agent.

This module contains the core domain entities and value objects for the self-consistency
Chain-of-Thought agent following the updated signatures specification.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from ..common.domain import LLMResponse


@dataclass(frozen=True)
class ConsensusResult:
    """Immutable Value object for argmax results."""
    final_answer: str
    vote_count: int
    confidence: float


@dataclass(frozen=True)
class EnhancedLLMResponse:
    """Enhanced LLM response with token-level confidence data."""
    reasoning: str
    answer: str
    logprobs: Optional[Dict[str, Any]] = None  # Token-level confidence data


@dataclass(frozen=True)
class ConfidenceReport:
    """Data collection report for future correlation analysis."""
    consensus_confidence: float  # Traditional vote-based confidence
    token_confidence_reasoning: float  # Average reasoning token confidence
    token_confidence_answer: float  # Average answer token confidence
    individual_response_data: List[Dict[str, Any]]  # Per-response detailed data


@dataclass(frozen=True)
class EnhancedConsensusResult:
    """Traditional result enhanced with confidence data."""
    final_answer: str
    vote_count: int
    confidence: float  # Traditional consensus confidence (unchanged)
    confidence_report: ConfidenceReport  # Additional data for analysis