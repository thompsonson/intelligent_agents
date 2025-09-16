"""Unified wrapper for both self-consistency and self-reflection agents.

This module provides a common interface for interacting with both agent types
through the Gradio interface, handling configuration and result formatting.
"""

from typing import Dict, Any, Union, Optional, List
from dataclasses import dataclass
from enum import Enum
import time

from ..common.interfaces import LiteLLMAdapter, EnhancedLiteLLMAdapter
from .debug_adapter import DebugLiteLLMAdapter
from ..self_consistency.agent import SelfConsistencyAgent
from ..self_consistency.enhanced_agent import EnhancedSelfConsistencyAgent, ConfidenceDataExporter
from ..self_consistency.config import AgentConfig
from ..self_consistency.domain import ConsensusResult, EnhancedConsensusResult
from ..self_reflection.agent import SelfReflectionAgent
from ..self_reflection.config import ReflectionConfig
from ..self_reflection.domain import ReflectionResult


class AgentType(Enum):
    """Available agent types."""
    SELF_CONSISTENCY = "self_consistency"
    ENHANCED_SELF_CONSISTENCY = "enhanced_self_consistency"
    SELF_REFLECTION = "self_reflection"


@dataclass
class DebugInfo:
    """Debug information for LLM requests and responses."""
    requests: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    parsed_answers: List[str]
    
@dataclass
class UnifiedResult:
    """Unified result format for display in Gradio interface."""
    agent_type: str
    final_answer: str
    confidence: float
    total_responses: int
    early_stopping: bool
    answer_distribution: Dict[str, float]
    uncertainty_level: str
    convergence_analysis: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    debug_info: Optional[DebugInfo] = None
    
    # Entropy-based intelligence fields (self-reflection only)
    distribution_entropy: Optional[float] = None  # Raw Shannon entropy value
    normalized_entropy: Optional[float] = None  # Entropy normalized by max possible (0.0-1.0)
    entropy_level: Optional[str] = None  # "concentrated", "scattered", "uniform"
    consensus_type: Optional[str] = None  # "strong", "emerging", "divided", "binary"
    
    # Token confidence fields (enhanced self-consistency only)
    token_confidence_reasoning: Optional[float] = None  # Normalized reasoning confidence (0.0-1.0)
    token_confidence_answer: Optional[float] = None  # Normalized answer confidence (0.0-1.0)
    individual_response_confidence: Optional[List[Dict[str, Any]]] = None  # Per-response token confidence data


