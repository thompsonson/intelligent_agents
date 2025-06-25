# Claude.md - Self-Consistency Agent Integration

## Project Context

This project is an educational system for exploring and visualizing search algorithms in maze environments. It follows a clean, modular architecture with separation of concerns and comprehensive educational features.

**Current Project Structure:**
```
maze_solver/
├── algorithms/            # Search algorithm implementations
│   ├── uninformed/        # BFS, DFS
│   └── informed/          # Greedy Best-First, A*
├── core/                  # Core functionality and data structures
│   ├── config.py         # Configuration management
│   ├── environment.py    # MazeEnvironment class
│   └── search_result.py  # SearchResult dataclass
└── visualization/         # Visualization and educational components
    └── dashboards/        # Algorithm-specific dashboards
```

**Current Agent Types:** Search algorithms (BFS, DFS, Greedy Best-First, A*)
**Design Principles:** SOLID, educational focus, comprehensive visualization, modular architecture

## Objective

Add a **Self-Consistency Chain-of-Thought Agent** to this project as a new type of intelligent agent. This agent represents a different paradigm from search algorithms - it's an LLM reasoning agent that uses multiple sampling to achieve consensus.

## Self-Consistency Agent Overview

**Purpose:** Improve LLM reasoning accuracy by generating multiple reasoning paths and selecting the most frequent answer.

**Agent Function:** `argmax_a Σ_{i=1}^m 𝟙_a(a_i = a)`

**Key Characteristics:**
- **Agent Type:** Model-based reflex agent
- **Environment:** Partially observable, stochastic, static, episodic, discrete, known, single-agent
- **Performance Measure:** Return most frequent answer
- **Complexity:** O(m) using Counter for efficient aggregation

## Technical Implementation Plan

### 1. New Directory Structure
```
intelligent_agents/
├── maze_solver/              # Existing maze-solving search agents
│   ├── algorithms/
│   ├── core/
│   └── visualization/
└── llm_agents/               # NEW: LLM-based reasoning agents
    └── self_consistency/     # Self-consistency agent implementation
        ├── __init__.py
        ├── agent.py          # SelfConsistencyAgent
        ├── domain.py         # LLMResponse, ConsensusResult
        ├── interfaces.py     # LLMInterface, LiteLLMAdapter
        ├── config.py         # AgentConfig
        └── dashboard.py      # SelfConsistencyDashboard
```

### 2. Core Components to Implement

#### Domain Objects (domain.py)
```python
@dataclass(frozen=True)
class LLMResponse:
    """Domain entity representing a single LLM response."""
    reasoning: str
    answer: str
    confidence: Optional[float] = None

@dataclass(frozen=True)
class ConsensusResult:
    """Value object for aggregation results."""
    final_answer: str
    vote_count: int
    total_responses: int
    answer_distribution: Dict[str, int]
    confidence: float
```

#### LLM Interface (interfaces.py)
```python
class LLMInterface(ABC):
    """Abstract interface for LLM interactions."""
    
    @abstractmethod
    def generate_llm_response(self, prompt: str, question: str) -> LLMResponse:
        """Generate a single LLM response for the given question."""
        pass

class LiteLLMAdapter(LLMInterface):
    """LiteLLM implementation using OpenAI client for Docker container."""
    
    def __init__(self, 
                 model: Optional[str] = None,
                 temperature: Optional[float] = None,
                 base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 **kwargs):
        """Initialize with environment variable defaults:
        - LLM_MODEL (default: "gpt-3.5-turbo")
        - LLM_TEMPERATURE (default: "0.7")
        - LLM_BASE_URL (default: "http://localhost:4000")
        - LLM_API_KEY (default: "sk-dummy")
        """
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
```

#### Agent Configuration (config.py)
```python
@dataclass
class AgentConfig:
    """Configuration for self-consistency agent."""
    llm_interface: LLMInterface
    target_responses: int = 5
    prompt_template: str = ""
```

#### Main Agent (agent.py)
```python
class SelfConsistencyAgent:
    """Main agent implementing self-consistency CoT reasoning."""
    
    def __init__(self, config: AgentConfig, question: str):
        """Initialize agent with configuration and question."""
        self._config = config
        self._question = question
        self._llm_responses: List[LLMResponse] = []
    
    def process_question(self) -> ConsensusResult:
        """Process the question and return consensus result."""
        # Implementation with O(m) complexity
        pass
    
    def _perform_argmax(self) -> str:
        """Private method to perform majority vote aggregation."""
        # Extract answers - O(m) linear pass through responses
        answers = [response.answer for response in self._llm_responses]
        # Counter uses O(1) hash operations for counting, avoiding O(m^2) nested loops
        counts = Counter(answers)
        answer, count = counts.most_common(1)[0]
        return answer
```

