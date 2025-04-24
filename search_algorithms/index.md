# Search Algorithms

## Uninformed Search Algorithms

Uninformed search algorithms (also called blind search algorithms) operate without using domain-specific knowledge about the problem beyond what is provided in the problem definition. They systematically explore the search space without any information about how close they are to the goal.

### Available Algorithms

- [Breadth-First Search (BFS)](breadth_first_search.md)
- [Depth-First Search (DFS)](depth_first_search.md)

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

### Implementation Notes

There is an abstract base class for uninformed searches.

This is to reduce code duplication. As the BFS and DFS algorithms are identical except for the data storage and next node retrieval, the code is the same.

The code for the base class is here:

`maze_solver/algorithms/uninformed/base.py`

Each algorithm implements the following key methods to accomadte the differences in algorithms:
- `__init__`: Sets the name of the frontier (queue/stack)
- `_initialize_frontier`: Sets up the data structure (queue/stack)
- `_get_next_node`: Retrieves the next node based on strategy (FIFO/LIFO)

