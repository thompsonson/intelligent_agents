# Depth-first Search (DFS)

## DFS Algorithm in Mathematical Notation

**Input:** Graph $G = (V, E)$, start vertex $s$, goal vertex $g$

**Output:** Path from $s$ to $g$ if exists, otherwise ∅

**Algorithm:**
1. Initialize stack $S ← \{s\}$
2. Initialize visited set $V_{visited} ← \{s\}$
3. Initialize parent map $π[s] ← null$
4. While $S ≠ ∅$:
   - $v ← \text{pop}(S)$
   - If $v = g$:
     - Return path by following $π$ from $g$ to $s$
   - For each $u \in \text{Adj}(v)$:
     - If $u \notin V_{visited}$:
       - $V_{visited} ← V_{visited} \cup \{u\}$
       - $π[u] ← v$
       - $\text{push}(S, u)$
5. Return ∅ (no path exists)

where:
- $V$ are the Vertices/Nodes
- $E$ are the Edges/Connections
- $π$ contains the connections
- Adj(v) represents the adjacent vertices/nodes

The solution (if there is one) is found by reconstructing the path from the goal to the start:

- Start at $t$
- Follow the parent connections: $t → π[t] → π[π[t]] → ...$ until $s$ is reached
- Reverse this sequence to get the complete path from $s$ to $t$

## DFS Algorithm in Python

```python
# Initialize stack with start node S ← {s}
stack = [start]

# Track visited nodes and parent pointers for path reconstruction
visited = set([start]) # V_visited ← {s}
parent = {start: None} # $π[s] ← null

while stack:
    # Pop next node from stack
    current_node = stack.pop()

    # Check if reached goal
    if current_node == goal: # v=g
        # Reconstruct and return path
        return reconstruct_path(parent, start, goal) # t → π[t] → π[π[t]] → ...

    # Process all unvisited neighbors
    for neighbor in graph[current_node]: # For each u in Adj(v)
        if neighbor not in visited:
            visited.add(neighbor) # V_visited ←V_visited ∪ {u}
            parent[neighbor] = current_node # π[u] ← v
            stack.append(neighbor) # push(S,u)

# No path found
return None
```

## DFS Properties

### Key Characteristic

- **LIFO Stack**: DFS processes vertices by exploring as far as possible along each branch before backtracking, which guarantees depth-first exploration

### Analysis

- **Completeness**: Yes - guaranteed to find a solution if one exists (for finite graphs)
- **Time Complexity**: $O(V + E)$ where $V$ = vertices, $E$ = edges
- **Space Complexity**: $O(h)$ where $h$ = height/maximum depth of the search tree
- **Optimality**: Not optimal - does not guarantee shortest path in terms of number of edges

In maze solving, DFS can find paths quickly with less memory overhead than BFS, but the solution may not be the shortest possible path.