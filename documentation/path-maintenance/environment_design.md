# Path Maintenance Agent: Environment Design (Step 1)

## Purpose

The real motivation for this toy example is a topological system — GitHub CI/CD, Kubernetes, generic platform health — where an agent traverses a known graph, checks each node is in the correct state, repairs the nodes that aren't, and escalates to a human when repair isn't possible. That's a large target. This document specifies the first, deliberately narrow step toward it: a maze-based **path maintenance agent** that walks a fixed route and repairs cells, nothing else.

Two things this step is *not*, stated up front because both were live candidates before being ruled out:

- **Not a plan-repair problem.** `documentation/d-star/environment_changes.md` and `agent_changes.md` design D* Lite over a maze where an *edge cost* can toggle (`break_edge`/`fix_edge`), forcing the agent to replan its route. This document does not extend or depend on that design. Here, the route never changes — it's computed once and walked exactly as computed. D* Lite, LPA*, and the rest of the incremental-replanning family (`documentation/d-star/related_algorithms.md`) are out of scope for this step; they become relevant only if a later step lets repair *fail*, so that a route through the graph is no longer guaranteed to work.
- **Not a belief distribution.** "Belief state" here means the single path an A* search computes and commits to, not a probability distribution over possible states (contrast with `self_reflection`'s `ReflectionResult.answer_distribution`). There's no uncertainty being tracked — the agent knows the maze topology completely; the only thing it doesn't know in advance is *which* cells will need repair, and it finds that out by arriving at them.

What this step *is*: a cell, not an edge, can be in a state that needs fixing. The agent's job is to notice that and fix it — MAPE-K's Monitor-Analyze-Plan-Execute loop and Dijkstra's self-stabilization (a system reaching a correct state through purely local repair actions) are the relevant prior art, not the incremental-search literature. `DualStateAgent`/`ActionPair`/atomicguard's retry-and-escalate machinery, already built in `real_task_graph_solver/atomicguard_backed/`, is the target mechanism for a later, richer step and for the real CI/CD/Kubernetes application — not used here. Repair in this step is a single deterministic action that always succeeds.

## Environment Analysis

| Element | Description |
|---|---|
| **Performance** | Reach the goal having repaired every `needs_repair` cell encountered on the way; the route itself is not up for optimization once computed |
| **Environment** | The existing `maze_solver` grid maze, plus a per-cell state (`open` / `needs_repair`) on top of the existing wall/open distinction |
| **Actuators** | `repair_cell()` — deterministic, always succeeds, no retries, no failure mode |
| **Sensors** | `get_cell_state()` — the agent checks a cell's state before entering it |

## Environment properties

| Property | Value | Why |
|---|---|---|
| **Topology** | Known and fixed | Same grid, same walls, same graph as today's `MazeEnvironment` — nothing about connectivity changes |
| **Cell state** | Set once, before the walk starts | A single discrete mutation event (`inject_repairs`) marks some already-open cells as `needs_repair`, before the agent takes its first step. Not a continuous or scheduled process — there is exactly one state change, and it happens between "compute the path" and "walk the path" |
| **Static vs. dynamic** | Static during the walk | Unlike the D* Lite maze, nothing changes *while* the agent is moving. The one state change happens up front. This is what keeps the plan valid throughout — there's never a moment where the environment differs from what it looked like when the path was computed, only a moment where a cell's *content* needs attention |
| **Sequential** | No | The walk doesn't depend on history beyond "which cells has the agent already repaired" — there's no analogue of D* Lite's `km` term or replanning state to carry forward |
| **Discrete** | Yes | Grid, discrete steps, two-valued cell state |
| **Observable** | Fully, but lazily | The agent *could* query any cell's state at any time (nothing hides it), but by design it only ever checks the cell it's about to enter — mirroring the real target (you don't re-check every node in a cluster before every step, you check the one you're about to act on) |

## What's missing today

`maze_solver/core/environment.py` has no notion of cell state beyond wall vs. open (`self.grid`, `0`/`1`). There's no way to mark an open cell as needing anything, no way to query that, and no repair action at all. This is a different gap from the one `environment_changes.md` identifies (`get_step_cost` always returning `1`, no per-edge cost storage) — that gap is about edges, this one is about node content, and fixing it doesn't touch `get_step_cost`, `graph`, or wall placement at all.

## Proposed API surface (signatures only — no implementation yet)

```python
class CellState(Enum):
    OPEN = "open"
    NEEDS_REPAIR = "needs_repair"
    # Walls are not a CellState. They stay encoded in `grid`/`graph` exactly as
    # today, permanent by construction (mazelib doesn't support removing a wall
    # post-generation without invalidating the graph it produced). Only already-
    # open cells can be marked NEEDS_REPAIR.


class MazeEnvironment:
    # existing methods, attributes unchanged: generate(), get_minimum_steps(),
    # is_valid_move(), visualize(), calculate_manhattan_distance(),
    # calculate_euclidean_distance(), get_step_cost(), graph, grid, start, end,
    # optimal_path, optimal_path_length

    def get_cell_state(self, cell: Tuple[int, int]) -> CellState:
        """Current state of an open cell. Raises if `cell` is a wall or out of bounds."""

    def inject_repairs(self, cells: List[Tuple[int, int]]) -> None:
        """One-time, discrete mutation: mark each of `cells` NEEDS_REPAIR.
        Called once, by the Driver, before the agent starts walking — not a
        scheduled or continuous process. Raises if any cell is a wall or
        already NEEDS_REPAIR. Cells not on the belief-state path are legal to
        pass here but will never be sensed or repaired, since the agent only
        checks cells it walks through (see open question below)."""

    def repair_cell(self, cell: Tuple[int, int]) -> None:
        """Deterministic repair: NEEDS_REPAIR -> OPEN. Always succeeds — no
        retry budget, no failure mode, no return value to check. Raises if
        `cell` is already OPEN or is a wall."""
```

```python
class PathMaintenanceAgent:
    def __init__(self, environment: MazeEnvironment, path: List[Tuple[int, int]]):
        """`path` is the belief state: an already-computed route (e.g. the
        output of AStarSearch.search(start, goal).path), taken as given.
        The agent never calls a search algorithm itself and never recomputes
        this list."""

    def walk(self) -> WalkResult:
        """Walk `path` in order, one cell at a time. Before entering each
        cell (except the start), call get_cell_state(); if NEEDS_REPAIR, call
        repair_cell() before proceeding. Never deviates from `path`, never
        re-invokes search, never checks a cell that isn't on `path`."""
```

```python
@dataclass(frozen=True)
class WalkResult:
    path: List[Tuple[int, int]]              # identical to the input path — restated for the record, not recomputed
    repairs_performed: List[Tuple[int, int]]  # cells that were NEEDS_REPAIR when the agent reached them, in walk order
    success: bool                             # True once the agent reaches path[-1]; always True in this step, since repair can't fail
```

## Belief state, precisely

The "belief state" in this step is nothing more than:

```python
belief_path: List[Tuple[int, int]] = AStarSearch(env, config).search(env.start, env.end).path
```

computed once, before `inject_repairs()` is called, and handed to `PathMaintenanceAgent` unchanged. It is deliberately *not* a `Dict[str, float]`-style distribution (contrast `self_reflection.domain.ReflectionResult.answer_distribution`) — there's nothing probabilistic about it. Calling it a belief state at all is a nod toward the later, harder version of this problem (where the agent's model of the world can diverge from reality in ways worth representing explicitly), not a claim that any distribution is being tracked here.

