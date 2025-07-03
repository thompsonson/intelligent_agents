# 🤖 LLM Agents System

A comprehensive system for exploring intelligent agent architectures with Chain-of-Thought reasoning, consensus mechanisms, and confidence-aware decision making.

## 🏗️ Architecture Overview

```
llm_agents/
├── common/                    # Shared interfaces and domain objects
│   ├── interfaces.py         # LLM interface abstractions
│   └── domain.py            # Common data structures
├── self_consistency/         # Self-Consistency Agent (majority voting)
│   ├── agent.py             # Core agent implementation
│   ├── config.py            # Configuration management
│   └── domain.py            # Agent-specific data structures
├── self_reflection/          # Self-Reflection Agent (confidence-aware)
│   ├── agent.py             # Core agent with early stopping
│   ├── config.py            # Enhanced configuration
│   └── domain.py            # Rich result objects with entropy
├── benchmark/                # Performance evaluation tools
│   ├── gsm8k_poc.py         # GSM8K mathematical reasoning benchmark
│   └── run_gsm8k.py         # Standalone benchmark runner
├── gradio_interface/         # Web-based comparison interface
│   └── app.py               # Interactive agent comparison tool
└── tests/                    # Comprehensive test suite
    └── test_*.py            # Unit and integration tests
```

## 🎯 Agent Types

### Self-Consistency Agent
**Agent Type:** Model-based reflex agent
**Key Features:**
- Multiple independent reasoning attempts
- Majority voting for consensus
- Fixed number of responses
- Simple confidence scoring (vote ratio)

**Best for:** Factual questions, mathematical problems, clear right/wrong answers

### Self-Reflection Agent  
**Agent Type:** Utility-based agent
**Key Features:**
- Confidence-aware early stopping
- Full probability distributions
- Entropy-based uncertainty quantification
- Convergence analysis and consensus classification

**Best for:** Complex reasoning, uncertainty-aware tasks, cost-sensitive applications

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Install dependencies
make install

# Create environment configuration
make setup-env
# Edit .env with your API keys and model preferences
```

### 2. Start LLM Server
```bash
# Install and start LiteLLM proxy server
make litellm-install

# Check server status
make litellm-status

# View available models
make litellm-models
```

### 3. Run Agents
```bash
# Test agents with real LLM
make test-agent-live

# Run mathematical reasoning benchmark
make benchmark-gsm8k

# Launch interactive web interface
make gradio-dev
```

## 🔧 Supported LLM Providers

### Cloud Providers (API Key Required)
- **OpenAI**: gpt-4o, gpt-4o-mini
- **Anthropic**: claude-3-5-sonnet, claude-3-haiku
- **Google**: gemini-pro, gemini-1.5-pro (via API key)

### Self-Hosted/Open Source (No API Key)
- **Ollama**: mistral-7b, gemma, phi4, codegeex4, gemma2-2b, gemma-2b
  - Remote endpoint: `http://100.93.83.103:11434`
  - Privacy-focused, cost-effective option
  - Full local control over models

### Mathematical Reasoning Specialists
- **Qwen2-Math-7B**: `qwen2-math-7b` (Official)
  - Specialized mathematical reasoning model
  - Outperforms many closed-source models on math benchmarks
  - Optimized for step-by-step mathematical problem solving
- **DeepSeek-Math-7B**: `deepseek-math-7b` (Community)
  - 51.7% accuracy on competition-level MATH benchmark
  - Strong performance on step-by-step reasoning
  - Approaches 60% accuracy with tool use

### Configuration
Set your preferred model in `.env`:
```bash
# Cloud provider examples
LLM_MODEL=claude-3-haiku
LLM_MODEL=gpt-4o-mini

# Ollama examples  
LLM_MODEL=mistral-7b
LLM_MODEL=gemma
LLM_MODEL=phi4

# Mathematical reasoning specialists
LLM_MODEL=qwen2-math-7b
LLM_MODEL=deepseek-math-7b
```

## 📊 Benchmarking

### GSM8K Mathematical Reasoning
Test agent effectiveness on grade-school math problems:

```bash
# Run 5-question proof of concept
make benchmark-gsm8k
```

**Expected Results:** Accuracy improves with more attempts
- 1 attempt: ~60-70% accuracy (general models), ~70-80% (math specialists)
- 3 attempts: ~75-85% accuracy (general models), ~85-90% (math specialists)
- 5 attempts: ~80-90% accuracy (general models), ~90-95% (math specialists)
- 10 attempts: ~85-95% accuracy (general models), ~95-98% (math specialists)

**Mathematical Reasoning Models Expected Performance:**
- **Qwen2-Math-7B**: Superior performance on mathematical word problems
- **DeepSeek-Math-7B**: Excellent step-by-step reasoning, competitive accuracy

### Custom Benchmarks
```python
from llm_agents.benchmark import GSM8KBenchmark
from llm_agents.common.interfaces import LiteLLMAdapter

# Create custom benchmark
llm_interface = LiteLLMAdapter()
benchmark = GSM8KBenchmark(llm_interface)

# Run with different configurations
report = benchmark.run_benchmark(attempt_counts=[1, 5, 10])
benchmark.print_detailed_results(report)
```

