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


class TestEntropyCalculations:
    """Tests for entropy calculation accuracy and validation."""
    
    def test_entropy_calculation_accuracy(self):
        """Test Shannon entropy calculations with known distributions."""
        # Test case 1: Single answer (entropy = 0.0)
        responses_single = [LLMResponse(reasoning=f"R{i}", answer="Single") for i in range(4)]
        
        mock_interface = MockReflectionInterface(responses_single)
        config = ReflectionConfig(llm_interface=mock_interface, target_responses=4)
        
        agent = SelfReflectionAgent(config, "Single answer test")
        result = agent.process_question()
        
        assert result.distribution_entropy == pytest.approx(0.0)
        assert result.normalized_entropy == pytest.approx(0.0)
        assert result.entropy_level == "concentrated"
        assert result.consensus_type == "strong"
        
        # Test case 2: Binary 50/50 split (entropy = 1.0)
        responses_binary = [
            LLMResponse(reasoning="R1", answer="A"),
            LLMResponse(reasoning="R2", answer="B"),
            LLMResponse(reasoning="R3", answer="A"), 
            LLMResponse(reasoning="R4", answer="B"),
        ]
        
        mock_interface2 = MockReflectionInterface(responses_binary)
        config2 = ReflectionConfig(llm_interface=mock_interface2, target_responses=4)
        
        agent2 = SelfReflectionAgent(config2, "Binary split test")
        result2 = agent2.process_question()
        
        assert result2.distribution_entropy == pytest.approx(1.0)  # log2(2) = 1.0 for 50/50
        assert result2.normalized_entropy == pytest.approx(1.0)    # Already at max for 2 options
        assert result2.entropy_level == "uniform"
        assert result2.consensus_type == "binary"
        
        # Test case 3: Uniform 4-way split (entropy = 2.0)
        responses_uniform = [
            LLMResponse(reasoning="R1", answer="A"),
            LLMResponse(reasoning="R2", answer="B"),
            LLMResponse(reasoning="R3", answer="C"),
            LLMResponse(reasoning="R4", answer="D"),
        ]
        
        mock_interface3 = MockReflectionInterface(responses_uniform)
        config3 = ReflectionConfig(llm_interface=mock_interface3, target_responses=4)
        
        agent3 = SelfReflectionAgent(config3, "Uniform distribution test")
        result3 = agent3.process_question()
        
        assert result3.distribution_entropy == pytest.approx(2.0)  # log2(4) = 2.0 for uniform
        assert result3.normalized_entropy == pytest.approx(1.0)    # 2.0 / 2.0 = 1.0
        assert result3.entropy_level == "uniform"
        assert result3.consensus_type == "divided"
    
    def test_entropy_edge_cases(self):
        """Test entropy calculations with edge cases."""
        # Empty responses
        responses_empty = []
        
        mock_interface = MockReflectionInterface(responses_empty)
        config = ReflectionConfig(llm_interface=mock_interface, target_responses=0, min_responses=0)
        
        agent = SelfReflectionAgent(config, "Empty test")
        result = agent.process_question()
        
        assert result.distribution_entropy == 0.0
        assert result.normalized_entropy == 0.0
        assert result.entropy_level == "concentrated"
        
        # Single response case
        responses_single = [LLMResponse(reasoning="Only", answer="Single")]
        
        mock_interface2 = MockReflectionInterface(responses_single)
        config2 = ReflectionConfig(llm_interface=mock_interface2, target_responses=1, min_responses=1)
        
        agent2 = SelfReflectionAgent(config2, "Single response test")
        result2 = agent2.process_question()
        
        assert result2.distribution_entropy == 0.0
        assert result2.normalized_entropy == 0.0
        assert result2.entropy_level == "concentrated"
        assert result2.consensus_type == "strong"
    
    def test_consensus_type_classification(self):
        """Test consensus type classification accuracy."""
        # Strong consensus: 80%, 10%, 10%
        responses_strong = [
            LLMResponse(reasoning=f"R{i}", answer="A") for i in range(8)
        ] + [
            LLMResponse(reasoning="R8", answer="B"),
            LLMResponse(reasoning="R9", answer="C"),
        ]
        
        mock_interface = MockReflectionInterface(responses_strong)
        config = ReflectionConfig(
            llm_interface=mock_interface, 
            target_responses=10,
            confidence_threshold=1.1,  # Prevent early stopping
            entropy_mode="off"  # Disable entropy-based stopping
        )
        
        agent = SelfReflectionAgent(config, "Strong consensus test")
        result = agent.process_question()
        
        assert result.consensus_type == "strong"
        assert result.entropy_level in ["concentrated", "scattered"]  # Should be low entropy
        
        # Emerging consensus: 40%, 30%, 20%, 10%
        responses_emerging = [
            LLMResponse(reasoning=f"R{i}", answer="A") for i in range(4)
        ] + [
            LLMResponse(reasoning=f"R{i}", answer="B") for i in range(4, 7)
        ] + [
            LLMResponse(reasoning=f"R{i}", answer="C") for i in range(7, 9)
        ] + [
            LLMResponse(reasoning="R9", answer="D")
        ]
        
        mock_interface2 = MockReflectionInterface(responses_emerging)
        config2 = ReflectionConfig(
            llm_interface=mock_interface2, 
            target_responses=10,
            confidence_threshold=1.1,  # Prevent early stopping
            entropy_mode="off"  # Disable entropy-based stopping
        )
        
        agent2 = SelfReflectionAgent(config2, "Emerging consensus test")
        result2 = agent2.process_question()
        
        assert result2.consensus_type == "emerging"
        
        # Binary split: 50%, 50%
        responses_binary = [
            LLMResponse(reasoning=f"R{i}", answer="A") for i in range(5)
        ] + [
            LLMResponse(reasoning=f"R{i}", answer="B") for i in range(5, 10)
        ]
        
        mock_interface3 = MockReflectionInterface(responses_binary)
        config3 = ReflectionConfig(
            llm_interface=mock_interface3, 
            target_responses=10,
            confidence_threshold=1.1,  # Prevent early stopping
            entropy_mode="off"  # Disable entropy-based stopping
        )
        
        agent3 = SelfReflectionAgent(config3, "Binary split test")
        result3 = agent3.process_question()
        
        assert result3.consensus_type == "binary"


