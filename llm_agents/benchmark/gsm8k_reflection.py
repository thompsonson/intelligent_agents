"""GSM8K benchmark for SelfReflectionAgent with entropy tracking."""

import time
import math
from collections import Counter
from typing import List, Dict, Any
from dataclasses import dataclass
from ..self_reflection.agent import SelfReflectionAgent
from ..self_reflection.config import ReflectionConfig
from ..self_reflection.domain import ReflectionResult
from ..common.domain import LLMResponse
from .database import BenchmarkDatabase
from .gsm8k_poc import BenchmarkQuestion  # Reuse existing questions


@dataclass
class ReflectionBenchmarkResult:
    """Enhanced result with entropy evolution tracking."""
    question_id: str
    question: str
    expected_answer: str
    reflection_result: ReflectionResult
    is_correct: bool
    processing_time: float
    entropy_evolution: List[Dict[str, Any]]  # Per-response entropy/confidence
    individual_responses: List[str]


class TrackingReflectionAgent(SelfReflectionAgent):
    """Modified SelfReflectionAgent that tracks entropy evolution."""
    
    def __init__(self, config: ReflectionConfig, question: str):
        super().__init__(config, question)
        self._entropy_evolution = []
        self._individual_responses = []
    
    def process_question(self) -> ReflectionResult:
        """Process with entropy tracking at each step."""
        for i in range(self._config.target_responses):
            # Generate response (same as parent)
            response = self._config.llm_interface.generate_llm_response(
                self._config.prompt_template, self._question
            )
            self._llm_responses.append(self._parse_llm_output(response))
            self._individual_responses.append(response.answer)
            
            # Track entropy evolution after each response
            self._track_entropy_evolution(i + 1)
            
            # Check early stopping
            if self._should_stop_early(i + 1):
                return self._build_reflection_result(early_stopping=True)
        
        return self._build_reflection_result(early_stopping=False)
    
    def _track_entropy_evolution(self, response_num: int):
        """Track entropy and confidence at current step."""
        distribution = self._calculate_distribution()
        confidence = self._calculate_consensus_confidence()
        normalized_entropy = self._calculate_normalized_entropy(distribution)
        entropy_level = self._get_entropy_level(normalized_entropy)
        consensus_type = self._classify_consensus_type(distribution)
        
        self._entropy_evolution.append({
            'response_num': response_num,
            'normalized_entropy': normalized_entropy,
            'confidence': confidence,
            'consensus_type': consensus_type,
            'entropy_level': entropy_level
        })
    
    def get_entropy_evolution(self) -> List[Dict[str, Any]]:
        """Get tracked entropy evolution data."""
        return self._entropy_evolution.copy()
    
    def get_individual_responses(self) -> List[str]:
        """Get all individual response answers."""
        return self._individual_responses.copy()


