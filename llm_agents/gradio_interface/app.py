"""Main Gradio application for LLM agent comparison interface.

This module creates the web-based interface for comparing self-consistency
and self-reflection agents with interactive controls and visualizations.
"""

import gradio as gr
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional, Tuple
import json
import traceback

from .agent_wrapper import AgentWrapper, AgentType, UnifiedResult
from .config_manager import ConfigManager, UIConfig
from .visualization import (
    create_probability_distribution_chart,
    create_confidence_evolution_chart,
    create_comparison_chart,
    create_uncertainty_analysis_chart,
    create_cost_analysis_chart
)
from .examples import Examples


class GradioInterface:
    """Main Gradio interface for agent comparison."""
    
    def __init__(self):
        """Initialize the interface with components."""
        self.config_manager = ConfigManager()
        self.agent_wrapper = None
        self.examples = Examples()
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
        temperature: float
    ) -> Tuple[str, str, str, Optional[plt.Figure], Optional[plt.Figure], str]:
        """Process question with single agent and return results.
        
        Returns:
            Tuple of (result_text, prob_table, debug_info, distribution_chart, evolution_chart, status_message)
        """
        try:
            # Validate inputs
            if not question.strip():
                return "Please enter a question.", "", "", None, None, "❌ No question provided"
            
            # Create LLM adapter with current settings
            llm_adapter = self.config_manager.create_llm_adapter(
                model_name=model_name,
                temperature=temperature
            )
            agent_wrapper = AgentWrapper(llm_adapter)
            
            # Test connection
            if not agent_wrapper.validate_llm_connection():
                return ("Connection failed", "", "", None, None, 
                       "❌ Cannot connect to LLM. Check that LiteLLM is running.")
            
            # Process question
            agent_type_enum = AgentType.SELF_CONSISTENCY if agent_type == "Self-Consistency" else AgentType.SELF_REFLECTION
            
            result = agent_wrapper.process_question(
                question=question,
                agent_type=agent_type_enum,
                target_responses=target_responses,
                confidence_threshold=confidence_threshold,
                min_responses=min_responses,
                prompt_template=prompt_template
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
        temperature: float
    ) -> Tuple[str, str, Optional[plt.Figure], Optional[plt.Figure], str]:
        """Compare both agents on the same question.
        
        Returns:
            Tuple of (comparison_text, comparison_table, comparison_chart, cost_chart, status_message)
        """
        try:
            if not question.strip():
                return "Please enter a question.", "", None, None, "❌ No question provided"
            
            # Create LLM adapter
            llm_adapter = self.config_manager.create_llm_adapter(
                model_name=model_name,
                temperature=temperature
            )
            agent_wrapper = AgentWrapper(llm_adapter)
            
            # Test connection
            if not agent_wrapper.validate_llm_connection():
                return ("Connection failed", "", None, None,
                       "❌ Cannot connect to LLM. Check that LiteLLM is running.")
            
            # Compare agents
            results = agent_wrapper.compare_agents(
                question=question,
                target_responses=target_responses,
                confidence_threshold=confidence_threshold,
                min_responses=min_responses,
                prompt_template=prompt_template
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
            f"",
            f"## Efficiency Analysis",
        ]
        
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
    
    def create_interface(self) -> gr.Interface:
        """Create and return the Gradio interface."""
        
        with gr.Blocks(title="LLM Agent Comparison", theme=gr.themes.Soft()) as interface:
            
            # Header
            gr.Markdown("""
            # 🤖 LLM Agent Comparison Interface
            
            Compare **Self-Consistency** and **Self-Reflection** agents with interactive controls and visualizations.
            
            - **Self-Consistency**: Fixed sampling with majority vote
            - **Self-Reflection**: Confidence-aware early stopping with probability distributions
            """)
            
            # Connection status
            status_display = gr.Textbox(
                label="Status",
                value="Ready to process questions",
                interactive=False
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
                                choices=["Self-Consistency", "Self-Reflection"],
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
                                    value="claude-3-haiku",
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
                                comp_prompt_template = gr.Dropdown(
                                    choices=list(self.examples.get_prompt_templates().keys()),
                                    value="Standard",
                                    label="Prompt Template"
                                )
                                comp_model_name = gr.Dropdown(
                                    choices=list(self.config_manager.get_available_models().keys()),
                                    value="claude-3-haiku",
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
            
            # Event handlers
            process_btn.click(
                fn=self.process_single_agent,
                inputs=[
                    question_input, agent_type, target_responses, confidence_threshold,
                    min_responses, prompt_template, model_name, temperature
                ],
                outputs=[result_display, prob_table, debug_panel, dist_chart, evolution_chart, status_display]
            )
            
            compare_btn.click(
                fn=self.compare_agents,
                inputs=[
                    comp_question, comp_target_responses, comp_confidence_threshold,
                    comp_min_responses, comp_prompt_template, comp_model_name, comp_temperature
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