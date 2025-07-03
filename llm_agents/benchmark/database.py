"""Database operations for reflection benchmark."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict


class BenchmarkDatabase:
    """SQLite database for storing reflection benchmark results."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = "gsm8k_reflection_results.db"
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                -- Benchmark runs metadata
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    total_questions INTEGER,
                    completed_at TEXT
                );

                -- Question-level results
                CREATE TABLE IF NOT EXISTS question_results (
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
                CREATE TABLE IF NOT EXISTS response_evolution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER NOT NULL,
                    response_num INTEGER NOT NULL,
                    response_text TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    FOREIGN KEY (result_id) REFERENCES question_results (id)
                );

                -- Entropy and confidence evolution
                CREATE TABLE IF NOT EXISTS entropy_evolution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER NOT NULL,
                    response_num INTEGER NOT NULL,
                    normalized_entropy REAL NOT NULL,
                    confidence REAL NOT NULL,
                    consensus_type TEXT,
                    entropy_level TEXT,
                    FOREIGN KEY (result_id) REFERENCES question_results (id)
                );

                -- Convergence analysis metrics
                CREATE TABLE IF NOT EXISTS convergence_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER NOT NULL,
                    convergence_rate REAL NOT NULL,
                    final_stability REAL NOT NULL,
                    entropy_convergence_rate REAL NOT NULL,
                    entropy_final_stability REAL NOT NULL,
                    FOREIGN KEY (result_id) REFERENCES question_results (id)
                );
            ''')
    
    def create_benchmark_run(self, agent_type: str, model_name: str, 
                           config: Dict[str, Any], total_questions: int) -> int:
        """Create new benchmark run, return run_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO benchmark_runs (timestamp, agent_type, model_name, config_json, total_questions)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                agent_type,
                model_name,
                json.dumps(config, indent=2),
                total_questions
            ))
            return cursor.lastrowid
    
    def save_question_result(self, run_id: int, question_result: Dict[str, Any]) -> int:
        """Save question result, return result_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO question_results (
                    run_id, question_id, question_text, expected_answer, final_answer,
                    is_correct, early_stopping, total_responses, consensus_confidence,
                    uncertainty_level, processing_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_id,
                question_result['question_id'],
                question_result['question_text'],
                question_result['expected_answer'],
                question_result['final_answer'],
                question_result['is_correct'],
                question_result['early_stopping'],
                question_result['total_responses'],
                question_result['consensus_confidence'],
                question_result['uncertainty_level'],
                question_result['processing_time']
            ))
            return cursor.lastrowid
    
    def save_response_evolution(self, result_id: int, individual_responses: List[str]):
        """Save individual response evolution data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for i, response in enumerate(individual_responses, 1):
                cursor.execute('''
                    INSERT INTO response_evolution (result_id, response_num, response_text, answer)
                    VALUES (?, ?, ?, ?)
                ''', (result_id, i, response, response))  # For now, response_text and answer are the same
    
    def save_entropy_evolution(self, result_id: int, evolution_data: List[Dict[str, Any]]):
        """Save entropy/confidence evolution data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for data in evolution_data:
                cursor.execute('''
                    INSERT INTO entropy_evolution (
                        result_id, response_num, normalized_entropy, confidence,
                        consensus_type, entropy_level
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    result_id,
                    data['response_num'],
                    data['normalized_entropy'],
                    data['confidence'],
                    data['consensus_type'],
                    data['entropy_level']
                ))
    
    def save_convergence_metrics(self, result_id: int, metrics: Dict[str, Any]):
        """Save convergence analysis metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO convergence_metrics (
                    result_id, convergence_rate, final_stability,
                    entropy_convergence_rate, entropy_final_stability
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                result_id,
                metrics['convergence_rate'],
                metrics['final_stability'],
                metrics['entropy_convergence_rate'],
                metrics['entropy_final_stability']
            ))
    
    def complete_benchmark_run(self, run_id: int):
        """Mark benchmark run as completed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE benchmark_runs 
                SET completed_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), run_id))
    
    def get_run_summary(self, run_id: int) -> Dict[str, Any]:
        """Get summary statistics for a run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Basic run info
            cursor.execute('''
                SELECT agent_type, model_name, total_questions, timestamp, completed_at
                FROM benchmark_runs WHERE id = ?
            ''', (run_id,))
            run_info = cursor.fetchone()
            
            if not run_info:
                return {}
            
            # Question results summary
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_questions,
                    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                    SUM(CASE WHEN early_stopping THEN 1 ELSE 0 END) as early_stops,
                    AVG(total_responses) as avg_responses,
                    AVG(consensus_confidence) as avg_confidence,
                    AVG(processing_time) as avg_processing_time
                FROM question_results WHERE run_id = ?
            ''', (run_id,))
            stats = cursor.fetchone()
            
            return {
                'run_id': run_id,
                'agent_type': run_info[0],
                'model_name': run_info[1],
                'total_questions': run_info[2],
                'timestamp': run_info[3],
                'completed_at': run_info[4],
                'accuracy': stats[1] / stats[0] if stats[0] > 0 else 0,
                'early_stopping_rate': stats[2] / stats[0] if stats[0] > 0 else 0,
                'avg_responses': stats[3] or 0,
                'avg_confidence': stats[4] or 0,
                'avg_processing_time': stats[5] or 0
            }
    
    def get_entropy_analysis(self, run_id: int) -> Dict[str, Any]:
        """Get entropy analysis for a run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get entropy evolution data
            cursor.execute('''
                SELECT 
                    response_num,
                    AVG(normalized_entropy) as avg_entropy,
                    AVG(confidence) as avg_confidence,
                    consensus_type,
                    entropy_level
                FROM entropy_evolution ee
                JOIN question_results qr ON ee.result_id = qr.id
                WHERE qr.run_id = ?
                GROUP BY response_num
                ORDER BY response_num
            ''', (run_id,))
            
            evolution_data = cursor.fetchall()
            
            return {
                'entropy_evolution': [
                    {
                        'response_num': row[0],
                        'avg_entropy': row[1],
                        'avg_confidence': row[2],
                        'consensus_type': row[3],
                        'entropy_level': row[4]
                    }
                    for row in evolution_data
                ]
            }