"""Self-consistency Chain-of-Thought agent implementation.

This module contains the main SelfConsistencyAgent class that implements
the self-consistency reasoning approach with O(m) complexity optimization.
"""

from typing import List
from collections import Counter
from .domain import LLMResponse, ConsensusResult
from .config import AgentConfig


class SelfConsistencyAgent:
    """Main agent implementing self-consistency CoT reasoning."""
    
    def __init__(self, config: AgentConfig, question: str):
        """Initialize agent with configuration and question."""
        self._config = config
        self._question = question
        self._llm_responses: List[LLMResponse] = []
    
    def process_question(self) -> ConsensusResult:
        """Process the question and return consensus result."""
        # Clear any previous responses
        self._llm_responses = []
        
        # Sequential processing: Loop m times (config.target_responses)
        for _ in range(self._config.target_responses):
            # Generate LLM response
            llm_response = self._config.llm_interface.generate_llm_response(
                self._config.prompt_template, 
                self._question
            )
            # Store parsed response in collection
            self._llm_responses.append(llm_response)
        
        # Perform argmax to get final answer and vote count
        final_answer, vote_count = self._perform_argmax()
        
        # Calculate confidence
        confidence = vote_count / len(self._llm_responses)
        
        # Return consensus result
        return ConsensusResult(
            final_answer=final_answer,
            vote_count=vote_count,
            confidence=confidence
        )
    
    def _perform_argmax(self) -> tuple[str, int]:
        """Private method to perform majority vote aggregation with O(m) complexity."""
        # Extract answers - O(m) linear pass through responses
        answers = [response.answer for response in self._llm_responses]
        # Counter uses O(1) hash operations for counting, avoiding O(m^2) nested loops
        counts = Counter(answers)
        answer, count = counts.most_common(1)[0]
        return answer, count
    
    def _parse_llm_output(self, raw_response: str) -> LLMResponse:
        """Parse raw LLM output into structured LLMResponse."""
        # This method is not used in current implementation since parsing
        # is handled in the LiteLLMAdapter.generate_llm_response method
        # Keeping for future use or if parsing needs to be done at agent level
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
                answer = answer_line.split('the answer is', 1)[1].strip()
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