class AgentWrapper:
    """Unified wrapper for both agent types with consistent interface."""
    
    def __init__(self, llm_adapter: Optional[LiteLLMAdapter] = None):
        """Initialize wrapper with LLM adapter.
        
        Args:
            llm_adapter: Optional LLM adapter. Creates default if not provided.
        """
        self.llm_adapter = llm_adapter or LiteLLMAdapter()
    
    def process_question(
        self,
        question: str,
        agent_type: AgentType,
        target_responses: int = 5,
        confidence_threshold: float = 0.8,
        min_responses: int = 3,
        prompt_template: str = "Think step by step:",
        debug_mode: bool = True,
        # Entropy-specific parameters (reflection only)
        entropy_threshold: float = 0.3,
        entropy_weight: float = 0.3,
        min_entropy_samples: int = 4,
        entropy_mode: str = "combined"
    ) -> UnifiedResult:
        """Process question with specified agent type and parameters.
        
        Args:
            question: The question to process
            agent_type: Which agent type to use
            target_responses: Maximum number of responses to generate
            confidence_threshold: Confidence threshold for early stopping (reflection only)
            min_responses: Minimum responses before early stopping (reflection only)
            prompt_template: Template for LLM prompts
            
        Returns:
            UnifiedResult with standardized output format
        """
        import time
        start_time = time.time()
        
        # Create debug adapter if debug mode is enabled
        debug_adapter = DebugLiteLLMAdapter(
            model=self.llm_adapter.model,
            temperature=self.llm_adapter.temperature,
            base_url=self.llm_adapter.base_url,
            api_key=self.llm_adapter.api_key,
            **self.llm_adapter.kwargs
        ) if debug_mode else None
        
        if agent_type == AgentType.SELF_CONSISTENCY:
            result = self._process_with_self_consistency(
                question, target_responses, prompt_template, debug_adapter
            )
        elif agent_type == AgentType.ENHANCED_SELF_CONSISTENCY:
            result = self._process_with_enhanced_self_consistency(
                question, target_responses, prompt_template, debug_adapter
            )
        elif agent_type == AgentType.SELF_REFLECTION:
            result = self._process_with_self_reflection(
                question, target_responses, confidence_threshold, 
                min_responses, prompt_template, debug_adapter,
                entropy_threshold, entropy_weight, min_entropy_samples, entropy_mode
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        processing_time = time.time() - start_time
        result.processing_time = processing_time
        
        # Add debug information if available
        if debug_adapter:
            debug_info_dict = debug_adapter.get_debug_info()
            result.debug_info = DebugInfo(
                requests=debug_info_dict["requests"],
                responses=debug_info_dict["responses"],
                parsed_answers=debug_info_dict["parsed_answers"]
            )
        
        return result
    
    def _process_with_self_consistency(
        self, question: str, target_responses: int, prompt_template: str, debug_adapter: Optional[DebugLiteLLMAdapter] = None
    ) -> UnifiedResult:
        """Process with self-consistency agent."""
        config = AgentConfig(
            llm_interface=debug_adapter or self.llm_adapter,
            target_responses=target_responses,
            prompt_template=prompt_template
        )
        
        agent = SelfConsistencyAgent(config, question)
        result: ConsensusResult = agent.process_question()
        
        # Convert to unified format
        # For self-consistency, create a simple distribution
        answer_distribution = {result.final_answer: result.confidence}
        if result.confidence < 1.0:
            # Add "other" category for remaining probability
            answer_distribution["<other answers>"] = 1.0 - result.confidence
        
        uncertainty_level = self._calculate_uncertainty_level(result.confidence)
        
        return UnifiedResult(
            agent_type="Self-Consistency",
            final_answer=result.final_answer,
            confidence=result.confidence,
            total_responses=target_responses,
            early_stopping=False,  # Self-consistency doesn't use early stopping
            answer_distribution=answer_distribution,
            uncertainty_level=uncertainty_level
        )
    
    def _process_with_self_reflection(
        self, 
        question: str, 
        target_responses: int, 
        confidence_threshold: float,
        min_responses: int,
        prompt_template: str,
        debug_adapter: Optional[DebugLiteLLMAdapter] = None,
        entropy_threshold: float = 0.3,
        entropy_weight: float = 0.3,
        min_entropy_samples: int = 4,
        entropy_mode: str = "combined"
    ) -> UnifiedResult:
        """Process with self-reflection agent."""
        config = ReflectionConfig(
            llm_interface=debug_adapter or self.llm_adapter,
            target_responses=target_responses,
            confidence_threshold=confidence_threshold,
            min_responses=min_responses,
            prompt_template=prompt_template,
            entropy_threshold=entropy_threshold,
            entropy_weight=entropy_weight,
            min_entropy_samples=min_entropy_samples,
            entropy_mode=entropy_mode
        )
        
        agent = SelfReflectionAgent(config, question)
        result: ReflectionResult = agent.process_question()
        
        return UnifiedResult(
            agent_type="Self-Reflection",
            final_answer=result.final_answer,
            confidence=result.consensus_confidence,
            total_responses=result.total_responses,
            early_stopping=result.early_stopping,
            answer_distribution=result.answer_distribution,
            uncertainty_level=result.uncertainty_level,
            convergence_analysis=result.convergence_analysis,
            distribution_entropy=result.distribution_entropy,
            normalized_entropy=result.normalized_entropy,
            entropy_level=result.entropy_level,
            consensus_type=result.consensus_type
        )
    
    def _process_with_enhanced_self_consistency(
        self, question: str, target_responses: int, prompt_template: str, debug_adapter: Optional[DebugLiteLLMAdapter] = None
    ) -> UnifiedResult:
        """Process with enhanced self-consistency agent."""
        try:
            # Check if model supports structured outputs + logprobs
            model_name = debug_adapter.model if debug_adapter else self.llm_adapter.model
            if not self._check_enhanced_model_compatibility(model_name):
                raise ValueError(f"Model '{model_name}' does not support structured outputs + logprobs. Please use a compatible model like openrouter/gpt-4o-mini or gpt-4o-mini.")
            
            # Create enhanced LLM adapter (not debug version for structured outputs)
            enhanced_adapter = EnhancedLiteLLMAdapter(
                model=self.llm_adapter.model,
                temperature=self.llm_adapter.temperature,
                base_url=self.llm_adapter.base_url,
                api_key=self.llm_adapter.api_key,
                **self.llm_adapter.kwargs
            )
            
            config = AgentConfig(
                llm_interface=enhanced_adapter,
                target_responses=target_responses,
                prompt_template=prompt_template
            )
            
            agent = EnhancedSelfConsistencyAgent(config, question)
            result: EnhancedConsensusResult = agent.process_question()
            
            # Convert to unified format
            answer_distribution = {result.final_answer: result.confidence}
            if result.confidence < 1.0:
                # Add "other" category for remaining probability
                answer_distribution["<other answers>"] = 1.0 - result.confidence
            
            uncertainty_level = self._calculate_uncertainty_level(result.confidence)
            
            return UnifiedResult(
                agent_type="Enhanced Self-Consistency",
                final_answer=result.final_answer,
                confidence=result.confidence,
                total_responses=target_responses,
                early_stopping=False,  # Enhanced self-consistency doesn't use early stopping
                answer_distribution=answer_distribution,
                uncertainty_level=uncertainty_level,
                # Token confidence data
                token_confidence_reasoning=result.confidence_report.token_confidence_reasoning,
                token_confidence_answer=result.confidence_report.token_confidence_answer,
                individual_response_confidence=result.confidence_report.individual_response_data
            )
            
        except Exception as e:
            # Re-raise with clear error message
            raise ValueError(f"Enhanced Self-Consistency processing failed: {str(e)}")
    
    def _check_enhanced_model_compatibility(self, model_name: str) -> bool:
        """Check if model supports structured outputs + logprobs."""
        compatible_models = [
            'gpt-4o', 'gpt-4o-mini',
            'openrouter/gpt-4o', 'openrouter/gpt-4o-mini',
            'openrouter/openai/gpt-4o', 'openrouter/openai/gpt-4o-mini'
        ]
        
        return any(
            model_name == compat_model or 
            model_name.endswith(compat_model.split('/')[-1])
            for compat_model in compatible_models
        )
    
    def compare_agents(
        self,
        question: str,
        target_responses: int = 10,
        confidence_threshold: float = 0.8,
        min_responses: int = 3,
        prompt_template: str = "Think step by step:",
        # Entropy parameters for self-reflection
        entropy_threshold: float = 0.3,
        entropy_weight: float = 0.3,
        min_entropy_samples: int = 4,
        entropy_mode: str = "combined"
    ) -> Dict[str, UnifiedResult]:
        """Compare both agents on the same question.
        
        Args:
            question: The question to process with both agents
            target_responses: Maximum responses for both agents
            confidence_threshold: Confidence threshold for reflection agent
            min_responses: Minimum responses for reflection agent
            prompt_template: Template for LLM prompts
            
        Returns:
            Dictionary with results from both agents
        """
        results = {}
        
        # Process with self-consistency (no entropy parameters needed)
        results["self_consistency"] = self.process_question(
            question=question,
            agent_type=AgentType.SELF_CONSISTENCY,
            target_responses=target_responses,
            prompt_template=prompt_template,
            debug_mode=False  # Disable debug for comparison to avoid interference
        )
        
        # Process with self-reflection
        results["self_reflection"] = self.process_question(
            question=question,
            agent_type=AgentType.SELF_REFLECTION,
            target_responses=target_responses,
            confidence_threshold=confidence_threshold,
            min_responses=min_responses,
            prompt_template=prompt_template,
            entropy_threshold=entropy_threshold,
            entropy_weight=entropy_weight,
            min_entropy_samples=min_entropy_samples,
            entropy_mode=entropy_mode
        )
        
        return results
    
    @staticmethod
    def _calculate_uncertainty_level(confidence: float) -> str:
        """Calculate uncertainty level from confidence score."""
        if confidence >= 0.8:
            return "low"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "high"
    
    def validate_llm_connection(self) -> bool:
        """Test LLM connection and return status."""
        try:
            test_response = self.llm_adapter.generate_llm_response(
                "Say 'OK':", "Test connection"
            )
            return test_response.answer is not None
        except Exception:
            return False