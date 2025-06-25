"""Interface definitions for LLM interactions.

This module defines the abstract interface for LLM interactions and provides
concrete implementations for different LLM providers.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional
from openai import OpenAI
from .domain import LLMResponse


class LLMInterface(ABC):
    """Abstract interface for LLM interactions."""
    
    @abstractmethod
    def generate_llm_response(self, prompt: str, question: str) -> LLMResponse:
        """Generate a single LLM response for the given question."""
        pass


class LiteLLMAdapter(LLMInterface):
    """LiteLLM implementation of LLM interface with environment variable defaults."""
    
    def __init__(self, 
                 model: Optional[str] = None,
                 temperature: Optional[float] = None,
                 base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 **kwargs):
        """Initialize LiteLLM adapter with environment variable defaults.
        
        Args:
            model: LLM model name (defaults to LLM_MODEL env var or "gpt-3.5-turbo")
            temperature: Sampling temperature (defaults to LLM_TEMPERATURE env var or 0.7)
            base_url: Base URL for LLM API (defaults to LLM_BASE_URL env var or "http://localhost:4000")
            api_key: API key (defaults to LLM_API_KEY env var or "sk-dummy")
            **kwargs: Additional parameters
        """
        self.model = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:4000")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "sk-dummy")
        self.kwargs = kwargs
        
        # Initialize OpenAI client pointing to LiteLLM Docker container
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def generate_llm_response(self, prompt: str, question: str) -> LLMResponse:
        """Generate LLM response using LiteLLM via OpenAI client."""
        # Combine prompt and question
        full_prompt = f"{prompt}\n\nQuestion: {question}"
        
        # Make API call to LiteLLM Docker container
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=self.temperature,
            **self.kwargs
        )
        
        # Extract response content
        raw_response = response.choices[0].message.content
        
        # Parse into reasoning and answer (basic implementation)
        return self._parse_llm_output(raw_response)
    
    def _parse_llm_output(self, raw_response: str) -> LLMResponse:
        """Parse raw LLM output into structured LLMResponse."""
        # Simple parsing logic - look for "The answer is X" pattern
        lines = raw_response.split('\n')
        answer_line = None
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('the answer is'):
                answer_line = line
                break
            elif line.lower().startswith('answer:'):
                answer_line = line
                break
        
        if answer_line:
            # Extract answer from line
            if 'the answer is' in answer_line.lower():
                # Use case-insensitive split
                lower_line = answer_line.lower()
                split_pos = lower_line.find('the answer is') + len('the answer is')
                answer = answer_line[split_pos:].strip()
            else:
                answer = answer_line.split(':', 1)[1].strip()
            
            # Everything before the answer line is reasoning
            answer_index = raw_response.find(answer_line)
            reasoning = raw_response[:answer_index].strip()
        else:
            # Fallback: use last line as answer, everything else as reasoning
            lines = [l.strip() for l in lines if l.strip()]
            if lines:
                answer = lines[-1]
                reasoning = '\n'.join(lines[:-1])
            else:
                reasoning = raw_response
                answer = "No clear answer found"
        
        return LLMResponse(reasoning=reasoning, answer=answer)