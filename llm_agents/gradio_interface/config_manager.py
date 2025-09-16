"""Configuration manager for Gradio interface.

This module handles dynamic configuration creation from UI inputs,
environment variable integration, and LLM interface initialization.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..common.interfaces import LiteLLMAdapter


@dataclass
class UIConfig:
    """Configuration object for UI settings."""
    target_responses: int = 5
    confidence_threshold: float = 0.8
    min_responses: int = 3
    prompt_template: str = "Think step by step:"
    model_name: str = "claude-3-haiku"
    temperature: float = 0.7
    base_url: str = "http://localhost:4000"
    api_key: str = "sk-1234"


class ConfigManager:
    """Manages configuration for the Gradio interface."""
    
    def __init__(self):
        """Initialize configuration manager with environment defaults."""
        self._load_environment_defaults()
    
    def _load_environment_defaults(self) -> None:
        """Load default configuration from environment variables."""
        self.default_config = UIConfig(
            model_name=os.getenv("LLM_MODEL", "claude-3-haiku"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:4000"),
            api_key=os.getenv("LLM_API_KEY", "sk-1234")
        )
    
    def create_llm_adapter(
        self, 
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> LiteLLMAdapter:
        """Create LLM adapter with specified or default configuration.
        
        Args:
            model_name: LLM model to use
            temperature: Temperature for LLM responses
            base_url: Base URL for LLM API
            api_key: API key for authentication
            
        Returns:
            Configured LiteLLMAdapter instance
        """
        # Use provided values or fall back to defaults
        config = UIConfig(
            model_name=model_name or self.default_config.model_name,
            temperature=temperature or self.default_config.temperature,
            base_url=base_url or self.default_config.base_url,
            api_key=api_key or self.default_config.api_key
        )
        
        # Set environment variables for LiteLLMAdapter
        os.environ["LLM_MODEL"] = config.model_name
        os.environ["LLM_TEMPERATURE"] = str(config.temperature)
        os.environ["LLM_BASE_URL"] = config.base_url
        os.environ["LLM_API_KEY"] = config.api_key
        
        return LiteLLMAdapter()
    
    def get_available_models(self) -> Dict[str, str]:
        """Get dictionary of available models with display names.
        
        Returns:
            Dictionary mapping model IDs to display names
        """
        return {
            "claude-3-haiku": "Claude 3 Haiku (Fast, Cost-Effective)",
            "claude-3-5-sonnet": "Claude 3.5 Sonnet (Balanced)",
            "gpt-4o": "GPT-4o (Advanced) ✨ Enhanced Support",
            "gpt-4o-mini": "GPT-4o Mini (Fast) ✨ Enhanced Support",
            "openrouter/gpt-4o": "OpenRouter GPT-4o (Advanced) ✨ Enhanced Support",
            "openrouter/gpt-4o-mini": "OpenRouter GPT-4o Mini (Recommended) ✨ Enhanced Support",
            "gpt-3.5-turbo": "GPT-3.5 Turbo (Classic)"
        }
    
    def get_default_prompts(self) -> Dict[str, str]:
        """Get dictionary of default prompt templates.
        
        Returns:
            Dictionary mapping prompt names to templates
        """
        return {
            "Standard": "Think step by step:",
            "Detailed": "Think step by step and explain your reasoning in detail:",
            "Concise": "Answer concisely:",
            "Mathematical": "Solve this step by step, showing all work:",
            "Logical": "Use logical reasoning to analyze this problem:",
            "Creative": "Think creatively about this question:"
        }
    
    def validate_configuration(self, config: UIConfig) -> Dict[str, Any]:
        """Validate configuration and return status information.
        
        Args:
            config: UI configuration to validate
            
        Returns:
            Dictionary with validation results and status
        """
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Validate target_responses
        if config.target_responses < 1:
            validation_result["errors"].append("Target responses must be at least 1")
            validation_result["valid"] = False
        elif config.target_responses > 20:
            validation_result["warnings"].append("High target responses may be slow and expensive")
        
        # Validate confidence_threshold
        if not 0.0 <= config.confidence_threshold <= 1.0:
            validation_result["errors"].append("Confidence threshold must be between 0.0 and 1.0")
            validation_result["valid"] = False
        
        # Validate min_responses
        if config.min_responses < 1:
            validation_result["errors"].append("Minimum responses must be at least 1")
            validation_result["valid"] = False
        elif config.min_responses > config.target_responses:
            validation_result["errors"].append("Minimum responses cannot exceed target responses")
            validation_result["valid"] = False
        
        # Validate temperature
        if not 0.0 <= config.temperature <= 2.0:
            validation_result["warnings"].append("Temperature outside typical range (0.0-2.0)")
        
        # Validate model availability
        available_models = self.get_available_models()
        if config.model_name not in available_models:
            validation_result["warnings"].append(f"Model '{config.model_name}' may not be available")
        
        return validation_result
    
    def get_cost_estimate(self, config: UIConfig, agent_type: str) -> Dict[str, Any]:
        """Estimate cost and performance for given configuration.
        
        Args:
            config: UI configuration
            agent_type: Type of agent ("self_consistency" or "self_reflection")
            
        Returns:
            Dictionary with cost and performance estimates
        """
        # Basic cost estimation (simplified)
        base_cost_per_token = {
            "claude-3-haiku": 0.00025,
            "claude-3-5-sonnet": 0.003,
            "gpt-4o": 0.005,
            "gpt-4o-mini": 0.00015,
            "gpt-3.5-turbo": 0.0015
        }
        
        cost_per_token = base_cost_per_token.get(config.model_name, 0.002)
        
        if agent_type == "self_consistency":
            expected_tokens = config.target_responses * 100  # Rough estimate
            expected_responses = config.target_responses
            early_stopping_savings = 0
        else:  # self_reflection
            # Estimate early stopping savings
            if config.confidence_threshold >= 0.8:
                early_stopping_savings = 0.3  # 30% average savings
            else:
                early_stopping_savings = 0.1  # 10% average savings
            
            expected_responses = config.target_responses * (1 - early_stopping_savings)
            expected_tokens = expected_responses * 100
        
        estimated_cost = expected_tokens * cost_per_token
        
        return {
            "estimated_cost": estimated_cost,
            "expected_responses": int(expected_responses),
            "expected_tokens": int(expected_tokens),
            "early_stopping_savings": early_stopping_savings,
            "cost_per_response": estimated_cost / expected_responses if expected_responses > 0 else 0
        }
    
    def create_ui_config_from_inputs(
        self,
        target_responses: int,
        confidence_threshold: float,
        min_responses: int,
        prompt_template: str,
        model_name: str,
        temperature: float
    ) -> UIConfig:
        """Create UIConfig from individual input values.
        
        Args:
            target_responses: Maximum number of responses
            confidence_threshold: Confidence threshold for early stopping
            min_responses: Minimum responses before early stopping
            prompt_template: Template for LLM prompts
            model_name: LLM model to use
            temperature: Temperature for LLM responses
            
        Returns:
            UIConfig object with specified values
        """
        return UIConfig(
            target_responses=target_responses,
            confidence_threshold=confidence_threshold,
            min_responses=min_responses,
            prompt_template=prompt_template,
            model_name=model_name,
            temperature=temperature,
            base_url=self.default_config.base_url,
            api_key=self.default_config.api_key
        )