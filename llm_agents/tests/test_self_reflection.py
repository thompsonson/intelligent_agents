"""Tests for self-reflection agent with confidence-aware early stopping."""

import pytest
from unittest.mock import Mock
from collections import Counter

from llm_agents.self_reflection.agent import SelfReflectionAgent
from llm_agents.self_reflection.config import ReflectionConfig
from llm_agents.self_reflection.domain import ReflectionResult
from llm_agents.common.domain import LLMResponse
from llm_agents.common.interfaces import LLMInterface


class MockReflectionInterface(LLMInterface):
    """Mock LLM interface for self-reflection testing."""
    
    def __init__(self, responses: list[LLMResponse]):
        """Initialize with predefined responses.
        
        Args:
            responses: List of LLMResponse objects to return sequentially
        """
        self.responses = responses
        self.call_count = 0
    
    def generate_llm_response(self, prompt: str, question: str) -> LLMResponse:
        """Return the next predefined response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        else:
            # Fallback for extra calls
            return LLMResponse(reasoning="Extra call", answer="fallback")


class TestSelfReflectionAgent:
    """Core self-reflection agent tests."""
    
    def test_early_stopping_with_high_confidence(self):
        """Test early stopping when confidence threshold is reached."""
        # Create responses that converge quickly to same answer
        responses = [
            LLMResponse(reasoning="Thinking 1", answer="42"),
            LLMResponse(reasoning="Thinking 2", answer="42"),
            LLMResponse(reasoning="Thinking 3", answer="42"),
            LLMResponse(reasoning="Thinking 4", answer="42"),
            LLMResponse(reasoning="Thinking 5", answer="42"),  # 5th response = 100% confidence
            # These shouldn't be called due to early stopping
            LLMResponse(reasoning="Extra 1", answer="42"),
            LLMResponse(reasoning="Extra 2", answer="42"),
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=10,
            confidence_threshold=0.8,  # Should trigger early stopping at 100%
            min_responses=5
        )
        
        agent = SelfReflectionAgent(config, "What is 6*7?")
        result = agent.process_question()
        
        # Verify early stopping occurred
        assert result.early_stopping is True
        assert result.total_responses == 5  # Stopped at minimum
        assert result.final_answer == "42"
        assert result.consensus_confidence == 1.0  # 100% confidence
        assert result.uncertainty_level == "low"
        assert mock_interface.call_count == 5  # Only called 5 times
    
    def test_continued_sampling_with_low_confidence(self):
        """Test continued sampling when confidence remains low."""
        # Create responses with mixed answers (low confidence)
        responses = [
            LLMResponse(reasoning="Think 1", answer="A"),
            LLMResponse(reasoning="Think 2", answer="B"),
            LLMResponse(reasoning="Think 3", answer="A"),
            LLMResponse(reasoning="Think 4", answer="C"),
            LLMResponse(reasoning="Think 5", answer="B"),
            LLMResponse(reasoning="Think 6", answer="A"),  # A=3, B=2, C=1 -> max 50%
            LLMResponse(reasoning="Think 7", answer="A"),
            LLMResponse(reasoning="Think 8", answer="A"),
            LLMResponse(reasoning="Think 9", answer="A"),
            LLMResponse(reasoning="Think 10", answer="A"),  # A=7, B=2, C=1 -> max 70%
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=10,
            confidence_threshold=0.8,  # Never reached
            min_responses=5
        )
        
        agent = SelfReflectionAgent(config, "Ambiguous question?")
        result = agent.process_question()
        
        # Verify no early stopping occurred
        assert result.early_stopping is False
        assert result.total_responses == 10  # Used all responses
        assert result.final_answer == "A"  # Most frequent
        assert result.consensus_confidence == 0.7  # 7/10 = 70%
        assert result.uncertainty_level == "medium"
        assert mock_interface.call_count == 10  # All responses used
    
    def test_confidence_calculation_accuracy(self):
        """Test confidence calculation with known distributions."""
        responses = [
            LLMResponse(reasoning="R1", answer="Yes"),
            LLMResponse(reasoning="R2", answer="Yes"),
            LLMResponse(reasoning="R3", answer="No"),
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=3,
            confidence_threshold=1.1,  # Never trigger early stopping (impossible threshold)
            min_responses=2
        )
        
        agent = SelfReflectionAgent(config, "Test question")
        result = agent.process_question()
        
        # Verify distribution and confidence
        expected_distribution = {"Yes": 2/3, "No": 1/3}
        assert result.answer_distribution == pytest.approx(expected_distribution)
        assert result.consensus_confidence == pytest.approx(2/3)
        assert result.final_answer == "Yes"
        assert result.uncertainty_level == "medium"  # 67% is medium confidence
    
    def test_probability_distribution_validation(self):
        """Test that probability distributions sum to 1.0."""
        responses = [
            LLMResponse(reasoning="R1", answer="A"),
            LLMResponse(reasoning="R2", answer="B"),
            LLMResponse(reasoning="R3", answer="C"),
            LLMResponse(reasoning="R4", answer="A"),
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(llm_interface=mock_interface, target_responses=4)
        
        agent = SelfReflectionAgent(config, "Question")
        result = agent.process_question()
        
        # Verify distribution sums to 1.0
        total_probability = sum(result.answer_distribution.values())
        assert total_probability == pytest.approx(1.0)
        
        # Verify individual probabilities
        assert result.answer_distribution["A"] == 0.5  # 2/4
        assert result.answer_distribution["B"] == 0.25  # 1/4
        assert result.answer_distribution["C"] == 0.25  # 1/4
    
    def test_convergence_analysis(self):
        """Test convergence analysis tracking."""
        responses = [
            LLMResponse(reasoning="R1", answer="X"),  # 100% X
            LLMResponse(reasoning="R2", answer="Y"),  # 50% X, 50% Y
            LLMResponse(reasoning="R3", answer="X"),  # 66% X, 33% Y
            LLMResponse(reasoning="R4", answer="X"),  # 75% X, 25% Y
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(llm_interface=mock_interface, target_responses=4)
        
        agent = SelfReflectionAgent(config, "Question")
        result = agent.process_question()
        
        # Verify convergence analysis exists and has expected structure
        convergence = result.convergence_analysis
        assert "confidence_evolution" in convergence
        assert "convergence_rate" in convergence
        assert "final_stability" in convergence
        
        # Verify confidence evolution
        expected_evolution = [1.0, 0.5, 2/3, 0.75]
        assert convergence["confidence_evolution"] == pytest.approx(expected_evolution)
        
        # Verify convergence rate (decrease then increase)
        assert convergence["convergence_rate"] == pytest.approx((0.75 - 1.0) / 4)


class TestReflectionIntegration:
    """Integration tests for the complete self-reflection system."""
    
    def test_unanimous_early_stopping(self):
        """Test early stopping with unanimous responses."""
        responses = [LLMResponse(reasoning=f"Think {i}", answer="Unanimous") for i in range(10)]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            confidence_threshold=0.8,
            min_responses=3
        )
        
        agent = SelfReflectionAgent(config, "Clear question")
        result = agent.process_question()
        
        assert result.early_stopping is True
        assert result.total_responses == 3  # Stopped at minimum
        assert result.consensus_confidence == 1.0
        assert result.uncertainty_level == "low"
    
    def test_tie_handling(self):
        """Test handling of tied responses."""
        responses = [
            LLMResponse(reasoning="R1", answer="Option A"),
            LLMResponse(reasoning="R2", answer="Option B"),
            LLMResponse(reasoning="R3", answer="Option A"),
            LLMResponse(reasoning="R4", answer="Option B"),
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(llm_interface=mock_interface, target_responses=4)
        
        agent = SelfReflectionAgent(config, "Tied question")
        result = agent.process_question()
        
        # With ties, Counter.most_common() returns first encountered
        assert result.final_answer in ["Option A", "Option B"]
        assert result.consensus_confidence == 0.5  # 50-50 tie
        assert result.uncertainty_level == "high"  # 50% confidence is high uncertainty
        assert len(result.answer_distribution) == 2


class TestEdgeCases:
    """Edge case tests for self-reflection agent."""
    
    def test_single_response_scenario(self):
        """Test with minimum possible responses."""
        responses = [LLMResponse(reasoning="Only response", answer="Single")]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=1,
            min_responses=1
        )
        
        agent = SelfReflectionAgent(config, "Single question")
        result = agent.process_question()
        
        assert result.total_responses == 1
        assert result.final_answer == "Single"
        assert result.consensus_confidence == 1.0
        assert result.uncertainty_level == "low"
    
    def test_empty_responses_handling(self):
        """Test graceful handling of edge cases in analysis."""
        responses = []
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=0,
            min_responses=0
        )
        
        agent = SelfReflectionAgent(config, "No responses")
        result = agent.process_question()
        
        assert result.total_responses == 0
        assert result.final_answer == "No consensus reached"
        assert result.consensus_confidence == 0.0
        assert result.uncertainty_level == "high"
        assert result.answer_distribution == {}


class TestConfigurationValidation:
    """Tests for configuration validation and edge cases."""
    
    def test_confidence_threshold_validation(self):
        """Test various confidence threshold values."""
        responses = [LLMResponse(reasoning=f"R{i}", answer="Test") for i in range(5)]
        
        # Test with very low threshold (should trigger immediately at min_responses)
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            confidence_threshold=0.1,  # Very low
            min_responses=3
        )
        
        agent = SelfReflectionAgent(config, "Question")
        result = agent.process_question()
        
        assert result.early_stopping is True
        assert result.total_responses == 3  # Stopped at minimum
        
        # Test with very high threshold (should never trigger)
        mock_interface2 = MockReflectionInterface(responses)  # Fresh interface
        config2 = ReflectionConfig(
            llm_interface=mock_interface2,
            confidence_threshold=1.1,  # Impossible to reach
            min_responses=3,
            target_responses=5
        )
        
        agent2 = SelfReflectionAgent(config2, "Question")
        result2 = agent2.process_question()
        
        assert result2.early_stopping is False
        assert result2.total_responses == 5  # Used all responses