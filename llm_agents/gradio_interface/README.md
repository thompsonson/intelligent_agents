# 🤖 Gradio Interface for LLM Agent Comparison

A web-based interface for comparing **Self-Consistency** and **Self-Reflection** agents with interactive controls and visualizations.

## 🌟 Features

### 🔄 Single Agent Mode
- Process questions with either Self-Consistency or Self-Reflection agents
- Real-time configuration of parameters (responses, confidence thresholds, etc.)
- Interactive visualizations of results
- Model and temperature selection

### ⚖️ Comparison Mode  
- Side-by-side comparison of both agents on the same question
- Performance metrics comparison
- Cost analysis and efficiency visualization
- Processing time comparison

### 📊 Visualizations
- **Probability Distribution Charts**: Bar charts showing answer distributions
- **Confidence Evolution**: Line charts tracking confidence over time  
- **Performance Comparison**: Multi-metric comparison charts
- **Cost Analysis**: Estimated cost and response efficiency charts

### 🎯 Educational Features
- Pre-loaded example questions organized by category
- Demonstration configurations showcasing agent differences
- Sample questions by difficulty level
- Interactive parameter explanations

## 🚀 Quick Start

### Prerequisites
1. **Install Dependencies**:
   ```bash
   make install  # Installs gradio and other dependencies
   ```

2. **Start LiteLLM Server**:
   ```bash
   make litellm-install  # Install and start LiteLLM Docker container
   ```

3. **Configure Environment**:
   ```bash
   make setup-env  # Create .env file
   # Edit .env with your API keys and settings
   ```

### Launch Interface

#### Development Mode
```bash
make gradio-dev
```
- Interface available at: http://localhost:7860
- Debug mode enabled
- Auto-reloading on changes

#### Production Mode  
```bash
make gradio-serve
```
- Interface available at: http://0.0.0.0:7860
- Optimized for performance
- Suitable for deployment

### Testing

#### Component Testing
```bash
make gradio-test
```
Tests basic component imports and initialization.

#### Live Testing (with LLM)
```bash
make gradio-test-live
```
Tests full workflow with real LLM connections.

## 🏗️ Architecture

### Core Components

#### `agent_wrapper.py`
- **UnifiedResult**: Standardized result format for both agents
- **AgentWrapper**: Common interface for both agent types
- **AgentType**: Enum for agent selection
- Handles agent initialization, processing, and comparison

#### `config_manager.py`
- **ConfigManager**: Manages LLM configuration and validation
- **UIConfig**: Configuration data class for UI inputs
- Environment variable integration
- Model availability and cost estimation

#### `visualization.py` 
- **Chart Generation**: Creates matplotlib/seaborn visualizations
- **Distribution Charts**: Probability distribution bar charts
- **Evolution Charts**: Confidence tracking over time
- **Comparison Charts**: Multi-agent performance comparison
- **Cost Analysis**: Cost and efficiency visualizations

#### `examples.py`
- **Sample Questions**: Organized by category and difficulty
- **Demonstration Configs**: Predefined configurations
- **Educational Examples**: Concept-focused question sets
- **Prompt Templates**: Various prompt styles

#### `app.py`
- **GradioInterface**: Main interface class
- **Tab Organization**: Single agent, comparison, examples
- **Event Handlers**: UI interaction logic
- **Error Handling**: Graceful error management

## 🎛️ Interface Guide

### Single Agent Tab
1. **Question Input**: Enter your question
2. **Agent Selection**: Choose Self-Consistency or Self-Reflection
3. **Configuration**: Adjust parameters in accordion
   - Target Responses (1-20)
   - Confidence Threshold (0.5-0.95)
   - Minimum Responses (1-10)
   - Prompt Template selection
   - Model selection
   - Temperature (0.0-2.0)
4. **Process**: Click "Process Question" button
5. **Results**: View formatted results and visualizations

### Comparison Tab
1. **Question Input**: Enter question for both agents
2. **Configuration**: Set parameters for comparison
3. **Compare**: Click "Compare Agents" button  
4. **Analysis**: Review side-by-side results and metrics

### Examples Tab
- **Example Configurations**: Load predefined setups
- **Sample Questions**: Browse questions by category
- **Educational Focus**: Understand agent differences

## 📈 Understanding Results

### Self-Consistency Results
- **Final Answer**: Majority vote result
- **Confidence**: Vote ratio (vote_count / total_responses)
- **Fixed Responses**: Always uses target_responses
- **Simple Distribution**: Binary (answer vs other)

