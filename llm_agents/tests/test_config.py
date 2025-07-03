"""Tests for configuration and environment variables."""

import pytest
import os
from unittest.mock import patch, Mock

from llm_agents.self_consistency.config import AgentConfig
from llm_agents.common.interfaces import LiteLLMAdapter, LLMInterface
from llm_agents.common.domain import LLMResponse


class TestAgentConfig:
    """Configuration Tests - AgentConfig validation."""
    
    def test_agent_config_creation(self):
        """Test basic AgentConfig creation."""
        mock_llm = Mock(spec=LLMInterface)
        config = AgentConfig(
            llm_interface=mock_llm,
            target_responses=5,
            prompt_template="Think step by step:"
        )
        
        assert config.llm_interface == mock_llm
        assert config.target_responses == 5
        assert config.prompt_template == "Think step by step:"
    
    def test_agent_config_defaults(self):
        """Test AgentConfig with default values."""
        mock_llm = Mock(spec=LLMInterface)
        config = AgentConfig(llm_interface=mock_llm)
        
        assert config.target_responses == 5  # Default value
        assert config.prompt_template == ""  # Default value


class TestLiteLLMAdapterEnvironment:
    """Configuration Tests - Environment variables."""
    
    @patch.dict(os.environ, {
        'LLM_MODEL': 'gpt-4',
        'LLM_TEMPERATURE': '0.3',
        'LLM_BASE_URL': 'http://test:8080',
        'LLM_API_KEY': 'test-key-123'
    })
    def test_environment_variables_override(self):
        """Test that environment variables are used as defaults."""
        adapter = LiteLLMAdapter()
        
        assert adapter.model == 'gpt-4'
        assert adapter.temperature == 0.3
        assert adapter.base_url == 'http://test:8080'
        assert adapter.api_key == 'test-key-123'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_environment_variables_defaults(self):
        """Test fallback to hardcoded defaults when env vars not set."""
        adapter = LiteLLMAdapter()
        
        assert adapter.model == 'claude-3-haiku'
        assert adapter.temperature == 0.7
        assert adapter.base_url == 'http://localhost:4000'
        assert adapter.api_key == 'sk-1234'
    
    def test_code_parameters_override_environment(self):
        """Test that code parameters override environment variables."""
        with patch.dict(os.environ, {
            'LLM_MODEL': 'gpt-4',
            'LLM_TEMPERATURE': '0.3'
        }, clear=True):
            adapter = LiteLLMAdapter(
                model='claude-3',
                temperature=0.9
            )
            
            assert adapter.model == 'claude-3'  # Code override
            assert adapter.temperature == 0.9   # Code override
            # Env vars still used for others
            assert adapter.base_url == 'http://localhost:4000'  # Default
            assert adapter.api_key == 'sk-1234'                # Default
    
    @patch.dict(os.environ, {'LLM_TEMPERATURE': 'invalid'})
    def test_invalid_environment_temperature(self):
        """Test handling of invalid temperature in environment."""
        with pytest.raises(ValueError):
            LiteLLMAdapter()  # Should fail when trying to convert 'invalid' to float