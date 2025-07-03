"""Tests for LLM response parsing edge cases."""

import pytest
from unittest.mock import Mock, patch
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from llm_agents.common.interfaces import LiteLLMAdapter
from llm_agents.common.domain import LLMResponse


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
    
    def test_final_answer_format(self):
        """Test parsing with 'Final answer: X' format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me work through this problem step by step.
        
Step 1: Calculate the first part
Step 2: Add the second part

Final answer: 42"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Step 1" in result.reasoning
        assert "Step 2" in result.reasoning
        assert result.answer == "42"
    
    def test_answer_equals_format(self):
        """Test parsing with 'Answer = X' format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Given the equation x + 5 = 10
Solving for x:
x = 10 - 5

Answer = 5"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Given the equation" in result.reasoning
        assert "Solving for x" in result.reasoning
        assert result.answer == "5"
    
    def test_latex_boxed_basic(self):
        """Test parsing with basic LaTeX boxed format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """This is a mathematical problem.
        
Let me solve it step by step.
The calculation gives us:

\\boxed{42}"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "mathematical problem" in result.reasoning
        assert "calculation" in result.reasoning
        assert result.answer == "42"
    
    def test_latex_boxed_with_spaces(self):
        """Test parsing with LaTeX boxed format with spaces."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Working through the algebraic manipulation:
        
2x + 3 = 7
2x = 4
x = 2

\\boxed {2}"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "algebraic manipulation" in result.reasoning
        assert "2x + 3 = 7" in result.reasoning
        assert result.answer == "2"
    
    def test_latex_display_boxed(self):
        """Test parsing with LaTeX display math boxed format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The quadratic formula gives us:
        
Using a=1, b=-5, c=6:

\\[ \\boxed{42} \\]"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "quadratic formula" in result.reasoning
        assert "a=1, b=-5, c=6" in result.reasoning
        assert result.answer == "42"
    
    def test_latex_inline_boxed(self):
        """Test parsing with LaTeX inline math boxed format."""
        adapter = LiteLLMAdapter()
        
        raw_response = """For this integral calculation:
        
∫x²dx from 0 to 3
= [x³/3] from 0 to 3
= 27/3 - 0

\\( \\boxed{9} \\)"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "integral calculation" in result.reasoning
        assert "∫x²dx" in result.reasoning
        assert result.answer == "9"
    
    def test_latex_display_plain(self):
        """Test parsing with LaTeX display math without boxed."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The series sum is:
        
1 + 2 + 3 + ... + n = n(n+1)/2
For n=10:

\\[ 55 \\]"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "series sum" in result.reasoning
        assert "n(n+1)/2" in result.reasoning
        assert result.answer == "55"
    
    def test_latex_inline_plain(self):
        """Test parsing with LaTeX inline math without boxed."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The derivative of x² is:
        
d/dx(x²) = 2x
At x=3:

\\( 6 \\)"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "derivative" in result.reasoning
        assert "d/dx(x²) = 2x" in result.reasoning
        assert result.answer == "6"
    
    def test_answer_pattern_priority(self):
        """Test that last matching pattern takes priority."""
        adapter = LiteLLMAdapter()
        
        raw_response = """First attempt: Answer: 10
        
Let me recalculate...
Actually, I made an error above.

Final answer: 20"""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should take the last matching pattern (Final answer: 20)
        assert "First attempt" in result.reasoning
        assert "recalculate" in result.reasoning
        assert result.answer == "20"
    
    def test_cleanup_so_the_answer_is(self):
        """Test removal of 'So, the answer is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me calculate this step by step.
        
2 + 2 = 4
5 × 6 = 30

Answer: So, the answer is 34"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "calculate this step by step" in result.reasoning
        assert result.answer == "34"
    
    def test_cleanup_therefore_number_is(self):
        """Test removal of 'Therefore, the number is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Looking at the sequence: 2, 4, 8, 16, ...
        
Each term is double the previous term.
The next term would be 16 × 2 = 32.

Answer: Therefore, the number is 32"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Looking at the sequence" in result.reasoning
        assert "double the previous term" in result.reasoning
        assert result.answer == "32"
    
    def test_cleanup_thus_value_would_be(self):
        """Test removal of 'Thus, the value would be' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Given f(x) = x² + 3x + 2
        
We need to find f(5):
f(5) = 5² + 3(5) + 2 = 25 + 15 + 2 = 42

Answer: Thus, the value would be 42"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Given f(x)" in result.reasoning
        assert "f(5) = 5²" in result.reasoning
        assert result.answer == "42"
    
    def test_cleanup_hence_answer_is(self):
        """Test removal of 'Hence, the answer is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The equation is 3x - 7 = 14
        
Adding 7 to both sides: 3x = 21
Dividing by 3: x = 7

Answer: Hence, the answer is 7"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "The equation is" in result.reasoning
        assert "Adding 7 to both sides" in result.reasoning
        assert result.answer == "7"
    
    def test_cleanup_so_i_think_answer_is(self):
        """Test removal of 'So, I think the answer is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """This is a probability problem.
        
