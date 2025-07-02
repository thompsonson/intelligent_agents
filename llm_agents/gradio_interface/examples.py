"""Example questions and configurations for the Gradio interface.

This module provides sample questions and configurations that demonstrate
the capabilities and differences between the self-consistency and self-reflection agents.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ExampleConfig:
    """Configuration for an example demonstration."""
    name: str
    description: str
    question: str
    target_responses: int
    confidence_threshold: float
    min_responses: int
    prompt_template: str
    expected_behavior: str


class Examples:
    """Collection of example questions and configurations."""
    
    @staticmethod
    def get_sample_questions() -> Dict[str, List[str]]:
        """Get dictionary of sample questions organized by category.
        
        Returns:
            Dictionary mapping question categories to sample questions
        """
        return {
            "Mathematical Reasoning": [
                "What is 15% of 240?",
                "If a train travels 120 miles in 2.5 hours, what is its average speed?",
                "Solve for x: 2x + 5 = 17",
                "What is the area of a circle with radius 7cm?",
                "Calculate the compound interest on $1000 at 5% annual rate for 3 years",
                "If log₂(x) = 5, what is the value of x?",
                "Find the derivative of f(x) = 3x² + 2x - 1"
            ],
            "Logical Reasoning": [
                "If all cats are mammals and all mammals are animals, are all cats animals?",
                "A farmer has chickens and cows. If there are 35 heads and 94 legs total, how many chickens are there?",
                "If it takes 5 machines 5 minutes to make 5 widgets, how long does it take 100 machines to make 100 widgets?",
                "All roses are flowers. Some flowers fade quickly. Therefore, do some roses fade quickly?",
                "If A implies B, and B implies C, what can we conclude about A and C?",
                "Three friends have different ages. Alice is older than Bob. Carol is younger than Bob. Who is the youngest?"
            ],
            "Number Sequences": [
                "What is the next number in the sequence: 15, 29, 56, 108, 208, ...?",
                "Find the next term: 13, -21, 34, -55, 89, ...?",
                "What comes next: 52, 56, 48, 64, 32, ...?",
                "Continue the sequence: 1, 3, 7, 11, 13, ...?",
                "Next number: 230, 460, 46, 92, 9.2, ...?",
                "What follows: 3, 12, 24, 33, 66, ...?",
                "Find the pattern: 3, 5, 7, 11, 13, ...?",
                "Next term: 8, 16, 24, 36, 48, ...?",
                "Continue: 68, 36, 20, 12, 8, ...?",
                "What's next: 18, 6, 24, 8, 32, ...?",
                "Pattern: 99, 18, 36, 9, 18, ...?",
                "Next: 3, 8, 23, 68, 203, ...?",
                "Continue: 144, 73, 14, 8, 236, ...?",
                "What follows: 10, 45, 15, 38, 20, ...?",
                "Next term: 1, 10, 37, 82, 145, ...?",
                "Continue: -2, 1, 6, 13, 22, ...?",
                "Pattern: 34, -21, 13, -8, 5, ...?",
                "Next: 1, 0, 1, -1, 2, ...?",
                "What comes next: 108, 56, 29, 15, 8, ...?",
                "Continue: 1, 8, 27, 64, 125, ...?",
                "Next term: -3, 3, 27, 69, 129, ...?"
            ],
            "General Knowledge": [
                "What is the capital of Australia?",
                "Who wrote the novel '1984'?",
                "What is the chemical symbol for gold?",
                "In what year did World War II end?",
                "What is the largest planet in our solar system?",
                "Who painted the Mona Lisa?",
                "What is the speed of light in a vacuum?",
                "Which element has the atomic number 1?"
            ],
            "Scientific Facts": [
                "What is the chemical formula for water?",
                "How many chambers does a human heart have?",
                "What gas do plants absorb during photosynthesis?",
                "At what temperature does water boil at sea level in Celsius?",
                "What is the smallest unit of matter?",
                "How many bones are in an adult human body?",
                "What is the most abundant gas in Earth's atmosphere?",
                "What force keeps planets in orbit around the sun?"
            ],
            "Problem Solving": [
                "You have a 3-gallon jug and a 5-gallon jug. How can you measure exactly 4 gallons?",
                "A clock shows 3:15. What is the angle between the hour and minute hands?",
                "How many ways can you arrange the letters in the word 'MATH'?",
                "If you fold a piece of paper in half 7 times, how many layers will you have?",
                "A ladder leans against a wall. The bottom is 6 feet from the wall, the top touches 8 feet up. What's the ladder's length?",
                "You have 12 balls, one weighs differently. Using a balance scale 3 times, how do you find it?"
            ]
        }
    
    @staticmethod
    def get_demonstration_configs() -> List[ExampleConfig]:
        """Get predefined configurations for demonstrations.
        
        Returns:
            List of ExampleConfig objects for different scenarios
        """
        return [
            ExampleConfig(
                name="Simple Math",
                description="Basic arithmetic with high confidence expected",
                question="What is 12 × 8?",
                target_responses=5,
                confidence_threshold=0.9,
                min_responses=3,
                prompt_template="Mathematical",
                expected_behavior="Self-reflection should stop early with high confidence"
            ),
            ExampleConfig(
                name="Number Sequence",
                description="Pattern recognition in sequences",
                question="What is the next number in the sequence: 15, 29, 56, 108, 208, ...?",
                target_responses=8,
                confidence_threshold=0.8,
                min_responses=4,
                prompt_template="Logical",
                expected_behavior="May require multiple attempts to identify pattern"
            ),
            ExampleConfig(
                name="Complex Reasoning",
                description="Multi-step logical problem",
                question="A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
                target_responses=10,
                confidence_threshold=0.8,
                min_responses=5,
                prompt_template="Verification",
                expected_behavior="May require full sampling due to common incorrect intuition"
            ),
            ExampleConfig(
                name="Scientific Fact",
                description="Clear factual question with definitive answer",
                question="What is the chemical formula for water?",
                target_responses=5,
                confidence_threshold=0.95,
                min_responses=2,
                prompt_template="Factual",
                expected_behavior="Very high confidence, likely early stopping"
            ),
            ExampleConfig(
                name="Fibonacci Sequence",
                description="Well-known mathematical sequence",
                question="Find the next term: 13, -21, 34, -55, 89, ...?",
                target_responses=7,
                confidence_threshold=0.85,
                min_responses=3,
                prompt_template="Mathematical",
                expected_behavior="Should converge once pattern is recognized"
            )
        ]
    
    @staticmethod
    def get_comparison_scenarios() -> List[Dict[str, Any]]:
        """Get scenarios specifically designed for agent comparison.
        
        Returns:
            List of scenarios highlighting agent differences
        """
        return [
            {
                "name": "Early Stopping Efficiency",
                "description": "Demonstrates cost savings through early stopping",
                "question": "What is 7 × 9?",
                "config": {
                    "target_responses": 10,
                    "confidence_threshold": 0.9,
                    "min_responses": 3,
                    "prompt_template": "Mathematical"
                },
                "expected_outcome": "Self-reflection stops early, self-consistency uses all responses"
            },
            {
                "name": "Sequence Pattern Recognition",
                "description": "Shows different convergence rates for pattern problems",
                "question": "What comes next: 1, 8, 27, 64, 125, ...?",
                "config": {
                    "target_responses": 8,
                    "confidence_threshold": 0.8,
                    "min_responses": 4,
                    "prompt_template": "Logical"
                },
                "expected_outcome": "Variable confidence based on pattern recognition"
            },
            {
                "name": "Convergence Analysis",
                "description": "Demonstrates confidence evolution over responses",
                "question": "If a car travels 60 mph for 2.5 hours, how far does it go?",
                "config": {
                    "target_responses": 10,
                    "confidence_threshold": 0.85,
                    "min_responses": 4,
                    "prompt_template": "Mathematical"
                },
                "expected_outcome": "Clear convergence pattern, early stopping likely"
            }
        ]
    
    @staticmethod
    def get_educational_examples() -> Dict[str, Dict[str, Any]]:
        """Get examples designed for educational purposes.
        
        Returns:
            Dictionary mapping educational concepts to example configurations
        """
        return {
            "early_stopping": {
                "title": "Early Stopping Demonstration",
                "description": "Shows how self-reflection can save computational cost",
                "questions": [
                    "What is 5 + 5?",
                    "What is the capital of the United States?",
                    "How many sides does a triangle have?"
                ],
                "config": {
                    "target_responses": 10,
                    "confidence_threshold": 0.9,
                    "min_responses": 3
                }
            },
            "sequence_patterns": {
                "title": "Number Sequence Recognition",
                "description": "Tests pattern recognition abilities with various sequences",
                "questions": [
                    "Continue: 3, 5, 7, 11, 13, ...?",
                    "Next term: 8, 16, 24, 36, 48, ...?",
                    "What follows: 68, 36, 20, 12, 8, ...?"
                ],
                "config": {
                    "target_responses": 8,
                    "confidence_threshold": 0.8,
                    "min_responses": 4
                }
            },
            "probability_distributions": {
                "title": "Probability Distributions",
                "description": "Shows detailed probability analysis vs simple majority vote",
                "questions": [
                    "What comes after Monday?",
                    "How many legs does a spider have?",
                    "What is 10 divided by 2?"
                ],
                "config": {
                    "target_responses": 6,
                    "confidence_threshold": 0.8,
                    "min_responses": 4
                }
            },
            "convergence_patterns": {
                "title": "Convergence Analysis",
                "description": "Demonstrates how confidence evolves over time",
                "questions": [
                    "What is 144 ÷ 12?",
                    "What is the chemical symbol for gold?",
                    "What gas do plants produce during photosynthesis?"
                ],
                "config": {
                    "target_responses": 10,
                    "confidence_threshold": 0.85,
                    "min_responses": 4
                }
            }
        }
    
    @staticmethod
    def get_random_question() -> str:
        """Get a random sample question from all categories.
        
        Returns:
            Random question string
        """
        import random
        
        all_questions = []
        questions_by_category = Examples.get_sample_questions()
        
        for category_questions in questions_by_category.values():
            all_questions.extend(category_questions)
        
        return random.choice(all_questions)
    
    @staticmethod
    def get_questions_by_difficulty() -> Dict[str, List[str]]:
        """Get questions organized by expected difficulty/complexity.
        
        Returns:
            Dictionary mapping difficulty levels to questions
        """
        return {
            "Easy": [
                "What is 5 + 3?",
                "What is the chemical formula for water?",
                "How many days are in a week?",
                "What is the capital of France?",
                "Continue: 1, 8, 27, 64, 125, ...?"
            ],
            "Medium": [
                "If a pizza is cut into 8 equal slices and you eat 3, what fraction remains?",
                "What is the next number in this sequence: 3, 5, 7, 11, 13, ...?",
                "How many minutes are in 2.5 hours?",
                "Find the next term: 8, 16, 24, 36, 48, ...?",
                "What is the derivative of f(x) = 3x² + 2x - 1?"
            ],
            "Hard": [
                "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
                "You have 12 balls, one of which weighs slightly more. Using a balance scale only 3 times, how do you find the heavier ball?",
                "What is the next number: 13, -21, 34, -55, 89, ...?",
                "Continue the sequence: 144, 73, 14, 8, 236, ...?",
                "Next term: 3, 8, 23, 68, 203, ...?"
            ]
        }
    
    @staticmethod
    def get_prompt_templates() -> Dict[str, str]:
        """Get various prompt templates for different question types.
        
        Returns:
            Dictionary mapping template names to prompt strings
        """
        return {
            "Standard": "Think step by step and provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Detailed": "Think step by step and explain your reasoning in detail. End with ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Mathematical": "Solve this step by step, showing all work. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Creative": "Think creatively about this question. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Logical": "Use logical reasoning to analyze this problem. End with ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Factual": "Answer directly and factually. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Perspective": "Consider different perspectives before answering. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):",
            "Verification": "Think step by step, then double-check your answer. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):"
        }