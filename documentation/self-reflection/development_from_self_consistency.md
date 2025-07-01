# Self-Reflective Agent Transformation Guide

## Overview

Transform the agent from a simple majority-vote calculator into a **self-reflective agent with uncertainty awareness**. The agent becomes consensus-seeking rather than accuracy-seeking, since it has no access to ground truth.

## Key Changes Required

### 1. Updated PEAS Analysis

| Element | Description |
|---------|-------------|
| **Performance** | Return answer with consensus confidence assessment |
| **Environment** | User + LLM + prompt/question context |
| **Actuators** | LLM queries, confidence assessment, early stopping decisions, user response |
| **Sensors** | User text input, LLM response pairs (reasoning, answer), own consensus confidence level |


### 1. Agent Function Evolution

**Current:** Simple threshold-based decision
```python
if state.response_count < target_m:
    action ← QUERY-LLM()
else:
    action ← MAJORITY-VOTE() # Returns single answer
```

**New:** Confidence-aware decision making
```python
if state.response_count < target_m AND consensus_confidence < confidence_threshold:
    action ← QUERY-LLM()
elif consensus_confidence >= confidence_threshold:
    action ← RETURN-DISTRIBUTION() # Early stopping with high confidence
else:
    action ← RETURN-DISTRIBUTION() # Max samples reached
```

### 2. Percept Sequence Changes

**Current percepts:**
- Question
- LLM Responses

**New percepts:**
- Question  
- LLM Responses
- **Own consensus confidence level** (self-perception!)

#### Updated Percept Sequence

**Percepts:**
- Question
- LLM Responses  
- Own consensus confidence level (self-perception)

**Actions:**
- Query the LLM
- Assess consensus confidence
- Early stopping decision
- Reply to user with distribution

**Confidence-aware percept sequence:**

| Percept sequence | Action |
|------------------|--------|
| [Question] | QUERY-LLM |
| [Question, Response1] | QUERY-LLM |
| [Question, Response1-4] | QUERY-LLM |
| [Question, Response1-5, HighConfidence] | EARLY-STOP + REPLY-TO-USER |
| [Question, Response1-5, LowConfidence] | QUERY-LLM |
| [Question, Response1-10, MediumConfidence] | REPLY-TO-USER (max reached) |

*Note: Confidence assessment only begins after minimum N responses (default: 5)*

This makes the agent **partially self-aware** - it can perceive its own uncertainty state about consensus.

### 3. Return Value Transformation

```python
@dataclass(frozen=True)
class ReflectionResult:
    """Enhanced result with full probability distribution."""
    final_answer: str
    consensus_confidence: float  # Entropy-based or max probability
    answer_distribution: Dict[str, float]  # Normalized probabilities
    uncertainty_level: str  # "high", "medium", "low"
    early_stopping: bool  # Did it stop early due to confidence?
    total_responses: int
    convergence_rate: float  # How quickly consensus emerged
```

### 4. Mathematical Foundation

Instead of just `argmax_a Σ 𝟙_a(a_i = a)`, we get the full distribution:

```python
def _calculate_distribution(self) -> Dict[str, float]:
    """Calculate probability distribution over answers."""
    counts = Counter(answers)
    total = sum(counts.values())
    return {answer: count/total for answer, count in counts.items()}

def _calculate_consensus_confidence(self, distribution: Dict[str, float]) -> float:
    """Calculate confidence in consensus using entropy or max probability."""
    # Option 1: Max probability (dominant answer strength)
    return max(distribution.values())
    
    # Option 2: Entropy-based (lower entropy = higher consensus)
    entropy = -sum(p * log2(p) for p in distribution.values() if p > 0)
    max_entropy = log2(len(distribution))
    return 1 - (entropy / max_entropy)  # Normalize to [0,1]

def _calculate_convergence_rate(self) -> float:
    """Measure how quickly consensus is emerging."""
    # Track consensus confidence over time
    # Higher rate = faster convergence = more confident stopping
    pass
```

## Agent Type Implications

**Current:** Model-based reflex agent
- Simple condition-action rules
- No goal reasoning

**New:** **Utility-based agent**
- **Utility:** Balance consensus confidence vs computational cost
- **Goal:** Achieve sufficient consensus confidence 
- **Reasoning:** "Should I sample more or am I confident in the consensus?"

