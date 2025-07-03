"""Debug-enabled LLM adapter for Gradio interface.

This module provides a wrapper around the LiteLLMAdapter that captures
debug information for display in the Gradio interface.
"""

from typing import List, Dict, Any
from ..common.interfaces import LiteLLMAdapter, LLMResponse


class DebugLiteLLMAdapter(LiteLLMAdapter):
    """LiteLLM adapter that captures debug information."""
    
    def __init__(self, *args, **kwargs):
        """Initialize debug adapter."""
        super().__init__(*args, **kwargs)
        self.debug_requests: List[Dict[str, Any]] = []
        self.debug_responses: List[Dict[str, Any]] = []
        self.parsed_answers: List[str] = []
    
    def generate_llm_response(self, prompt: str, question: str) -> LLMResponse:
        """Generate LLM response and capture debug information."""
        # Construct full prompt
        full_prompt = f"{prompt} {question}"
        
        # Record the request
        request_info = {
            "model": self.model,
            "temperature": self.temperature,
            "prompt": prompt,
            "question": question,
            "full_prompt": full_prompt,
            "timestamp": self._get_timestamp()
        }
        self.debug_requests.append(request_info)
        
        # Make the actual request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=self.temperature,
            **self.kwargs
        )
        
        # Extract raw response
        raw_response = response.choices[0].message.content
        
        # Record the raw response
        response_info = {
            "raw_content": raw_response,
            "model": response.model,
            "usage": response.usage.dict() if response.usage else None,
            "finish_reason": response.choices[0].finish_reason,
            "timestamp": self._get_timestamp()
        }
        self.debug_responses.append(response_info)
        
        # Parse the response
        parsed_response = self._parse_llm_output(raw_response)
        
        # Record the parsed answer
        self.parsed_answers.append(parsed_response.answer)
        
        return parsed_response
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get all collected debug information."""
        return {
            "requests": self.debug_requests.copy(),
            "responses": self.debug_responses.copy(),
            "parsed_answers": self.parsed_answers.copy(),
            "total_requests": len(self.debug_requests)
        }
    
    def clear_debug_info(self):
        """Clear all debug information."""
        self.debug_requests.clear()
        self.debug_responses.clear()
        self.parsed_answers.clear()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]