class TestEntropyEarlyStopping:
    """Tests for entropy-aware early stopping functionality."""
    
    def test_entropy_only_early_stopping(self):
        """Test early stopping based purely on entropy threshold."""
        # Converging responses (high confidence, low entropy)
        responses = [
            LLMResponse(reasoning="R1", answer="Consensus"),
            LLMResponse(reasoning="R2", answer="Consensus"),
            LLMResponse(reasoning="R3", answer="Consensus"),
            LLMResponse(reasoning="R4", answer="Consensus"),
            LLMResponse(reasoning="R5", answer="Other"),      # 80% vs 20%
            # Should stop here due to low entropy
            LLMResponse(reasoning="Extra", answer="Consensus"),
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=10,
            entropy_mode="entropy_only",
            entropy_threshold=0.5,  # Stop when entropy drops below 0.5
            min_entropy_samples=4,
            min_responses=4
        )
        
        agent = SelfReflectionAgent(config, "Entropy stopping test")
        result = agent.process_question()
        
        assert result.early_stopping is True
        assert result.total_responses >= 4  # Should stop after reaching entropy threshold
        assert result.normalized_entropy <= 0.5  # Entropy should be low
    
    def test_combined_confidence_entropy_stopping(self):
        """Test combined scoring mode for early stopping."""
        responses = [
            LLMResponse(reasoning="R1", answer="Answer"),
            LLMResponse(reasoning="R2", answer="Answer"),
            LLMResponse(reasoning="R3", answer="Answer"),
            LLMResponse(reasoning="R4", answer="Answer"),
            LLMResponse(reasoning="R5", answer="Answer"),  # 100% confidence, 0 entropy
            # Should trigger combined early stopping
            LLMResponse(reasoning="Extra", answer="Answer"),
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=10,
            entropy_mode="combined",
            confidence_threshold=0.8,
            entropy_threshold=0.3,
            entropy_weight=0.3,
            min_responses=3,
            min_entropy_samples=3
        )
        
        agent = SelfReflectionAgent(config, "Combined stopping test")
        result = agent.process_question()
        
        assert result.early_stopping is True
        assert result.total_responses >= 3  # Should stop after meeting combined criteria
        assert result.consensus_confidence >= 0.8
        assert result.normalized_entropy <= 0.3
    
    def test_entropy_mode_selection(self):
        """Test different entropy modes work correctly."""
        responses = [LLMResponse(reasoning=f"R{i}", answer="Same") for i in range(6)]
        
        # Test "off" mode (should use confidence only)
        mock_interface1 = MockReflectionInterface(responses)
        config1 = ReflectionConfig(
            llm_interface=mock_interface1,
            entropy_mode="off",
            confidence_threshold=0.7,
            min_responses=3
        )
        
        agent1 = SelfReflectionAgent(config1, "Mode off test")
        result1 = agent1.process_question()
        
        assert result1.early_stopping is True  # Should stop on confidence alone
        
        # Test "confidence_only" mode (same as off)
        mock_interface2 = MockReflectionInterface(responses)
        config2 = ReflectionConfig(
            llm_interface=mock_interface2,
            entropy_mode="confidence_only",
            confidence_threshold=0.7,
            min_responses=3
        )
        
        agent2 = SelfReflectionAgent(config2, "Mode confidence_only test")
        result2 = agent2.process_question()
        
        assert result2.early_stopping is True


