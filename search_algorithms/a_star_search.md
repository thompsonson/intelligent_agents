# A* Search Algorithm

## A* Algorithm in Mathematical Notation

**Input:** Graph $G = (V, E)$, start vertex $s$, goal vertex $g$, heuristic function $h$

**Output:** Shortest path from $s$ to $g$ if exists, otherwise ∅

**Algorithm:**
1. Initialize priority queue (open set) $O ← \{s\}$ with $f(s) = g(s) + h(s)$, where $g(s) = 0$
2. Initialize closed set $C ← ∅$
3. Initialize parent map $π[s] ← null$
4. Initialize cost map $g[s] ← 0$ (cost from start to node)
5. While $O ≠ ∅$:
   - $v ← extract_{min}(O)$ (node with minimum $f$-value)
   - Add $v$ to closed set $C$
   - If $v = g$:
     - Return path by following $π$ from $g$ to $s$
   - For each $u \in \text{Adj}(v)$:
     - If $u \in C$:
       - Continue to next neighbor
     - $tentative_g ← g[v] + cost(v, u)$
     - If $u \notin O$ OR $tentative_g < g[u]$:
       - $π[u] ← v$
       - $g[u] ← tentative_g$
       - $f[u] ← g[u] + h(u, g)$
       - If $u \notin O$:
         - Add $u$ to $O$ with priority $f[u]$
       - Else:
         - Update $u$ in $O$ with new priority $f[u]$
6. Return ∅ (no path exists)

where:
- $f(n) = g(n) + h(n)$ is the estimated total cost
- $g(n)$ is the cost from start to node $n$
- $h(n)$ is the heuristic estimate from $n$ to goal
- $V$ are the Vertices/Nodes
- $E$ are the Edges/Connections
- $π$ contains the connections for path reconstruction

The solution (if there is one) is found by reconstructing the path from the goal to the start:

- Start at $t$
- Follow the parent connections: $t → π[t] → π[π[t]] → ...$ until $s$ is reached
- Reverse this sequence to get the complete path from $s$ to $t$

## A* Algorithm in Python

```python
# Initialize data structures
open_set = [(h(start, goal), 0, start)]  # Priority queue: (f, g, node)
open_set_dict = {start: h(start, goal)}  # For quick lookups: node -> f-value
closed_set = set()
g_value = {start: 0}  # Cost from start to node
parent = {start: None}

while open_set:
    # Get node with lowest f-value
    open_set.sort(key=lambda x: (x[0], -x[1]))  # Sort by f, break ties with higher g
    f, g, current = open_set.pop(0)
    del open_set_dict[current]

    # Add to closed set
    closed_set.add(current)

    # Check if goal reached
    if current == goal:
        return reconstruct_path(parent, start, goal)

    # Process all neighbors
    for neighbor in graph[current]:
        if neighbor in closed_set:
            continue

        # Calculate new path cost
        tentative_g = g_value[current] + cost(current, neighbor)

        # If we found a better path or this is a new node
        if neighbor not in open_set_dict or tentative_g < g_value.get(neighbor, float('inf')):
            # Update parent and cost
            parent[neighbor] = current
            g_value[neighbor] = tentative_g

            # Calculate f-value
            h_value = heuristic(neighbor, goal)
            f_value = tentative_g + h_value

            # Update priority queue
            if neighbor in open_set_dict:
                # Remove old entry
                open_set = [(f, g, n) for f, g, n in open_set if n != neighbor]

            # Add with new values
            open_set.append((f_value, tentative_g, neighbor))
            open_set_dict[neighbor] = f_value

# No path found
return None
```

## A* Properties

### Key Characteristic

- **Best-First with Path Cost**: A* evaluates nodes using the sum of the cost to reach the node (g) and the estimated cost to the goal (h). This combines the benefits of Dijkstra's algorithm and Greedy Best-First Search.

### Analysis

- **Completeness**: Yes - guaranteed to find a solution if one exists
- **Time Complexity**: $O(b^d)$ where $b$ is the branching factor and $d$ is the depth of the solution, but often performs much better in practice
- **Space Complexity**: $O(b^d)$ - must store all generated nodes
- **Optimality**: Optimal if the heuristic function is admissible (never overestimates the true cost)

### Heuristic Properties

- **Admissible Heuristic**: Never overestimates the true cost to the goal (e.g., Manhattan distance for grid maps)
- **Consistent Heuristic**: For any node $n$ and successor $n'$, $h(n) ≤ cost(n, n') + h(n')$
- **Dominance**: If $h_1(n) ≥ h_2(n)$ for all $n$, then $h_1$ dominates $h_2$ and is more efficient

### Note

A* is widely used in pathfinding for games, robotics, and any domain where:
- The shortest path is required
- A good heuristic can be defined
- The state space is too large for exhaustive search

In maze solving, A* finds the optimal path while typically expanding fewer nodes than BFS, making it more efficient when a good heuristic is available.