"""Tests for LLM response parsing edge cases."""

import pytest
from unittest.mock import Mock, patch
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from llm_agents.self_consistency.interfaces import LiteLLMAdapter
from llm_agents.self_consistency.domain import LLMResponse


class TestLLMResponseParsing:
    """Integration Tests - Parsing edge cases."""
    
    def test_standard_parsing_format(self):
        """Test parsing with standard 'The answer is X' format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me think through this step by step.
        
First, I need to consider the problem carefully.
Then, I'll analyze the options.

The answer is 42"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert result.reasoning.strip().startswith("Let me think")
        assert result.answer == "42"
    
    def test_answer_colon_format(self):
        """Test parsing with 'Answer: X' format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Step 1: Analyze the question
Step 2: Consider alternatives
Step 3: Make conclusion

Answer: Yes, it is correct"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Step 1" in result.reasoning
        assert result.answer == "Yes, it is correct"
    
    def test_no_clear_answer_pattern(self):
        """Test fallback parsing when no clear pattern is found."""
        adapter = LiteLLMAdapter()
        
        raw_response = """This is just some text.
Multiple lines here.
Final conclusion here."""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert result.reasoning == "This is just some text.\nMultiple lines here."
        assert result.answer == "Final conclusion here."
    
    def test_empty_response(self):
        """Test handling of empty or whitespace-only response."""
        adapter = LiteLLMAdapter()
        
        raw_response = "   \n  \n   "
        
        result = adapter._parse_llm_output(raw_response)
        
        assert result.reasoning == "   \n  \n   "
        assert result.answer == "No clear answer found"
    
    def test_single_line_response(self):
        """Test handling of single line response."""
        adapter = LiteLLMAdapter()
        
        raw_response = "Just one line answer"
        
        result = adapter._parse_llm_output(raw_response)
        
        assert result.reasoning == ""
        assert result.answer == "Just one line answer"
    
    def test_multiple_answer_patterns(self):
        """Test when multiple answer patterns are present."""
        adapter = LiteLLMAdapter()
        
        raw_response = """First, let me say the answer is maybe.
        
But after more thought...

The answer is definitely yes."""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should find the first line that starts with "The answer is"
        assert "But after more thought" in result.reasoning
        assert result.answer == "definitely yes."


class TestLiteLLMAdapterIntegration:
    """Integration test with mocked OpenAI client."""
    
    @patch('llm_agents.self_consistency.interfaces.OpenAI')
    def test_generate_llm_response_success(self, mock_openai_class):
        """Test successful LLM response generation."""
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Setup mock response
        mock_message = ChatCompletionMessage(
            role="assistant",
            content="I need to think about this.\n\nThe answer is 42"
        )
        mock_choice = Choice(
            index=0,
            message=mock_message,
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[mock_choice]
        )
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test the adapter
        adapter = LiteLLMAdapter(model="gpt-3.5-turbo", temperature=0.7)
        result = adapter.generate_llm_response("Think carefully:", "What is 6*7?")
        
        # Verify the API call
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Think carefully:\n\nQuestion: What is 6*7?"}],
            temperature=0.7
        )
        
        # Verify the result
        assert isinstance(result, LLMResponse)
        assert result.reasoning == "I need to think about this."
        assert result.answer == "42"
    
    @patch('llm_agents.self_consistency.interfaces.OpenAI')
    def test_generate_llm_response_with_kwargs(self, mock_openai_class):
        """Test LLM response generation with additional kwargs."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_message = ChatCompletionMessage(role="assistant", content="Test response")
        mock_choice = Choice(index=0, message=mock_message, finish_reason="stop")
        mock_response = ChatCompletion(
            id="test", object="chat.completion", created=123, 
            model="test", choices=[mock_choice]
        )
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test with additional kwargs
        adapter = LiteLLMAdapter(
            model="gpt-4", 
            temperature=0.5,
            max_tokens=100,
            top_p=0.9
        )
        adapter.generate_llm_response("prompt", "question")
        
        # Verify kwargs are passed through
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[{"role": "user", "content": "prompt\n\nQuestion: question"}],
            temperature=0.5,
            max_tokens=100,
            top_p=0.9
        )