class GSM8KReflectionBenchmark:
    """GSM8K benchmark for SelfReflectionAgent with database storage."""
    
    def __init__(self, llm_interface, db_path: str = None):
        self.llm_interface = llm_interface
        self.database = BenchmarkDatabase(db_path)
        self.questions = self._get_test_questions()
    
    def _get_test_questions(self) -> List[BenchmarkQuestion]:
        """Get the 5 test questions (reuse from gsm8k_poc)."""
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
    
    def run_benchmark(self, config: ReflectionConfig = None) -> Dict[str, Any]:
        """Run complete benchmark with entropy tracking."""
        if config is None:
            config = self._get_default_config()
        
        print(f"🔍 Starting GSM8K SelfReflectionAgent Benchmark")
        print(f"📊 Testing {len(self.questions)} questions with entropy tracking")
        print(f"⚙️ Model: {self.llm_interface.model}")
        print(f"🎯 Confidence threshold: {config.confidence_threshold}")
        print(f"🌀 Entropy mode: {config.entropy_mode}")
        print("-" * 60)
        
        # Create benchmark run
        run_id = self.database.create_benchmark_run(
            agent_type="self_reflection",
            model_name=self.llm_interface.model,
            config=self._config_to_dict(config),
            total_questions=len(self.questions)
        )
        
        results = []
        for i, question in enumerate(self.questions, 1):
            print(f"\n📝 Question {i}/{len(self.questions)}: {question.id} ({question.difficulty})")
            print(f"   Processing with entropy tracking...")
            
            result = self._evaluate_question_with_tracking(question, config)
            result_id = self._save_question_result(run_id, result)
            results.append(result)
            
            status = "✅ Correct" if result.is_correct else "❌ Incorrect"
            print(f"   Expected: {result.expected_answer}, Got: {result.reflection_result.final_answer} - {status}")
            print(f"   Early stopping: {'Yes' if result.reflection_result.early_stopping else 'No'}")
            print(f"   Responses: {result.reflection_result.total_responses}")
            print(f"   Confidence: {result.reflection_result.consensus_confidence:.3f}")
            print(f"   Entropy level: {result.reflection_result.entropy_level}")
            print(f"   Completed in {result.processing_time:.1f}s")
        
        self.database.complete_benchmark_run(run_id)
        return self._generate_report(run_id, results)
    
    def _evaluate_question_with_tracking(self, question: BenchmarkQuestion, 
                                       config: ReflectionConfig) -> ReflectionBenchmarkResult:
        """Evaluate question with detailed entropy tracking."""
        start_time = time.time()
        
        # Create tracking agent
        agent = TrackingReflectionAgent(config, question.question)
        reflection_result = agent.process_question()
        
        processing_time = time.time() - start_time
        is_correct = self._evaluate_answer(reflection_result.final_answer, question.expected_answer)
        
        # Extract evolution data
        entropy_evolution = agent.get_entropy_evolution()
        individual_responses = agent.get_individual_responses()
        
        return ReflectionBenchmarkResult(
            question_id=question.id,
            question=question.question,
            expected_answer=question.expected_answer,
            reflection_result=reflection_result,
            is_correct=is_correct,
            processing_time=processing_time,
            entropy_evolution=entropy_evolution,
            individual_responses=individual_responses
        )
    
    def _save_question_result(self, run_id: int, result: ReflectionBenchmarkResult) -> int:
        """Save question result and related data to database."""
        # Save main question result
        question_data = {
            'question_id': result.question_id,
            'question_text': result.question,
            'expected_answer': result.expected_answer,
            'final_answer': result.reflection_result.final_answer,
            'is_correct': result.is_correct,
            'early_stopping': result.reflection_result.early_stopping,
            'total_responses': result.reflection_result.total_responses,
            'consensus_confidence': result.reflection_result.consensus_confidence,
            'uncertainty_level': result.reflection_result.uncertainty_level,
            'processing_time': result.processing_time
        }
        
        result_id = self.database.save_question_result(run_id, question_data)
        
        # Save response evolution
        self.database.save_response_evolution(result_id, result.individual_responses)
        
        # Save entropy evolution
        self.database.save_entropy_evolution(result_id, result.entropy_evolution)
        
        # Save convergence metrics
        convergence_data = result.reflection_result.convergence_analysis
        metrics = {
            'convergence_rate': convergence_data.get('convergence_rate', 0.0),
            'final_stability': convergence_data.get('final_stability', 1.0),
            'entropy_convergence_rate': convergence_data.get('entropy_convergence_rate', 0.0),
            'entropy_final_stability': convergence_data.get('entropy_final_stability', 1.0)
        }
        self.database.save_convergence_metrics(result_id, metrics)
        
        return result_id
    
    def _evaluate_answer(self, predicted: str, expected: str) -> bool:
        """Evaluate if predicted answer matches expected answer (reuse from gsm8k_poc)."""
        import re
        
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
    
    def _extract_number(self, text: str) -> str:
        """Extract the first number from text (reuse from gsm8k_poc)."""
        import re
        
        # Look for numbers (including decimals)
        number_pattern = r'-?\d+\.?\d*'
        match = re.search(number_pattern, text.replace(',', ''))
        
        if match:
            return match.group()
        
        return None
    
    def _get_default_config(self) -> ReflectionConfig:
        """Default configuration optimized for math problems."""
        return ReflectionConfig(
            llm_interface=self.llm_interface,
            target_responses=10,
            confidence_threshold=0.8,
            min_responses=3,
            entropy_threshold=0.3,
            entropy_weight=0.3,
            entropy_mode="combined",
            prompt_template="Solve this step by step, showing all work. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):"
        )
    
    def _config_to_dict(self, config: ReflectionConfig) -> Dict[str, Any]:
        """Convert ReflectionConfig to dictionary for JSON serialization."""
        return {
            'target_responses': config.target_responses,
            'confidence_threshold': config.confidence_threshold,
            'min_responses': config.min_responses,
            'entropy_threshold': config.entropy_threshold,
            'entropy_weight': config.entropy_weight,
            'entropy_mode': config.entropy_mode,
            'min_entropy_samples': config.min_entropy_samples,
            'prompt_template': config.prompt_template
        }
    
    def _generate_report(self, run_id: int, results: List[ReflectionBenchmarkResult]) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        correct_count = sum(1 for r in results if r.is_correct)
        early_stop_count = sum(1 for r in results if r.reflection_result.early_stopping)
        
        accuracy = correct_count / len(results) if results else 0
        early_stopping_rate = early_stop_count / len(results) if results else 0
        
        avg_responses = sum(r.reflection_result.total_responses for r in results) / len(results) if results else 0
        avg_confidence = sum(r.reflection_result.consensus_confidence for r in results) / len(results) if results else 0
        avg_processing_time = sum(r.processing_time for r in results) / len(results) if results else 0
        
        # Entropy analysis
        entropy_levels = [r.reflection_result.entropy_level for r in results]
        entropy_level_counts = Counter(entropy_levels)
        
        consensus_types = [r.reflection_result.consensus_type for r in results]
        consensus_type_counts = Counter(consensus_types)
        
        return {
            'run_id': run_id,
            'accuracy': accuracy,
            'early_stopping_rate': early_stopping_rate,
            'avg_responses': avg_responses,
            'avg_confidence': avg_confidence,
            'avg_processing_time': avg_processing_time,
            'entropy_level_distribution': dict(entropy_level_counts),
            'consensus_type_distribution': dict(consensus_type_counts),
            'total_questions': len(results),
            'correct_answers': correct_count,
            'early_stops': early_stop_count,
            'detailed_results': [
                {
                    'question_id': r.question_id,
                    'is_correct': r.is_correct,
                    'early_stopping': r.reflection_result.early_stopping,
                    'total_responses': r.reflection_result.total_responses,
                    'consensus_confidence': r.reflection_result.consensus_confidence,
                    'entropy_level': r.reflection_result.entropy_level,
                    'consensus_type': r.reflection_result.consensus_type,
                    'processing_time': r.processing_time
                }
                for r in results
            ]
        }