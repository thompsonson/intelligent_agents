"""Tests for GSM8K reflection benchmark components."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from ..benchmark.database import BenchmarkDatabase
from ..benchmark.gsm8k_reflection import GSM8KReflectionBenchmark, TrackingReflectionAgent
from ..self_reflection.agent import SelfReflectionAgent
from ..self_reflection.config import ReflectionConfig
from ..self_reflection.domain import ReflectionResult
from ..common.domain import LLMResponse


class TestBenchmarkDatabase:
    """Test database operations for reflection benchmark."""
    
    def test_database_creation(self):
        """Test SQLite database initialization."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Initialize database
            db = BenchmarkDatabase(db_path)
            
            # Verify database file exists
            assert Path(db_path).exists()
            
            # Verify tables exist by trying to query them
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check if tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = [
                    'benchmark_runs', 'question_results', 'response_evolution',
                    'entropy_evolution', 'convergence_metrics'
                ]
                
                for table in expected_tables:
                    assert table in tables
        
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_create_benchmark_run(self):
        """Test creating a benchmark run."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = BenchmarkDatabase(db_path)
            
            config = {
                'target_responses': 10,
                'confidence_threshold': 0.8,
                'entropy_mode': 'combined'
            }
            
            run_id = db.create_benchmark_run(
                agent_type='self_reflection',
                model_name='test-model',
                config=config,
                total_questions=5
            )
            
            assert isinstance(run_id, int)
            assert run_id > 0
            
            # Verify run was created
            summary = db.get_run_summary(run_id)
            assert summary['agent_type'] == 'self_reflection'
            assert summary['model_name'] == 'test-model'
            assert summary['total_questions'] == 5
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_save_question_result(self):
        """Test saving question results."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = BenchmarkDatabase(db_path)
            
            # Create a run first
            run_id = db.create_benchmark_run(
                agent_type='self_reflection',
                model_name='test-model',
                config={'test': 'config'},
                total_questions=1
            )
            
            # Save question result
            question_result = {
                'question_id': 'test_question',
                'question_text': 'What is 2+2?',
                'expected_answer': '4',
                'final_answer': '4',
                'is_correct': True,
                'early_stopping': True,
                'total_responses': 3,
                'consensus_confidence': 0.9,
                'uncertainty_level': 'low',
                'processing_time': 5.2
            }
            
            result_id = db.save_question_result(run_id, question_result)
            
            assert isinstance(result_id, int)
            assert result_id > 0
            
            # Verify data was saved
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM question_results WHERE id = ?", (result_id,))
                row = cursor.fetchone()
                assert row is not None
                assert row[2] == 'test_question'  # question_id
                assert row[5] == '4'  # final_answer
                assert row[6] == 1  # is_correct (True as int)
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_save_entropy_evolution(self):
        """Test saving entropy evolution data."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = BenchmarkDatabase(db_path)
            
            # Create run and question result
            run_id = db.create_benchmark_run(
                agent_type='self_reflection',
                model_name='test-model',
                config={'test': 'config'},
                total_questions=1
            )
            
            question_result = {
                'question_id': 'test_question',
                'question_text': 'What is 2+2?',
                'expected_answer': '4',
                'final_answer': '4',
                'is_correct': True,
                'early_stopping': True,
                'total_responses': 3,
                'consensus_confidence': 0.9,
                'uncertainty_level': 'low',
                'processing_time': 5.2
            }
            
            result_id = db.save_question_result(run_id, question_result)
            
            # Save entropy evolution
            evolution_data = [
                {
                    'response_num': 1,
                    'normalized_entropy': 0.0,
                    'confidence': 1.0,
                    'consensus_type': 'strong',
                    'entropy_level': 'concentrated'
                },
                {
                    'response_num': 2,
                    'normalized_entropy': 0.5,
                    'confidence': 0.75,
                    'consensus_type': 'emerging',
                    'entropy_level': 'scattered'
                }
            ]
            
            db.save_entropy_evolution(result_id, evolution_data)
            
            # Verify data was saved
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entropy_evolution WHERE result_id = ?", (result_id,))
                count = cursor.fetchone()[0]
                assert count == 2
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestTrackingReflectionAgent:
    """Test TrackingReflectionAgent entropy evolution tracking."""
    
    def test_tracking_agent_inherits_from_base(self):
        """Test that TrackingReflectionAgent properly inherits from SelfReflectionAgent."""
        # This is a simple test to verify class inheritance
        assert issubclass(TrackingReflectionAgent, SelfReflectionAgent)
    
    def test_tracking_methods_exist(self):
        """Test that tracking methods exist on the agent."""
        mock_interface = Mock()
        mock_interface.model = "test-model"
        
        config = ReflectionConfig(
            llm_interface=mock_interface,
            target_responses=5,
            confidence_threshold=0.8,
            min_responses=2,
            entropy_mode='combined'
        )
        
        agent = TrackingReflectionAgent(config, "Test question")
        
        # Verify tracking methods exist
        assert hasattr(agent, 'get_entropy_evolution')
        assert hasattr(agent, 'get_individual_responses')
        assert callable(agent.get_entropy_evolution)
        assert callable(agent.get_individual_responses)


class TestGSM8KReflectionBenchmark:
    """Test GSM8K reflection benchmark."""
    
    @pytest.fixture
    def mock_llm_interface(self):
        """Mock LLM interface for testing."""
        mock_interface = Mock()
        mock_interface.model = "test-model"
        return mock_interface
    
    def test_benchmark_initialization(self, mock_llm_interface):
        """Test benchmark initialization."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            benchmark = GSM8KReflectionBenchmark(mock_llm_interface, db_path)
            
            assert benchmark.llm_interface == mock_llm_interface
            assert benchmark.database is not None
            assert len(benchmark.questions) == 5  # Should have 5 test questions
            
            # Verify database was created
            assert Path(db_path).exists()
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_config_to_dict(self, mock_llm_interface):
        """Test ReflectionConfig to dictionary conversion."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            benchmark = GSM8KReflectionBenchmark(mock_llm_interface, db_path)
            
            config = ReflectionConfig(
                llm_interface=mock_llm_interface,
                target_responses=10,
                confidence_threshold=0.8,
                entropy_mode='combined'
            )
            
            config_dict = benchmark._config_to_dict(config)
            
            assert config_dict['target_responses'] == 10
            assert config_dict['confidence_threshold'] == 0.8
            assert config_dict['entropy_mode'] == 'combined'
            assert 'llm_interface' not in config_dict  # Should not include the interface
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_evaluate_answer(self, mock_llm_interface):
        """Test answer evaluation logic."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            benchmark = GSM8KReflectionBenchmark(mock_llm_interface, db_path)
            
            # Test exact matches
            assert benchmark._evaluate_answer("4", "4") == True
            assert benchmark._evaluate_answer("10", "10") == True
            
            # Test number extraction
            assert benchmark._evaluate_answer("Answer: 4", "4") == True
            assert benchmark._evaluate_answer("The answer is 10.", "10") == True
            
            # Test incorrect answers
            assert benchmark._evaluate_answer("5", "4") == False
            assert benchmark._evaluate_answer("Answer: 5", "4") == False
            
            # Test decimal precision
            assert benchmark._evaluate_answer("4.00", "4") == True
            assert benchmark._evaluate_answer("4.01", "4") == True  # 0.01 difference is within 0.01 tolerance
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_extract_number(self, mock_llm_interface):
        """Test number extraction from text."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            benchmark = GSM8KReflectionBenchmark(mock_llm_interface, db_path)
            
            # Test basic number extraction
            assert benchmark._extract_number("4") == "4"
            assert benchmark._extract_number("Answer: 4") == "4"
            assert benchmark._extract_number("The answer is 42.") == "42."  # Matches actual regex behavior
            assert benchmark._extract_number("I think it's 123.45") == "123.45"
            
            # Test with negative numbers
            assert benchmark._extract_number("The result is -5") == "-5"
            
            # Test with no numbers
            assert benchmark._extract_number("No numbers here") is None
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @patch('llm_agents.benchmark.gsm8k_reflection.TrackingReflectionAgent')
    def test_question_evaluation_with_tracking(self, mock_tracking_agent, mock_llm_interface):
        """Test complete question evaluation with entropy tracking."""
        # Mock the tracking agent and its methods
        mock_agent_instance = Mock()
        mock_tracking_agent.return_value = mock_agent_instance
        
        # Mock reflection result
        mock_reflection_result = ReflectionResult(
            final_answer="9",  # Correct answer for first question
            consensus_confidence=0.9,
            answer_distribution={"9": 1.0},
            uncertainty_level="low",
            early_stopping=True,
            total_responses=3,
            convergence_analysis={
                'convergence_rate': 0.1,
                'final_stability': 0.9,
                'entropy_convergence_rate': -0.2,
                'entropy_final_stability': 0.8
            },
            distribution_entropy=0.0,
            normalized_entropy=0.0,
            entropy_level="concentrated",
            consensus_type="strong"
        )
        
        mock_agent_instance.process_question.return_value = mock_reflection_result
        mock_agent_instance.get_entropy_evolution.return_value = [
            {
                'response_num': 1,
                'normalized_entropy': 0.0,
                'confidence': 1.0,
                'consensus_type': 'strong',
                'entropy_level': 'concentrated'
            }
        ]
        mock_agent_instance.get_individual_responses.return_value = ["9", "9", "9"]
        
        # Create benchmark
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            benchmark = GSM8KReflectionBenchmark(mock_llm_interface, db_path)
            
            # Get a test question
            question = benchmark.questions[0]
            
            # Create config
            config = ReflectionConfig(
                llm_interface=mock_llm_interface,
                target_responses=5,
                confidence_threshold=0.8
            )
            
            # Evaluate question
            result = benchmark._evaluate_question_with_tracking(question, config)
            
            # Verify result structure
            assert result.question_id == question.id
            assert result.question == question.question
            assert result.expected_answer == question.expected_answer
            assert result.reflection_result == mock_reflection_result
            assert result.is_correct == True  # "9" should match expected answer
            assert isinstance(result.processing_time, float)
            assert len(result.entropy_evolution) == 1
            assert result.individual_responses == ["9", "9", "9"]
            
            # Verify agent was called correctly
            mock_tracking_agent.assert_called_once_with(config, question.question)
            mock_agent_instance.process_question.assert_called_once()
        
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestIntegration:
    """Integration tests for the complete reflection benchmark system."""
    
    def test_benchmark_database_integration(self):
        """Test that benchmark and database work together."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            mock_interface = Mock()
            mock_interface.model = "test-model"
            
            # Create benchmark
            benchmark = GSM8KReflectionBenchmark(mock_interface, db_path)
            
            # Verify database was created
            assert benchmark.database is not None
            assert Path(db_path).exists()
            
            # Test basic functionality
            assert len(benchmark.questions) == 5
            assert benchmark.llm_interface == mock_interface
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)