# Building a Reflective Judgment Agent: From PEAS Analysis to Production Code

Following the Agent Design Process for creating an agent that demonstrates **reflective judgment** - the ability to critically evaluate instructions and refuse invalid options.

## Environment Analysis

### PEAS Framework

| Element | Description |
|---------|-------------|
| **Performance** | Correctly identify when no valid option exists; provide accurate answers when possible |
| **Environment** | User + question + multiple choice options (potentially all incorrect) |
| **Actuators** | Option selection, refusal response, alternative answer provision |
| **Sensors** | Question text, multiple choice options, context cues |

### Environment Properties

- **Partially Observable**: Agent must evaluate option validity without knowing user intent
- **Single Agent**: One agent making decisions about option validity
- **Stochastic**: Questions may vary in difficulty and deception level
- **Episodic**: Each question evaluation is independent
- **Static**: Question content doesn't change during evaluation
- **Discrete**: Finite set of responses (A, B, refuse, alternative answer)
- **Known**: Clear input format and expected output types

## Architecture Selection

### Agent Function

**Percept Sequence → Action mapping:**

| Percept Sequence | Action |
|------------------|--------|
| [Question, Options] | EVALUATE-OPTIONS |
| [Question, Options, Analysis] | SELECT-VALID / REFUSE-INVALID |
| [Question, Options, No-Valid-Found] | PROVIDE-ALTERNATIVE |

### Ideal Agent Function

```python
function REFLECTIVE-JUDGMENT-AGENT(percept) returns action
persistent: question, options, analysis_complete, validity_scores

if percept contains new question:
    question ← percept.question
    options ← percept.options
    analysis_complete ← false
    
if not analysis_complete:
    action ← EVALUATE-OPTION-VALIDITY(question, options)
    analysis_complete ← true
else:
    if any_option_valid():
        action ← SELECT-BEST-OPTION()
    else:
        action ← REFUSE-AND-EXPLAIN() or PROVIDE-CORRECT-ANSWER()
        
return action
```

### Agent Type Selection

**Model-Based Reflex Agent** - requires internal state to:
- Track question analysis progress
- Maintain validity assessments for each option
- Store confidence levels for decisions

## Architecture Overview

### Class Diagram

