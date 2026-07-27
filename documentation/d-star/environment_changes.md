# D* Lite: Environment Changes

## Purpose

`MazeEnvironment` (`maze_solver/core/environment.py`) was built for algorithms that see the whole graph once and never touch it again. D* Lite needs the environment itself to become a first-class part of the story: something that changes mid-traversal, in a way the agent can detect and react to. This document covers only the environment side — see [`agent_changes.md`](agent_changes.md) for what that implies for the search algorithm.

## Environment Analysis: current vs. proposed

| Element | Current (`MazeEnvironment`) | Proposed (dynamic bridge scenario) |
|---|---|---|
| **Performance** | Provide a static graph + heuristics for a single search | Provide a graph whose edge costs can change mid-traversal, plus a way for an agent to discover *that* they changed |
| **Environment** | Grid maze, generated once, fixed for the process lifetime | Same grid maze, plus one or more designated "bridge" edges whose cost can flip between passable and broken |
| **Actuators** | None (environment is passive; algorithms only read it) | `break_edge()` / `fix_edge()` — the mechanism by which the world state changes (triggered externally: a script, a notebook cell, a scheduled event) |
| **Sensors** | `graph`, `get_step_cost()`, `calculate_manhattan_distance()` — all queried freely, all constant | Same, plus something the agent can poll to find out *which* edges changed since it last looked |

## Environment properties: what actually changes

Using the same property vocabulary this repo already applies to its LLM agents (see `CLAUDE.md`'s PEAS analysis):

| Property | Today | With a dynamic bridge | Why |
|---|---|---|---|
| **Static** | Yes — grid, costs, and graph never change after `generate()` | **No — dynamic** | The whole point of the exercise: an edge cost changes *while* the agent is mid-path |
| **Known** | Yes — full grid is exposed via `.grid`/`.graph` from the start | Still **known** | We are *not* adding limited sensing in this version — the agent can always ask "what does the graph look like right now," it just can't predict *when* it'll change. (A hidden-obstacle/sensing-radius variant would flip this to partially observable — worth a footnote, not this iteration.) |
| **Deterministic** | Yes | Still **deterministic** given a fixed event schedule (bridge breaks at step N) — the *scenario* is scripted, not randomised | Keeps the toy example easy to reason about and to reproduce for teaching |
| **Episodic vs. sequential** | Episodic — each `search()` call is independent | **Sequential** — the outcome of past moves (where the agent already is) affects what "changed" means and what needs to be repaired | This is the property change that actually breaks `SearchAlgorithmBase`'s one-shot `search()` contract |
| **Discrete** | Yes | Unchanged | Grid, discrete time steps |

The one property flip that matters is **static → sequential/dynamic**. That's what forces a different agent shape, documented in `agent_changes.md`.

## What's missing today

Walking through `maze_solver/core/environment.py`:

1. **`get_step_cost(state1, state2)` (line 241-244) ignores its arguments and always returns `1`.** There's no per-edge cost storage at all — cost is a hardcoded constant, not a queryable property of an edge. D* Lite's entire mechanism (`rhs(s) = min(cost(s, s') + g(s'))`) depends on `cost` being a real lookup.
2. **`graph` (built once in `_create_graph()`) has no update path.** Once populated, nothing in the class ever mutates it. Breaking a bridge means either removing an edge from `graph` or setting its cost to infinity — neither is currently possible without reaching into private state.
3. **No concept of "this edge is special."** A bridge is an edge that's allowed to toggle; ordinary maze walls are not (walls are cells, not edges, and are permanent by construction — mazelib doesn't support removing a wall post-generation without invalidating the graph it produced). The environment needs to know, at setup time, which edges are eligible to become bridges.
4. **No change feed.** Even once an edge cost can change, the agent needs a way to find out. D* Lite's `Main()` loop (see `d_star_lite.md`) has an explicit step: *"scan graph for edges with changed cost."* Nothing today records *that* an edge changed, only its current value — so there's no way to answer "what's different since I last checked."

## Proposed API surface (signatures only — no implementation yet)

```python
class MazeEnvironment:
    # existing methods unchanged: generate(), get_minimum_steps(), is_valid_move(), visualize(),
    # calculate_manhattan_distance(), calculate_euclidean_distance()

    def get_step_cost(self, state1: Tuple[int, int], state2: Tuple[int, int]) -> float:
        """Look up the current cost of the (state1, state2) edge.
        Returns float('inf') if the edge is currently broken."""

    def designate_bridge(self, state1: Tuple[int, int], state2: Tuple[int, int]) -> None:
        """Mark an existing edge as a bridge — the only kind of edge allowed to toggle."""

    def break_edge(self, state1: Tuple[int, int], state2: Tuple[int, int]) -> None:
        """Set a bridge edge's cost to infinity (impassable). Raises if the edge isn't a designated bridge."""

    def fix_edge(self, state1: Tuple[int, int], state2: Tuple[int, int], cost: float = 1.0) -> None:
        """Restore a bridge edge to a passable cost."""

    def drain_changed_edges(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Return and clear the list of edges whose cost changed since this was last called.
        This is the 'sense' step in D* Lite's Main() loop."""
```

Notes on these choices, for discussion rather than settled decisions:

- **Bridges are edges, not cells.** A wall toggling would change node validity (and thus `graph` topology, which every algorithm iterates over); an edge toggling only changes `get_step_cost`, which only informed search algorithms consult. This keeps BFS/DFS/GBFS unaffected by the new capability.
- **`drain_changed_edges()` is a pull, not a push.** D* Lite's loop polls once per move ("scan graph for edges with changed cost") rather than reacting to a callback — simpler to reason about and matches the textbook pseudocode directly.
- **Cost is `float('inf')` for a broken bridge, not edge removal.** Keeps `graph` (topology) and cost (weight) as separate concerns — an edge always exists once built; only its traversability changes. This also means Manhattan distance heuristics stay valid (they only depend on coordinates, never on cost).

## Config changes

`Config` (`maze_solver/core/config.py`) currently has no notion of a schedule or of designated bridges. Candidate additions, again as a discussion point rather than a final design:

```python
@dataclass
class Config:
    # ... existing fields unchanged ...
    bridge_edges: Optional[List[Tuple[Tuple[int, int], Tuple[int, int]]]] = None
    # When each bridge event fires, keyed by the agent's step count.
    # e.g. {3: [("break", bridge_0)], 8: [("fix", bridge_0)]}
    bridge_schedule: Optional[Dict[int, List[Tuple[str, int]]]] = None
```

Whether the schedule lives in `Config` (declarative, reproducible, good for teaching) or is driven externally by whatever's running the agent loop (more flexible, closer to "real" unpredictability) is an open question for `agent_changes.md` and worth settling before writing any code.

## Key differences summary

| | Current `MazeEnvironment` | Proposed dynamic `MazeEnvironment` |
|---|---|---|
| Edge cost | Hardcoded `1` | Per-edge, mutable, `inf` when broken |
| Graph topology | Fixed after `generate()` | Fixed — only cost changes, not topology |
| Change visibility | N/A (nothing changes) | `drain_changed_edges()` gives the agent a way to sense what's new |
| Environment property | Static, episodic-compatible | Sequential — history matters, order of calls matters |
| Affects which algorithms | N/A | Only cost-aware (informed) algorithms; BFS/DFS unaffected since they never call `get_step_cost` |
