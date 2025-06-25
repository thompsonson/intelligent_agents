"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock

from llm_agents.self_consistency.interfaces import LLMInterface
from llm_agents.self_consistency.domain import LLMResponse
from llm_agents.self_consistency.config import AgentConfig


@pytest.fixture
def sample_llm_responses():
    """Fixture providing sample LLM responses for testing."""
    return [
        LLMResponse(reasoning="First, let me analyze...", answer="A"),
        LLMResponse(reasoning="Considering the options...", answer="B"), 
        LLMResponse(reasoning="After careful thought...", answer="A"),
        LLMResponse(reasoning="My conclusion is...", answer="A"),
        LLMResponse(reasoning="Based on the evidence...", answer="C")
    ]


@pytest.fixture
def mock_llm_interface():
    """Fixture providing a mock LLM interface."""
    mock = Mock(spec=LLMInterface)
    mock.generate_llm_response.return_value = LLMResponse(
        reasoning="Mock reasoning",
        answer="Mock answer"
    )
    return mock


@pytest.fixture
def basic_agent_config(mock_llm_interface):
    """Fixture providing a basic agent configuration."""
    return AgentConfig(
        llm_interface=mock_llm_interface,
        target_responses=5,
        prompt_template="Think step by step and provide your answer:"
    )


@pytest.fixture
def unanimous_responses():
    """Fixture providing responses with unanimous consensus."""
    return [
        LLMResponse(reasoning="Reasoning 1", answer="unanimous"),
        LLMResponse(reasoning="Reasoning 2", answer="unanimous"),
        LLMResponse(reasoning="Reasoning 3", answer="unanimous"),
        LLMResponse(reasoning="Reasoning 4", answer="unanimous"),
        LLMResponse(reasoning="Reasoning 5", answer="unanimous")
    ]


@pytest.fixture
def split_decision_responses():
    """Fixture providing responses with 3-2 split decision."""
    return [
        LLMResponse(reasoning="Reasoning 1", answer="majority"),
        LLMResponse(reasoning="Reasoning 2", answer="minority"),
        LLMResponse(reasoning="Reasoning 3", answer="majority"),
        LLMResponse(reasoning="Reasoning 4", answer="majority"),
        LLMResponse(reasoning="Reasoning 5", answer="minority")
    ]


@pytest.fixture
def tie_responses():
    """Fixture providing responses with tied votes."""
    return [
        LLMResponse(reasoning="Reasoning 1", answer="option_a"),
        LLMResponse(reasoning="Reasoning 2", answer="option_b"),
        LLMResponse(reasoning="Reasoning 3", answer="option_a"),
        LLMResponse(reasoning="Reasoning 4", answer="option_b")
    ]