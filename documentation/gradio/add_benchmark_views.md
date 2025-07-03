# Gradio Interface Improvements & Benchmark Integration Plan

## 1. Fix Existing Issues

### 1.1 Fix Entropy Parameter Pollution (`agent_wrapper.py`)

**Problem**: Entropy parameters passed to self-consistency agent unnecessarily

```python
# Current (incorrect)
def process_question(self, ...entropy_threshold, entropy_weight, ...):
    if agent_type == AgentType.SELF_CONSISTENCY:
        result = self._process_with_self_consistency(..., entropy_threshold, ...)

# Fixed
def process_question(self, ...entropy_threshold=0.3, entropy_weight=0.3, ...):
    if agent_type == AgentType.SELF_CONSISTENCY:
        result = self._process_with_self_consistency(question, target_responses, prompt_template, debug_adapter)
    elif agent_type == AgentType.SELF_REFLECTION:
        result = self._process_with_self_reflection(
            question, target_responses, confidence_threshold, min_responses, 
            prompt_template, debug_adapter, entropy_threshold, entropy_weight, 
            min_entropy_samples, entropy_mode
        )
```

### 1.2 Make Debug Adapter Conditional (`agent_wrapper.py`)

```python
# Current (inefficient)
if debug_mode:
    debug_adapter = DebugLiteLLMAdapter(...)
else:
    debug_adapter = None

# Process with debug_adapter or self.llm_adapter

# Fixed
adapter = DebugLiteLLMAdapter(...) if debug_mode else self.llm_adapter
```

### 1.3 Add Input Validation (`app.py`)

```python
def _validate_inputs(self, question: str, target_responses: int, 
                    confidence_threshold: float) -> Tuple[bool, str]:
    """Validate user inputs and return status."""
    if not question.strip():
        return False, "❌ No question provided"
    
    if len(question.strip()) > 2000:
        return False, "❌ Question too long (max 2000 characters)"
    
    if target_responses < 1 or target_responses > 20:
        return False, "❌ Target responses must be 1-20"
    
    if not 0.5 <= confidence_threshold <= 0.95:
        return False, "❌ Confidence threshold must be 0.5-0.95"
    
    return True, "✅ Valid inputs"
```

### 1.4 Refactor Long Methods (`app.py`)

```python
def process_single_agent(self, question: str, agent_type: str, ...):
    """Process question with single agent."""
    # Validate inputs
    valid, message = self._validate_inputs(question, target_responses, confidence_threshold)
    if not valid:
        return message, "", "", None, None, message
    
    # Create adapter and test connection
    adapter, status = self._create_and_test_adapter(model_name, temperature, debug_mode)
    if not adapter:
        return "Connection failed", "", "", None, None, status
    
    # Process question
    result = self._process_question_with_agent(adapter, question, agent_type, ...)
    
    # Format and return results
    return self._format_single_result_output(result)
```

## 2. Benchmark Integration

### 2.1 Add Benchmark Analysis Tab (`app.py`)

```python
# Add fourth tab to Gradio interface
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
                interactive=True
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
                entropy_chart = gr.Plot(label="Entropy Evolution")
                early_stopping_chart = gr.Plot(label="Early Stopping Analysis")
            
            question_breakdown = gr.HTML(label="Question Results")
```

### 2.2 Add Database Interface (`app.py`)

```python
from ..benchmark.database import BenchmarkDatabase

class GradioInterface:
    def __init__(self):
        # ... existing init
        self.benchmark_db = None
    
    def refresh_benchmark_database(self, db_path: str) -> Tuple[List[str], str]:
        """Refresh database connection and return available runs."""
        try:
            self.benchmark_db = BenchmarkDatabase(db_path)
            runs = self._get_available_runs()
            return runs, f"✅ Found {len(runs)} benchmark runs"
        except Exception as e:
            return [], f"❌ Error loading database: {e}"
    
    def _get_available_runs(self) -> List[str]:
        """Get list of available benchmark runs."""
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
                            show_early_stopping: bool, show_breakdown: bool) -> Tuple[str, plt.Figure, plt.Figure, str]:
        """Analyze selected benchmark run."""
        if not run_display or not self.benchmark_db:
            return "No run selected", None, None, ""
        
        # Extract run ID from display string
        run_id = int(run_display.split(":")[0].replace("Run ", ""))
        
        # Get run summary
        summary = self.benchmark_db.get_run_summary(run_id)
        summary_text = self._format_benchmark_summary(summary)
        
        # Create charts
        entropy_fig = self._create_entropy_evolution_chart(run_id) if show_entropy else None
        early_stopping_fig = self._create_early_stopping_chart(run_id) if show_early_stopping else None
        
        # Get question breakdown
        breakdown_html = self._create_question_breakdown_table(run_id) if show_breakdown else ""
        
        return summary_text, entropy_fig, early_stopping_fig, breakdown_html
```

### 2.3 Add Benchmark Visualization Functions (`visualization.py`)

