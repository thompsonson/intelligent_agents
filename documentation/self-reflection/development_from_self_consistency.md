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
    """Enhanced result with full probability distribution and entropy intelligence."""
    final_answer: str
    consensus_confidence: float  # Max probability method
    answer_distribution: Dict[str, float]  # Normalized probabilities
    uncertainty_level: str  # "high", "medium", "low"
    early_stopping: bool  # Did it stop early due to confidence/entropy?
    total_responses: int
    convergence_analysis: Dict[str, Any]  # Convergence metrics
    
    # Entropy-based intelligence fields
    distribution_entropy: float  # Raw Shannon entropy value
    normalized_entropy: float  # Entropy normalized by max possible (0.0-1.0)
    entropy_level: str  # "concentrated", "scattered", "uniform"
    consensus_type: str  # "strong", "emerging", "divided", "binary"
```

### 4. Mathematical Foundation

Instead of just `argmax_a Σ 𝟙_a(a_i = a)`, we get the full distribution with entropy-based intelligence:

```python
def _calculate_distribution(self) -> Dict[str, float]:
    """Calculate probability distribution over answers."""
    counts = Counter(answers)
    total = sum(counts.values())
    return {answer: count/total for answer, count in counts.items()}

def _calculate_consensus_confidence(self, distribution: Dict[str, float]) -> float:
    """Calculate confidence in consensus using max probability."""
    return max(distribution.values())

def _calculate_entropy(self, distribution: Dict[str, float]) -> float:
    """Calculate Shannon entropy from probability distribution."""
    # Shannon entropy: H = -Σ(p * log2(p))
    entropy = 0.0
    for probability in distribution.values():
        if probability > 0:  # Avoid log(0)
            entropy -= probability * math.log2(probability)
    return entropy

def _calculate_normalized_entropy(self, distribution: Dict[str, float]) -> float:
    """Calculate normalized entropy (0.0 = concentrated, 1.0 = uniform)."""
    if len(distribution) <= 1:
        return 0.0  # Single answer = perfectly concentrated
    
    entropy = self._calculate_entropy(distribution)
    max_entropy = math.log2(len(distribution))  # Uniform distribution entropy
    return entropy / max_entropy if max_entropy > 0 else 0.0

def _classify_consensus_type(self, distribution: Dict[str, float]) -> str:
    """Classify consensus pattern from distribution."""
    probabilities = sorted(distribution.values(), reverse=True)
    max_prob = probabilities[0]
    
    # Binary split: Two main answers roughly equal
    if len(probabilities) >= 2 and probabilities[1] >= 0.35:
        if abs(probabilities[0] - probabilities[1]) <= 0.15:
            return "binary"
    
    # Strong consensus: One answer dominates significantly (80%+)
    if max_prob >= 0.8:
        return "strong"
    
    # Emerging consensus: One answer leading but not dominant (40-79%)
    if max_prob >= 0.4:
        return "emerging"
    
    # Divided: No clear leader (under 40%)
    return "divided"
