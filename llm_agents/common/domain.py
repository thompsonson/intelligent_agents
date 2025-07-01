"""Common domain objects shared across LLM agents."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Immutable Domain entity representing a single LLM response."""
    reasoning: str
    answer: str