### 3. Integration with Project Architecture

#### Separate Domain Approach
- LLM agents operate independently from maze-solving algorithms
- Self-contained implementation with own domain objects and interfaces
- Educational visualization follows similar patterns to existing dashboards
- Maintains project's educational focus and comprehensive documentation

#### Configuration Management
- Independent configuration system specific to LLM agents
- `AgentConfig` class handles LLM-specific parameters
- Follows existing patterns for educational parameter management

#### Educational Features
- `SelfConsistencyDashboard` follows existing dashboard patterns
- Implement step-by-step visualization of consensus building
- Show LLM response collection and aggregation process
- Demonstrate O(m) complexity optimization

### 4. Educational Dashboard Features

```python
class SelfConsistencyDashboard:
    """Educational dashboard for self-consistency agent."""
    
    def visualize_consensus_building(self, responses: List[LLMResponse]):
        """Show how consensus emerges through multiple responses."""
        # Visualize response collection and frequency counting
        pass
    
    def show_complexity_analysis(self):
        """Demonstrate O(m) vs O(m²) complexity difference."""
        # Educational visualization of algorithmic complexity
        pass
    
    def animate_aggregation_process(self, consensus_result: ConsensusResult):
        """Animate the argmax process."""
        # Step-by-step majority vote visualization
        pass
```

## Dependencies to Add

```toml
# Add to existing requirements
openai = "^1.0.0"   # For communicating with LiteLLM Docker container
```

## Testing Strategy

**Testing Framework:** pytest

### Domain Objects Tests
1. **LLMResponse validation** - Test immutability and basic creation
2. **ConsensusResult validation** - Test confidence calculation, immutability

### Agent Core Logic Tests  
3. **Majority vote accuracy** - Test `_perform_argmax()` with known inputs
4. **Unanimous consensus** - All responses same answer
5. **Split decision** - 3-2 vote split
6. **Tie handling** - 2-2 tie (what should happen?)
7. **O(m) complexity** - Performance test with large m values

### Integration Tests
8. **Mock LLM responses** - Test full `process_question()` flow
9. **Different response counts** - Test with m=1, m=5, m=10
10. **Parsing edge cases** - Empty responses, malformed answers

### Configuration Tests
11. **Environment variables** - Test LiteLLMAdapter defaults
12. **AgentConfig validation** - Invalid configurations

**Key Testing Approach:**
- Mock the LLM interface so tests are deterministic and don't require actual API calls
- Use pytest fixtures for common test data
- Test both happy path and edge cases
- Performance tests for O(m) complexity validation

## Blog Post Integration

This implementation will serve as the practical demonstration for the blog post:
**"[IA Series 7/n] Building a Self-Consistency Agent: From PEAS Analysis to Production Code"**

The code should demonstrate:
- PEAS analysis in practice
- Environment property analysis
- Agent type selection reasoning
- Mathematical formulation implementation
- Software engineering principles (SOLID, DDD)
- O(m) complexity optimization

## Success Criteria

1. **Functional Requirements:**
   - ✅ Agent correctly implements self-consistency algorithm
   - ✅ O(m) performance with Counter optimization
   - ✅ Clean integration with existing architecture
   - ✅ Comprehensive test coverage

2. **Educational Requirements:**
   - ✅ Clear visualization of consensus building
   - ✅ Interactive dashboard following existing patterns
   - ✅ Step-by-step explanation of majority vote
   - ✅ Complexity analysis demonstration

3. **Software Quality:**
   - ✅ SOLID principles implementation
   - ✅ Domain-driven design with proper value objects
   - ✅ Consistent with existing code style
   - ✅ Comprehensive documentation

## Implementation Notes

- **Synchronous Implementation:** Uses sync OpenAI client for simplicity
- **Environment Configuration:** All LLM settings default to environment variables
- **Docker Integration:** OpenAI client communicates with LiteLLM Docker container
- **Follow Patterns:** Maintain consistency with existing search algorithm patterns
- **Educational Focus:** Every component should have educational value
- **Extensibility:** Design for future addition of other reasoning agents
- **Testing:** Mock LLM responses for reliable testing

## Questions for Implementation

1. ✅ **Directory Structure:** Created separate `llm_agents/` directory alongside `maze_solver/`
2. ✅ **LLM Abstraction:** Environment-driven configuration with OpenAI client
3. ✅ **Async Processing:** Started with synchronous implementation for simplicity
4. **Error Handling:** Basic implementation, can be enhanced later
5. **Educational Features:** Dashboard and visualization still to be implemented

## Related Files

- **Blog Outline:** See existing blog post outline artifact
- **Current Architecture:** Review `README.md` and `class_diagram.md`
- **Code Patterns:** Study existing algorithm implementations for consistency