"""Tests for domain objects."""

import pytest
from llm_agents.self_consistency.domain import LLMResponse, ConsensusResult


class TestLLMResponse:
    """Domain Objects Tests - LLMResponse validation."""
    
    def test_llm_response_creation(self):
        """Test basic LLMResponse creation."""
        response = LLMResponse(
            reasoning="Step 1: Think about X. Step 2: Consider Y.",
            answer="42"
        )
        assert response.reasoning == "Step 1: Think about X. Step 2: Consider Y."
        assert response.answer == "42"
    
    def test_llm_response_immutability(self):
        """Test that LLMResponse is immutable."""
        response = LLMResponse(reasoning="test", answer="test")
        with pytest.raises(AttributeError):
            response.reasoning = "new value"
        with pytest.raises(AttributeError):
            response.answer = "new value"


class TestConsensusResult:
    """Domain Objects Tests - ConsensusResult validation."""
    
    def test_consensus_result_creation(self):
        """Test basic ConsensusResult creation."""
        result = ConsensusResult(
            final_answer="yes",
            vote_count=3,
            confidence=0.6
        )
        assert result.final_answer == "yes"
        assert result.vote_count == 3
        assert result.confidence == 0.6
    
    def test_consensus_result_immutability(self):
        """Test that ConsensusResult is immutable."""
        result = ConsensusResult(final_answer="test", vote_count=1, confidence=1.0)
        with pytest.raises(AttributeError):
            result.final_answer = "new value"
        with pytest.raises(AttributeError):
            result.vote_count = 5
        with pytest.raises(AttributeError):
            result.confidence = 0.5
    
    def test_confidence_calculation(self):
        """Test confidence is properly calculated."""
        # 100% confidence (unanimous)
        result = ConsensusResult(final_answer="yes", vote_count=5, confidence=1.0)
        assert result.confidence == 1.0
        
        # 60% confidence (majority)
        result = ConsensusResult(final_answer="yes", vote_count=3, confidence=0.6)
        assert result.confidence == 0.6
        
        # 50% confidence (tie)
        result = ConsensusResult(final_answer="yes", vote_count=1, confidence=0.5)
        assert result.confidence == 0.5