# Breadth-first Search (BFS)

## BFS Algorithm in Mathematical Notation

**Input:** Graph $G = (V, E)$, start vertex $s$, goal vertex $g$

**Output:** Path from $s$ to $g$ if exists, otherwise ∅

**Algorithm:**
1. Initialize queue $Q ← \{s\}$
2. Initialize visited set $V_{visited} ← \{s\}$
3. Initialize parent map $π[s] ← null$
4. While $Q ≠ ∅$:
   - $v ← \text{dequeue}(Q)$
   - If $v = g$:
     - Return path by following $π$ from $g$ to $s$
   - For each $u \in \text{Adj}(v)$:
     - If $u \notin V_{visited}$:
       - $V_{visited} ← V_{visited} \cup \{u\}$
       - $π[u] ← v$
       - $\text{enqueue}(Q, u)$
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

## BFS Algorithm in Python

```python
# Initialize queue with start node Q ← {s}
queue = deque([start])

# Track visited nodes and parent pointers for path reconstruction
visited = set([start]) # V_visited ← {s}
parent = {start: None} # $π[s] ← null

while queue:
    # Dequeue next node
    current_node = queue.popleft()

    # Check if reached goal
    if current_node == goal: # v=g
        # Reconstruct and return path
        return reconstruct_path(parent, start, goal) # t → π[t] → π[π[t]] → ...

    # Process all unvisited neighbors
    for neighbor in graph[current_node]: # For each u in Adj(v)
        if neighbor not in visited:
            visited.add(neighbor) # V_visited ←V_visited ∪ {u}
            parent[neighbor] = current_node # π[u] ← v
            queue.append(neighbor) # enqueue(Q,u)

# No path found
return None
```

## BFS Properties

### Key Characteristic

- **FIFO Queue**: BFS processes vertices in order of their discovery, which guarantees breadth-first exploration

### Analysis

- **Completeness**: Yes - guaranteed to find a solution if one exists (for finite graphs)
- **Time Complexity**: $O(V + E)$ where $V$ = vertices, $E$ = edges
- **Space Complexity**: $O(V)$ for storing the queue, visited set, and parent pointers
- **Optimality**: Optimal for unweighted graphs - guarantees shortest path in terms of number of edges

In maze solving, BFS always finds the path with the minimum number of steps but uses more memory than depth-first approaches.

