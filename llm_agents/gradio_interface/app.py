"""Main Gradio application for LLM agent comparison interface.

This module creates the web-based interface for comparing self-consistency
and self-reflection agents with interactive controls and visualizations.
"""

import gradio as gr
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional, Tuple, List
import json
import traceback
import sqlite3
from pathlib import Path

from .agent_wrapper import AgentWrapper, AgentType, UnifiedResult
from .config_manager import ConfigManager, UIConfig
from .visualization import (
    create_probability_distribution_chart,
    create_confidence_evolution_chart,
    create_comparison_chart,
    create_uncertainty_analysis_chart,
    create_cost_analysis_chart,
    create_entropy_evolution_benchmark_chart,
    create_early_stopping_analysis_chart
)
from .examples import Examples
from ..benchmark.database import BenchmarkDatabase


class UIConstants:
    """Configuration constants for the UI."""
    MAX_QUESTION_LENGTH = 2000
    MAX_TARGET_RESPONSES = 20
    MIN_TARGET_RESPONSES = 1
    
    # Confidence threshold bounds
    MIN_CONFIDENCE_THRESHOLD = 0.5
    MAX_CONFIDENCE_THRESHOLD = 0.95


class GradioInterface:
    """Main Gradio interface for agent comparison."""
    
    def __init__(self):
        """Initialize the interface with components."""
        self.config_manager = ConfigManager()
        self.agent_wrapper = None
        self.examples = Examples()
        self.benchmark_db = None
        self._initialize_agent_wrapper()
    
    def _initialize_agent_wrapper(self):
        """Initialize agent wrapper with default configuration."""
        try:
            llm_adapter = self.config_manager.create_llm_adapter()
            self.agent_wrapper = AgentWrapper(llm_adapter)
        except Exception as e:
            print(f"Warning: Could not initialize LLM adapter: {e}")
            self.agent_wrapper = None
    
    def process_single_agent(
        self,
        question: str,
        agent_type: str,
        target_responses: int,
        confidence_threshold: float,
        min_responses: int,
        prompt_template: str,
        model_name: str,
        temperature: float,
        # Entropy parameters
        entropy_mode: str,
        entropy_threshold: float,
        entropy_weight: float,
        min_entropy_samples: int
    ) -> Tuple[str, str, str, Optional[plt.Figure], Optional[plt.Figure], str]:
        """Process question with single agent and return results.
        
        Returns:
            Tuple of (result_text, prob_table, debug_info, distribution_chart, evolution_chart, status_message)
        """
        try:
            # Validate inputs
            valid, message = self._validate_inputs(question, target_responses, confidence_threshold)
            if not valid:
                return message, "", "", None, None, message
            
            # Create adapter and test connection
            agent_wrapper, status = self._create_and_test_adapter(model_name, temperature)
            if not agent_wrapper:
                return "Connection failed", "", "", None, None, status
            
            # Process question
            if agent_type == "Self-Consistency":
                agent_type_enum = AgentType.SELF_CONSISTENCY
            elif agent_type == "Enhanced Self-Consistency":
                agent_type_enum = AgentType.ENHANCED_SELF_CONSISTENCY
            else:
                agent_type_enum = AgentType.SELF_REFLECTION
            
            result = agent_wrapper.process_question(
                question=question,
                agent_type=agent_type_enum,
                target_responses=target_responses,
                confidence_threshold=confidence_threshold,
                min_responses=min_responses,
                prompt_template=prompt_template,
                entropy_mode=entropy_mode,
                entropy_threshold=entropy_threshold,
                entropy_weight=entropy_weight,
                min_entropy_samples=min_entropy_samples
            )
            
            # Format result text
            result_text = self._format_single_result(result)
            
            # Create probability distribution table
            prob_table = self._create_probability_table(result)
            
            # Create debug information display
            debug_info = self._create_debug_display(result)
            
            # Create visualizations
            dist_chart = create_probability_distribution_chart(result)
            evolution_chart = create_confidence_evolution_chart(result)
            
            status_msg = f"✅ Processed with {result.total_responses} responses in {result.processing_time:.2f}s"
            
            return result_text, prob_table, debug_info, dist_chart, evolution_chart, status_msg
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            print(f"Error details: {traceback.format_exc()}")
            return error_msg, "", "", None, None, f"❌ {error_msg}"
    
    def compare_agents(
        self,
        question: str,
        target_responses: int,
        confidence_threshold: float,
        min_responses: int,
        prompt_template: str,
        model_name: str,
        temperature: float,
        # Entropy parameters for self-reflection
        entropy_mode: str,
        entropy_threshold: float,
        entropy_weight: float,
        min_entropy_samples: int
    ) -> Tuple[str, str, Optional[plt.Figure], Optional[plt.Figure], str]:
        """Compare both agents on the same question.
        
        Returns:
            Tuple of (comparison_text, comparison_table, comparison_chart, cost_chart, status_message)
        """
        try:
            # Validate inputs
            valid, message = self._validate_inputs(question, target_responses, confidence_threshold)
            if not valid:
                return message, "", None, None, message
            
            # Create adapter and test connection
            agent_wrapper, status = self._create_and_test_adapter(model_name, temperature)
            if not agent_wrapper:
                return "Connection failed", "", None, None, status
            
            # Compare agents
            results = agent_wrapper.compare_agents(
                question=question,
                target_responses=target_responses,
                confidence_threshold=confidence_threshold,
                min_responses=min_responses,
                prompt_template=prompt_template,
                entropy_mode=entropy_mode,
                entropy_threshold=entropy_threshold,
                entropy_weight=entropy_weight,
                min_entropy_samples=min_entropy_samples
            )
            
            # Format comparison text
            comparison_text = self._format_comparison_results(results)
            
            # Create comparison table
            comparison_table = self._create_comparison_table(results)
            
            # Create comparison chart
            comparison_chart = create_comparison_chart(results)
            
            # Create cost analysis
            ui_config = self.config_manager.create_ui_config_from_inputs(
                target_responses, confidence_threshold, min_responses,
                prompt_template, model_name, temperature
            )
            
            cost_estimates = {
                "self_consistency": self.config_manager.get_cost_estimate(ui_config, "self_consistency"),
                "self_reflection": self.config_manager.get_cost_estimate(ui_config, "self_reflection")
            }
            
            cost_chart = create_cost_analysis_chart(cost_estimates, ["self_consistency", "self_reflection"])
            
            total_time = sum(r.processing_time for r in results.values())
            status_msg = f"✅ Compared both agents in {total_time:.2f}s total"
            
            return comparison_text, comparison_table, comparison_chart, cost_chart, status_msg
            
        except Exception as e:
            error_msg = f"Error comparing agents: {str(e)}"
            print(f"Error details: {traceback.format_exc()}")
            return error_msg, "", None, None, f"❌ {error_msg}"
    
    def _format_single_result(self, result: UnifiedResult) -> str:
        """Format single agent result for display."""
        lines = [
            f"## {result.agent_type} Result",
            f"",
            f"**Final Answer:** {result.final_answer}",
            f"**Confidence:** {result.confidence:.3f} ({result.uncertainty_level} uncertainty)",
            f"**Responses Used:** {result.total_responses}",
            f"**Early Stopping:** {'Yes' if result.early_stopping else 'No'}",
            f"**Processing Time:** {result.processing_time:.2f} seconds",
            f"",
            f"### Answer Distribution",
        ]
        
        for answer, prob in result.answer_distribution.items():
            lines.append(f"- **{answer}:** {prob:.3f} ({prob*100:.1f}%)")
        
        # Add token confidence information for enhanced self-consistency
        if result.token_confidence_reasoning is not None or result.token_confidence_answer is not None:
            lines.extend([
                f"",
                f"### Token Confidence Analysis (Normalized 0-1 Scale)",
                f"- **Reasoning Confidence:** {result.token_confidence_reasoning:.3f} ({result.token_confidence_reasoning*100:.1f}%)" if result.token_confidence_reasoning is not None else "",
                f"- **Answer Confidence:** {result.token_confidence_answer:.3f} ({result.token_confidence_answer*100:.1f}%)" if result.token_confidence_answer is not None else "",
            ])
            
            # Add individual response token confidence
            if result.individual_response_confidence:
                lines.extend([
                    f"",
                    f"### Individual Response Token Confidence"
                ])
                for i, resp_data in enumerate(result.individual_response_confidence):
                    status = "✅ CONSENSUS" if resp_data.get("matches_consensus", False) else "❌ OUTLIER"
                    lines.append(f"- **Response {i+1}:** '{resp_data['answer']}' {status}")
                    lines.append(f"  - Reasoning: {resp_data['reasoning_confidence']:.3f} ({resp_data['reasoning_confidence']*100:.1f}%)")
                    lines.append(f"  - Answer: {resp_data['answer_confidence']:.3f} ({resp_data['answer_confidence']*100:.1f}%)")
        
        # Add entropy information for self-reflection
        if result.distribution_entropy is not None:
            lines.extend([
                f"",
                f"### Entropy Analysis",
                f"- **Raw Entropy:** {result.distribution_entropy:.3f}",
                f"- **Normalized Entropy:** {result.normalized_entropy:.3f} ({result.entropy_level})",
                f"- **Consensus Type:** {result.consensus_type}"
            ])
        
        if result.convergence_analysis:
            lines.extend([
                f"",
                f"### Convergence Analysis",
                f"- **Convergence Rate:** {result.convergence_analysis.get('convergence_rate', 0):.3f}",
                f"- **Final Stability:** {result.convergence_analysis.get('final_stability', 0):.3f}"
            ])
        
        return "\n".join(lines)
    
    def _format_comparison_results(self, results: Dict[str, UnifiedResult]) -> str:
        """Format comparison results for display."""
        sc_result = results["self_consistency"]
        sr_result = results["self_reflection"]
        
        lines = [
            f"# Agent Comparison Results",
            f"",
            f"## Answers",
            f"- **Self-Consistency:** {sc_result.final_answer}",
            f"- **Self-Reflection:** {sr_result.final_answer}",
            f"",
            f"## Performance Metrics",
            f"",
            f"| Metric | Self-Consistency | Self-Reflection |",
            f"|--------|------------------|-----------------|",
            f"| **Confidence** | {sc_result.confidence:.3f} | {sr_result.confidence:.3f} |",
            f"| **Responses Used** | {sc_result.total_responses} | {sr_result.total_responses} |",
            f"| **Processing Time** | {sc_result.processing_time:.2f}s | {sr_result.processing_time:.2f}s |",
            f"| **Early Stopping** | {'Yes' if sc_result.early_stopping else 'No'} | {'Yes' if sr_result.early_stopping else 'No'} |",
            f"| **Uncertainty Level** | {sc_result.uncertainty_level} | {sr_result.uncertainty_level} |",
        ]
        
        # Add entropy metrics for self-reflection
        if sr_result.distribution_entropy is not None:
            lines.extend([
                f"| **Entropy (Raw)** | N/A | {sr_result.distribution_entropy:.3f} |",
                f"| **Entropy (Normalized)** | N/A | {sr_result.normalized_entropy:.3f} |",
                f"| **Entropy Level** | N/A | {sr_result.entropy_level} |",
                f"| **Consensus Type** | N/A | {sr_result.consensus_type} |",
            ])
        
        lines.extend([
            f"",
            f"## Efficiency Analysis",
        ])
        
        if sr_result.total_responses < sc_result.total_responses:
            savings = (sc_result.total_responses - sr_result.total_responses) / sc_result.total_responses * 100
            lines.append(f"🎯 **Self-reflection saved {savings:.1f}% of responses** through early stopping")
        else:
            lines.append(f"📊 Both agents used similar number of responses")
        
        if sr_result.processing_time < sc_result.processing_time:
            time_savings = (sc_result.processing_time - sr_result.processing_time) / sc_result.processing_time * 100
            lines.append(f"⚡ **Self-reflection was {time_savings:.1f}% faster**")
        
        return "\n".join(lines)
    
    def _create_probability_table(self, result: UnifiedResult) -> str:
        """Create HTML table showing probability distribution."""
        # Sort answers by probability (highest first)
        sorted_items = sorted(result.answer_distribution.items(), key=lambda x: x[1], reverse=True)
        
        table_rows = []
        for i, (answer, prob) in enumerate(sorted_items):
            # Highlight the final answer
            row_class = 'style="background-color: #ffe6e6; font-weight: bold;"' if answer == result.final_answer else ''
            table_rows.append(f'''
                <tr {row_class}>
                    <td>{i+1}</td>
                    <td>{answer}</td>
                    <td>{prob:.4f}</td>
                    <td>{prob*100:.2f}%</td>
                    <td>{'✓ Final Answer' if answer == result.final_answer else ''}</td>
                </tr>
            ''')
        
        table_html = f'''
        <div style="margin: 10px 0;">
            <h4>📊 Answer Probability Distribution</h4>
            <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                <thead style="background-color: #f0f0f0;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Rank</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Answer</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Probability</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Percentage</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Selected</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
            <p style="font-size: 0.9em; color: #666;">
                <strong>Agent:</strong> {result.agent_type} | 
                <strong>Responses Used:</strong> {result.total_responses} | 
                <strong>Confidence:</strong> {result.confidence:.3f} | 
                <strong>Uncertainty:</strong> {result.uncertainty_level}
                {f'<br><strong>Entropy:</strong> {result.normalized_entropy:.3f} ({result.entropy_level}) | <strong>Consensus:</strong> {result.consensus_type}' if result.distribution_entropy is not None else ''}
                {f'<br><strong>Token Confidence:</strong> Reasoning {result.token_confidence_reasoning:.3f} ({result.token_confidence_reasoning*100:.1f}%) | Answer {result.token_confidence_answer:.3f} ({result.token_confidence_answer*100:.1f}%)' if result.token_confidence_reasoning is not None else ''}
            </p>
        </div>
        '''
        return table_html
    
    def _create_comparison_table(self, results: Dict[str, UnifiedResult]) -> str:
        """Create HTML table comparing both agents' probability distributions."""
        sc_result = results["self_consistency"]
        sr_result = results["self_reflection"]
        
        # Get all unique answers from both agents
        all_answers = set(sc_result.answer_distribution.keys()) | set(sr_result.answer_distribution.keys())
        
        table_rows = []
        for answer in sorted(all_answers):
            sc_prob = sc_result.answer_distribution.get(answer, 0.0)
            sr_prob = sr_result.answer_distribution.get(answer, 0.0)
            
            # Highlight final answers
            sc_highlight = 'style="background-color: #e6f3ff; font-weight: bold;"' if answer == sc_result.final_answer else ''
            sr_highlight = 'style="background-color: #e6ffe6; font-weight: bold;"' if answer == sr_result.final_answer else ''
            
            table_rows.append(f'''
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{answer}</td>
                    <td {sc_highlight} style="border: 1px solid #ddd; padding: 8px; text-align: center;">{sc_prob:.4f} ({sc_prob*100:.1f}%)</td>
                    <td {sr_highlight} style="border: 1px solid #ddd; padding: 8px; text-align: center;">{sr_prob:.4f} ({sr_prob*100:.1f}%)</td>
                </tr>
            ''')
        
        table_html = f'''
        <div style="margin: 10px 0;">
            <h4>📊 Agent Comparison - Probability Distributions</h4>
            <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                <thead style="background-color: #f0f0f0;">
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Answer</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center; background-color: #e6f3ff;">Self-Consistency</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center; background-color: #e6ffe6;">Self-Reflection</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
            <div style="font-size: 0.9em; color: #666; margin-top: 10px;">
                <div style="display: inline-block; margin-right: 20px;">
                    <span style="background-color: #e6f3ff; padding: 2px 5px; border-radius: 3px;">Self-Consistency Final Answer</span>: {sc_result.final_answer}
                </div>
                <div style="display: inline-block;">
                    <span style="background-color: #e6ffe6; padding: 2px 5px; border-radius: 3px;">Self-Reflection Final Answer</span>: {sr_result.final_answer}
                </div>
            </div>
        </div>
        '''
        return table_html
    
    def _create_debug_display(self, result: UnifiedResult) -> str:
        """Create HTML display for debug information."""
        if not result.debug_info:
            return "<p>No debug information available.</p>"
        
        debug_info = result.debug_info
        
        debug_html = f"""
        <div style="margin: 10px 0;">
            <h4>🔍 Debug Information</h4>
            <p><strong>Total Requests:</strong> {len(debug_info.requests)}</p>
            
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background-color: #f9f9f9;">
        """
        
        for i, (req, resp, answer) in enumerate(zip(debug_info.requests, debug_info.responses, debug_info.parsed_answers)):
            debug_html += f"""
                <div style="margin-bottom: 20px; padding: 10px; border: 1px solid #ccc; background-color: white;">
                    <h5>Request {i+1} ({req['timestamp']})</h5>
                    <p><strong>Model:</strong> {req['model']} | <strong>Temperature:</strong> {req['temperature']}</p>
                    <p><strong>Prompt Template:</strong> <code>{req['prompt']}</code></p>
                    <p><strong>Question:</strong> {req['question']}</p>
                    <p><strong>Full Prompt:</strong></p>
                    <pre style="background-color: #f0f0f0; padding: 5px; white-space: pre-wrap; font-size: 0.9em;">{req['full_prompt']}</pre>
                    
                    <h6>Raw Response ({resp['timestamp']}):</h6>
                    <pre style="background-color: #e8f5e8; padding: 5px; white-space: pre-wrap; font-size: 0.9em; max-height: 150px; overflow-y: auto;">{resp['raw_content']}</pre>
                    
                    <p><strong>Parsed Answer:</strong> <span style="background-color: #ffe6e6; padding: 2px 5px; font-weight: bold;">{answer}</span></p>
                    
                    {f'<p><strong>Finish Reason:</strong> {resp["finish_reason"]}</p>' if resp.get("finish_reason") else ''}
                    {f'<p><strong>Token Usage:</strong> {resp["usage"]}</p>' if resp.get("usage") else ''}
                </div>
            """
        
        debug_html += """
            </div>
        </div>
        """
        
        return debug_html
    
    def load_example(self, example_name: str) -> Tuple[str, int, float, int, str]:
        """Load example configuration and return parameters."""
        configs = {config.name: config for config in self.examples.get_demonstration_configs()}
        
        if example_name in configs:
            config = configs[example_name]
            return (
                config.question,
                config.target_responses,
                config.confidence_threshold,
                config.min_responses,
                config.prompt_template
            )
        
        return "", 5, 0.8, 3, "Think step by step:"
    
    def get_random_question(self) -> str:
        """Get a random example question."""
        return self.examples.get_random_question()
    
    def _validate_inputs(self, question: str, target_responses: int, 
                        confidence_threshold: float) -> Tuple[bool, str]:
        """Validate user inputs and return status."""
        if not question.strip():
            return False, "❌ No question provided"
        
        if len(question.strip()) > UIConstants.MAX_QUESTION_LENGTH:
            return False, f"❌ Question too long (max {UIConstants.MAX_QUESTION_LENGTH} characters)"
        
        if target_responses < UIConstants.MIN_TARGET_RESPONSES or target_responses > UIConstants.MAX_TARGET_RESPONSES:
            return False, f"❌ Target responses must be {UIConstants.MIN_TARGET_RESPONSES}-{UIConstants.MAX_TARGET_RESPONSES}"
        
        if not UIConstants.MIN_CONFIDENCE_THRESHOLD <= confidence_threshold <= UIConstants.MAX_CONFIDENCE_THRESHOLD:
            return False, f"❌ Confidence threshold must be {UIConstants.MIN_CONFIDENCE_THRESHOLD}-{UIConstants.MAX_CONFIDENCE_THRESHOLD}"
        
        return True, "✅ Valid inputs"
    
    def _create_and_test_adapter(self, model_name: str, temperature: float) -> Tuple[Optional[AgentWrapper], str]:
        """Create LLM adapter and test connection."""
        try:
            # Create LLM adapter with current settings
            llm_adapter = self.config_manager.create_llm_adapter(
                model_name=model_name,
                temperature=temperature
            )
            agent_wrapper = AgentWrapper(llm_adapter)
            
            # Test connection
            if not agent_wrapper.validate_llm_connection():
                return None, "❌ Cannot connect to LLM. Check that LiteLLM is running."
            
            return agent_wrapper, "✅ Connection successful"
            
        except Exception as e:
            return None, f"❌ Error creating adapter: {e}"
    
    def refresh_benchmark_database(self, db_path: str) -> Tuple[gr.Dropdown, str]:
        """Refresh database connection and return updated dropdown."""
        try:
            if not db_path.strip():
                return gr.Dropdown(choices=[], value=None), "❌ Database path cannot be empty"
            
            db_path_obj = Path(db_path)
            if not db_path_obj.exists():
                return gr.Dropdown(choices=[], value=None), f"❌ Database file not found: {db_path}"
            
            self.benchmark_db = BenchmarkDatabase(db_path)
            runs = self._get_available_runs()
            return gr.Dropdown(choices=runs, value=None), f"✅ Found {len(runs)} benchmark runs"
        except Exception as e:
            return gr.Dropdown(choices=[], value=None), f"❌ Error loading database: {e}"
    
    def _get_available_runs(self) -> List[str]:
        """Get list of available benchmark runs."""
        if not self.benchmark_db:
            return []
        
        with sqlite3.connect(self.benchmark_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, agent_type, model_name, timestamp, total_questions
                FROM benchmark_runs
                ORDER BY timestamp DESC
            ''')
            runs = cursor.fetchall()
            
            return [
                f"Run {run[0]}: {run[1]} ({run[2]}) - {run[4]} questions - {run[3][:16]}"
                for run in runs
            ]
    
    def analyze_benchmark_run(self, run_display: str, show_entropy: bool, 
                            show_early_stopping: bool, show_breakdown: bool) -> Tuple[str, Optional[plt.Figure], Optional[plt.Figure], str, bool, bool]:
        """Analyze selected benchmark run."""
        if not run_display or not self.benchmark_db:
            return "No run selected", None, None, "", False, False
        
        try:
            # Extract run ID from display string
            run_id = int(run_display.split(":")[0].replace("Run ", ""))
            
            # Get run summary
            summary = self.benchmark_db.get_run_summary(run_id)
            summary_text = self._format_benchmark_summary(summary)
            
            # Create charts
            entropy_fig = create_entropy_evolution_benchmark_chart(
                str(self.benchmark_db.db_path), run_id) if show_entropy else None
            early_stopping_fig = create_early_stopping_analysis_chart(
                str(self.benchmark_db.db_path), run_id) if show_early_stopping else None
            
            # Get question breakdown
            breakdown_html = self._create_question_breakdown_table(run_id) if show_breakdown else ""
            
            # Show expand buttons only when charts are available
            show_entropy_btn = show_entropy and entropy_fig is not None
            show_early_stopping_btn = show_early_stopping and early_stopping_fig is not None
            
            return summary_text, entropy_fig, early_stopping_fig, breakdown_html, show_entropy_btn, show_early_stopping_btn
            
        except Exception as e:
            return f"Error analyzing run: {e}", None, None, "", False, False
    
    def _format_benchmark_summary(self, summary: Dict[str, Any]) -> str:
        """Format benchmark summary for display."""
        if not summary:
            return "No benchmark data available."
        
        return f"""
# 🎯 Benchmark Run Summary

## Run Information
- **Run ID**: {summary['run_id']}
- **Agent Type**: {summary['agent_type']}
- **Model**: {summary['model_name']}
- **Started**: {summary['timestamp'][:19].replace('T', ' ')}
- **Completed**: {summary['completed_at'][:19].replace('T', ' ') if summary['completed_at'] else 'In Progress'}

## Performance Metrics
- **Accuracy**: {summary['accuracy']:.1%} ({summary['accuracy'] * summary['total_questions']:.0f}/{summary['total_questions']} correct)
- **Early Stopping Rate**: {summary['early_stopping_rate']:.1%}
- **Average Responses**: {summary['avg_responses']:.1f}
- **Average Confidence**: {summary['avg_confidence']:.3f}
- **Average Processing Time**: {summary['avg_processing_time']:.2f} seconds

## Efficiency Analysis
- **Potential Responses**: {summary['total_questions'] * 10} (10 per question)
- **Actual Responses**: {summary['avg_responses'] * summary['total_questions']:.0f}
- **Response Savings**: {(1 - (summary['avg_responses'] / 10)) * 100:.1f}%
"""
    
    def _create_question_breakdown_table(self, run_id: int) -> str:
        """Create HTML table with question-by-question results."""
        if not self.benchmark_db:
            return "<p>No database connection available.</p>"
        
        with sqlite3.connect(self.benchmark_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT question_id, question_text, expected_answer, final_answer,
                       is_correct, early_stopping, total_responses, consensus_confidence,
                       uncertainty_level, processing_time
                FROM question_results
                WHERE run_id = ?
                ORDER BY question_id
            ''', (run_id,))
            
            results = cursor.fetchall()
        
        if not results:
            return "<p>No question results found.</p>"
        
        table_rows = []
        for result in results:
            correct_icon = "✅" if result[4] else "❌"
            early_stop_icon = "⚡" if result[5] else "🔄"
            
            table_rows.append(f'''
                <tr style="{'background-color: #e6ffe6;' if result[4] else 'background-color: #ffe6e6;'}">
                    <td style="padding: 8px; border: 1px solid #ddd;">{result[0]}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; max-width: 300px; word-wrap: break-word;">{result[1][:100]}{'...' if len(result[1]) > 100 else ''}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{result[2]}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{result[3]}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{correct_icon}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{early_stop_icon}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{result[6]}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{result[7]:.3f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{result[8]}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{result[9]:.2f}s</td>
                </tr>
            ''')
        
        return f'''
        <div style="margin: 10px 0;">
            <h4>📝 Question-by-Question Results</h4>
            <div style="max-height: 500px; overflow-y: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background-color: #f0f0f0; position: sticky; top: 0;">
                        <tr>
                            <th style="padding: 8px; border: 1px solid #ddd;">ID</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Question</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Expected</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Actual</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Correct</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Early Stop</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Responses</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Confidence</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Uncertainty</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
            </div>
        </div>
        '''
    
    def show_entropy_modal(self, run_display: str) -> Tuple[gr.Row, Optional[plt.Figure]]:
        """Show entropy evolution chart in modal dialog."""
        if not run_display or not self.benchmark_db:
            return gr.Row(visible=False), None
        
        try:
            run_id = int(run_display.split(":")[0].replace("Run ", ""))
            # Create larger chart (bigger figure size)
            large_fig = self._create_large_entropy_chart(run_id)
            return gr.Row(visible=True), large_fig
        except Exception as e:
            return gr.Row(visible=False), None
    
    def show_early_stopping_modal(self, run_display: str) -> Tuple[gr.Row, Optional[plt.Figure]]:
        """Show early stopping analysis chart in modal dialog."""
        if not run_display or not self.benchmark_db:
            return gr.Row(visible=False), None
        
        try:
            run_id = int(run_display.split(":")[0].replace("Run ", ""))
            # Create larger chart (bigger figure size)
            large_fig = self._create_large_early_stopping_chart(run_id)
            return gr.Row(visible=True), large_fig
        except Exception as e:
            return gr.Row(visible=False), None
    
    def hide_entropy_modal(self) -> gr.Row:
        """Hide entropy modal dialog."""
        return gr.Row(visible=False)
    
    def hide_early_stopping_modal(self) -> gr.Row:
        """Hide early stopping modal dialog."""
        return gr.Row(visible=False)
    
    def _create_large_entropy_chart(self, run_id: int) -> Optional[plt.Figure]:
        """Create larger version of entropy evolution chart."""
        # Create chart with larger figure size
        import matplotlib.pyplot as plt
        from .visualization import setup_plot_style
        
        setup_plot_style()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))  # Larger size
        
        with sqlite3.connect(self.benchmark_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    response_num,
                    AVG(normalized_entropy) as avg_entropy,
                    AVG(confidence) as avg_confidence
                FROM entropy_evolution ee
                JOIN question_results qr ON ee.result_id = qr.id
                WHERE qr.run_id = ?
                GROUP BY response_num
                ORDER BY response_num
            ''', (run_id,))
            
            evolution_data = cursor.fetchall()
        
        if not evolution_data:
            ax1.text(0.5, 0.5, 'No entropy data available', 
                    ha='center', va='center', transform=ax1.transAxes, fontsize=16)
            ax2.text(0.5, 0.5, 'No confidence data available',
                    ha='center', va='center', transform=ax2.transAxes, fontsize=16)
            return fig
        
        response_nums = [d[0] for d in evolution_data]
        avg_entropy = [d[1] for d in evolution_data]
        avg_confidence = [d[2] for d in evolution_data]
        
        # Plot entropy evolution with larger markers and lines
        ax1.plot(response_nums, avg_entropy, 'o-', color='red', label='Normalized Entropy', linewidth=3, markersize=8)
        ax1.set_title('Average Entropy Evolution Across All Questions', fontsize=16)
        ax1.set_xlabel('Response Number', fontsize=14)
        ax1.set_ylabel('Normalized Entropy', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=12)
        ax1.set_ylim(0, 1.0)
        
        # Plot confidence evolution with larger markers and lines
        ax2.plot(response_nums, avg_confidence, 'o-', color='blue', label='Confidence', linewidth=3, markersize=8)
        ax2.set_title('Average Confidence Evolution Across All Questions', fontsize=16)
        ax2.set_xlabel('Response Number', fontsize=14)
        ax2.set_ylabel('Confidence Score', fontsize=14)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=12)
        ax2.set_ylim(0, 1.0)
        
        plt.tight_layout()
        return fig
    
    def _create_large_early_stopping_chart(self, run_id: int) -> Optional[plt.Figure]:
        """Create larger version of early stopping analysis chart."""
        import matplotlib.pyplot as plt
        from .visualization import setup_plot_style
        
        setup_plot_style()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))  # Larger size
        
        with sqlite3.connect(self.benchmark_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Early stopping distribution
            cursor.execute('''
                SELECT total_responses, COUNT(*) as count, 
                       SUM(CASE WHEN early_stopping THEN 1 ELSE 0 END) as early_stops
                FROM question_results 
                WHERE run_id = ?
                GROUP BY total_responses
                ORDER BY total_responses
            ''', (run_id,))
            
            response_data = cursor.fetchall()
            
            if response_data:
                responses = [r[0] for r in response_data]
                counts = [r[1] for r in response_data]
                early_stops = [r[2] for r in response_data]
                
                # Stacked bar chart with larger bars
                ax1.bar(responses, early_stops, label='Early Stops', alpha=0.7, color='green', width=0.6)
                ax1.bar(responses, [c - e for c, e in zip(counts, early_stops)], 
                       bottom=early_stops, label='Full Runs', alpha=0.7, color='red', width=0.6)
                
                ax1.set_title('Response Distribution', fontsize=16)
                ax1.set_xlabel('Number of Responses Used', fontsize=14)
                ax1.set_ylabel('Number of Questions', fontsize=14)
                ax1.legend(fontsize=12)
                ax1.tick_params(labelsize=12)
            else:
                ax1.text(0.5, 0.5, 'No response data available', 
                        ha='center', va='center', transform=ax1.transAxes, fontsize=16)
            
            # Accuracy by early stopping
            cursor.execute('''
                SELECT early_stopping, 
                       COUNT(*) as total,
                       SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                FROM question_results 
                WHERE run_id = ?
                GROUP BY early_stopping
            ''', (run_id,))
            
            accuracy_data = cursor.fetchall()
            
            if accuracy_data:
                categories = []
                accuracies = []
                
                for early_stop, total, correct in accuracy_data:
                    accuracy = correct / total if total > 0 else 0
                    if early_stop:
                        categories.append('Early Stop')
                        accuracies.append(accuracy)
                    else:
                        categories.append('Full Run')
                        accuracies.append(accuracy)
                
                colors = ['green' if 'Early' in cat else 'red' for cat in categories]
                bars = ax2.bar(categories, accuracies, alpha=0.7, color=colors, width=0.6)
                ax2.set_title('Accuracy by Stopping Type', fontsize=16)
                ax2.set_ylabel('Accuracy', fontsize=14)
                ax2.set_ylim(0, 1.0)
                ax2.tick_params(labelsize=12)
                
                # Add value labels with larger font
                for bar, acc in zip(bars, accuracies):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                            f'{acc:.2f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
            else:
                ax2.text(0.5, 0.5, 'No accuracy data available',
                        ha='center', va='center', transform=ax2.transAxes, fontsize=16)
        
        plt.tight_layout()
        return fig
    
    def create_interface(self) -> gr.Interface:
        """Create and return the Gradio interface."""
        
        with gr.Blocks(title="LLM Agent Comparison", theme=gr.themes.Soft()) as interface:
            
            # Header
            gr.Markdown("""
            # 🤖 LLM Agent Comparison Interface
            
            Compare different agent types with interactive controls and visualizations.
            
            - **Self-Consistency**: Fixed sampling with majority vote
            - **Enhanced Self-Consistency**: Traditional consensus + token-level confidence data
            - **Self-Reflection**: Confidence-aware early stopping with probability distributions
            
            ⚠️ **Enhanced Self-Consistency** requires models supporting structured outputs + logprobs (OpenRouter GPT-4o models recommended)
            """)
            
            # Connection status
            status_display = gr.Textbox(
                label="Status",
                value="Ready to process questions",
                interactive=False,
                lines=3,
                max_lines=5,
                show_copy_button=True,
                container=True,
                scale=1
            )
            
            with gr.Tabs():
                
                # Single Agent Tab
                with gr.Tab("Single Agent"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            question_input = gr.Textbox(
                                label="Question",
                                placeholder="Enter your question here...",
                                lines=3
                            )
                            
                            agent_type = gr.Radio(
                                choices=["Self-Consistency", "Enhanced Self-Consistency", "Self-Reflection"],
                                value="Self-Reflection",
                                label="Agent Type"
                            )
                            
                            with gr.Accordion("⚙️ Agent Configuration", open=False):
                                gr.Markdown("""
                                **Parameter Explanations:**
                                - **Target Responses**: Maximum number of LLM responses to generate (both agents)
                                - **Confidence Threshold**: Early stopping threshold - Self-Reflection stops when confidence exceeds this value
                                - **Minimum Responses**: Self-Reflection won't stop before generating at least this many responses
                                
                                **⚠️ Note**: All prompts are designed to ensure LLM responses end with "Answer: <your_answer>" for consistent parsing.
                                """)
                                
                                target_responses = gr.Slider(
                                    minimum=1, maximum=20, value=5, step=1,
                                    label="🎯 Target Responses (Maximum)",
                                    info="Maximum number of LLM responses to generate"
                                )
                                confidence_threshold = gr.Slider(
                                    minimum=0.5, maximum=0.95, value=0.8, step=0.05,
                                    label="🎚️ Confidence Threshold (Self-Reflection only)",
                                    info="Stop early when confidence exceeds this value (0.8 = 80%)"
                                )
                                min_responses = gr.Slider(
                                    minimum=1, maximum=10, value=3, step=1,
                                    label="🔢 Minimum Responses (Self-Reflection only)",
                                    info="Don't stop before generating at least this many responses"
                                )
                                
                                # Entropy-based intelligence controls
                                gr.Markdown("### 🧠 Entropy Intelligence (Self-Reflection only)")
                                
                                entropy_mode = gr.Dropdown(
                                    choices=["off", "confidence_only", "entropy_only", "combined"],
                                    value="combined",
                                    label="🎛️ Entropy Mode",
                                    info="How to use entropy in early stopping decisions"
                                )
                                
                                entropy_threshold = gr.Slider(
                                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                                    label="🎚️ Entropy Threshold",
                                    info="Stop when normalized entropy drops below this value (lower = more concentrated)"
                                )
                                
                                entropy_weight = gr.Slider(
                                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                                    label="⚖️ Entropy Weight",
                                    info="Weight of entropy in combined scoring (0.0 = ignore entropy, 1.0 = entropy only)"
                                )
                                
                                min_entropy_samples = gr.Slider(
                                    minimum=2, maximum=10, value=4, step=1,
                                    label="📊 Min Entropy Samples",
                                    info="Minimum responses before entropy influences stopping decisions"
                                )
                                
                                prompt_template = gr.Dropdown(
                                    choices=list(self.examples.get_prompt_templates().keys()),
                                    value="Standard",
                                    label="Prompt Template"
                                )
                                
                                prompt_display = gr.Textbox(
                                    label="Current Prompt Template",
                                    value=self.examples.get_prompt_templates()["Standard"],
                                    interactive=False,
                                    lines=2
                                )
                                model_name = gr.Dropdown(
                                    choices=list(self.config_manager.get_available_models().keys()),
                                    value="openrouter/gpt-4o-mini",
                                    label="Model"
                                )
                                temperature = gr.Slider(
                                    minimum=0.0, maximum=2.0, value=0.7, step=0.1,
                                    label="Temperature"
                                )
                            
                            with gr.Row():
                                process_btn = gr.Button("Process Question", variant="primary")
                                random_question_btn = gr.Button("Random Question")
                        
                        with gr.Column(scale=3):
                            result_display = gr.Markdown(label="Results")
                            
                            prob_table = gr.HTML(label="Probability Distribution Table")
                            
                            with gr.Accordion("🔍 Debug Information", open=False):
                                debug_panel = gr.HTML(label="LLM Requests & Responses")
                            
                            with gr.Row():
                                dist_chart = gr.Plot(label="Answer Distribution Chart")
                                evolution_chart = gr.Plot(label="Confidence Evolution")
                
                # Comparison Tab
                with gr.Tab("Agent Comparison"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            comp_question = gr.Textbox(
                                label="Question",
                                placeholder="Enter question to compare both agents...",
                                lines=3
                            )
                            
                            with gr.Accordion("⚙️ Agent Configuration", open=False):
                                gr.Markdown("""
                                **Parameter Explanations:**
                                - **Target Responses**: Maximum number of LLM responses each agent will generate
                                - **Confidence Threshold**: Self-Reflection stops when confidence exceeds this value
                                - **Minimum Responses**: Self-Reflection won't stop before generating at least this many responses
                                
                                **⚠️ Note**: All prompts are designed to ensure LLM responses end with "Answer: <your_answer>" for consistent parsing.
                                """)
                                
                                comp_target_responses = gr.Slider(
                                    minimum=1, maximum=20, value=10, step=1,
                                    label="🎯 Target Responses (Maximum)",
                                    info="Maximum number of LLM responses for each agent"
                                )
                                comp_confidence_threshold = gr.Slider(
                                    minimum=0.5, maximum=0.95, value=0.8, step=0.05,
                                    label="🎚️ Confidence Threshold",
                                    info="Early stopping threshold for Self-Reflection agent"
                                )
                                comp_min_responses = gr.Slider(
                                    minimum=1, maximum=10, value=3, step=1,
                                    label="🔢 Minimum Responses",
                                    info="Minimum responses before Self-Reflection can stop early"
                                )
                                
                                # Entropy-based intelligence controls for comparison
                                gr.Markdown("### 🧠 Entropy Intelligence (Self-Reflection)")
                                
                                comp_entropy_mode = gr.Dropdown(
                                    choices=["off", "confidence_only", "entropy_only", "combined"],
                                    value="combined",
                                    label="🎛️ Entropy Mode",
                                    info="How to use entropy in early stopping decisions"
                                )
                                
                                comp_entropy_threshold = gr.Slider(
                                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                                    label="🎚️ Entropy Threshold",
                                    info="Stop when normalized entropy drops below this value"
                                )
                                
                                comp_entropy_weight = gr.Slider(
                                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                                    label="⚖️ Entropy Weight",
                                    info="Weight of entropy in combined scoring"
                                )
                                
                                comp_min_entropy_samples = gr.Slider(
                                    minimum=2, maximum=10, value=4, step=1,
                                    label="📊 Min Entropy Samples",
                                    info="Minimum responses before entropy influences stopping"
                                )
                                
                                comp_prompt_template = gr.Dropdown(
                                    choices=list(self.examples.get_prompt_templates().keys()),
                                    value="Standard",
                                    label="Prompt Template"
                                )
                                comp_model_name = gr.Dropdown(
                                    choices=list(self.config_manager.get_available_models().keys()),
                                    value="openrouter/gpt-4o-mini",
                                    label="Model"
                                )
                                comp_temperature = gr.Slider(
                                    minimum=0.0, maximum=2.0, value=0.7, step=0.1,
                                    label="Temperature"
                                )
                            
                            compare_btn = gr.Button("Compare Agents", variant="primary")
                        
                        with gr.Column(scale=3):
                            comparison_display = gr.Markdown(label="Comparison Results")
                            
                            comparison_table = gr.HTML(label="Probability Distribution Comparison")
                            
                            with gr.Row():
                                comparison_chart = gr.Plot(label="Performance Comparison")
                                cost_chart = gr.Plot(label="Cost Analysis")
                
                # Benchmark Analysis Tab
                with gr.Tab("Benchmark Analysis"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            # Benchmark controls
                            db_path_input = gr.Textbox(
                                label="Database Path",
                                value="gsm8k_reflection_results.db",
                                placeholder="Path to SQLite database"
                            )
                            
                            refresh_btn = gr.Button("Refresh Database")
                            
                            # Run selection
                            run_selector = gr.Dropdown(
                                label="Select Benchmark Run",
                                choices=[],
                                interactive=True,
                                allow_custom_value=False
                            )
                            
                            # Analysis options
                            with gr.Accordion("Analysis Options", open=True):
                                show_entropy_evolution = gr.Checkbox(
                                    label="Show Entropy Evolution", value=True
                                )
                                show_early_stopping = gr.Checkbox(
                                    label="Show Early Stopping Analysis", value=True
                                )
                                show_question_breakdown = gr.Checkbox(
                                    label="Show Question-by-Question Results", value=True
                                )
                            
                            analyze_btn = gr.Button("Analyze Run", variant="primary")
                        
                        with gr.Column(scale=2):
                            # Results display
                            benchmark_summary = gr.Markdown(label="Benchmark Summary")
                            
                            with gr.Row():
                                with gr.Column():
                                    entropy_chart = gr.Plot(label="Entropy Evolution")
                                    entropy_expand_btn = gr.Button("🔍 View Larger", size="sm", visible=False)
                                with gr.Column():
                                    early_stopping_chart = gr.Plot(label="Early Stopping Analysis")
                                    early_stopping_expand_btn = gr.Button("🔍 View Larger", size="sm", visible=False)
                            
                            question_breakdown = gr.HTML(label="Question Results")
                
                # Examples Tab
                with gr.Tab("Examples"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 📚 Example Configurations")
                            
                            example_configs = [config.name for config in self.examples.get_demonstration_configs()]
                            example_selector = gr.Dropdown(
                                choices=example_configs,
                                label="Select Example",
                                value=example_configs[0] if example_configs else None
                            )
                            
                            load_example_btn = gr.Button("Load Example")
                            
                            gr.Markdown("### 🎯 Sample Questions by Category")
                            
                            questions_by_category = self.examples.get_sample_questions()
                            for category, questions in questions_by_category.items():
                                with gr.Accordion(category, open=False):
                                    for question in questions:
                                        gr.Markdown(f"- {question}")
            
            # Modal dialogs for expanded chart views
            with gr.Row(visible=False) as entropy_modal:
                with gr.Column():
                    gr.Markdown("## 📊 Entropy Evolution Analysis (Expanded View)")
                    entropy_chart_large = gr.Plot(label="Entropy Evolution - Full Size")
                    with gr.Row():
                        entropy_close_btn = gr.Button("❌ Close", variant="secondary")
            
            with gr.Row(visible=False) as early_stopping_modal:
                with gr.Column():
                    gr.Markdown("## 📊 Early Stopping Analysis (Expanded View)")
                    early_stopping_chart_large = gr.Plot(label="Early Stopping Analysis - Full Size")
                    with gr.Row():
                        early_stopping_close_btn = gr.Button("❌ Close", variant="secondary")
            
            # Event handlers
            process_btn.click(
                fn=self.process_single_agent,
                inputs=[
                    question_input, agent_type, target_responses, confidence_threshold,
                    min_responses, prompt_template, model_name, temperature,
                    entropy_mode, entropy_threshold, entropy_weight, min_entropy_samples
                ],
                outputs=[result_display, prob_table, debug_panel, dist_chart, evolution_chart, status_display]
            )
            
            compare_btn.click(
                fn=self.compare_agents,
                inputs=[
                    comp_question, comp_target_responses, comp_confidence_threshold,
                    comp_min_responses, comp_prompt_template, comp_model_name, comp_temperature,
                    comp_entropy_mode, comp_entropy_threshold, comp_entropy_weight, comp_min_entropy_samples
                ],
                outputs=[comparison_display, comparison_table, comparison_chart, cost_chart, status_display]
            )
            
            random_question_btn.click(
                fn=self.get_random_question,
                outputs=[question_input]
            )
            
            load_example_btn.click(
                fn=self.load_example,
                inputs=[example_selector],
                outputs=[question_input, target_responses, confidence_threshold, min_responses, prompt_template]
            )
            
            # Update prompt template text when dropdown changes
            def update_prompt_text(template_name):
                templates = self.examples.get_prompt_templates()
                return templates.get(template_name, "Think step by step and provide your final answer in the format 'Answer: <your_answer>':")
            
            prompt_template.change(
                fn=update_prompt_text,
                inputs=[prompt_template],
                outputs=[prompt_display]
            )
            
            # Benchmark tab event handlers
            refresh_btn.click(
                fn=self.refresh_benchmark_database,
                inputs=[db_path_input],
                outputs=[run_selector, status_display]
            )
            
            def update_analysis_and_buttons(run_display, show_entropy, show_early_stopping, show_breakdown):
                summary, entropy_fig, early_stopping_fig, breakdown, show_entropy_btn, show_early_stopping_btn = self.analyze_benchmark_run(
                    run_display, show_entropy, show_early_stopping, show_breakdown
                )
                return (
                    summary, entropy_fig, early_stopping_fig, breakdown,
                    gr.Button(visible=show_entropy_btn), gr.Button(visible=show_early_stopping_btn)
                )
            
            analyze_btn.click(
                fn=update_analysis_and_buttons,
                inputs=[run_selector, show_entropy_evolution, show_early_stopping, show_question_breakdown],
                outputs=[benchmark_summary, entropy_chart, early_stopping_chart, question_breakdown, entropy_expand_btn, early_stopping_expand_btn]
            )
            
            # Modal event handlers
            entropy_expand_btn.click(
                fn=self.show_entropy_modal,
                inputs=[run_selector],
                outputs=[entropy_modal, entropy_chart_large]
            )
            
            early_stopping_expand_btn.click(
                fn=self.show_early_stopping_modal,
                inputs=[run_selector],
                outputs=[early_stopping_modal, early_stopping_chart_large]
            )
            
            entropy_close_btn.click(
                fn=self.hide_entropy_modal,
                outputs=[entropy_modal]
            )
            
            early_stopping_close_btn.click(
                fn=self.hide_early_stopping_modal,
                outputs=[early_stopping_modal]
            )
        
        return interface


def launch_interface(
    share: bool = False,
    server_name: str = "0.0.0.0",
    server_port: int = 7860,
    debug: bool = False
) -> None:
    """Launch the Gradio interface.
    
    Args:
        share: Whether to create a public shareable link
        server_name: Server hostname
        server_port: Server port
        debug: Enable debug mode
    """
    interface_app = GradioInterface()
    app = interface_app.create_interface()
    
    print(f"🚀 Launching LLM Agent Comparison Interface...")
    print(f"📍 URL: http://{server_name}:{server_port}")
    
    if share:
        print(f"🌐 Public link will be generated...")
    
    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        debug=debug,
        show_error=True
    )


if __name__ == "__main__":
    launch_interface(debug=True)