```

### 5. Entropy-Based Intelligence

The agent now uses **Shannon entropy** to understand the concentration vs scattering of responses:

#### Entropy Calculation
- **Raw Entropy**: `H = -Σ(p * log2(p))` measures uncertainty
- **Normalized Entropy**: `H_norm = H / log2(n)` scales to [0,1]
- **Entropy Level**: "concentrated" (≤0.2), "scattered" (0.2-0.7), "uniform" (>0.7)

#### Consensus Classification
The agent automatically recognizes patterns:
- **Strong**: 80%+ agreement (low entropy, high confidence)
- **Emerging**: 40-79% leading answer (medium entropy)  
- **Binary**: Two roughly equal options (high entropy, no clear winner)
- **Divided**: No clear pattern (maximum entropy, high uncertainty)

#### Smart Early Stopping Modes
1. **Off**: Traditional confidence-only stopping
2. **Confidence Only**: Pure confidence threshold
3. **Entropy Only**: Stop when entropy drops below threshold
4. **Combined**: Balanced confidence + entropy scoring

```python
def _should_stop_early(self, current_responses: int) -> bool:
    """Entropy-aware early stopping decision."""
    if current_responses < self._config.min_responses:
        return False
    
    distribution = self._calculate_distribution()
    confidence = max(distribution.values())
    
    if self._config.entropy_mode == "combined":
        normalized_entropy = self._calculate_normalized_entropy(distribution)
        
        # High confidence overrides entropy concerns
        if confidence >= 0.9:
            return True
        
        # Combined scoring: confidence weighted by entropy concentration
        entropy_factor = 1.0 - (self._config.entropy_weight * normalized_entropy)
        combined_score = confidence * entropy_factor
        
        return combined_score >= (self._config.confidence_threshold * 0.9)
    
    return confidence >= self._config.confidence_threshold
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
    """Configuration for self-reflective agent with entropy intelligence."""
    llm_interface: LLMInterface
    target_responses: int = 10  # Higher default for exploration
    confidence_threshold: float = 0.8  # Early stopping threshold
    min_responses: int = 5  # Minimum before early stop
    prompt_template: str = ""
    
    # Entropy-based intelligence parameters
    entropy_threshold: float = 0.3  # Stop if entropy below this (0.0 = very concentrated)
    entropy_weight: float = 0.3  # Weight of entropy in combined stopping score (0.0-1.0)
    min_entropy_samples: int = 4  # Minimum samples before entropy influences stopping
    entropy_mode: str = "combined"  # "off", "confidence_only", "entropy_only", "combined"
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