### Self-Reflection Results
- **Final Answer**: Highest probability answer
- **Consensus Confidence**: Maximum probability in distribution
- **Early Stopping**: May stop before target_responses
- **Full Distribution**: Detailed probability breakdown
- **Convergence Analysis**: Confidence evolution metrics
- **Uncertainty Level**: High/Medium/Low categorization

### Comparison Metrics
- **Efficiency**: Response count comparison
- **Speed**: Processing time comparison  
- **Cost**: Estimated API cost comparison
- **Accuracy**: Answer agreement analysis

## 🔧 Configuration Options

### Agent Parameters
- **Target Responses**: Maximum responses to generate (1-20)
- **Confidence Threshold**: Early stopping threshold (0.5-0.95, self-reflection only)
- **Minimum Responses**: Minimum before early stopping (1-10, self-reflection only)

### LLM Parameters  
- **Model**: claude-3-haiku, claude-3-5-sonnet, gpt-4o, gpt-4o-mini, gpt-3.5-turbo
- **Temperature**: Randomness control (0.0-2.0)
- **Prompt Template**: Various prompting styles

### Environment Variables
```bash
LLM_MODEL=claude-3-haiku          # Default model
LLM_TEMPERATURE=0.7               # Default temperature  
LLM_BASE_URL=http://localhost:4000 # LiteLLM server URL
LLM_API_KEY=sk-1234               # LiteLLM master key
```

## 🎓 Educational Use Cases

### Concept Demonstrations
1. **Early Stopping Efficiency**: 
   - Use simple questions (e.g., "What is 2+2?")
   - Show self-reflection stopping early vs self-consistency using all responses

2. **Uncertainty Handling**:
   - Use subjective questions (e.g., "What is the best color?")  
   - Compare uncertainty awareness between agents

3. **Probability Distributions**:
   - Use questions with clear correct answers
   - Show detailed distributions vs simple majority vote

4. **Convergence Patterns**:
   - Use mathematical problems
   - Track confidence evolution over responses

### Research Applications
- **Cost-Benefit Analysis**: Compare computational efficiency
- **Confidence Calibration**: Study confidence vs accuracy relationships  
- **Response Pattern Analysis**: Examine convergence behaviors
- **Parameter Sensitivity**: Test different thresholds and settings

## 🚨 Troubleshooting

### Common Issues

#### "Cannot connect to LLM" Error
1. Check LiteLLM status: `make litellm-status`
2. Start LiteLLM if stopped: `make litellm-start`
3. Verify API keys in .env file
4. Check network connectivity to localhost:4000

#### Import Errors
1. Ensure dependencies installed: `make install`
2. Check virtual environment activation
3. Verify Python path includes project directory

#### Gradio Interface Not Loading
1. Check port 7860 availability  
2. Try different port: modify server_port in app.py
3. Check firewall settings
4. Verify gradio installation: `pip list | grep gradio`

#### Performance Issues
1. Reduce target_responses for faster processing
2. Use faster models (claude-3-haiku, gpt-4o-mini)
3. Increase confidence_threshold for more early stopping
4. Check LiteLLM server resources

### Debug Mode
Launch with debug enabled:
```bash
uv run python -c "from llm_agents.gradio_interface import launch_interface; launch_interface(debug=True)"
```

## 🔗 Integration

### Programmatic Access
```python
from llm_agents.gradio_interface import AgentWrapper, AgentType

# Initialize wrapper
wrapper = AgentWrapper()

# Process single question
result = wrapper.process_question(
    question="What is 15% of 240?",
    agent_type=AgentType.SELF_REFLECTION,
    target_responses=5,
    confidence_threshold=0.8
)

# Compare agents
comparison = wrapper.compare_agents(
    question="What is the capital of France?",
    target_responses=5
)
```

### Custom Visualizations
```python
from llm_agents.gradio_interface.visualization import create_probability_distribution_chart

# Create custom charts
fig = create_probability_distribution_chart(result)
fig.show()
```

## 📝 Development

### Adding New Features
1. **New Visualizations**: Add functions to `visualization.py`
2. **New Examples**: Extend `examples.py` with additional question sets
3. **UI Components**: Modify `app.py` for new interface elements
4. **Agent Integration**: Extend `agent_wrapper.py` for new agent types

### Testing
```bash
make gradio-test       # Component testing
make gradio-test-live  # Full integration testing
make test             # Run all project tests
```

### Code Style
```bash
make lint    # Run linting
make format  # Format code
```

## 📚 Related Documentation

- [Self-Consistency Agent](../self_consistency/README.md)
- [Self-Reflection Agent](../self_reflection/README.md)  
- [Project Overview](../../README.md)
- [LiteLLM Configuration](../../litellm_config.yaml)