# SelfReflectionAgent GSM8K Benchmark Implementation Plan

## Overview
Implement GSM8K benchmark for SelfReflectionAgent with SQLite storage for entropy tracking and convergence analysis.

## File Structure

### New Files to Create
```
llm_agents/benchmark/
├── gsm8k_reflection.py     # Main reflection benchmark
├── run_gsm8k_reflection.py # Standalone runner
└── database.py             # SQLite schema and operations
```

### Files to Modify
```
llm_agents/benchmark/__init__.py  # Add new imports
```

## Database Schema (SQLite)

### Tables
```sql
-- Benchmark runs metadata
CREATE TABLE benchmark_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_type TEXT NOT NULL,  -- 'self_reflection'
    model_name TEXT NOT NULL,
    config_json TEXT NOT NULL,  -- Serialized ReflectionConfig
    total_questions INTEGER,
    completed_at TEXT
);

-- Question-level results
CREATE TABLE question_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    final_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    early_stopping BOOLEAN NOT NULL,
    total_responses INTEGER NOT NULL,
    consensus_confidence REAL NOT NULL,
    uncertainty_level TEXT NOT NULL,
    processing_time REAL NOT NULL,
    FOREIGN KEY (run_id) REFERENCES benchmark_runs (id)
);

-- Response evolution tracking
CREATE TABLE response_evolution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL,
    response_num INTEGER NOT NULL,  -- 1, 2, 3, ...
    response_text TEXT NOT NULL,
    answer TEXT NOT NULL,
    FOREIGN KEY (result_id) REFERENCES question_results (id)
);

-- Entropy and confidence evolution
CREATE TABLE entropy_evolution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL,
    response_num INTEGER NOT NULL,  -- 1, 2, 3, ...
    normalized_entropy REAL NOT NULL,
    confidence REAL NOT NULL,
    consensus_type TEXT,  -- 'strong', 'emerging', 'divided', 'binary'
    entropy_level TEXT,   -- 'concentrated', 'scattered', 'uniform'
    FOREIGN KEY (result_id) REFERENCES question_results (id)
);

-- Convergence analysis metrics
CREATE TABLE convergence_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL,
    convergence_rate REAL NOT NULL,
    final_stability REAL NOT NULL,
    entropy_convergence_rate REAL NOT NULL,
    entropy_final_stability REAL NOT NULL,
    FOREIGN KEY (result_id) REFERENCES question_results (id)
);
```

## Implementation Details

### 1. database.py
```python
"""Database operations for reflection benchmark."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict

class BenchmarkDatabase:
    def __init__(self, db_path: str = "gsm8k_reflection_results.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist."""
        # Implementation with CREATE TABLE statements above
    
    def create_benchmark_run(self, agent_type: str, model_name: str, 
                           config: Dict[str, Any], total_questions: int) -> int:
        """Create new benchmark run, return run_id."""
        
    def save_question_result(self, run_id: int, question_result: Dict[str, Any]) -> int:
        """Save question result, return result_id."""
        
    def save_entropy_evolution(self, result_id: int, evolution_data: List[Dict]):
        """Save entropy/confidence evolution data."""
        
    def save_convergence_metrics(self, result_id: int, metrics: Dict[str, Any]):
        """Save convergence analysis metrics."""
        
    def complete_benchmark_run(self, run_id: int):
        """Mark benchmark run as completed."""
        
    def get_run_summary(self, run_id: int) -> Dict[str, Any]:
        """Get summary statistics for a run."""
```

### 2. gsm8k_reflection.py
```python
"""GSM8K benchmark for SelfReflectionAgent with entropy tracking."""

import time
from typing import List, Dict, Any
from dataclasses import dataclass
from ..self_reflection.agent import SelfReflectionAgent
from ..self_reflection.config import ReflectionConfig
from ..self_reflection.domain import ReflectionResult
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

class GSM8KReflectionBenchmark:
    """GSM8K benchmark for SelfReflectionAgent with database storage."""
    
    def __init__(self, llm_interface, db_path: str = None):
        self.llm_interface = llm_interface
        self.database = BenchmarkDatabase(db_path)
        self.questions = self._get_test_questions()  # Reuse from gsm8k_poc
    
    def run_benchmark(self, config: ReflectionConfig = None) -> Dict[str, Any]:
        """Run complete benchmark with entropy tracking."""
        if config is None:
            config = self._get_default_config()
        
        # Create benchmark run
        run_id = self.database.create_benchmark_run(
            agent_type="self_reflection",
            model_name=self.llm_interface.model,
            config=self._config_to_dict(config),
            total_questions=len(self.questions)
        )
        
        results = []
        for question in self.questions:
            result = self._evaluate_question_with_tracking(question, config)
            result_id = self._save_question_result(run_id, result)
            results.append(result)
        
        self.database.complete_benchmark_run(run_id)
        return self._generate_report(run_id, results)
    
    def _evaluate_question_with_tracking(self, question: BenchmarkQuestion, 
                                       config: ReflectionConfig) -> ReflectionBenchmarkResult:
        """Evaluate question with detailed entropy tracking."""
        start_time = time.time()
        
        # Create modified agent that tracks evolution
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
```

