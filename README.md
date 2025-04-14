# Maze Solving Agents System Documentation

## Environment Setup Details

```bash
# Install uv in its own global location (using pipx)
pipx install uv
# Create a virtual environment
uv venv
# Activate the environment
source .venv/bin/activate
# Install the Jupyter notebook packages
uv pip install ipykernel jupyter notebook
# Install required packages
uv pip install networkx matplotlib pandas mazelib imageio
```

## Class Overview

### Config

```python
@dataclass
class Config:
    """Configuration parameters for maze generation and search"""
    # Maze parameters
    maze_size: int = 5  # Grid dimensions (nxn)
    maze_id: Optional[int] = None  # Seed for reproducible maze generation
    
    # Visualization parameters
    visualization_delay: float = 0.5  # Delay between search steps
    show_exploration: bool = True  # Whether to visualize exploration
    
    # Search parameters
    max_steps: Optional[int] = None  # Maximum steps for search (None for unlimited)
```

### MazeEnvironment

```python
class MazeEnvironment:
    """Handles maze generation, state management and visualization"""
    
    Properties:
    - grid: np.array  # Binary maze representation (0=path, 1=wall)
    - start: tuple  # Starting position (typically (1,1))
    - end: tuple  # Goal position (typically (height-2, width-2))
    - optimal_path: List[Tuple]  # Shortest solution path
    - optimal_path_length: int  # Length of shortest path
    - graph: Dict  # Graph representation for search algorithms
    
    Methods:
    - generate()  # Creates new maze using Sidewinder algorithm
    - is_valid_move(state)  # Checks if move is legal
    - visualize(path, visited, show_optimal, save_path)  # Displays/saves maze visualization
    - get_minimum_steps()  # Returns optimal path length
```

### SearchResult

```python
@dataclass
class SearchResult:
    """Enhanced container for search algorithm results with educational metrics"""
    
    Properties:
    - path: List[Tuple]  # Solution path from start to goal
    - visited: List[Tuple]  # List of visited nodes 
    - success: bool  # Whether the search found a path
    - steps: int  # Number of algorithm steps executed
    - execution_time: float  # Time taken for the search
    - exploration_history: List  # History of algorithm state (for visualization)
    - node_discovery: Dict  # When each node was discovered
    - node_expansion: Dict  # When each node was expanded
    
    Methods:
    - to_dict()  # Convert results to dictionary for analysis
    - generate_educational_report()  # Generate educational report about the search
```

### SearchAlgorithmBase

```python
class SearchAlgorithmBase(ABC):
    """Abstract base class for search algorithms"""
    
    Properties:
    - env: MazeEnvironment  # Reference to maze environment
    - config: Config  # Configuration parameters
    - name: str  # Algorithm name
    
    Methods:
    - search(start, goal)  # Search for path (to be implemented by subclasses)
    - run(start, goal)  # Run with timing and error handling
    - visualize_search(result, delay)  # Visualize the search process
```

### BreadthFirstSearch

```python
class BreadthFirstSearch(SearchAlgorithmBase):
    """Breadth-First Search implementation with enhanced educational output"""
    
    Methods:
    - search(start, goal)  # Perform BFS with educational tracking
    - _reconstruct_path(parent, start, goal)  # Reconstruct path from parent data
    - visualize_search(result, delay)  # Enhanced visualization with educational commentary
```

### MazeSearchVisualizer

```python
class MazeSearchVisualizer:
    """Handles visualization of search algorithms in mazes"""
    
    Methods:
    - visualize_search_step_by_step(algorithm_name, delay)  # Animated visualization
    - compare_algorithms(algorithm_names)  # Runs and compares multiple algorithms
    - visualize_comparison(comparison_df)  # Creates comparison charts
```

### MazeExperiments

```python
class MazeExperiments:
    """Manages experiments with maze search algorithms"""
    
    Methods:
    - run_maze_size_experiment(algorithm_classes, maze_sizes, iterations)  # Tests performance across maze sizes
    - visualize_maze_size_experiment(df)  # Creates visualizations of experiment results
```

### BFSEducationalDashboard