### 3. Self-Reflection Methods with Entropy Intelligence
```python
def _assess_convergence(self) -> Dict[str, Any]:
    """Enhanced convergence analysis with entropy evolution tracking."""
    confidences_over_time = []
    entropies_over_time = []
    
    # Calculate confidence and entropy evolution
    for i in range(1, len(self._llm_responses) + 1):
        subset_responses = self._llm_responses[:i]
        answers = [response.answer for response in subset_responses]
        counts = Counter(answers)
        total = sum(counts.values())
        
        # Calculate confidence and entropy for this subset
        if total > 0:
            subset_distribution = {answer: count / total for answer, count in counts.items()}
            confidence = max(subset_distribution.values())
            normalized_entropy = self._calculate_normalized_entropy(subset_distribution)
        else:
            confidence = 0.0
            normalized_entropy = 0.0
        
        confidences_over_time.append(confidence)
        entropies_over_time.append(normalized_entropy)
    
    return {
        'confidence_evolution': confidences_over_time,
        'entropy_evolution': entropies_over_time,
        'convergence_rate': self._calculate_convergence_rate(confidences_over_time),
        'final_stability': self._assess_stability(confidences_over_time),
        'entropy_convergence_rate': self._calculate_entropy_convergence_rate(entropies_over_time),
        'entropy_final_stability': self._assess_entropy_stability(entropies_over_time)
    }

def _get_entropy_level(self, normalized_entropy: float) -> str:
    """Convert normalized entropy to human-readable level."""
    if normalized_entropy <= 0.2:
        return "concentrated"  # Very low entropy - clear consensus
    elif normalized_entropy <= 0.7:
        return "scattered"     # Medium entropy - some disagreement
    else:
        return "uniform"       # High entropy - very scattered responses

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

### Core Benefits
1. **Adaptive Sampling:** Agent stops when confident, continues when uncertain
2. **Self-Awareness:** Agent knows its own uncertainty level
3. **Cost Efficiency:** Fewer LLM calls for high-confidence scenarios
4. **Transparency:** Full probability distribution reveals internal state
5. **Meta-Learning Potential:** Could learn optimal stopping strategies

### Entropy-Based Intelligence Benefits
6. **Pattern Recognition:** Automatically identifies consensus types (strong, emerging, divided, binary)
7. **Smart Decision Making:** Balances confidence and entropy for optimal stopping
8. **Uncertainty Quantification:** Mathematical precision in measuring response scatter
9. **Educational Value:** Students can visualize entropy vs confidence trade-offs
10. **Robust Stopping:** Multiple stopping modes prevent premature or delayed decisions

### Mathematical Advantages
- **Shannon Entropy:** Theoretically grounded uncertainty measurement
- **Normalized Scales:** All metrics scaled to [0,1] for consistent interpretation  
- **Evolution Tracking:** Monitors how uncertainty changes over time
- **Consensus Classification:** Automated pattern recognition in response distributions

### Meta-Learning Explanation

**Meta-learning:** The agent learns how to learn - it develops strategies about its own learning process rather than just learning task-specific content.

**Example Strategy:** The agent could track that math questions typically require confidence_threshold=0.9 and min_responses=4, while creative questions work well with confidence_threshold=0.7 and min_responses=2. Over time, it automatically adjusts these parameters based on question type classification.

## Testing Strategy

### Core Functionality Tests
1. **Consensus Emergence:** Test with questions that have clear correct answers
2. **Early Stopping:** Verify agent stops appropriately with high consensus
3. **Uncertainty Cases:** Test with ambiguous questions requiring more samples
4. **Edge Cases:** Single response achieving threshold, no consensus scenarios

### Entropy-Specific Tests (18 comprehensive tests implemented)
5. **Entropy Calculation Accuracy:** Validate Shannon entropy with known distributions
   - Single answer: entropy = 0.0
   - Binary 50/50: entropy = 1.0
   - Uniform 4-way: entropy = 2.0
6. **Early Stopping Modes:** Test all entropy modes
   - `off`: Traditional confidence-only
   - `confidence_only`: Pure confidence threshold
   - `entropy_only`: Stop on low entropy
   - `combined`: Balanced confidence + entropy
7. **Consensus Classification:** Verify pattern recognition
   - Strong: [80%, 10%, 10%] → "strong"
   - Emerging: [40%, 30%, 20%, 10%] → "emerging"
   - Binary: [50%, 50%] → "binary"
   - Divided: [25%, 25%, 25%, 25%] → "divided"
8. **Entropy Evolution:** Track entropy changes over time as consensus emerges
9. **Edge Case Handling:** Empty distributions, single responses, uniform spreads

### Integration Tests
10. **UI Integration:** Verify entropy controls work in Gradio interface
11. **Visualization:** Confirm entropy metrics display correctly in probability tables
12. **Configuration:** Test entropy parameter validation and boundary conditions

## Future Enhancements

### Core Enhancements
1. **Adaptive Thresholds:** Learn optimal confidence thresholds per question type
2. **Consensus History:** Track patterns in consensus emergence
3. **Meta-Reasoning:** "I usually need more samples for math questions"
4. **Uncertainty Calibration:** Validate that confidence correlates with consensus quality

### Entropy-Specific Enhancements
5. **Advanced Visualizations:** 
   - Confidence vs entropy scatter plots
   - Real-time entropy evolution charts
   - Consensus type transition timelines
6. **Smart Mode Selection:** Automatically choose entropy mode based on question characteristics
7. **Entropy-Based Question Classification:** Use entropy patterns to categorize question types
8. **Dynamic Threshold Adjustment:** Adapt entropy thresholds based on historical performance
9. **Multi-Dimensional Analysis:** Combine entropy with other uncertainty measures
10. **Educational Scenarios:** Pre-built examples showcasing different entropy patterns

### Research Opportunities
11. **Entropy vs Accuracy Correlation:** Study relationship between entropy and correctness
12. **Cross-Domain Validation:** Test entropy effectiveness across different question domains
13. **Optimal Weight Learning:** ML-based optimization of entropy weights in combined mode
14. **Consensus Prediction:** Use early entropy patterns to predict final consensus quality

## Implementation Status

### ✅ **COMPLETED** (Core entropy intelligence fully implemented)
- Shannon entropy calculation with mathematical accuracy
- 4 entropy modes: off, confidence_only, entropy_only, combined
- Automatic consensus type classification
- Entropy evolution tracking
- Complete UI integration with real-time controls
- Comprehensive test suite (18 tests, all passing)
- Enhanced visualizations with entropy metrics

### 📋 **Future Work** (Optional enhancements)
- Advanced entropy-specific visualizations
- Educational examples and documentation
- Research studies on entropy effectiveness