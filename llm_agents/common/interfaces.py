"""Interface definitions for LLM interactions.

This module defines the abstract interface for LLM interactions and provides
concrete implementations for different LLM providers.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
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
                 **kwargs: Any):
        """Initialize LiteLLM adapter with environment variable defaults.
        
        Args:
            model: LLM model name (defaults to LLM_MODEL env var or "claude-3-haiku")
            temperature: Sampling temperature (defaults to LLM_TEMPERATURE env var or 0.7)
            base_url: Base URL for LLM API (defaults to LLM_BASE_URL env var or "http://localhost:4000")
            api_key: API key (defaults to LLM_API_KEY env var or "sk-1234")
            **kwargs: Additional parameters
        """
        self.model = model or os.getenv("LLM_MODEL", "claude-3-haiku")
        self.temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:4000")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "sk-1234")
        self.kwargs: Dict[str, Any] = kwargs
        
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
        import re
        
        # Clean up the response
        raw_response = raw_response.strip()
        
        # Look for answer patterns in order of preference
        answer_patterns = [
            r'Answer:\s*(.+?)(?:\n|$)',  # Answer: <answer>
            r'The answer is\s*(.+?)(?:\n|$)',  # The answer is <answer>
            r'Final answer:\s*(.+?)(?:\n|$)',  # Final answer: <answer>
            r'Answer\s*=\s*(.+?)(?:\n|$)',  # Answer = <answer>
        ]
        
        answer = None
        answer_line = None
        answer_index = -1
        
        for pattern in answer_patterns:
            match = re.search(pattern, raw_response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).strip()
                answer_line = match.group(0).strip()
                answer_index = match.start()
                break
        
        if answer:
            # Clean up the answer - remove common leading and trailing phrases
            answer = answer.strip()
            
            # Remove common leading phrases that might be included
            leading_phrases = [
                r'^(?:So,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                r'^(?:Therefore,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                r'^(?:Thus,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                r'^(?:Hence,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                r'^(?:So,?\s*)?(?:I\s+think\s+)?(?:the\s+)?(?:answer|result|solution)\s+(?:is|would\s+be)\s*',
                r'^(?:Therefore,?\s*)?(?:I\s+think\s+)?(?:the\s+)?(?:answer|result|solution)\s+(?:is|would\s+be)\s*',
                r'^(?:The\s+)?(?:correct\s+)?(?:answer|result|solution)\s+(?:is|would\s+be)\s*',
                r'^(?:It\s+(?:is|would\s+be))\s*',
            ]
            
            for phrase_pattern in leading_phrases:
                answer = re.sub(phrase_pattern, '', answer, flags=re.IGNORECASE)
                answer = answer.strip()
            
            # Remove trailing punctuation and phrases
            answer = re.sub(r'[.!?]*$', '', answer)  # Remove trailing punctuation
            
            # Remove common trailing phrases
            trailing_phrases = [
                r'\s*(?:is\s+the|are\s+the)\s*(?:answer|solution|result).*$',
                r'\s*(?:is|are)\s*(?:correct|right|the\s+answer).*$',
                r'\s*(?:therefore|thus|hence|so).*$',
                r'\s*(?:in\s+the\s+sequence).*$',
                r'\s*(?:would\s+be\s+the\s+next).*$',
            ]
            
            for phrase_pattern in trailing_phrases:
                answer = re.sub(phrase_pattern, '', answer, flags=re.IGNORECASE)
                answer = answer.strip()
            
            # Additional cleanup for numeric answers - extract just the number/value
            if answer:
                # If the answer contains multiple words, try to extract just the key value
                words = answer.split()
                if len(words) > 1:
                    # Look for numeric values first
                    for word in words:
                        # Check if word is a number (integer, decimal, fraction, etc.)
                        if re.match(r'^-?\d+(?:\.\d+)?(?:/\d+)?$', word):
                            answer = word
                            break
                    else:
                        # If no clear number found, look for mathematical expressions
                        for word in words:
                            if re.match(r'^-?\d+(?:\.\d+)?(?:[+\-*/]\d+(?:\.\d+)?)*$', word):
                                answer = word
                                break
                        else:
                            # If still no match, try to find the most relevant word
                            # Keep the last word that looks like a value/answer
                            for word in reversed(words):
                                if not re.match(r'^(?:the|a|an|is|are|be|in|of|to|for|and|or|but)$', word, re.IGNORECASE):
                                    answer = word
                                    break
            
            # Everything before the answer line is reasoning
            if answer_index >= 0:
                reasoning = raw_response[:answer_index].strip()
            elif answer_line:
                reasoning = raw_response.replace(answer_line, '').strip()
            else:
                reasoning = raw_response
        else:
            # Enhanced fallback: try to find the most likely answer
            lines = [l.strip() for l in raw_response.split('\n') if l.strip()]
            
            if lines:
                # Look for lines that might contain the answer
                answer_candidates = []
                
                for line in lines:
                    # Skip very long lines (likely reasoning)
                    if len(line) > 100:
                        continue
                    
                    # Skip lines that are clearly questions
                    if line.endswith('?'):
                        continue
                    
                    # Skip lines that are clearly explanatory
                    if any(phrase in line.lower() for phrase in ['because', 'since', 'this is', 'we can see', 'looking at']):
                        continue
                    
                    # Apply same cleanup as above
                    cleaned_line = line
                    for phrase_pattern in [
                        r'^(?:So,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                        r'^(?:Therefore,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                        r'^(?:Thus,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                        r'^(?:Hence,?\s*)?(?:the\s+)?(?:next\s+)?(?:number|term|value|answer)\s+(?:in\s+the\s+sequence\s+)?(?:is|would\s+be)\s*',
                    ]:
                        cleaned_line = re.sub(phrase_pattern, '', cleaned_line, flags=re.IGNORECASE).strip()
                    
                    # Remove trailing punctuation
                    cleaned_line = re.sub(r'[.!?]*$', '', cleaned_line).strip()
                    
                    # Extract just numbers/values if possible
                    words = cleaned_line.split()
                    for word in words:
                        if re.match(r'^-?\d+(?:\.\d+)?(?:/\d+)?$', word):
                            answer_candidates.append(word)
                            break
                    else:
                        # If no number found, keep the cleaned line if it's short
                        if len(cleaned_line) < 50 and cleaned_line:
                            answer_candidates.append(cleaned_line)
                
                # Take the last suitable candidate or the last line
                if answer_candidates:
                    answer = answer_candidates[-1]
                else:
                    answer = lines[-1]
                
                # Find where this answer appears and use everything before as reasoning
                answer_index = raw_response.rfind(answer)
                if answer_index >= 0:
                    reasoning = raw_response[:answer_index].strip()
                else:
                    reasoning = '\n'.join(lines[:-1])
            else:
                reasoning = raw_response
                answer = "No clear answer found"
        
        # Final cleanup of answer
        if answer and answer != "No clear answer found":
            # Remove quotes if the entire answer is quoted
            if ((answer.startswith('"') and answer.endswith('"')) or 
                (answer.startswith("'") and answer.endswith("'"))):
                answer = answer[1:-1]
            
            # Clean up whitespace
            answer = ' '.join(answer.split())
        
        return LLMResponse(reasoning=reasoning, answer=answer)