### Key Insight: Consensus ≠ Accuracy

The agent optimizes for **internal consistency** (measurable) not **external correctness** (unmeasurable):
- Can be highly confident but completely wrong
- All responses could consistently converge on incorrect answer
- Agent measures agreement between its own responses, not truth

## Environment Analysis Updates

### Observable Properties
**Current:** Partially observable (can't see LLM internals)

**New:** Still partially observable, but now includes:
- Own consensus confidence state
- Convergence patterns
- Internal uncertainty levels

### Episodic vs Sequential
**Current:** Episodic (each question independent)

**New:** Could become **sequential** if agent uses confidence history for meta-learning:
- Learn optimal confidence thresholds for different question types
- Adapt sampling strategies based on past performance
- Remember convergence patterns

## Implementation Changes

### 1. Enhanced Configuration
```python
@dataclass
class ReflectionConfig:
    """Configuration for self-reflective agent."""
    llm_interface: LLMInterface
    target_responses: int = 5
    confidence_threshold: float = 0.8  # NEW: Early stopping threshold
    min_responses: int = 3  # NEW: Minimum before considering early stop
    prompt_template: str = ""
```

### 2. Updated Agent Function
```python
def process_question(self) -> ReflectionResult:
    """Process question with confidence-aware early stopping."""
    for i in range(self._config.target_responses):
        # Generate response
        response = await self._config.llm_interface.generate_llm_response(
            self._config.prompt_template, self._question
        )
        self._llm_responses.append(self._parse_llm_output(response))
        
        # Check for early stopping after minimum responses
        if i >= self._config.min_responses - 1:
            distribution = self._calculate_distribution()
            confidence = self._calculate_consensus_confidence(distribution)
            
            if confidence >= self._config.confidence_threshold:
                return self._build_reflection_result(
                    distribution=distribution,
                    early_stopping=True
                )
    
    # Max responses reached
    distribution = self._calculate_distribution()
    return self._build_reflection_result(
        distribution=distribution,
        early_stopping=False
    )
```

### 3. Self-Reflection Methods
```python
def _assess_consensus_quality(self) -> Dict[str, Any]:
    """Agent reflects on its own consensus quality."""
    distribution = self._calculate_distribution()
    return {
        'consensus_confidence': self._calculate_consensus_confidence(distribution),
        'answer_diversity': len(distribution),
        'dominant_answer_strength': max(distribution.values()),
        'uncertainty_level': self._categorize_uncertainty(distribution)
    }

def _categorize_uncertainty(self, distribution: Dict[str, float]) -> str:
    """Categorize agent's uncertainty about consensus."""
    max_prob = max(distribution.values())
    if max_prob >= 0.8:
        return "low"
    elif max_prob >= 0.6:
        return "medium"
    else:
        return "high"
```

## Benefits of Transformation

1. **Adaptive Sampling:** Agent stops when confident, continues when uncertain
2. **Self-Awareness:** Agent knows its own uncertainty level
3. **Cost Efficiency:** Fewer LLM calls for high-confidence scenarios
4. **Transparency:** Full probability distribution reveals internal state
5. **Meta-Learning Potential:** Could learn optimal stopping strategies

### Meta-Learning Explanation

**Meta-learning:** The agent learns how to learn - it develops strategies about its own learning process rather than just learning task-specific content.

**Example Strategy:** The agent could track that math questions typically require confidence_threshold=0.9 and min_responses=4, while creative questions work well with confidence_threshold=0.7 and min_responses=2. Over time, it automatically adjusts these parameters based on question type classification.

## Testing Strategy

1. **Consensus Emergence:** Test with questions that have clear correct answers
2. **Early Stopping:** Verify agent stops appropriately with high consensus
3. **Uncertainty Cases:** Test with ambiguous questions requiring more samples
4. **Edge Cases:** Single response achieving threshold, no consensus scenarios

## Future Enhancements

1. **Adaptive Thresholds:** Learn optimal confidence thresholds per question type
2. **Consensus History:** Track patterns in consensus emergence
3. **Meta-Reasoning:** "I usually need more samples for math questions"
4. **Uncertainty Calibration:** Validate that confidence correlates with consensus quality