```python
class BFSEducationalDashboard:
    """Interactive dashboard for teaching BFS algorithm concepts"""
    
    Methods:
    - visualize_step(step_idx)  # Display a single step of the BFS algorithm
    - create_gif(filename, fps, dpi)  # Create a GIF animation from BFS steps
    - animate_bfs_on_graph(output_file, fps, size)  # Animate BFS algorithm on graph representation
    - visualize_maze_graph(highlight_path)  # Visualize maze as a graph
    - run_animation(delay)  # Run the full BFS animation with explanations
    - create_interactive_widget()  # Create an interactive widget to step through BFS
```

## Example Usage

### Basic Example

```python
# Create a maze environment
config = Config(maze_size=10, visualization_delay=0.3)
env = MazeEnvironment(config)

# Create a BFS algorithm
bfs = BreadthFirstSearch(env)

# Run the search
result = bfs.run()

# Print the results
print(result)

# Visualize the final state
env.visualize(path=result.path, visited=set(result.visited))
```

### Step-by-Step Visualization

```python
config = Config(maze_size=5, show_exploration=True)
env = MazeEnvironment(config)

# Create an instance of the search algorithm
bfs = BreadthFirstSearch(env)

# Run and visualize
result = bfs.run()
bfs.visualize_search(result)
```

### Compare Multiple Algorithms

```python
config = Config(maze_size=10)
env = MazeEnvironment(config)

# Create algorithm instances
algorithms = [BreadthFirstSearch(env)]
# Add other algorithms as they are implemented

# Create visualizer
visualizer = MazeSearchVisualizer(env, algorithms)

# Run comparison
results_df = visualizer.compare_algorithms()

# Visualize comparison
visualizer.visualize_comparison(results_df)
```

### Run Experiments

```python
# Create experiment manager
experiments = MazeExperiments()

# Run experiments for different maze sizes
maze_sizes = [5, 10, 15, 20, 25]
algorithm_classes = [BreadthFirstSearch]

# Run experiments
results = experiments.run_maze_size_experiment(
    algorithm_classes, 
    maze_sizes, 
    iterations=3
)

# Visualize results
experiments.visualize_maze_size_experiment(results)
```

### Educational Dashboard

```python
config = Config(maze_size=5, show_exploration=True, visualization_delay=0.8)
env = MazeEnvironment(config)

# Create enhanced BFS instance
bfs = BreadthFirstSearch(env)

# Run the search and collect educational results
result = bfs.run()

# Create an educational dashboard
dashboard = BFSEducationalDashboard(env, result)

# Visualize a specific step
dashboard.visualize_step(3)

# Create animations
dashboard.create_gif(fps=1.5)
dashboard.animate_bfs_on_graph(fps=3, size=6)
```

## Example Output

### BFS Search Visualization

When running the step-by-step visualization, you'll see an animated display of the BFS algorithm in action. Each step shows:

- The current maze state with color-coded cells:
  - White: Unvisited path cells
  - Yellow: Visited cells
  - Blue: Start position
  - Purple: Goal position
  - Green: Current path
  - Lightblue: Frontier queue
  - Red: Currently expanded node

- Educational information:
  - Current step number
  - Expanded node coordinates
  - Neighbors discovered
  - Queue state before and after expansion
  - Detailed explanation of BFS concepts

### Results and Metrics

The `SearchResult` provides comprehensive metrics about the search:

```
✅ Search succeeded in 14 steps (0.003s)
📏 Path length: 9 nodes
🔍 Visited nodes: 15 nodes (1.07 nodes/step)
⚙️ Efficiency: 60.0% (path nodes / visited nodes)
🌲 Average branching factor: 1.50 neighbors/node
⏱️ Average time per step: 0.21 ms
```

### Educational Dashboard

The BFS Educational Dashboard provides:

1. Interactive step-by-step visualization
2. Algorithm state visualization with queue operations
3. Educational explanations of BFS concepts
4. GIF animations of the search process
5. Graph representation visualization

### Experiment Results

Experiment results are visualized with multiple charts:

1. Success Rate by Maze Size
2. Avg. Visited Nodes by Maze Size
3. Avg. Execution Time by Maze Size
4. Avg. Path Optimality by Maze Size

These visualizations help understand how BFS performance scales with different maze sizes.