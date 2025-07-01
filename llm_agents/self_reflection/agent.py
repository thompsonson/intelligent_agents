"""Self-reflection agent with confidence-aware early stopping.

This module implements a utility-based agent that balances consensus confidence
against computational cost, providing full probability distributions and
uncertainty awareness.
"""

import math
from collections import Counter
from typing import List, Dict, Any
from ..common.domain import LLMResponse
from .config import ReflectionConfig
from .domain import ReflectionResult


class SelfReflectionAgent:
    """Agent with confidence-aware early stopping and uncertainty assessment."""
    
    def __init__(self, config: ReflectionConfig, question: str):
        """Initialize the self-reflection agent.
        
        Args:
            config: Configuration with LLM interface and thresholds
            question: The question to process
        """
        self._config = config
        self._question = question
        self._llm_responses: List[LLMResponse] = []
    
    def process_question(self) -> ReflectionResult:
        """Process question with confidence-aware early stopping.
        
        Returns:
            ReflectionResult with probability distribution and confidence analysis
        """
        for i in range(self._config.target_responses):
            # Generate LLM response
            response = self._config.llm_interface.generate_llm_response(
                self._config.prompt_template, self._question
            )
            self._llm_responses.append(self._parse_llm_output(response))
            
            # Check early stopping after minimum responses
            if i >= self._config.min_responses - 1:
                confidence = self._calculate_consensus_confidence()
                if confidence >= self._config.confidence_threshold:
                    return self._build_reflection_result(early_stopping=True)
        
        # Max responses reached
        return self._build_reflection_result(early_stopping=False)
    
    def _parse_llm_output(self, response: LLMResponse) -> LLMResponse:
        """Parse LLM output (already structured by LLMInterface).
        
        Args:
            response: LLMResponse from the interface
            
        Returns:
            The same LLMResponse (no additional parsing needed)
        """
        return response
    
    def _calculate_consensus_confidence(self) -> float:
        """Calculate confidence using max probability method.
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        distribution = self._calculate_distribution()
        return max(distribution.values()) if distribution else 0.0
    
    def _calculate_distribution(self) -> Dict[str, float]:
        """Calculate normalized probability distribution over answers.
        
        Returns:
            Dictionary mapping answers to their normalized probabilities
        """
        answers = [response.answer for response in self._llm_responses]
        counts = Counter(answers)
        total = sum(counts.values())
        
        if total == 0:
            return {}
        
        return {answer: count / total for answer, count in counts.items()}
    
    def _assess_convergence(self) -> Dict[str, Any]:
        """Analyze how consensus is emerging over time.
        
        Returns:
            Dictionary with convergence analysis metrics
        """
        if len(self._llm_responses) < 2:
            return {
                'confidence_evolution': [0.0] if self._llm_responses else [],
                'convergence_rate': 0.0,
                'final_stability': 1.0
            }
        
        confidences_over_time = []
        
        # Calculate confidence evolution
        for i in range(1, len(self._llm_responses) + 1):
            subset_responses = self._llm_responses[:i]
            answers = [response.answer for response in subset_responses]
            counts = Counter(answers)
            total = sum(counts.values())
            
            if total > 0:
                max_count = max(counts.values())
                confidence = max_count / total
            else:
                confidence = 0.0
            
            confidences_over_time.append(confidence)
        
        return {
            'confidence_evolution': confidences_over_time,
            'convergence_rate': self._calculate_convergence_rate(confidences_over_time),
            'final_stability': self._assess_stability(confidences_over_time)
        }
    
    def _calculate_convergence_rate(self, confidences: List[float]) -> float:
        """Calculate how quickly confidence increased.
        
        Args:
            confidences: List of confidence values over time
            
        Returns:
            Average rate of confidence increase per response
        """
        if len(confidences) < 2:
            return 0.0
        return (confidences[-1] - confidences[0]) / len(confidences)
    
    def _assess_stability(self, confidences: List[float]) -> float:
        """Assess stability of final confidence.
        
        Args:
            confidences: List of confidence values over time
            
        Returns:
            Stability score (1.0 = perfectly stable, lower = less stable)
        """
        if len(confidences) < 3:
            return 1.0
        
        last_three = confidences[-3:]
        return 1.0 - (max(last_three) - min(last_three))
    
    def _categorize_uncertainty(self, distribution: Dict[str, float]) -> str:
        """Categorize agent's uncertainty about consensus.
        
        Args:
            distribution: Probability distribution over answers
            
        Returns:
            Uncertainty level: "low", "medium", or "high"
        """
        if not distribution:
            return "high"
        
        max_prob = max(distribution.values())
        if max_prob >= 0.8:
            return "low"
        elif max_prob >= 0.6:
            return "medium"
        else:
            return "high"
    
    def _build_reflection_result(self, early_stopping: bool) -> ReflectionResult:
        """Build the final reflection result.
        
        Args:
            early_stopping: Whether early stopping occurred
            
        Returns:
            Complete ReflectionResult with all analysis
        """
        distribution = self._calculate_distribution()
        
        # Get most likely answer
        if distribution:
            final_answer = max(distribution.items(), key=lambda x: x[1])[0]
        else:
            final_answer = "No consensus reached"
        
        # Calculate confidence and uncertainty
        consensus_confidence = self._calculate_consensus_confidence()
        uncertainty_level = self._categorize_uncertainty(distribution)
        
        # Perform convergence analysis
        convergence_analysis = self._assess_convergence()
        
        return ReflectionResult(
            final_answer=final_answer,
            consensus_confidence=consensus_confidence,
            answer_distribution=distribution,
            uncertainty_level=uncertainty_level,
            early_stopping=early_stopping,
            total_responses=len(self._llm_responses),
            convergence_analysis=convergence_analysis
        )