## 🎛️ Interactive Interface

Launch the web-based comparison tool:

```bash
make gradio-dev
# Open http://localhost:7860
```

**Features:**
- Side-by-side agent comparison
- Real-time parameter adjustment
- Probability distribution visualizations
- Confidence evolution tracking
- Cost and efficiency analysis
- Pre-loaded example questions

## 🧪 Agent Comparison Examples

### Early Stopping Efficiency
```python
# Self-Reflection stops early with high confidence
question = "What is 7 × 9?"
# Expected: 2-3 responses vs 10 responses

# Self-Consistency uses all responses  
# Cost savings: 70-80% fewer LLM calls
```

### Uncertainty Awareness
```python
# Self-Reflection provides uncertainty metrics
question = "What is the best programming language?"
# Expected: Low confidence, high entropy, "divided" consensus
```

### Mathematical Reasoning
```python
# Both agents excel, but different efficiency
question = "If a train travels 120 miles in 2.5 hours, what is its average speed?"
# Expected: Self-reflection faster convergence
```

## 📈 Performance Metrics

### Self-Consistency Metrics
- **Final Answer**: Majority vote result
- **Vote Count**: Number of votes for winning answer
- **Confidence**: Vote ratio (votes/total_responses)
- **Total Responses**: Always equals target_responses

### Self-Reflection Metrics
- **Final Answer**: Highest probability answer
- **Consensus Confidence**: Maximum probability
- **Answer Distribution**: Full probability breakdown
- **Distribution Entropy**: Uncertainty quantification (0-1)
- **Consensus Type**: Strong/Emerging/Divided/Binary
- **Early Stopping**: Whether stopped before target_responses
- **Convergence Analysis**: Confidence evolution metrics

## 🔬 Research Applications

### Confidence Calibration Studies
```python
# Study relationship between confidence and accuracy
results = []
for question in test_set:
    result = agent.process_question(question)
    results.append({
        'confidence': result.consensus_confidence,
        'correct': evaluate_answer(result.final_answer, ground_truth)
    })
```

### Cost-Benefit Analysis
```python
# Compare computational efficiency
sc_result = self_consistency_agent.process_question(question)
sr_result = self_reflection_agent.process_question(question)

efficiency_gain = (sc_result.total_responses - sr_result.total_responses) / sc_result.total_responses
cost_savings = efficiency_gain * estimated_cost_per_response
```

### Entropy-Based Intelligence
```python
# Analyze uncertainty patterns
if result.entropy_level == "high":
    # Question may be ambiguous or subjective
    handle_uncertain_response(result)
elif result.consensus_type == "divided":
    # Multiple valid interpretations possible
    request_clarification(question)
```

## 🛠️ Development

### Running Tests
```bash
# Unit tests
make test

# Integration tests with live LLM
make test-agent-live

# Benchmark tests
make benchmark-gsm8k

# Web interface tests
make gradio-test-live
```

### Adding New Agents
1. Create agent module in `llm_agents/your_agent/`
2. Implement core interfaces from `common/interfaces.py`
3. Add configuration in `config.py`
4. Define domain objects in `domain.py`
5. Add tests in `tests/test_your_agent.py`
6. Update benchmark and interface integration

### Code Quality
```bash
make lint      # Run linting checks
make format    # Format code
make clean     # Clean temporary files
```

## 📚 Educational Use Cases

### Algorithm Comparison
- Demonstrate different consensus mechanisms
- Show efficiency vs accuracy trade-offs
- Explore uncertainty quantification approaches

### AI Safety Research
- Study confidence calibration in language models
- Analyze consensus formation patterns
- Investigate early stopping criteria effectiveness

### Cognitive Science
- Model human reasoning with multiple perspectives
- Study confidence-based decision making
- Explore uncertainty representation in AI systems

## 🔗 Related Projects

- **Tyler Burleigh's GSM8K Analysis**: [Blog Post](https://tylerburleigh.com/blog/2023/12/04/) - Methodology inspiration for benchmark
- **Self-Consistency CoT**: [Paper](https://arxiv.org/abs/2203.11171) - Original self-consistency concept
- **LiteLLM**: [GitHub](https://github.com/BerriAI/litellm) - Multi-provider LLM proxy

## 📄 License

This project is part of an educational system for exploring intelligent agents and algorithm comparison. See the main project repository for license details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Ensure all tests pass with `make test`
5. Submit a pull request with clear description

## 🆘 Support

### Common Issues
- **LLM Connection Errors**: Check `make litellm-status`
- **API Key Issues**: Verify `.env` configuration
- **Model Not Found**: Check available models with `make litellm-models`
- **Performance Issues**: Use smaller models or reduce response counts

### Documentation
- [Gradio Interface Guide](gradio_interface/README.md)
- [Development Documentation](../documentation/self-reflection/)
- [Project Architecture](../CLAUDE.md)

---

🚀 **Ready to explore intelligent agent architectures? Start with `make gradio-dev` for an interactive experience!**