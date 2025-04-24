# Greedy Best-First Search Algorithm

## Greedy Best-First Algorithm in Mathematical Notation

**Input:** Graph $G = (V, E)$, start vertex $s$, goal vertex $g$, heuristic function $h$

**Output:** Path from $s$ to $g$ if exists, otherwise ∅

**Algorithm:**
1. Initialize priority queue $O ← \{s\}$ with priority $h(s)$
2. Initialize closed set $C ← ∅$
3. Initialize parent map $π[s] ← null$
4. While $O ≠ ∅$:
   - $v ← extract_{min}(O)$ (node with minimum $h$-value)
   - Add $v$ to closed set $C$
   - If $v = g$:
     - Return path by following $π$ from $g$ to $s$
   - For each $u \in \text{Adj}(v)$:
     - If $u \in C$:
       - Continue to next neighbor
     - If $u \notin O$:
       - $π[u] ← v$
       - Add $u$ to $O$ with priority $h(u, g)$
5. Return ∅ (no path exists)

where:
- $h(n)$ is the heuristic estimate from node $n$ to goal
- $V$ are the Vertices/Nodes
- $E$ are the Edges/Connections
- $π$ contains the connections for path reconstruction

The solution (if there is one) is found by reconstructing the path from the goal to the start:

- Start at $t$
- Follow the parent connections: $t → π[t] → π[π[t]] → ...$ until $s$ is reached
- Reverse this sequence to get the complete path from $s$ to $t$

## Greedy Best-First Algorithm in Python

```python
# Initialize data structures
open_set = [(h(start, goal), start)]  # Priority queue: (h, node)
open_set_dict = {start: h(start, goal)}  # For quick lookups
closed_set = set()
parent = {start: None}

while open_set:
    # Get node with lowest h-value
    open_set.sort(key=lambda x: x[0])
    h_value, current = open_set.pop(0)
    del open_set_dict[current]

    # Add to closed set
    closed_set.add(current)

    # Check if goal reached
    if current == goal:
        return reconstruct_path(parent, start, goal)

    # Process all neighbors
    for neighbor in graph[current]:
        if neighbor in closed_set or neighbor in open_set_dict:
            continue

        # Add to frontier with heuristic as priority
        h_value = heuristic(neighbor, goal)
        parent[neighbor] = current
        open_set.append((h_value, neighbor))
        open_set_dict[neighbor] = h_value

# No path found
return None
```

## Greedy Best-First Properties

### Key Characteristic

- **Pure Heuristic Guidance**: Greedy Best-First Search always expands the node that appears closest to the goal according to the heuristic function, regardless of the path cost so far.

### Analysis

- **Completeness**: Not guaranteed - can get stuck in loops on infinite graphs
- **Time Complexity**: $O(b^m)$ where $b$ is the branching factor and $m$ is the maximum depth of the search space
- **Space Complexity**: $O(b^m)$ - must store all generated nodes
- **Optimality**: Not optimal - may find a path but not necessarily the shortest one

In maze solving, Greedy Best-First Search often finds paths more quickly than BFS, but these paths may contain unnecessary detours compared to the optimal path.