class TestEntropyEvolution:
    """Tests for entropy evolution tracking over multiple responses."""
    
    def test_entropy_evolution_tracking(self):
        """Test entropy changes as responses accumulate."""
        # Start scattered, then converge
        responses = [
            LLMResponse(reasoning="R1", answer="A"),     # 100% A
            LLMResponse(reasoning="R2", answer="B"),     # 50% A, 50% B  
            LLMResponse(reasoning="R3", answer="A"),     # 67% A, 33% B
            LLMResponse(reasoning="R4", answer="A"),     # 75% A, 25% B
            LLMResponse(reasoning="R5", answer="A"),     # 80% A, 20% B
        ]
        
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(llm_interface=mock_interface, target_responses=5)
        
        agent = SelfReflectionAgent(config, "Entropy evolution test")
        result = agent.process_question()
        
        # Check that entropy evolution is tracked
        convergence = result.convergence_analysis
        assert "entropy_evolution" in convergence
        assert len(convergence["entropy_evolution"]) == 5
        
        # Entropy should generally decrease as consensus emerges
        entropies = convergence["entropy_evolution"]
        assert entropies[0] == 0.0  # Single answer = no entropy
        assert entropies[1] == 1.0  # Binary 50/50 = max entropy for 2 options
        assert entropies[4] < entropies[1]  # Should decrease as A dominates
        
        # Check entropy convergence metrics
        assert "entropy_convergence_rate" in convergence
        assert "entropy_final_stability" in convergence


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
            target_responses=5,
            entropy_mode="off"  # Disable entropy-based stopping
        )
        
        agent2 = SelfReflectionAgent(config2, "Question")
        result2 = agent2.process_question()
        
        assert result2.early_stopping is False
        assert result2.total_responses == 5  # Used all responses
    
    def test_entropy_config_validation(self):
        """Test entropy configuration parameter validation."""
        responses = [LLMResponse(reasoning=f"R{i}", answer="Test") for i in range(6)]
        
        # Test entropy threshold boundaries
        mock_interface = MockReflectionInterface(responses)
        config = ReflectionConfig(
            llm_interface=mock_interface,
            entropy_threshold=0.0,  # Very restrictive
            entropy_mode="entropy_only",
            min_entropy_samples=3,
            min_responses=3
        )
        
        agent = SelfReflectionAgent(config, "Entropy config test")
        result = agent.process_question()
        
        # With identical responses, entropy = 0, should stop early
        assert result.early_stopping is True
        assert result.normalized_entropy == 0.0