### 3. run_gsm8k_reflection.py
```python
#!/usr/bin/env python3
"""Standalone runner for GSM8K SelfReflectionAgent benchmark."""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm_agents.common.interfaces import LiteLLMAdapter
from llm_agents.self_reflection.config import ReflectionConfig
from llm_agents.benchmark.gsm8k_reflection import GSM8KReflectionBenchmark

def main():
    parser = argparse.ArgumentParser(description='GSM8K SelfReflectionAgent Benchmark')
    parser.add_argument('--model', '-m', help='LLM model to use')
    parser.add_argument('--confidence-threshold', '-c', type=float, default=0.8,
                       help='Confidence threshold for early stopping')
    parser.add_argument('--entropy-mode', '-e', default='combined',
                       choices=['off', 'confidence_only', 'entropy_only', 'combined'],
                       help='Entropy calculation mode')
    parser.add_argument('--db-path', '-d', help='SQLite database path')
    
    args = parser.parse_args()
    
    print("🔍 GSM8K SelfReflectionAgent Benchmark")
    print("=" * 50)
    print("Testing entropy-aware early stopping with mathematical reasoning")
    
    # Initialize LLM interface
    llm_interface = LiteLLMAdapter(model=args.model) if args.model else LiteLLMAdapter()
    print(f"Model: {llm_interface.model}")
    
    # Create custom config
    config = ReflectionConfig(
        llm_interface=llm_interface,
        confidence_threshold=args.confidence_threshold,
        entropy_mode=args.entropy_mode,
        target_responses=10,
        min_responses=3,
        prompt_template="Solve this step by step, showing all work. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42':"
    )
    
    print(f"Confidence threshold: {config.confidence_threshold}")
    print(f"Entropy mode: {config.entropy_mode}")
    
    # Run benchmark
    benchmark = GSM8KReflectionBenchmark(llm_interface, args.db_path)
    
    try:
        results = benchmark.run_benchmark(config)
        
        print("\n" + "=" * 60)
        print("🎯 REFLECTION BENCHMARK COMPLETE")
        print("=" * 60)
        print(f"Accuracy: {results['accuracy']:.1%}")
        print(f"Early stopping rate: {results['early_stopping_rate']:.1%}")
        print(f"Average responses: {results['avg_responses']:.1f}")
        print(f"Database: {benchmark.database.db_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

## Configuration Requirements

### ReflectionConfig Defaults for Math
```python
ReflectionConfig(
    llm_interface=llm_interface,
    target_responses=10,              # Allow exploration
    confidence_threshold=0.8,         # High confidence for math
    min_responses=3,                  # Minimum for reasoning
    entropy_threshold=0.3,            # Stop if concentrated 
    entropy_weight=0.3,               # Moderate entropy influence
    entropy_mode="combined",          # Balance confidence + entropy
    min_entropy_samples=4,            # Minimum for entropy calculations
    prompt_template="Solve this step by step, showing all work. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42':"
)
```

## Integration Points

### Existing Code Reuse
- Import `BenchmarkQuestion` from `gsm8k_poc.py`
- Reuse `_evaluate_answer()` and `_extract_number()` methods
- Use existing `LiteLLMAdapter` interface

### New Dependencies
```python
# Add to gsm8k_reflection.py imports
from ..self_reflection.agent import SelfReflectionAgent
from ..self_reflection.config import ReflectionConfig  
from ..self_reflection.domain import ReflectionResult
```

## Testing Strategy

### Unit Tests (test_gsm8k_reflection.py)
```python
class TestGSM8KReflectionBenchmark:
    def test_database_creation(self):
        """Test SQLite database initialization."""
        
    def test_entropy_tracking(self):
        """Test entropy evolution tracking during processing."""
        
    def test_early_stopping_detection(self):
        """Test early stopping triggers and recording."""
        
    def test_config_serialization(self):
        """Test ReflectionConfig JSON serialization."""
        
    def test_question_evaluation_with_tracking(self):
        """Test complete question evaluation with entropy tracking."""
```

### Integration Tests
```python
def test_full_benchmark_with_mock_llm(self):
    """Test complete benchmark run with mocked LLM responses."""
    
def test_database_persistence(self):
    """Test data persistence across benchmark runs."""
```

## Makefile Targets

### Add to Makefile
```makefile
# SelfReflectionAgent GSM8K benchmark
benchmark-gsm8k-reflection:
	cd llm_agents/benchmark && python run_gsm8k_reflection.py

# Test reflection benchmark
test-reflection-benchmark:
	python -m pytest llm_agents/tests/test_gsm8k_reflection.py -v

# Analyze benchmark results
analyze-reflection-results:
	@echo "Opening SQLite database for analysis..."
	sqlite3 gsm8k_reflection_results.db
```

## Success Criteria

### Functional Requirements
- ✅ SelfReflectionAgent runs GSM8K questions
- ✅ SQLite database stores all entropy evolution data
- ✅ Early stopping analysis and reporting
- ✅ Entropy tracking at each response step
- ✅ Convergence metrics calculation

### Performance Requirements  
- ✅ Benchmark completes 5 questions in <5 minutes
- ✅ Database operations add <1% overhead
- ✅ Early stopping reduces total LLM calls by 20-50%

### Quality Requirements
- ✅ 90%+ accuracy on GSM8K with math models
- ✅ Consistent entropy calculations
- ✅ Comprehensive test coverage for new components

## Implementation Order

1. **Database module** (`database.py`) - Core data persistence
2. **Tracking agent** (`TrackingReflectionAgent`) - Enhanced entropy tracking  
3. **Benchmark class** (`GSM8KReflectionBenchmark`) - Main orchestration
4. **Runner script** (`run_gsm8k_reflection.py`) - CLI interface
5. **Tests** (`test_gsm8k_reflection.py`) - Validation
6. **Documentation updates** - Update Claude.md with new features