## Sequence for one run

1. `env = MazeEnvironment(config)` — generate the maze, as today.
2. `belief_path = AStarSearch(env, config).search(env.start, env.end).path` — compute the route once.
3. `env.inject_repairs(cells)` — Driver picks a subset of open cells on `belief_path` (see open question) and marks them `NEEDS_REPAIR`. One discrete event, not a schedule.
4. `result = PathMaintenanceAgent(env, belief_path).walk()` — the agent walks `belief_path` exactly, repairing as it goes.
5. Inspect `result.repairs_performed` against the cells injected in step 3 — every injected cell that was on `belief_path` should appear, in path order.

## Open questions (explicitly undecided)

- **Which cells are eligible for `inject_repairs()`?** Restricting the Driver to cells already on `belief_path` makes step 3 guaranteed-observable (the agent will definitely walk over every injected cell) and keeps the demo legible. Allowing off-path cells too is closer to "real" — a Kubernetes node can drift whether or not anything is currently routing through it — but means some injected repairs are never noticed in this step, since the agent has no reason to look anywhere but the path it's walking. Leaning toward path-only for step 1, with off-path drift as a natural extension once there's a reason for the agent to sense beyond its immediate route.
- **Does `inject_repairs()` live on `MazeEnvironment` directly, or on a thin Driver-facing wrapper**, so that "the environment mutates itself" and "an external actor mutates the environment" stay visibly distinct, matching `agent_changes.md`'s Driver/agent separation even though no replanning is involved here? Leaning toward keeping it a plain method for step 1 — the separation matters more once escalation exists and there's a human on the other end of it.
- **Where does `PathMaintenanceAgent` live in the module tree?** — `maze_solver/agents/` (new), alongside `maze_solver/algorithms/`? Or does it belong closer to `real_task_graph_solver/atomicguard_backed/`, since a later step is explicitly meant to swap `repair_cell()` for a real `ActionPair`? Leaning toward `maze_solver/`, since step 1 has no atomicguard dependency at all — move it later if and when that dependency actually gets introduced.

## Non-goals for this step

Restated explicitly, since earlier framings of this problem conflated them with what's actually needed here:

- No path/plan recalculation of any kind. `belief_path` is computed exactly once and never touched again.
- No D* Lite, no LPA*, no incremental replanning — `documentation/d-star/` is unrelated to this document.
- No `DualStateAgent`, no `ActionPair`, no atomicguard retry budgets or guard functions — `repair_cell()` is unconditional.
- No escalation to a human. Repair cannot fail in this step, so there is nothing to escalate.
- No probability distribution over states. "Belief state" means one committed path, not a POMDP-style belief.

## Relationship to other docs in this repo

This sits alongside, not underneath, `documentation/d-star/`: both start from `maze_solver`, but they extend it in orthogonal directions (edge cost vs. cell state) toward different endpoints (route repair vs. node repair). `documentation/task-graph/` is the more distant cousin — a different environment entirely (AND-DAG of guarded tasks, no grid, no spatial movement) built to give AND-composition and real repair machinery a home; this document's later steps (repair-can-fail, escalation) are where a convergence with that machinery — and with atomicguard's `DualStateAgent`/`ActionPair` — actually happens, but step 1 deliberately doesn't reach for any of it yet.
