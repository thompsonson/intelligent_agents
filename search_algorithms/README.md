# Search Algorithms and Intelligent Agents

## Introduction

Search Algorithms are a key part of how Intelligent Agents learn and navigate their environment. In these examples, I'm using Search to find a route through a maze - the agent will determine a sequence of actions to achieve its goal of reaching the end point.

The purpose of this document is to dive into the details of four search algorithms and show their tradeoffs in a simple environment. I've implemented two categories: Uninformed and Informed Search. For the Informed Algorithms, I've included heuristics and cost calculations to guide the search process.

These are purely Symbolic agents - but what does "Symbolic" actually mean?

In this context, Symbolic means that the agent uses explicit rules and symbols to represent knowledge and perform reasoning. Reasoning in this context is the ability to take rational actions, to act as a [rational agent](https://en.wikipedia.org/wiki/Rational_agent).

The agents here use clear, human-readable representations (like coordinates in a grid) and follow well-defined logical steps to find the end of the maze. The algorithms manipulate these symbols according to formal rules - there's no statistical learning or pattern recognition involved. Everything is explicit, transparent, and based on logical operations.

The key characteristics of my symbolic implementations:
- They use explicit representations of the maze as a graph
- They follow clear, deterministic rules for exploration
- The decision-making process can be traced step-by-step
- The solutions are guaranteed (when they exist) rather than probabilistic

In contrast, neural approaches might learn to navigate mazes through experience, without explicit programming of the navigation rules.

See [here](https://github.com/thompsonson/q-learning) for a Basic Q-Learning Statistical/Reinforcement Learning Agent.

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->
## Table of contents

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [Uninformed Search Algorithms](#uninformed-search-algorithms)
   * [Available Uninformed Search Algorithms](#available-uninformed-search-algorithms)
   * [Algorithm Comparison](#algorithm-comparison)
   * [Implementation Notes](#implementation-notes)
- [Informed Search Algorithms](#informed-search-algorithms)
   * [Available Informed Search Algorithms](#available-informed-search-algorithms)
   * [Maze Solver Heuristics](#maze-solver-heuristics)
   * [Step Cost Calculation](#step-cost-calculation)
   * [Algorithm Comparison](#algorithm-comparison-1)
- [Other Search Algorithms (not (yet 🤞) implemented in the current codebase)](#other-search-algorithms-not-yet-implemented-in-the-current-codebase)

<!-- TOC end -->


<!-- TOC --><a name="uninformed-search-algorithms"></a>
## Uninformed Search Algorithms

Uninformed search algorithms (also called blind search algorithms) operate without using domain-specific knowledge about the problem beyond what is provided in the problem definition. They systematically explore the search space without any information about how close they are to the goal.

<!-- TOC --><a name="available-uninformed-search-algorithms"></a>
### Available Uninformed Search Algorithms

- [Breadth-First Search (BFS)](breadth_first_search.md)
- [Depth-First Search (DFS)](depth_first_search.md)

<!-- TOC --><a name="algorithm-comparison"></a>
### Algorithm Comparison

| Feature | Breadth-First Search | Depth-First Search |
|---------|---------------------|-------------------|
| **Data Structure** | FIFO Queue | LIFO Stack |
| **Strategy** | Explores all nodes at present depth before moving to next level | Explores as far as possible along each branch before backtracking |
| **Completeness** | Yes (finds solution if one exists in finite graphs) | Yes (for finite graphs) |
| **Time Complexity** | O(V + E) | O(V + E) |
| **Space Complexity** | O(V) - must store all vertices at a level | O(h) - h is maximum depth of search tree |
| **Optimality** | Optimal for unweighted graphs (finds shortest path) | Not optimal (may not find shortest path) |
| **Memory Usage** | Higher (stores all nodes at current level) | Lower (stores only nodes on current path) |
| **Best Use Cases** | Finding shortest paths, exploring graphs with shallow solutions | Memory-constrained environments, graphs with deep solutions |

<!-- TOC --><a name="implementation-notes"></a>
### Implementation Notes

There is an abstract base class for uninformed searches.

This is to reduce code duplication. As the BFS and DFS algorithms are identical except for the data storage and next node retrieval, the code is the same.

The code for the base class is here:

`maze_solver/algorithms/uninformed/base.py`

Each algorithm implements the following key methods to accommodate the differences in algorithms:
- `__init__`: Sets the name of the frontier (queue/stack)
- `_initialize_frontier`: Sets up the data structure (queue/stack)
- `_get_next_node`: Retrieves the next node based on strategy (FIFO/LIFO)


<!-- TOC --><a name="informed-search-algorithms"></a>
## Informed Search Algorithms

Informed search algorithms use domain-specific knowledge (heuristics) to guide exploration toward the goal more efficiently. They leverage additional information about how close a state might be to the goal.

One way to frame the difference is that an uninformed search is like being blindfolded in a maze and feeling your way around, whereas an informed search is one where you can jump up and see the maze's exit sign, you (sort of) know how far away you are.

Clearly this is a metaphor, in practice agents work on numbers and need measurements rather than visual cues, so we need to measure the distiances. For Greedy Best First Search we need the estimated distance to the goal and for A* we also need the cost of the distance we have travelled.

<!-- TOC --><a name="available-informed-search-algorithms"></a>
### Available Informed Search Algorithms

- [Greedy Best-First Search](greedy_best_first_search.md)
- [A* Search](a_star_search.md)


<!-- TOC --><a name="maze-solver-heuristics"></a>
### Maze Solver Heuristics

So this information needs to be available to the agent and the best place for it is in the Maze Environment. This is not complex for the simple two dimensional mazes generated by the Maze Environment class.

The `maze_solver/core/environment.py` file has been edited to include the following distance metrics as heuristics:

<!-- TOC --><a name="manhattan-distance"></a>
#### Manhattan Distance

The [Manhattan Distance (also known as Taxicab Geometry)](https://en.wikipedia.org/wiki/Taxicab_geometry) measures the sum of the absolute differences between two points' coordinates. In a grid-based maze, this represents the minimum number of horizontal and vertical moves needed to reach the goal, assuming no walls.

```python
def calculate_manhattan_distance(self, state: Tuple[int, int], goal: Tuple[int, int]) -> int:
    """Calculate Manhattan distance heuristic from state to goal."""
    return abs(state[0] - goal[0]) + abs(state[1] - goal[1])
```

<!-- TOC --><a name="euclidean-distance"></a>
#### Euclidean Distance

The Euclidean distance measures the straight-line or "as the crow flies" distance between two points.

```python
def calculate_euclidean_distance(self, state: Tuple[int, int], goal: Tuple[int, int]) -> float:
    """Calculate Euclidean distance heuristic from state to goal."""
    return ((state[0] - goal[0]) ** 2 + (state[1] - goal[1]) ** 2) ** 0.5
```

<!-- TOC --><a name="why-manhattan-is-often-preferred"></a>
#### Why Manhattan is Often Preferred

While both heuristics can work, Manhattan distance is generally preferred for grid-based pathfinding because:

1. It matches the movement constraints in a grid where diagonal movement is not allowed.
2. It maintains consistency with step costs (each move costs 1 unit).
3. It's an admissible heuristic for grid movement. It never overestimates the true cost to the goal.
4. It's computationally simpler (no square roots).

For A* search in particular, using Manhattan distance as the heuristic ensures that the algorithm remains consistent when it adds the path cost (also measured in grid steps) to the estimated distance to the goal.

<!-- TOC --><a name="step-cost-calculation"></a>
### Step Cost Calculation

The cost of moving between adjacent cells is defined as follows:

```python
def get_step_cost(self, state1: Tuple[int, int], state2: Tuple[int, int]) -> int:
    """Calculate cost of moving from state1 to state2."""
    # For uniform cost in grid-based maze, return 1
    return 1
```

This unified cost model means each step has the same weight, which aligns perfectly with Manhattan distance calculations in a grid-based environment.

<!-- TOC --><a name="making-the-maze-fun-and-costly"></a>
#### Making the Maze fun and costly

This implmentation uses a uniform cost of 1, which doesn't really add value whilst adding more code. To highlight why I think it's worthwhile keeping in mind, imagine the maze as an obstacle course, especially valuable if there are more than one route to the end goal. If there is an obstacle at a particular point it would cost more to traverse.

An example would be

```python
# Example: Higher cost for muddy terrain
def get_step_cost(self, state1: Tuple[int, int], state2: Tuple[int, int]) -> int:
    if state2 in self.muddy_terrain:
        return 5  # 5x cost to traverse mud
    return 1  # Normal terrain
```

Note: this would only impact the A* Search, the Greedy Best First Search is unaware of costs.


<!-- TOC --><a name="algorithm-comparison-1"></a>
### Algorithm Comparison

<!-- TOC --><a name="algorithmic-complexity-variables"></a>
#### Algorithmic Complexity Variables

First the notation used:

| Variable | Definition | Significance |
|----------|------------|-------------|
| **b** | Branching factor | Average number of successors (children) per node; represents available choices at each decision point |
| **d** | Shallowest solution depth | Length of the shortest path from start to goal |
| **m** | Maximum depth | Maximum depth of the search tree/graph (potentially infinite in unbounded graphs) |
| **C*** | Optimal solution cost | Total path cost from start to goal along the optimal path |
| **ε** | Minimum edge cost | Smallest step cost in the graph |

The ratio **C*/ε** represents the maximum number of steps in any optimal solution, which is particularly relevant for understanding the performance bounds of algorithms like Uniform-Cost Search.

These variables help quantify the tradeoffs between different search algorithms in terms of time efficiency, space requirements, completeness, and optimality guarantees.

<!-- TOC --><a name="table-of-comparison"></a>
#### Table of comparison

| Feature | Greedy Best-First Search | A* Search |
|---------|--------------------------|-----------|
| **Decision Function** | $f(n) = h(n)$ | $f(n) = g(n) + h(n)$ |
| **Strategy** | Expand node closest to goal according to heuristic | Balance path cost so far and estimated cost to goal |
| **Completeness** | Not guaranteed | Yes (with finite, non-negative edge costs) |
| **Time Complexity** | O(b^m) worst case | O(b^d) worst case, but better in practice |
| **Space Complexity** | O(b^m) | O(b^d) |
| **Optimality** | Not optimal | Optimal if heuristic is admissible |
| **Memory Usage** | High | High |
| **Best Use Cases** | Quick approximate solutions | Finding optimal paths when good heuristic available |
| **Key Advantage** | Often finds decent solutions quickly | Guaranteed to find shortest path with admissible heuristic |
| **Key Weakness** | Can make poor choices with misleading heuristics | Requires more memory than Greedy |

<!-- TOC --><a name="other-search-algorithms-not-yet-implemented-in-the-current-codebase"></a>
## Other Search Algorithms (not (yet 🤞) implemented in the current codebase)

This is the "if I had more time chapter" :)

We've covered four fundamental search algorithms (BFS, DFS, Greedy Best-First, and A*), there are several other important search algorithms worth exploring:

- **Uniform-Cost Search**: An uninformed algorithm that expands nodes in order of their path cost, guaranteeing optimality even with varying edge costs. Think of it as A* without a heuristic function.

- **Iterative Deepening Search**: Combines the space efficiency of DFS with the completeness of BFS by running a series of depth-limited searches with increasing depth limits.

- **Depth-Limited Search**: A variation of DFS that stops exploring when it reaches a predefined depth limit, preventing infinite loops in infinite graphs.

- **Bidirectional Search**: Searches simultaneously from both the start and goal, dramatically reducing the search space by meeting in the middle.

- **Beam Search**: A modification of BFS that only keeps a fixed number of the most promising nodes at each depth, trading optimality for efficiency.

- **Jump Point Search**: An optimization of A* for uniform-cost grid maps that skips over "obvious" paths, dramatically improving performance in many scenarios.


<!-- TOC --><a name="full-table-of-comparison"></a>
### Full table of comparison

The table below summarizes the key properties of several search algorithms (see above for the notation):

| Algorithm | Complete? | Optimal? | Time Complexity | Space Complexity |
|-----------|-----------|----------|----------------|------------------|
| Breadth-First | Yes¹ | Yes² | O(b^d) | O(b^d) |
| Uniform-Cost | Yes¹ | Yes | O(b^[1+C*/ε]) | O(b^[1+C*/ε]) |
| Depth-First | No | No | O(b^m) | O(bm) |
| Depth-Limited | No | No | O(b^l) | O(bl) |
| Iterative Deepening | Yes¹ | Yes² | O(b^d) | O(bd) |
| Bidirectional | Yes¹ | Yes² | O(b^(d/2)) | O(b^(d/2)) |
| Greedy Best-First | No | No | O(b^m) | O(b^m) |
| A* | Yes¹ | Yes³ | O(b^d) | O(b^d) |

¹Complete if the branching factor b is finite
²Optimal for unweighted graphs
³Optimal if the heuristic is admissible

These algorithms represent different tradeoffs between completeness, optimality, time efficiency, and space efficiency. The best choice depends on your specific problem characteristics and constraints.