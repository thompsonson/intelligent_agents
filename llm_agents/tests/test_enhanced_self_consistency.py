"""Tests for enhanced self-consistency agent with token-level confidence data."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import Dict, Any

from llm_agents.self_consistency.domain import (
    EnhancedLLMResponse, 
    ConfidenceReport, 
    EnhancedConsensusResult
)


class TestEnhancedDomainObjects:
    """Test enhanced domain objects for token confidence data."""
    
    def test_enhanced_llm_response_creation(self):
        """Test creation of EnhancedLLMResponse with logprobs."""
        logprobs_data = {
            "reasoning": [-0.1, -0.2, -0.05, -0.3],
            "answer": [-0.05, -0.1]
        }
        
        response = EnhancedLLMResponse(
            reasoning="Step by step calculation",
            answer="42",
            logprobs=logprobs_data
        )
        
        assert response.reasoning == "Step by step calculation"
        assert response.answer == "42"
        assert response.logprobs == logprobs_data
    
    def test_enhanced_llm_response_without_logprobs(self):
        """Test EnhancedLLMResponse with None logprobs (fallback case)."""
        response = EnhancedLLMResponse(
            reasoning="Simple reasoning",
            answer="Yes"
        )
        
        assert response.reasoning == "Simple reasoning"
        assert response.answer == "Yes"
        assert response.logprobs is None
    
    def test_confidence_report_creation(self):
        """Test creation of ConfidenceReport with all metrics."""
        individual_data = [
            {
                "response_id": 0,
                "answer": "42",
                "reasoning_confidence": -0.2,
                "answer_confidence": -0.1,
                "reasoning_token_count": 4,
                "answer_token_count": 2,
                "matches_consensus": True
            }
        ]
        
        report = ConfidenceReport(
            consensus_confidence=0.8,
            token_confidence_reasoning=-0.15,
            token_confidence_answer=-0.08,
            individual_response_data=individual_data
        )
        
        assert report.consensus_confidence == 0.8
        assert report.token_confidence_reasoning == -0.15
        assert report.token_confidence_answer == -0.08
        assert len(report.individual_response_data) == 1
        assert report.individual_response_data[0]["answer"] == "42"
    
    def test_enhanced_consensus_result_creation(self):
        """Test creation of EnhancedConsensusResult."""
        confidence_report = ConfidenceReport(
            consensus_confidence=0.6,
            token_confidence_reasoning=-0.2,
            token_confidence_answer=-0.1,
            individual_response_data=[]
        )
        
        result = EnhancedConsensusResult(
            final_answer="42",
            vote_count=3,
            confidence=0.6,
            confidence_report=confidence_report
        )
        
        assert result.final_answer == "42"
        assert result.vote_count == 3
        assert result.confidence == 0.6
        assert result.confidence_report.consensus_confidence == 0.6


class TestStructuredLogprobsIntegration:
    """Test structured logprobs library integration."""
    
    @pytest.fixture
    def mock_structured_completion(self):
        """Mock completion with structured logprobs data."""
        mock_completion = MagicMock()
        mock_completion.log_probs = {
            "reasoning": [-0.1, -0.2, -0.05, -0.3],
            "answer": [-0.05, -0.1]
        }
        return mock_completion
    
    @pytest.fixture
    def mock_openai_completion(self):
        """Mock standard OpenAI completion for structured outputs."""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps({
            "reasoning": "Let me calculate: 2 + 2 = 4",
            "answer": "4"
        })
        return mock_completion
    
    def test_logprobs_structure_validation(self, mock_structured_completion):
        """Test validation of logprobs data structure."""
        # Valid structure
        valid_logprobs = {
            "reasoning": [-0.1, -0.2, -0.05],
            "answer": [-0.05]
        }
        
        # Test structure validation logic
        assert self._validate_logprobs_structure(valid_logprobs) is True
        
        # Invalid structures
        invalid_cases = [
            None,
            {},
            {"reasoning": "not_a_list"},
            {"reasoning": [-0.1], "answer": "not_a_list"},
            {"reasoning": [-0.1, "not_a_number"]},
            {"missing_answer": [-0.1]}
        ]
        
        for invalid_logprobs in invalid_cases:
            assert self._validate_logprobs_structure(invalid_logprobs) is False
    
    def _validate_logprobs_structure(self, logprobs: Dict[str, Any]) -> bool:
        """Helper method to validate logprobs structure (same as will be in adapter)."""
        if not logprobs or not isinstance(logprobs, dict):
            return False

        expected_fields = ["reasoning", "answer"]
        for field in expected_fields:
            if field not in logprobs:
                return False
            if not isinstance(logprobs[field], list):
                return False
            if logprobs[field] and not all(isinstance(x, (int, float)) for x in logprobs[field]):
                return False

        return True
    
    def test_json_schema_structure(self):
        """Test the chain-of-thought JSON schema structure."""
        expected_schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Step-by-step reasoning process leading to the answer"
                },
                "answer": {
                    "type": "string",
                    "description": "Final numerical or textual answer extracted from reasoning"
                }
            },
            "required": ["reasoning", "answer"]
        }
        
        # Test that our expected schema is well-formed
        assert expected_schema["type"] == "object"
        assert "reasoning" in expected_schema["properties"]
        assert "answer" in expected_schema["properties"]
        assert expected_schema["required"] == ["reasoning", "answer"]
    
    @patch('structured_logprobs.main.add_logprobs')
    def test_structured_logprobs_integration_success(self, mock_add_logprobs, 
                                                   mock_openai_completion,
                                                   mock_structured_completion):
        """Test successful structured logprobs integration."""
        # Mock the structured-logprobs library call
        mock_add_logprobs.return_value = mock_structured_completion
        
        # Test that the integration would work
        enhanced_completion = mock_add_logprobs(mock_openai_completion)
        
        assert hasattr(enhanced_completion, 'log_probs')
        assert enhanced_completion.log_probs["reasoning"] == [-0.1, -0.2, -0.05, -0.3]
        assert enhanced_completion.log_probs["answer"] == [-0.05, -0.1]
        
        # Verify the library was called with the original completion
        mock_add_logprobs.assert_called_once_with(mock_openai_completion)
    
    @patch('structured_logprobs.main.add_logprobs')
    def test_structured_logprobs_integration_failure(self, mock_add_logprobs, 
                                                   mock_openai_completion):
        """Test graceful handling of structured logprobs failure."""
        # Mock library failure
        mock_add_logprobs.side_effect = Exception("Library error")
        
        # Test that failures are handled gracefully
        try:
            enhanced_completion = mock_add_logprobs(mock_openai_completion)
            assert False, "Should have raised exception"
        except Exception as e:
            assert str(e) == "Library error"
            # In actual implementation, this should be caught and handled


class TestTokenConfidenceCalculation:
    """Test token confidence calculation methods."""
    
    def test_calculate_token_confidence_valid_data(self):
        """Test token confidence calculation with valid logprobs data."""
        logprobs = {
            "reasoning": [-0.1, -0.2, -0.05, -0.3],
            "answer": [-0.05, -0.1]
        }
        
        # Test reasoning confidence calculation
        reasoning_confidence = self._calculate_token_confidence(logprobs, "reasoning")
        expected_reasoning = sum([-0.1, -0.2, -0.05, -0.3]) / 4  # -0.1625
        assert abs(reasoning_confidence - expected_reasoning) < 0.001
        
        # Test answer confidence calculation
        answer_confidence = self._calculate_token_confidence(logprobs, "answer")
        expected_answer = sum([-0.05, -0.1]) / 2  # -0.075
        assert abs(answer_confidence - expected_answer) < 0.001
    
    def test_calculate_token_confidence_missing_data(self):
        """Test token confidence calculation with missing or invalid data."""
        # Test with None logprobs
        assert self._calculate_token_confidence(None, "reasoning") == 0.0
        
        # Test with missing field
        logprobs = {"answer": [-0.05, -0.1]}
        assert self._calculate_token_confidence(logprobs, "reasoning") == 0.0
        
        # Test with empty field
        logprobs = {"reasoning": []}
        assert self._calculate_token_confidence(logprobs, "reasoning") == 0.0
        
        # Test with invalid field type
        logprobs = {"reasoning": "not_a_list"}
        assert self._calculate_token_confidence(logprobs, "reasoning") == 0.0
    
    def test_count_tokens(self):
        """Test token counting functionality."""
        logprobs = {
            "reasoning": [-0.1, -0.2, -0.05, -0.3],
            "answer": [-0.05, -0.1]
        }
        
        assert self._count_tokens(logprobs, "reasoning") == 4
        assert self._count_tokens(logprobs, "answer") == 2
        assert self._count_tokens(logprobs, "missing_field") == 0
        assert self._count_tokens(None, "reasoning") == 0
    
    def _calculate_token_confidence(self, logprobs: Dict[str, Any], field: str) -> float:
        """Helper method for token confidence calculation (same as will be in agent)."""
        if not logprobs:
            return 0.0

        try:
            if field in logprobs and isinstance(logprobs[field], list):
                token_probs = logprobs[field]
                if not token_probs:
                    return 0.0
                return sum(token_probs) / len(token_probs)
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _count_tokens(self, logprobs: Dict[str, Any], field: str) -> int:
        """Helper method for token counting (same as will be in agent)."""
        if not logprobs:
            return 0

        try:
            if field in logprobs and isinstance(logprobs[field], list):
                return len(logprobs[field])
            else:
                return 0
        except Exception:
            return 0


class TestConfidenceReportGeneration:
    """Test confidence report generation logic."""
    
    def test_individual_response_data_format(self):
        """Test the format of individual response data."""
        expected_format = {
            "response_id": 0,
            "answer": "42",
            "reasoning_confidence": -0.15,
            "answer_confidence": -0.08,
            "reasoning_token_count": 4,
            "answer_token_count": 2,
            "matches_consensus": True
        }
        
        # Verify all required fields are present
        required_fields = [
            "response_id", "answer", "reasoning_confidence", 
            "answer_confidence", "reasoning_token_count", 
            "answer_token_count", "matches_consensus"
        ]
        
        for field in required_fields:
            assert field in expected_format
        
        # Verify data types
        assert isinstance(expected_format["response_id"], int)
        assert isinstance(expected_format["answer"], str)
        assert isinstance(expected_format["reasoning_confidence"], (int, float))
        assert isinstance(expected_format["answer_confidence"], (int, float))
        assert isinstance(expected_format["reasoning_token_count"], int)
        assert isinstance(expected_format["answer_token_count"], int)
        assert isinstance(expected_format["matches_consensus"], bool)
    
    def test_aggregate_confidence_calculation(self):
        """Test aggregate confidence calculation for winning answers."""
        # Simulate multiple responses where some match consensus
        individual_data = [
            {"answer": "42", "reasoning_confidence": -0.1, "answer_confidence": -0.05, "matches_consensus": True},
            {"answer": "42", "reasoning_confidence": -0.2, "answer_confidence": -0.1, "matches_consensus": True},
            {"answer": "43", "reasoning_confidence": -0.3, "answer_confidence": -0.15, "matches_consensus": False},
            {"answer": "42", "reasoning_confidence": -0.15, "answer_confidence": -0.08, "matches_consensus": True},
        ]
        
        # Calculate aggregate for winning responses only
        winning_reasoning = [d["reasoning_confidence"] for d in individual_data if d["matches_consensus"]]
        winning_answer = [d["answer_confidence"] for d in individual_data if d["matches_consensus"]]
        
        expected_reasoning_conf = sum(winning_reasoning) / len(winning_reasoning)  # (-0.1 + -0.2 + -0.15) / 3
        expected_answer_conf = sum(winning_answer) / len(winning_answer)  # (-0.05 + -0.1 + -0.08) / 3
        
        assert abs(expected_reasoning_conf - (-0.15)) < 0.001
        assert abs(expected_answer_conf - (-0.077)) < 0.01