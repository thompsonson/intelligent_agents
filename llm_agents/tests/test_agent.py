"""Tests for SelfConsistencyAgent core logic."""

import pytest
import time
from unittest.mock import Mock, MagicMock
from collections import Counter

from llm_agents.self_consistency.agent import SelfConsistencyAgent
from llm_agents.self_consistency.domain import ConsensusResult
from llm_agents.common.domain import LLMResponse
from llm_agents.self_consistency.config import AgentConfig
from llm_agents.common.interfaces import LLMInterface


class MockLLMInterface(LLMInterface):
    """Mock LLM interface for testing."""
    
    def __init__(self, responses):
        """Initialize with predefined responses."""
        self.responses = responses
        self.call_count = 0
    
    def generate_llm_response(self, prompt: str, question: str) -> LLMResponse:
        """Return predefined responses in sequence."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        else:
            # Return last response if we run out
            return self.responses[-1]


class TestSelfConsistencyAgent:
    """Agent Core Logic Tests."""
    
    def test_majority_vote_accuracy(self):
        """Test _perform_argmax() with known inputs."""
        # Setup agent with mock responses
        mock_responses = [
            LLMResponse(reasoning="reason1", answer="A"),
            LLMResponse(reasoning="reason2", answer="B"),
            LLMResponse(reasoning="reason3", answer="A"),
            LLMResponse(reasoning="reason4", answer="A"),
            LLMResponse(reasoning="reason5", answer="B")
        ]
        
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(llm_interface=mock_llm, target_responses=5)
        agent = SelfConsistencyAgent(config, "Test question")
        
        # Manually set responses to test _perform_argmax
        agent._llm_responses = mock_responses
        answer, count = agent._perform_argmax()
        
        assert answer == "A"  # A appears 3 times, B appears 2 times
        assert count == 3
    
    def test_unanimous_consensus(self):
        """Test when all responses have the same answer."""
        mock_responses = [
            LLMResponse(reasoning="reason1", answer="yes"),
            LLMResponse(reasoning="reason2", answer="yes"),
            LLMResponse(reasoning="reason3", answer="yes")
        ]
        
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(llm_interface=mock_llm, target_responses=3)
        agent = SelfConsistencyAgent(config, "Test question")
        
        result = agent.process_question()
        
        assert result.final_answer == "yes"
        assert result.vote_count == 3
        assert result.confidence == 1.0  # 100% confidence
    
    def test_split_decision(self):
        """Test 3-2 vote split."""
        mock_responses = [
            LLMResponse(reasoning="reason1", answer="option1"),
            LLMResponse(reasoning="reason2", answer="option2"),
            LLMResponse(reasoning="reason3", answer="option1"),
            LLMResponse(reasoning="reason4", answer="option1"),
            LLMResponse(reasoning="reason5", answer="option2")
        ]
        
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(llm_interface=mock_llm, target_responses=5)
        agent = SelfConsistencyAgent(config, "Test question")
        
        result = agent.process_question()
        
        assert result.final_answer == "option1"
        assert result.vote_count == 3
        assert result.confidence == 0.6  # 3/5 = 0.6
    
    def test_tie_handling(self):
        """Test 2-2 tie (Counter.most_common() returns first encountered)."""
        mock_responses = [
            LLMResponse(reasoning="reason1", answer="A"),
            LLMResponse(reasoning="reason2", answer="B"),
            LLMResponse(reasoning="reason3", answer="A"),
            LLMResponse(reasoning="reason4", answer="B")
        ]
        
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(llm_interface=mock_llm, target_responses=4)
        agent = SelfConsistencyAgent(config, "Test question")
        
        result = agent.process_question()
        
        # Counter.most_common() returns the first encountered when tied
        assert result.final_answer in ["A", "B"]
        assert result.vote_count == 2
        assert result.confidence == 0.5  # 2/4 = 0.5
    
    def test_o_m_complexity(self):
        """Performance test for O(m) complexity."""
        # Create large number of responses to test performance
        large_m = 1000
        mock_responses = [
            LLMResponse(reasoning=f"reason{i}", answer=f"answer_{i % 10}")
            for i in range(large_m)
        ]
        
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(llm_interface=mock_llm, target_responses=large_m)
        agent = SelfConsistencyAgent(config, "Test question")
        
        # Manually set responses to test just the argmax performance
        agent._llm_responses = mock_responses
        
        # Time the argmax operation
        start_time = time.time()
        answer, count = agent._perform_argmax()
        end_time = time.time()
        
        # Should complete quickly (under 1 second for 1000 responses)
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should be much faster with O(m)
        
        # Verify correctness - each answer appears 100 times (1000/10)
        assert count == 100
        assert answer.startswith("answer_")


class TestAgentIntegration:
    """Integration Tests."""
    
    def test_mock_llm_responses_full_flow(self):
        """Test full process_question() flow with mocked responses."""
        mock_responses = [
            LLMResponse(reasoning="Let me think...", answer="42"),
            LLMResponse(reasoning="Considering...", answer="42"),
            LLMResponse(reasoning="After analysis...", answer="41"),
            LLMResponse(reasoning="My conclusion...", answer="42")
        ]
        
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(
            llm_interface=mock_llm, 
            target_responses=4,
            prompt_template="Solve this carefully:"
        )
        agent = SelfConsistencyAgent(config, "What is the answer?")
        
        result = agent.process_question()
        
        assert result.final_answer == "42"  # 3 votes for "42", 1 for "41"
        assert result.vote_count == 3
        assert result.confidence == 0.75  # 3/4 = 0.75
        assert mock_llm.call_count == 4  # Verify all responses were used
    
    def test_different_response_counts(self):
        """Test with different values of m."""
        # Test with m=1
        mock_responses = [LLMResponse(reasoning="single", answer="only")]
        mock_llm = MockLLMInterface(mock_responses)
        config = AgentConfig(llm_interface=mock_llm, target_responses=1)
        agent = SelfConsistencyAgent(config, "Test")
        
        result = agent.process_question()
        assert result.final_answer == "only"
        assert result.vote_count == 1
        assert result.confidence == 1.0
        
        # Test with m=10
        mock_responses_10 = [
            LLMResponse(reasoning=f"reasoning{i}", answer="common")
            for i in range(10)
        ]
        mock_llm_10 = MockLLMInterface(mock_responses_10)
        config_10 = AgentConfig(llm_interface=mock_llm_10, target_responses=10)
        agent_10 = SelfConsistencyAgent(config_10, "Test")
        
        result_10 = agent_10.process_question()
        assert result_10.final_answer == "common"
        assert result_10.vote_count == 10
        assert result_10.confidence == 1.0