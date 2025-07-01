# Claude.md - Self-Reflection Agent

## Project Context

Educational system for exploring intelligent agents. Current structure:

```
intelligent_agents/
├── maze_solver/            # Search algorithms (BFS, DFS, A*)
└── llm_agents/
    ├── common/             # Shared LLM interfaces
    ├── self_consistency/   # Existing majority-vote agent
    └── self_reflection/    # NEW: Confidence-aware agent
```

**Design Principles:** SOLID, educational focus, modular architecture

## Objective

Create **Self-Reflection Agent** in `llm_agents/self_reflection/` - demonstrates confidence-aware early stopping and probability distributions rather than simple majority vote.

**Key Differences from self_consistency:**
- Returns probability distributions, not just argmax
- Early stopping based on consensus confidence
- Self-awareness of uncertainty
- Utility-based agent (not model-based reflex)

## Agent Characteristics

**Agent Function:** `question → confidence_aware_sampling → probability_distribution`
**Agent Type:** Utility-based (balances consensus confidence vs computational cost)
**Environment:** Partially observable, stochastic, static, episodic, discrete, known, single-agent

**PEAS Analysis:**
- **Performance:** Return answer with consensus confidence assessment
- **Environment:** User + LLM + prompt/question context
- **Actuators:** LLM queries, confidence assessment, early stopping decisions, user response
- **Sensors:** User text input, LLM response pairs, own consensus confidence level

## Implementation Plan

### 1. Directory Structure
```
llm_agents/self_reflection/
├── __init__.py
├── agent.py               # SelfReflectionAgent
├── domain.py             # Enhanced domain objects
└── config.py             # Enhanced configuration
```

### 2. Core Components

#### Enhanced Domain Objects (domain.py)
```python
@dataclass(frozen=True)
class ReflectionResult:
    """Enhanced result with full probability distribution."""
    final_answer: str
    consensus_confidence: float      # 0.0-1.0 confidence score
    answer_distribution: Dict[str, float]  # Normalized probabilities
    uncertainty_level: str          # "high", "medium", "low"
    early_stopping: bool           # Stopped early due to confidence?
    total_responses: int
    convergence_analysis: Dict[str, Any]  # Convergence metrics
```

#### Enhanced Configuration (config.py)
```python
@dataclass
class ReflectionConfig:
    """Configuration for self-reflection agent."""
    llm_interface: LLMInterface
    target_responses: int = 10
    confidence_threshold: float = 0.8    # Early stopping threshold
    min_responses: int = 5              # Minimum before early stop
    prompt_template: str = ""
```

#### Main Agent (agent.py)
```python
class SelfReflectionAgent:
    """Agent with confidence-aware early stopping."""
    
    def __init__(self, config: ReflectionConfig, question: str):
        self._config = config
        self._question = question
        self._llm_responses: List[LLMResponse] = []
    
    def process_question(self) -> ReflectionResult:
        """Process with confidence-aware early stopping."""
        for i in range(self._config.target_responses):
            # Generate LLM response
            response = self._config.llm_interface.generate_llm_response(
                self._config.prompt_template, self._question
            )
            self._llm_responses.append(self._parse_llm_output(response))
            
            # Check early stopping after minimum responses
            if i >= self._config.min_responses - 1:
                confidence = self._calculate_consensus_confidence()
                if confidence >= self._config.confidence_threshold:
                    return self._build_reflection_result(early_stopping=True)
        
        # Max responses reached
        return self._build_reflection_result(early_stopping=False)
    
    def _calculate_consensus_confidence(self) -> float:
        """Calculate confidence using entropy or max probability."""
        distribution = self._calculate_distribution()
        # Option 1: Max probability
        return max(distribution.values())
        
        # Option 2: Entropy-based (implement as alternative)
        # entropy = -sum(p * log2(p) for p in distribution.values() if p > 0)
        # max_entropy = log2(len(distribution))
        # return 1 - (entropy / max_entropy)
    
    def _calculate_distribution(self) -> Dict[str, float]:
        """Calculate normalized probability distribution."""
        answers = [response.answer for response in self._llm_responses]
        counts = Counter(answers)
        total = sum(counts.values())
        return {answer: count/total for answer, count in counts.items()}
    
    def _assess_convergence(self) -> Dict[str, Any]:
        """Analyze how consensus is emerging over time."""
        distributions_over_time = []
        confidences_over_time = []
        
        # Calculate confidence evolution
        for i in range(1, len(self._llm_responses) + 1):
            subset_responses = self._llm_responses[:i]
            answers = [response.answer for response in subset_responses]
            counts = Counter(answers)
            total = sum(counts.values())
            distribution = {answer: count/total for answer, count in counts.items()}
            confidence = max(distribution.values())
            
            distributions_over_time.append(distribution)
            confidences_over_time.append(confidence)
        
        return {
            'confidence_evolution': confidences_over_time,
            'convergence_rate': self._calculate_convergence_rate(confidences_over_time),
            'final_stability': self._assess_stability(confidences_over_time)
        }
    
    def _calculate_convergence_rate(self, confidences: List[float]) -> float:
        """Calculate how quickly confidence increased."""
        if len(confidences) < 2:
            return 0.0
        return (confidences[-1] - confidences[0]) / len(confidences)
    
    def _assess_stability(self, confidences: List[float]) -> float:
        """Assess stability of final confidence."""
        if len(confidences) < 3:
            return 1.0
        last_three = confidences[-3:]
        return 1.0 - (max(last_three) - min(last_three))
```

### 3. Key Implementation Features

**Confidence Calculation:**
- Max probability method (simple)
- Entropy-based method (advanced)
- Convergence analysis over time

**Early Stopping Logic:**
- Minimum response threshold
- Confidence threshold check
- Cost vs confidence trade-off

**Probability Distribution:**
- Full normalized distribution
- Uncertainty categorization
- Convergence metrics


## Dependencies

Same as self_consistency:
```toml
openai = "^1.0.0"      # LiteLLM communication
```

Environment variables:
```bash
LLM_MODEL=claude-3-haiku
LLM_TEMPERATURE=0.7
LLM_BASE_URL=http://localhost:4000
LLM_API_KEY=sk-1234
```

## Testing Strategy

**Core Tests:**
1. Early stopping with high confidence
2. Continued sampling with low confidence  
3. Confidence calculation accuracy
4. Probability distribution validation
5. Convergence analysis

**Integration Tests:**
6. Compare efficiency vs self_consistency
7. Validate early stopping saves LLM calls
8. Test with various confidence thresholds

**Educational Tests:**
9. Convergence analysis accuracy
10. Confidence evolution tracking

## Development Workflow

```bash
make setup-all           # Initial setup
make test               # Run tests
make test-live          # Test with real LLM
```

## Success Criteria

**Functional:**
- ✅ Early stopping when confident
- ✅ Probability distributions returned
- ✅ Confidence calculation accurate
- ✅ Cost efficiency vs baseline

**Educational:**  
- ✅ Convergence analysis tracking
- ✅ Early stopping demonstration
- ✅ Uncertainty awareness display

**Architecture:**
- ✅ Follows existing patterns
- ✅ Clean separation from self_consistency
- ✅ Maintains educational focus

## Blog Integration

Demonstrates concepts from **Self-Reflective Agent Transformation Guide:**
- Confidence-aware decision making
- Utility-based agent architecture  
- Self-awareness of uncertainty
- Cost vs confidence optimization