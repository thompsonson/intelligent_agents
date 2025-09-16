"""Enhanced self-consistency agent with token-level confidence data collection.

This module implements an enhanced version of the self-consistency agent that collects
token-level confidence data alongside traditional consensus-based decision making.
"""

import logging
from collections import Counter
from typing import List, Dict, Any

from .domain import EnhancedLLMResponse, ConfidenceReport, EnhancedConsensusResult
from .config import AgentConfig
from ..common.interfaces import EnhancedLLMInterface


class EnhancedSelfConsistencyAgent:
    """Enhanced self-consistency agent with token confidence data collection.
    
    This agent maintains the same decision-making logic as the original self-consistency
    agent while collecting additional token-level confidence data for analysis.
    """
    
    def __init__(self, config: AgentConfig, question: str):
        """Initialize enhanced agent with configuration and question.
        
        Args:
            config: Agent configuration with enhanced LLM interface
            question: Question to process
        """
        if not isinstance(config.llm_interface, EnhancedLLMInterface):
            raise ValueError("Enhanced agent requires EnhancedLLMInterface")
        
        self._config = config
        self._question = question
        self._llm_responses: List[EnhancedLLMResponse] = []
    
    def process_question(self) -> EnhancedConsensusResult:
        """Process question with token confidence data collection.
        
        Returns:
            EnhancedConsensusResult with traditional consensus + confidence report
        """
        # Clear any previous responses
        self._llm_responses = []

        # Sequential processing: Loop m times (unchanged decision logic)
        for _ in range(self._config.target_responses):
            # Generate LLM response with structured outputs + token probabilities
            llm_response = self._config.llm_interface.generate_enhanced_llm_response(
                self._config.prompt_template,
                self._question
            )
            # Store enhanced response with token data
            self._llm_responses.append(llm_response)

        # Perform traditional argmax (decision logic unchanged)
        final_answer, vote_count = self._perform_argmax()
        consensus_confidence = vote_count / len(self._llm_responses)

        # Generate confidence report (new data collection)
        confidence_report = self._generate_confidence_report(final_answer, vote_count)

        # Return enhanced result with traditional decision + data collection
        return EnhancedConsensusResult(
            final_answer=final_answer,
            vote_count=vote_count,
            confidence=consensus_confidence,  # Traditional consensus confidence
            confidence_report=confidence_report  # Token confidence data
        )
    
    def _perform_argmax(self) -> tuple[str, int]:
        """Perform argmax to find the most frequent answer (unchanged logic).
        
        Returns:
            Tuple of (final_answer, vote_count)
        """
        if not self._llm_responses:
            return "No responses generated", 0
        
        # Extract answers and count votes
        answers = [response.answer for response in self._llm_responses]
        answer_counts = Counter(answers)
        
        # Return the most frequent answer and its count
        final_answer, vote_count = answer_counts.most_common(1)[0]
        return final_answer, vote_count
    
    def _generate_confidence_report(self, winning_answer: str, vote_count: int) -> ConfidenceReport:
        """Generate confidence report for data collection and analysis.
        
        Args:
            winning_answer: The consensus answer
            vote_count: Number of votes for the winning answer
            
        Returns:
            ConfidenceReport with token confidence analytics
        """
        # Calculate token confidence metrics for each response
        individual_data = []
        reasoning_confidences = []
        answer_confidences = []

        for i, response in enumerate(self._llm_responses):
            # Calculate per-response token confidence
            reasoning_conf = self._calculate_token_confidence(response.logprobs, "reasoning")
            answer_conf = self._calculate_token_confidence(response.logprobs, "answer")

            individual_data.append({
                "response_id": i,
                "answer": response.answer,
                "reasoning_confidence": reasoning_conf,
                "answer_confidence": answer_conf,
                "reasoning_token_count": self._count_tokens(response.logprobs, "reasoning"),
                "answer_token_count": self._count_tokens(response.logprobs, "answer"),
                "matches_consensus": response.answer == winning_answer
            })

            # Collect confidences for winning responses only
            if response.answer == winning_answer:
                reasoning_confidences.append(reasoning_conf)
                answer_confidences.append(answer_conf)

        # Aggregate metrics for winning answer
        avg_reasoning_conf = sum(reasoning_confidences) / len(reasoning_confidences) if reasoning_confidences else 0.0
        avg_answer_conf = sum(answer_confidences) / len(answer_confidences) if answer_confidences else 0.0

        return ConfidenceReport(
            consensus_confidence=vote_count / len(self._llm_responses),
            token_confidence_reasoning=avg_reasoning_conf,
            token_confidence_answer=avg_answer_conf,
            individual_response_data=individual_data
        )
    
    def _calculate_token_confidence(self, logprobs: Dict[str, Any], field: str) -> float:
        """Calculate normalized token confidence for specified field.
        
        Args:
            logprobs: Token probability data from structured-logprobs library
                     Expected format: [{"reasoning": float, "answer": float}] or {"reasoning": float, "answer": float}
            field: Field to calculate confidence for ("reasoning" or "answer")
            
        Returns:
            Normalized confidence score between 0.0 and 1.0
        """
        if not logprobs:
            return 0.0

        try:
            # Handle list format from structured-logprobs (take first element)
            if isinstance(logprobs, list):
                if len(logprobs) == 0:
                    return 0.0
                logprobs = logprobs[0]  # Take the first element
            
            # Extract the field-specific confidence value
            if isinstance(logprobs, dict) and field in logprobs:
                raw_confidence = logprobs[field]
                if isinstance(raw_confidence, (int, float)):
                    # Convert cumulative log probability to normalized confidence
                    return self._normalize_logprob_to_confidence(raw_confidence, field)
                else:
                    logging.warning(f"Field '{field}' value is not numeric: {type(raw_confidence)}")
                    return 0.0
            else:
                logging.warning(f"Field '{field}' not found in logprobs: {logprobs}")
                return 0.0
        except Exception as e:
            logging.error(f"Error calculating token confidence for field '{field}': {e}")
            return 0.0
    
    def _count_tokens(self, logprobs: Dict[str, Any], field: str) -> int:
        """Count tokens in specified field using enhanced field-specific text analysis.
        
        Args:
            logprobs: Token probability data from structured-logprobs library  
            field: Field to count tokens for ("reasoning" or "answer")
            
        Returns:
            Estimated number of tokens in the field based on text content
        """
        if not logprobs:
            return 0

        try:
            # Handle list format from structured-logprobs (take first element)
            if isinstance(logprobs, list):
                if len(logprobs) == 0:
                    return 0
                logprobs = logprobs[0]  # Take the first element
            
            # Check if field exists and has valid data
            if isinstance(logprobs, dict) and field in logprobs:
                confidence = logprobs[field]
                if isinstance(confidence, (int, float)):
                    # Get actual text content from the most recent response
                    if self._llm_responses:
                        last_response = self._llm_responses[-1]
                        field_text = getattr(last_response, field, "")
                        # Estimate token count: roughly 4 characters per token
                        # This is a reasonable approximation for GPT-style tokenizers
                        return max(1, len(field_text) // 4)
                    return 1
            return 0
        except Exception as e:
            logging.error(f"Error counting tokens for field '{field}': {e}")
            return 0
    
    def _normalize_logprob_to_confidence(self, raw_logprob: float, field: str) -> float:
        """Convert raw log probability to normalized 0-1 confidence score.
        
        Args:
            raw_logprob: Raw cumulative log probability from structured-logprobs
            field: Field name for context ("reasoning" or "answer")
            
        Returns:
            Normalized confidence score between 0.0 and 1.0
        """
        try:
            # Get token count for normalization
            token_count = self._count_tokens(self._llm_responses[-1].logprobs if self._llm_responses else {}, field)
            
            if token_count == 0:
                return 0.0
            
            # Calculate per-token average log probability
            avg_logprob = raw_logprob / token_count
            
            # Convert to probability using exponential (log prob -> prob)
            probability = min(1.0, max(0.0, 2 ** avg_logprob))
            
            # Apply confidence transformation to emphasize high-confidence regions
            # This maps: 0.5 -> 0.0, 1.0 -> 1.0, creating more intuitive scaling
            if probability < 0.5:
                normalized_confidence = 0.0
            else:
                normalized_confidence = 2 * (probability - 0.5)
            
            return min(1.0, max(0.0, normalized_confidence))
            
        except Exception as e:
            logging.error(f"Error normalizing logprob for field '{field}': {e}")
            return 0.0


class ConfidenceDataExporter:
    """Utility class for exporting confidence data for analysis."""
    
    @staticmethod
    def export_to_dict(result: EnhancedConsensusResult) -> Dict[str, Any]:
        """Export enhanced consensus result to dictionary format.
        
        Args:
            result: Enhanced consensus result with confidence data
            
        Returns:
            Dictionary representation suitable for JSON/CSV export
        """
        return {
            "final_answer": result.final_answer,
            "vote_count": result.vote_count,
            "total_responses": len(result.confidence_report.individual_response_data),
            "consensus_confidence": result.confidence_report.consensus_confidence,
            "token_confidence_reasoning": result.confidence_report.token_confidence_reasoning,
            "token_confidence_answer": result.confidence_report.token_confidence_answer,
            "individual_responses": result.confidence_report.individual_response_data
        }
    
    @staticmethod
    def export_to_csv_rows(result: EnhancedConsensusResult) -> List[Dict[str, Any]]:
        """Export enhanced consensus result to CSV-friendly row format.
        
        Args:
            result: Enhanced consensus result with confidence data
            
        Returns:
            List of dictionaries, one per individual response
        """
        base_data = {
            "final_answer": result.final_answer,
            "vote_count": result.vote_count,
            "total_responses": len(result.confidence_report.individual_response_data),
            "consensus_confidence": result.confidence_report.consensus_confidence,
            "aggregate_token_confidence_reasoning": result.confidence_report.token_confidence_reasoning,
            "aggregate_token_confidence_answer": result.confidence_report.token_confidence_answer,
        }
        
        rows = []
        for response_data in result.confidence_report.individual_response_data:
            row = {**base_data, **response_data}
            rows.append(row)
        
        return rows