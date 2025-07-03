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
            
            # Check early stopping using smart entropy-aware logic
            if self._should_stop_early(i + 1):  # i+1 because i is 0-indexed
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
    
    def _calculate_entropy(self, distribution: Dict[str, float] = None) -> float:
        """Calculate Shannon entropy from probability distribution.
        
        Args:
            distribution: Probability distribution dict. If None, uses current distribution.
            
        Returns:
            Shannon entropy value (higher = more scattered/uncertain)
        """
        if distribution is None:
            distribution = self._calculate_distribution()
        
        if not distribution:
            return 0.0
        
        # Shannon entropy: H = -Σ(p * log2(p))
        entropy = 0.0
        for probability in distribution.values():
            if probability > 0:  # Avoid log(0)
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _calculate_normalized_entropy(self, distribution: Dict[str, float] = None) -> float:
        """Calculate normalized entropy (0.0 = concentrated, 1.0 = uniform).
        
        Args:
            distribution: Probability distribution dict. If None, uses current distribution.
            
        Returns:
            Normalized entropy between 0.0 and 1.0
        """
        if distribution is None:
            distribution = self._calculate_distribution()
        
        if not distribution or len(distribution) <= 1:
            return 0.0  # Single answer = perfectly concentrated
        
        entropy = self._calculate_entropy(distribution)
        max_entropy = math.log2(len(distribution))  # Uniform distribution entropy
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _get_entropy_level(self, normalized_entropy: float) -> str:
        """Convert normalized entropy to human-readable level.
        
        Args:
            normalized_entropy: Normalized entropy (0.0-1.0)
            
        Returns:
            Entropy level: "concentrated", "scattered", or "uniform"
        """
        if normalized_entropy <= 0.2:
            return "concentrated"  # Very low entropy - clear consensus
        elif normalized_entropy <= 0.7:
            return "scattered"     # Medium entropy - some disagreement
        else:
            return "uniform"       # High entropy - very scattered responses
    
    def _classify_consensus_type(self, distribution: Dict[str, float] = None) -> str:
        """Classify the type of consensus from the distribution pattern.
        
        Args:
            distribution: Probability distribution dict. If None, uses current distribution.
            
        Returns:
            Consensus type: "strong", "emerging", "divided", or "binary"
        """
        if distribution is None:
            distribution = self._calculate_distribution()
        
        if not distribution:
            return "undefined"
        
        probabilities = sorted(distribution.values(), reverse=True)
        max_prob = probabilities[0]
        
        # Binary split: Two main answers roughly equal (check this first)
        if len(probabilities) >= 2 and probabilities[1] >= 0.35:
            if abs(probabilities[0] - probabilities[1]) <= 0.15:
                return "binary"
        
        # Strong consensus: One answer dominates significantly (80%+)
        if max_prob >= 0.8:
            return "strong"
        
        # Emerging consensus: One answer leading but not dominant (40-79%)
        if max_prob >= 0.4:
            return "emerging"
        
        # Divided: No clear leader (under 40%)
        return "divided"
    
    def _should_stop_early(self, current_responses: int) -> bool:
        """Determine if early stopping should occur based on confidence and entropy.
        
        Args:
            current_responses: Number of responses collected so far
            
        Returns:
            True if should stop early, False to continue sampling
        """
        # Must have minimum responses
        if current_responses < self._config.min_responses:
            return False
        
        # Get current metrics
        distribution = self._calculate_distribution()
        confidence = max(distribution.values()) if distribution else 0.0
        
        # Handle different entropy modes
        if self._config.entropy_mode == "off" or self._config.entropy_mode == "confidence_only":
            # Original behavior: confidence-only stopping
            return confidence >= self._config.confidence_threshold
        
        # Need minimum samples for entropy to be meaningful
        if current_responses < self._config.min_entropy_samples:
            return confidence >= self._config.confidence_threshold
        
        if self._config.entropy_mode == "entropy_only":
            # Stop only based on entropy (low entropy = concentrated)
            normalized_entropy = self._calculate_normalized_entropy(distribution)
            return normalized_entropy <= self._config.entropy_threshold
        
        elif self._config.entropy_mode == "combined":
            # Combined scoring: balance confidence and entropy
            normalized_entropy = self._calculate_normalized_entropy(distribution)
            
            # High confidence overrides entropy concerns
            if confidence >= 0.9:
                return True
            
            # Check confidence threshold first
            if confidence >= self._config.confidence_threshold:
                # High confidence + low entropy = strong consensus, stop early
                if normalized_entropy <= self._config.entropy_threshold:
                    return True
                # High confidence + high entropy = check if really confident
                elif confidence >= 0.8:
                    return True
            
            # Calculate combined score: confidence weighted by entropy concentration
            entropy_factor = 1.0 - (self._config.entropy_weight * normalized_entropy)
            combined_score = confidence * entropy_factor
            
            # Use a slightly lower threshold for combined scoring
            return combined_score >= (self._config.confidence_threshold * 0.9)
        
        # Default fallback
        return confidence >= self._config.confidence_threshold
    
    def _assess_convergence(self) -> Dict[str, Any]:
        """Analyze how consensus is emerging over time.
        
        Returns:
            Dictionary with convergence analysis metrics including entropy evolution
        """
        if len(self._llm_responses) < 2:
            return {
                'confidence_evolution': [0.0] if self._llm_responses else [],
                'entropy_evolution': [0.0] if self._llm_responses else [],
                'convergence_rate': 0.0,
                'final_stability': 1.0,
                'entropy_convergence_rate': 0.0,
                'entropy_final_stability': 1.0
            }
        
        confidences_over_time = []
        entropies_over_time = []
        
        # Calculate confidence and entropy evolution
        for i in range(1, len(self._llm_responses) + 1):
            subset_responses = self._llm_responses[:i]
            answers = [response.answer for response in subset_responses]
            counts = Counter(answers)
            total = sum(counts.values())
            
            # Calculate confidence
            if total > 0:
                max_count = max(counts.values())
                confidence = max_count / total
            else:
                confidence = 0.0
            
            # Calculate entropy for this subset
            if total > 0:
                subset_distribution = {answer: count / total for answer, count in counts.items()}
                entropy = self._calculate_entropy(subset_distribution)
                normalized_entropy = self._calculate_normalized_entropy(subset_distribution)
            else:
                entropy = 0.0
                normalized_entropy = 0.0
            
            confidences_over_time.append(confidence)
            entropies_over_time.append(normalized_entropy)  # Use normalized for consistency
        
        return {
            'confidence_evolution': confidences_over_time,
            'entropy_evolution': entropies_over_time,
            'convergence_rate': self._calculate_convergence_rate(confidences_over_time),
            'final_stability': self._assess_stability(confidences_over_time),
            'entropy_convergence_rate': self._calculate_entropy_convergence_rate(entropies_over_time),
            'entropy_final_stability': self._assess_entropy_stability(entropies_over_time)
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
    
    def _calculate_entropy_convergence_rate(self, entropies: List[float]) -> float:
        """Calculate how quickly entropy decreased (convergence).
        
        Args:
            entropies: List of normalized entropy values over time
            
        Returns:
            Average rate of entropy decrease per response (negative = decreasing entropy)
        """
        if len(entropies) < 2:
            return 0.0
        return (entropies[-1] - entropies[0]) / len(entropies)
    
    def _assess_entropy_stability(self, entropies: List[float]) -> float:
        """Assess stability of final entropy.
        
        Args:
            entropies: List of entropy values over time
            
        Returns:
            Stability score (1.0 = perfectly stable, lower = less stable)
        """
        if len(entropies) < 3:
            return 1.0
        
        last_three = entropies[-3:]
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
        
        # Calculate entropy metrics
        distribution_entropy = self._calculate_entropy(distribution)
        normalized_entropy = self._calculate_normalized_entropy(distribution)
        entropy_level = self._get_entropy_level(normalized_entropy)
        consensus_type = self._classify_consensus_type(distribution)
        
        # Perform convergence analysis
        convergence_analysis = self._assess_convergence()
        
        return ReflectionResult(
            final_answer=final_answer,
            consensus_confidence=consensus_confidence,
            answer_distribution=distribution,
            uncertainty_level=uncertainty_level,
            early_stopping=early_stopping,
            total_responses=len(self._llm_responses),
            convergence_analysis=convergence_analysis,
            distribution_entropy=distribution_entropy,
            normalized_entropy=normalized_entropy,
            entropy_level=entropy_level,
            consensus_type=consensus_type
        )