```mermaid
classDiagram
    class ReflectiveJudgmentAgent {
        -ReflectiveAgentConfig config
        -str current_question
        -List[str] current_options
        -List[OptionEvaluation] evaluations
        -bool analysis_complete
        +process_question(question, options, condition) ReflectiveResponse
        -evaluate_all_options() void
        -has_valid_options() bool
        -select_best_option() ReflectiveResponse
        -refuse_and_explain() ReflectiveResponse
        -reset_state(question, options) void
    }

    class ReflectiveLLMInterface {
        <<interface>>
        +evaluate_option_validity(question, option) OptionEvaluation
        +generate_alternative_answer(question) str
        +explain_refusal(question, options) str
    }

    class ReflectiveLiteLLMAdapter {
        -OpenAI client
        -List[OptionValidator] validators
        -str model
        -float temperature
        +evaluate_option_validity(question, option) OptionEvaluation
        +generate_alternative_answer(question) str
        +explain_refusal(question, options) str
    }

    class OptionValidator {
        <<interface>>
        +validate_option(question, option) OptionEvaluation
    }

    class ArithmeticValidator {
        +validate_option(question, option) OptionEvaluation
        -extract_numbers(text) List[float]
        -compute_answer(question) float
    }

    class LogicalValidator {
        +validate_option(question, option) OptionEvaluation
        -check_logical_consistency(question, option) bool
    }

    class SafetyValidator {
        +validate_option(question, option) OptionEvaluation
        -detect_harmful_content(option) bool
    }

    class OptionEvaluation {
        +str option_text
        +bool is_valid
        +float confidence
        +str reasoning
        +str validation_type
    }

    class ReflectiveResponse {
        +str action_type
        +Optional[str] selected_option
        +str explanation
        +float confidence
        +Optional[str] alternative_answer
    }

    class ReflectiveAgentConfig {
        +ReflectiveLLMInterface llm_interface
        +float validity_threshold
        +bool enable_alternative_answers
        +bool enable_explanation
        +List[str] reflection_conditions
        +Dict[str, str] prompt_templates
    }

    ReflectiveJudgmentAgent --> ReflectiveAgentConfig
    ReflectiveJudgmentAgent --> ReflectiveResponse
    ReflectiveJudgmentAgent --> OptionEvaluation
    ReflectiveAgentConfig --> ReflectiveLLMInterface
    ReflectiveLiteLLMAdapter --|> ReflectiveLLMInterface
    ReflectiveLiteLLMAdapter --> OptionValidator
    ArithmeticValidator --|> OptionValidator
    LogicalValidator --|> OptionValidator
    SafetyValidator --|> OptionValidator
    OptionValidator --> OptionEvaluation
    ReflectiveLLMInterface --> OptionEvaluation
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Agent as ReflectiveJudgmentAgent  
    participant LLM as ReflectiveLLMInterface
    participant Validator as OptionValidator
    participant Config as ReflectiveAgentConfig

    User->>Agent: process_question(question, options, condition)
    Agent->>Agent: reset_state(question, options)
    
    Note over Agent: Evaluation Phase
    Agent->>Agent: evaluate_all_options()
    
    loop For each option
        Agent->>LLM: evaluate_option_validity(question, option)
        LLM->>Validator: validate_option(question, option)
        Validator-->>LLM: OptionEvaluation
        LLM-->>Agent: OptionEvaluation
        Agent->>Agent: store evaluation
    end
    
    Note over Agent: Judgment Phase
    Agent->>Agent: has_valid_options()
    Agent->>Config: validity_threshold
    Config-->>Agent: threshold value
    
    alt Valid options exist
        Agent->>Agent: select_best_option()
        Agent->>Agent: find highest confidence valid option
        Agent-->>User: ReflectiveResponse(action="select")
    else No valid options
        Agent->>Agent: refuse_and_explain()
        Agent->>LLM: explain_refusal(question, options)
        LLM-->>Agent: refusal explanation
        
        alt Alternative answers enabled
            Agent->>LLM: generate_alternative_answer(question)
            LLM-->>Agent: correct answer
            Agent-->>User: ReflectiveResponse(action="alternative")
        else Simple refusal
            Agent-->>User: ReflectiveResponse(action="refuse")
        end
    end
```

## Implementation

### Core Components

**1. Option Validator**
```python
class OptionValidator:
    def evaluate_validity(self, question: str, options: List[str]) -> Dict[str, float]:
        # Returns validity scores for each option
        pass
    
    def has_valid_option(self, scores: Dict[str, float]) -> bool:
        return any(score > self.validity_threshold for score in scores.values())
```

**2. Reflective Judgment Engine**
```python
class ReflectiveAgent:
    def __init__(self, validator: OptionValidator, llm_interface: LLMInterface):
        self.validator = validator
        self.llm = llm_interface
        self.confidence_threshold = 0.8
    
    def process_question(self, question: str, options: List[str]) -> Response:
        # 1. Evaluate option validity
        validity_scores = self.validator.evaluate_validity(question, options)
        
        # 2. Apply reflective judgment
        if self.validator.has_valid_option(validity_scores):
            return self._select_best_option(validity_scores)
        else:
            return self._refuse_and_explain(question, options)
```

**3. Response Types**
```python
@dataclass(frozen=True)
class ReflectiveResponse:
    action_type: str  # "select", "refuse", "alternative"
    selected_option: Optional[str]
    explanation: str
    confidence: float
    alternative_answer: Optional[str]
```

### Key Differences from Self-Consistency Agent

- **Focus**: Critical evaluation vs. multiple sampling
- **State**: Validity analysis vs. response collection  
- **Decision**: Refusal capability vs. majority voting
- **Output**: Explanation of reasoning vs. consensus answer

This agent prioritizes **critical thinking over instruction compliance**, implementing the core insight from the paper that alignment should preserve reflective judgment capabilities.