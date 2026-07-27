# D* Lite (Dynamic A*, Lite version)

## Why this algorithm exists

Every algorithm covered so far — BFS, DFS, Greedy Best-First, A* — answers one question: *given this graph, find a path from start to goal.* If the graph changes after you've found the path (a bridge collapses, a door locks), the only option is to throw the old search away and run it again from scratch.

D* Lite answers a different question: *given a graph that changes over time, and a plan you've already computed, repair the plan as cheaply as possible.* It's the algorithm behind mobile robot navigation (originally developed for the Mars rovers' predecessor research and DARPA's autonomous vehicles) precisely because real-world maps are never fully known or fully static — sensors reveal obstacles, and terrain changes as the robot moves through it.

It's a "Lite" version of Anthony Stentz's original D* (1994) — same behaviour, but reformulated by Koenig & Likhachev (2002) as an incremental variant of A*, built on top of **Lifelong Planning A\*** (LPA*). If you understand A*, D* Lite is A* plus a repair mechanism, not a different algorithm.

## The core idea: two value functions instead of one

A* tracks one cost estimate per node: `g(n)`, the best known cost from *start* to `n`. When an edge cost changes, `g` values downstream of that edge are stale and A* has no way to know which ones without re-deriving everything.

D* Lite searches **backward from the goal** and tracks two values per node:

| Symbol | Meaning |
|---|---|
| `g(s)` | Current best known cost from `s` to the goal — like A*'s `g`, but measured *to* the goal since search runs backward |
| `rhs(s)` | "One-step lookahead" value: `min` over successors `s'` of `cost(s, s') + g(s')`. A locally-consistent estimate derived purely from neighbours |

A node is **locally consistent** when `g(s) == rhs(s)`. When they differ, the node is:
- **overconsistent** (`g(s) > rhs(s)`) — a cheaper path was just discovered (e.g. a bridge was fixed)
- **underconsistent** (`g(s) < rhs(s)`) — the node's cost went up and it doesn't know it yet (e.g. its bridge just broke)

Only inconsistent nodes are queued for update. This is the entire trick: **an edge-cost change only invalidates `rhs` for the handful of nodes adjacent to that edge**, so only those nodes (and whatever their inconsistency propagates to) get re-examined. Everything else in the maze keeps its already-computed `g` value.

## Priority queue key function

Like A*, D* Lite orders its frontier (`U`, the "open list" of inconsistent nodes) by a two-part key so it still expands in a best-first order from the agent's *current* position `s_start`:

```
key(s) = [ min(g(s), rhs(s)) + h(s_start, s) + km ,  min(g(s), rhs(s)) ]
```

- `h(s_start, s)` is the same admissible heuristic as A* (Manhattan distance works here too)
- `km` is a **key modifier** — accumulated heuristic drift each time the agent moves, so that old keys already in the queue stay comparable to new ones without having to re-key every entry in `U` on every move. This is the one piece of bookkeeping that has no A* equivalent: it's what makes it cheap to keep the priority queue "as if freshly keyed" without actually re-touching untouched entries.

## Algorithm in pseudocode

```
procedure CalculateKey(s):
    return [ min(g(s), rhs(s)) + h(s_start, s) + km,  min(g(s), rhs(s)) ]

procedure Initialize():
    U ← ∅
    km ← 0
    for all s: rhs(s) ← g(s) ← ∞
    rhs(s_goal) ← 0
    U.insert(s_goal, CalculateKey(s_goal))

procedure UpdateVertex(u):
    if u ≠ s_goal:
        rhs(u) ← min over successors s' of ( cost(u, s') + g(s') )
    if u in U: U.remove(u)
    if g(u) ≠ rhs(u):
        U.insert(u, CalculateKey(u))

procedure ComputeShortestPath():
    while U.top_key() < CalculateKey(s_start) OR rhs(s_start) ≠ g(s_start):
        u ← U.pop_min()
        if g(u) > rhs(u):
            g(u) ← rhs(u)                       # node got cheaper — settle it
            for each predecessor p of u: UpdateVertex(p)
        else:
            g(u) ← ∞                            # node got more expensive — unsettle it
            for each predecessor p of u, and u itself: UpdateVertex(p)

procedure Main():
    Initialize()
    ComputeShortestPath()
    while s_start ≠ s_goal:
        s_start ← argmin over successors s' of ( cost(s_start, s') + g(s') )
        move agent to s_start
        scan graph for edges with changed cost
        if any edge (u, v) changed cost:
            km ← km + h(s_last, s_start)
            s_last ← s_start
            for each changed edge (u, v): update cost(u, v); UpdateVertex(u); UpdateVertex(v)
            ComputeShortestPath()
```

The four-line "Main" loop is the part that has no counterpart in this repo's `SearchAlgorithmBase` today: **move, sense, patch, replan** — repeated for the life of the traversal, not called once.

## Properties / Analysis

| Property | A* | D* Lite |
|---|---|---|
| **Completeness** | Yes (finite graph, non-negative costs) | Yes, under the same conditions, *at every replan* |
| **Optimality** | Yes, with an admissible heuristic | Yes, with an admissible, consistent heuristic |
| **Search direction** | Start → goal | Goal → start (so `s_start` can move without re-deriving `h`) |
| **Cost of first plan** | `O(b^d)` | Same — first `ComputeShortestPath()` is equivalent work to A* |
| **Cost of a replan after a local change** | `O(b^d)` (must restart) | Proportional to the number of *newly inconsistent* nodes — typically small and local to the change, not the whole graph |
| **State carried between calls** | None — stateless per `search()` call | `g`, `rhs`, `U`, `km` persist across the whole traversal |
| **What a "changed edge" costs you** | A full new search | One `UpdateVertex` per endpoint, then however far the inconsistency propagates |

## Relationship to Lifelong Planning A* (LPA*)

D* Lite is LPA* run with the search direction reversed (goal-to-start) and re-triggered every time the agent moves, not just when the map changes. LPA* itself is the general "repair, don't recompute" idea; D* Lite specialises it for an agent that is *also* moving through the space it's planning in.

## Where this fits in the repo

This is a design-stage document — D* Lite is **not yet implemented** in `maze_solver/`. It doesn't map cleanly onto `SearchAlgorithmBase`'s `search(start, goal) → SearchResult` shape, because that shape assumes one call, one answer, no persisted state, and a graph that doesn't move under it. See:

- [`documentation/d-star/environment_changes.md`](../documentation/d-star/environment_changes.md) — what `MazeEnvironment` needs to expose (mutable edge costs, a changed-edges feed) to make the `Main()` loop above possible
- [`documentation/d-star/agent_changes.md`](../documentation/d-star/agent_changes.md) — how the agent's shape changes from a stateless one-shot planner to a stateful, persistent replanner, and what that does to its PEAS classification
- [`documentation/d-star/beyond_the_maze.md`](../documentation/d-star/beyond_the_maze.md) — stress-tests the same design against a real dynamic graph (a multi-repo CI/CD pipeline) to check where the abstraction holds and where it strains; a cross-check, not a build spec