There are 6 faces on a die.
The probability of rolling a 6 is 1/6.

Answer: So, I think the answer is 1/6"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "probability problem" in result.reasoning
        assert "6 faces on a die" in result.reasoning
        assert result.answer == "1/6"
    
    def test_cleanup_therefore_solution_is(self):
        """Test removal of 'Therefore, the solution is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """We have the system of equations:
x + y = 10
x - y = 2
        
Adding the equations: 2x = 12, so x = 6
Substituting back: 6 + y = 10, so y = 4

Answer: Therefore, the solution is (6, 4)"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "system of equations" in result.reasoning
        assert "Adding the equations" in result.reasoning
        assert result.answer == "(6, 4)"
    
    def test_cleanup_correct_answer_is(self):
        """Test removal of 'The correct answer is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me check each option:
        
A) 15 - This is too small
B) 25 - This looks right: 5²
C) 35 - This is too large

Answer: The correct answer is 25"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "check each option" in result.reasoning
        assert "This looks right" in result.reasoning
        assert result.answer == "25"
    
    def test_cleanup_it_is(self):
        """Test removal of 'It is' leading phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """What is the capital of France?
        
Paris is the capital and largest city of France.
It has been the capital since 1789.

Answer: It is Paris"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "capital of France" in result.reasoning
        assert "largest city of France" in result.reasoning
        assert result.answer == "Paris"
    
    def test_cleanup_is_the_answer(self):
        """Test removal of 'is the answer' trailing phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me solve this arithmetic problem:
        
15 + 27 = 42
Let me double-check: 15 + 27 = 42

Answer: 42 is the answer"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "arithmetic problem" in result.reasoning
        assert "double-check" in result.reasoning
        assert result.answer == "42"
    
    def test_cleanup_therefore_at_end(self):
        """Test removal of 'therefore' at end of answer."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The triangle has sides 3, 4, and 5.
        
Using the Pythagorean theorem: 3² + 4² = 9 + 16 = 25 = 5²
This confirms it's a right triangle.

Answer: Yes therefore"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "triangle has sides" in result.reasoning
        assert "Pythagorean theorem" in result.reasoning
        assert result.answer == "Yes"
    
    def test_cleanup_in_the_sequence(self):
        """Test removal of 'in the sequence' trailing phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Looking at the pattern: 1, 4, 9, 16, ...
        
These are perfect squares: 1², 2², 3², 4², ...
The next term would be 5² = 25.

Answer: 25 in the sequence"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Looking at the pattern" in result.reasoning
        assert "perfect squares" in result.reasoning
        assert result.answer == "25"
    
    def test_cleanup_would_be_the_next(self):
        """Test removal of 'would be the next' trailing phrase."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13, ...
        
Each term is the sum of the two previous terms.
13 + 8 = 21

Answer: 21 would be the next"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Fibonacci sequence" in result.reasoning
        assert "sum of the two previous terms" in result.reasoning
        assert result.answer == "21"
    
    def test_extract_integer(self):
        """Test extraction of integer from mixed text."""
        adapter = LiteLLMAdapter()
        
        raw_response = """The area of the rectangle is calculated as:
        
length × width = 8 × 5 = 40
So the area is 40 square units.

Answer: The value is 40 units"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "area of the rectangle" in result.reasoning
        assert "8 × 5 = 40" in result.reasoning
        assert result.answer == "40"
    
    def test_extract_decimal(self):
        """Test extraction of decimal from mixed text."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Calculating the circumference of a circle:
        
C = 2πr = 2 × 3.14159 × 5 = 31.4159
Rounded to two decimal places.

Answer: The result is 31.42 approximately"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "circumference of a circle" in result.reasoning
        assert "2πr" in result.reasoning
        assert result.answer == "31.42"
    
    def test_extract_fraction(self):
        """Test extraction of fraction from mixed text."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Finding the probability of drawing a red card:
        
There are 26 red cards in a standard deck of 52 cards.
Probability = 26/52 = 1/2

Answer: The fraction is 1/2 or 0.5"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "probability of drawing a red card" in result.reasoning
        assert "26 red cards" in result.reasoning
        assert result.answer == "1/2"
    
    def test_extract_negative(self):
        """Test extraction of negative number from mixed text."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Solving the equation 2x + 10 = 0:
        
2x = -10
x = -5
Let me verify: 2(-5) + 10 = -10 + 10 = 0 ✓

Answer: The answer is -5 degrees"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Solving the equation" in result.reasoning
        assert "Let me verify" in result.reasoning
        assert result.answer == "-5"
    
    def test_extract_expression(self):
        """Test extraction of mathematical expression from mixed text."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Simplifying the algebraic expression:
        
3x + 2x - x = (3 + 2 - 1)x = 4x
The coefficient of x is 4.

