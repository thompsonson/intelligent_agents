"""GSM8K-style benchmark proof of concept.

This module implements a small-scale benchmark using 5 GSM8K-style questions
to demonstrate the self-consistency approach effectiveness, following the
methodology from Tyler Burleigh's blog post analysis.
"""

import re
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from ..self_consistency.agent import SelfConsistencyAgent
from ..self_consistency.config import AgentConfig
from ..common.interfaces import LLMInterface


@dataclass
class BenchmarkQuestion:
    """A single benchmark question with expected answer."""
    id: str
    question: str
    expected_answer: str
    difficulty: str
    category: str


@dataclass
class BenchmarkResult:
    """Result for a single question with multiple attempts."""
    question_id: str
    question: str
    expected_answer: str
    attempts: int
    responses: List[str]
    final_answer: str
    is_correct: bool
    confidence: float
    processing_time: float


@dataclass
class BenchmarkReport:
    """Complete benchmark report across all configurations."""
    questions: List[BenchmarkQuestion]
    results: Dict[int, List[BenchmarkResult]]  # attempts -> results
    accuracy_by_attempts: Dict[int, float]
    total_questions: int
    summary: str


class GSM8KBenchmark:
    """GSM8K-style benchmark for mathematical reasoning evaluation."""
    
    def __init__(self, llm_interface: LLMInterface):
        """Initialize benchmark with LLM interface.
        
        Args:
            llm_interface: Interface for making LLM calls
        """
        self.llm_interface = llm_interface
        self.questions = self._get_test_questions()
        
    def _get_test_questions(self) -> List[BenchmarkQuestion]:
        """Get the 5 test questions representing different difficulty levels.
        
        Returns:
            List of BenchmarkQuestion objects
        """
        return [
            BenchmarkQuestion(
                id="easy_arithmetic",
                question="Sarah has 12 apples. She gives away 3 apples to her friend. How many apples does Sarah have left?",
                expected_answer="9",
                difficulty="Easy",
                category="Basic Arithmetic"
            ),
            BenchmarkQuestion(
                id="multi_step_calculation",
                question="A store sells books for $8 each. If Tom buys 5 books and pays with a $50 bill, how much change does he get?",
                expected_answer="10",
                difficulty="Medium",
                category="Multi-step Calculation"
            ),
            BenchmarkQuestion(
                id="percentage_problem",
                question="In a class of 30 students, 60% are girls. How many boys are in the class?",
                expected_answer="12",
                difficulty="Medium",
                category="Percentage"
            ),
            BenchmarkQuestion(
                id="rate_time_distance",
                question="A car travels at 60 mph for 2.5 hours, then 40 mph for 1.5 hours. What is the total distance traveled?",
                expected_answer="210",
                difficulty="Medium-Hard",
                category="Rate/Time/Distance"
            ),
            BenchmarkQuestion(
                id="complex_word_problem",
                question="A bakery made 145 cupcakes. They sold 80% of them. The remaining cupcakes are packed into boxes of 6. How many full boxes can they fill with the remaining cupcakes?",
                expected_answer="4",
                difficulty="Hard",
                category="Multi-step Word Problem"
            )
        ]
    
    def run_benchmark(self, attempt_counts: List[int] = None) -> BenchmarkReport:
        """Run the complete benchmark across different attempt configurations.
        
        Args:
            attempt_counts: List of attempt counts to test (default: [1, 3, 5, 10])
            
        Returns:
            BenchmarkReport with complete results
        """
        if attempt_counts is None:
            attempt_counts = [1, 3, 5, 10]
            
        print(f"🧮 Starting GSM8K Benchmark Proof of Concept")
        print(f"📊 Testing {len(self.questions)} questions with {len(attempt_counts)} configurations")
        print(f"⚙️ Attempt counts: {attempt_counts}")
        print("-" * 60)
        
        all_results = {}
        accuracy_by_attempts = {}
        
        for attempts in attempt_counts:
            print(f"\n🎯 Testing with {attempts} attempt(s)...")
            results = []
            
            for i, question in enumerate(self.questions, 1):
                print(f"  📝 Question {i}/{len(self.questions)}: {question.id} ({question.difficulty})")
                print(f"     Processing {attempts} attempt(s)... (this may take ~{attempts * 30}s)")
                
                result = self._evaluate_question(question, attempts)
                results.append(result)
                
                status = "✅ Correct" if result.is_correct else "❌ Incorrect"
                print(f"     Expected: {result.expected_answer}, Got: {result.final_answer} - {status}")
                print(f"     Completed in {result.processing_time:.1f}s")
            
            all_results[attempts] = results
            correct_count = sum(1 for r in results if r.is_correct)
            accuracy = correct_count / len(results)
            accuracy_by_attempts[attempts] = accuracy
            
            print(f"  📈 Accuracy: {correct_count}/{len(results)} = {accuracy:.1%}")
        
        # Generate summary
        summary = self._generate_summary(accuracy_by_attempts)
        
        return BenchmarkReport(
            questions=self.questions,
            results=all_results,
            accuracy_by_attempts=accuracy_by_attempts,
            total_questions=len(self.questions),
            summary=summary
        )
    
    def _evaluate_question(self, question: BenchmarkQuestion, attempts: int) -> BenchmarkResult:
        """Evaluate a single question with specified number of attempts.
        
        Args:
            question: The question to evaluate
            attempts: Number of attempts to make
            
        Returns:
            BenchmarkResult for this question
        """
        start_time = time.time()
        
        # Configure agent for mathematical reasoning
        config = AgentConfig(
            llm_interface=self.llm_interface,
            target_responses=attempts,
            prompt_template="Solve this step by step, showing all work. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):"
        )
        
        # Run self-consistency agent
        agent = SelfConsistencyAgent(config, question.question)
        consensus_result = agent.process_question()
        
        processing_time = time.time() - start_time
        
        # Extract all individual responses for analysis
        individual_responses = [response.answer for response in agent._llm_responses]
        
        # Evaluate correctness
        is_correct = self._evaluate_answer(consensus_result.final_answer, question.expected_answer)
        
        return BenchmarkResult(
            question_id=question.id,
            question=question.question,
            expected_answer=question.expected_answer,
            attempts=attempts,
            responses=individual_responses,
            final_answer=consensus_result.final_answer,
            is_correct=is_correct,
            confidence=consensus_result.confidence,
            processing_time=processing_time
        )
    
    def _evaluate_answer(self, predicted: str, expected: str) -> bool:
        """Evaluate if predicted answer matches expected answer.
        
        Args:
            predicted: The agent's predicted answer
            expected: The expected correct answer
            
        Returns:
            True if answers match, False otherwise
        """
        # Normalize both answers by extracting numbers
        predicted_num = self._extract_number(predicted)
        expected_num = self._extract_number(expected)
        
        if predicted_num is not None and expected_num is not None:
            # Compare as numbers (handles decimal precision)
            return abs(float(predicted_num) - float(expected_num)) < 0.01
        
        # Fallback to string comparison (case-insensitive, whitespace-stripped)
        predicted_clean = predicted.strip().lower()
        expected_clean = expected.strip().lower()
        
        return predicted_clean == expected_clean
    
    def _extract_number(self, text: str) -> Optional[str]:
        """Extract the first number from text.
        
        Args:
            text: Text potentially containing a number
            
        Returns:
            The first number found as string, or None if no number found
        """
        # Look for numbers (including decimals)
        number_pattern = r'-?\d+\.?\d*'
        match = re.search(number_pattern, text.replace(',', ''))
        
        if match:
            return match.group()
        
        return None
    
    def _generate_summary(self, accuracy_by_attempts: Dict[int, float]) -> str:
        """Generate a summary of benchmark results.
        
        Args:
            accuracy_by_attempts: Dictionary mapping attempt counts to accuracy
            
        Returns:
            Summary string
        """
        lines = [
            "🎯 GSM8K Benchmark Results Summary",
            "=" * 40,
            ""
        ]
        
        # Show results by attempt count
        for attempts in sorted(accuracy_by_attempts.keys()):
            accuracy = accuracy_by_attempts[attempts]
            lines.append(f"{attempts:2d} attempt(s): {accuracy:.1%} accuracy")
        
        # Calculate improvement
        if len(accuracy_by_attempts) >= 2:
            min_attempts = min(accuracy_by_attempts.keys())
            max_attempts = max(accuracy_by_attempts.keys())
            
            baseline_accuracy = accuracy_by_attempts[min_attempts]
            best_accuracy = accuracy_by_attempts[max_attempts]
            
            improvement = best_accuracy - baseline_accuracy
            
            lines.extend([
                "",
                f"📈 Improvement from {min_attempts} to {max_attempts} attempts: {improvement:+.1%}",
                f"📊 Best configuration: {max_attempts} attempts ({best_accuracy:.1%} accuracy)"
            ])
        
        lines.extend([
            "",
            "🔬 This demonstrates the self-consistency approach where",
            "   multiple independent reasoning paths improve accuracy",
            "   through majority voting aggregation."
        ])
        
        return "\n".join(lines)
    
    def print_detailed_results(self, report: BenchmarkReport) -> None:
        """Print detailed results for analysis.
        
        Args:
            report: The benchmark report to display
        """
        print("\n" + "=" * 80)
        print("📋 DETAILED BENCHMARK RESULTS")
        print("=" * 80)
        
        for attempts in sorted(report.results.keys()):
            print(f"\n🎯 {attempts} ATTEMPT(S) CONFIGURATION")
            print("-" * 50)
            
            results = report.results[attempts]
            
            for result in results:
                print(f"\n📝 Question: {result.question_id}")
                print(f"   Question: {result.question}")
                print(f"   Expected: {result.expected_answer}")
                print(f"   Got: {result.final_answer}")
                print(f"   Correct: {'✅ Yes' if result.is_correct else '❌ No'}")
                print(f"   Confidence: {result.confidence:.3f}")
                print(f"   Time: {result.processing_time:.2f}s")
                print(f"   All responses: {result.responses}")
        
        print(f"\n{report.summary}")
    
    def export_results(self, report: BenchmarkReport, filename: str = "gsm8k_benchmark_results.txt") -> None:
        """Export benchmark results to file.
        
        Args:
            report: The benchmark report to export
            filename: Output filename
        """
        with open(filename, 'w') as f:
            f.write("GSM8K Benchmark Results\n")
            f.write("=" * 50 + "\n\n")
            
            # Summary
            f.write(report.summary + "\n\n")
            
            # Detailed results
            for attempts in sorted(report.results.keys()):
                f.write(f"\n{attempts} ATTEMPTS CONFIGURATION\n")
                f.write("-" * 30 + "\n")
                
                for result in report.results[attempts]:
                    f.write(f"\nQuestion: {result.question_id}\n")
                    f.write(f"Text: {result.question}\n")
                    f.write(f"Expected: {result.expected_answer}\n")
                    f.write(f"Predicted: {result.final_answer}\n")
                    f.write(f"Correct: {result.is_correct}\n")
                    f.write(f"Confidence: {result.confidence:.3f}\n")
                    f.write(f"Responses: {result.responses}\n")
        
        print(f"📁 Results exported to: {filename}")