```python
def create_entropy_evolution_benchmark_chart(db: BenchmarkDatabase, run_id: int) -> plt.Figure:
    """Create entropy evolution chart from benchmark database."""
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Get entropy data
    entropy_data = db.get_entropy_analysis(run_id)
    evolution = entropy_data['entropy_evolution']
    
    if not evolution:
        ax1.text(0.5, 0.5, 'No entropy data available', 
                ha='center', va='center', transform=ax1.transAxes)
        return fig
    
    response_nums = [d['response_num'] for d in evolution]
    avg_entropy = [d['avg_entropy'] for d in evolution]
    avg_confidence = [d['avg_confidence'] for d in evolution]
    
    # Plot entropy evolution
    ax1.plot(response_nums, avg_entropy, 'o-', color='red', label='Normalized Entropy')
    ax1.set_title('Average Entropy Evolution Across All Questions')
    ax1.set_xlabel('Response Number')
    ax1.set_ylabel('Normalized Entropy')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot confidence evolution
    ax2.plot(response_nums, avg_confidence, 'o-', color='blue', label='Confidence')
    ax2.set_title('Average Confidence Evolution Across All Questions')
    ax2.set_xlabel('Response Number')
    ax2.set_ylabel('Confidence Score')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    return fig

def create_early_stopping_analysis_chart(db: BenchmarkDatabase, run_id: int) -> plt.Figure:
    """Create early stopping analysis chart."""
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    with sqlite3.connect(db.db_path) as conn:
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
            
            # Stacked bar chart
            ax1.bar(responses, early_stops, label='Early Stops', alpha=0.7, color='green')
            ax1.bar(responses, [c - e for c, e in zip(counts, early_stops)], 
                   bottom=early_stops, label='Full Runs', alpha=0.7, color='red')
            
            ax1.set_title('Response Distribution')
            ax1.set_xlabel('Number of Responses Used')
            ax1.set_ylabel('Number of Questions')
            ax1.legend()
        
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
            categories = ['Full Run', 'Early Stop']
            accuracies = []
            
            for early_stop, total, correct in accuracy_data:
                accuracy = correct / total if total > 0 else 0
                if early_stop:
                    accuracies.insert(0, accuracy)  # Early stop first
                else:
                    accuracies.append(accuracy)     # Full run second
            
            bars = ax2.bar(categories, accuracies, alpha=0.7, color=['red', 'green'])
            ax2.set_title('Accuracy by Stopping Type')
            ax2.set_ylabel('Accuracy')
            ax2.set_ylim(0, 1.0)
            
            # Add value labels
            for bar, acc in zip(bars, accuracies):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{acc:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    return fig
```

### 2.4 Add Benchmark HTML Tables (`app.py`)

```python
def _create_question_breakdown_table(self, run_id: int) -> str:
    """Create HTML table with question-by-question results."""
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
```

## 3. Event Handler Updates (`app.py`)

```python
# Add event handlers for benchmark tab
refresh_btn.click(
    fn=self.refresh_benchmark_database,
    inputs=[db_path_input],
    outputs=[run_selector, status_display]
)

analyze_btn.click(
    fn=self.analyze_benchmark_run,
    inputs=[run_selector, show_entropy_evolution, show_early_stopping, show_question_breakdown],
    outputs=[benchmark_summary, entropy_chart, early_stopping_chart, question_breakdown]
)
```

## 4. Configuration Constants (`config_manager.py`)

```python
# Replace hardcoded values with constants
class ModelConfig:
    MATH_MODEL_TIMEOUT = 180.0  # 3 minutes
    LARGE_MODEL_TIMEOUT = 90.0  # 1.5 minutes
    DEFAULT_TIMEOUT = 60.0      # 1 minute
    
    MAX_QUESTION_LENGTH = 2000
    MAX_TARGET_RESPONSES = 20
    MIN_TARGET_RESPONSES = 1
    
    MATH_MODEL_KEYWORDS = ["qwen2-math", "deepseek-math", "math"]
    LARGE_MODEL_KEYWORDS = ["7b", "13b", "70b", "phi4"]
```

## 5. Implementation Priority

1. **Phase 1**: Fix existing issues (1.1-1.4)
2. **Phase 2**: Add database interface (2.2)
3. **Phase 3**: Add benchmark tab (2.1)
4. **Phase 4**: Add visualization functions (2.3)
5. **Phase 5**: Add HTML tables and formatting (2.4)

## 6. Testing Requirements

```python
# Add to test suite
def test_benchmark_integration():
    """Test benchmark database integration."""
    
def test_entropy_visualization():
    """Test entropy evolution charts."""
    
def test_input_validation():
    """Test input validation functions."""
    
def test_refactored_methods():
    """Test refactored processing methods."""
```

## 7. Documentation Updates

- Update README.md with benchmark analysis features
- Add Claude.md section for database integration
- Create usage examples for benchmark analysis