Answer: The calculation is 2+3 simplified"""
        
        result = adapter._parse_llm_output(raw_response)
        
        assert "Simplifying the algebraic expression" in result.reasoning
        assert "coefficient of x" in result.reasoning
        assert result.answer == "2+3"
    
    def test_multiple_latex_patterns(self):
        """Test when multiple LaTeX patterns are present - last one wins."""
        adapter = LiteLLMAdapter()
        
        raw_response = """First calculation: \\boxed{10}
        
But let me recalculate more carefully:
Using the quadratic formula:
x = (-b ± √(b² - 4ac)) / 2a

\\[ \\boxed{25} \\]"""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should take the last LaTeX pattern
        assert "recalculate more carefully" in result.reasoning
        assert "quadratic formula" in result.reasoning
        assert result.answer == "25"
    
    def test_mixed_answer_formats(self):
        """Test when both standard and LaTeX formats are present."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Initial approach: Answer: 15
        
Actually, let me use proper mathematical notation:
The solution to the integral is:

\\boxed{25}"""
        
        result = adapter._parse_llm_output(raw_response)
        
        # The "Answer: 15" pattern matches first and stops processing
        assert "Initial approach" in result.reasoning
        assert result.answer == "15"
    
    def test_nested_cleanup(self):
        """Test multiple leading and trailing phrases that need cleanup."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Working on this probability problem:
        
P(A∩B) = P(A) × P(B) = 0.5 × 0.3 = 0.15
This gives us the joint probability.

Answer: So, therefore, the answer is 0.15 is the solution"""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should clean up both leading and trailing phrases
        assert "probability problem" in result.reasoning
        assert "joint probability" in result.reasoning
        assert result.answer == "0.15"
    
    def test_preserve_text_answers(self):
        """Test that text answers like 'Yes, it is correct' are preserved."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me check if this statement is true:
        
The sum of angles in a triangle is 180°.
This is a fundamental theorem in geometry.
It applies to all triangles in Euclidean geometry.

Answer: Yes, it is correct"""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should preserve the full text answer, not extract individual words
        assert "fundamental theorem" in result.reasoning
        assert "Euclidean geometry" in result.reasoning
        assert result.answer == "Yes, it is correct"
    
    def test_punctuation_handling(self):
        """Test that punctuation is handled correctly for numbers vs text."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me solve this equation:
        
2x + 5 = 15
2x = 10
x = 5

Answer: 5"""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should preserve the number without extra punctuation
        assert "solve this equation" in result.reasoning
        assert "2x = 10" in result.reasoning
        assert result.answer == "5"
    
    def test_whitespace_variations(self):
        """Test various whitespace patterns in answer formats."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Calculating the derivative:
        
f(x) = x³ + 2x² - 5x + 3
f'(x) = 3x² + 4x - 5
At x = 2: f'(2) = 3(4) + 4(2) - 5 = 12 + 8 - 5 = 15

Answer:    15   """
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should handle extra whitespace properly
        assert "Calculating the derivative" in result.reasoning
        assert "f'(2) = 3(4)" in result.reasoning
        assert result.answer == "15"
    
    def test_fallback_candidate_selection(self):
        """Test fallback logic when no answer patterns match."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Let me work through this problem step by step.
        
This is a complex geometric problem involving triangles.
The calculation involves several steps and intermediate values.
First, I need to find the area using the base and height.
Then I can determine the final measurement.
The measurement comes out to be 42."""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Should use fallback logic to select the last suitable line
        assert "complex geometric problem" in result.reasoning
        assert "intermediate values" in result.reasoning
        assert result.answer == "The measurement comes out to be 42."
    
    def test_fallback_numeric_priority(self):
        """Test that fallback logic uses last line when no patterns match."""
        adapter = LiteLLMAdapter()
        
        raw_response = """Working on this calculation problem.
        
The steps are quite involved and require careful attention.
We need to consider multiple factors in the computation.
The final result is 156."""
        
        result = adapter._parse_llm_output(raw_response)
        
        # Fallback takes the last line
        assert "calculation problem" in result.reasoning
        assert "multiple factors" in result.reasoning
        assert result.answer == "The final result is 156."
    
    def test_fallback_line_length_filter(self):
        """Test that fallback logic takes the last line when no patterns match."""
        adapter = LiteLLMAdapter()
        
        raw_response = """This is a very long and detailed explanation that goes on and on about the mathematical principles involved in solving this particular type of problem, including historical context and various alternative approaches.
        
The computation involves several steps.
We start with the given values.
The answer is 73."""
        
        result = adapter._parse_llm_output(raw_response)
        
        # The "The answer is" pattern matches and extracts "73."
        assert "computation involves several steps" in result.reasoning
        assert result.answer == "73."


class TestLiteLLMAdapterIntegration:
    """Integration test with mocked OpenAI client."""
    
    @patch('llm_agents.common.interfaces.OpenAI')
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
    
    @patch('llm_agents.common.interfaces.OpenAI')
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