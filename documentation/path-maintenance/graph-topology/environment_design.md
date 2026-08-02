# Graph Topology: Environment Design (Step 2)

## Purpose

Step 1 (`../environment_design.md`) walks a single corridor: one A*-computed path, one cell at a time, no alternative routes and no fan-out. A real pipeline a change moves through — pre-commit, then CI, then a deployment that only proceeds once several independent checks have all passed — isn't a corridor. It's a DAG: some nodes have more than one prerequisite, and all of them must hold before the dependent node is reachable. Composition across a fan-out like that is AND, not OR — there's no "pick whichever branch is cheapest" choice anywhere in it, the same way `task_graph_solver`'s own domain has none.

This document is exactly one change from step 1: **the environment becomes a DAG with `requires`-only AND edges instead of a spatial grid.** Nothing else moves. Node state is still the same two values step 1 already built — `OPEN`/`NEEDS_REPAIR` — repaired by the same deterministic, always-succeeding action. There is no job lifecycle, no `PENDING`/`IN_PROGRESS`, no other agents, no multi-agent reclassification in this step. That's a separate, later step (`../job-lifecycle/`), built on top of what this document establishes, not alongside it — a job graph without fan-out already proven wouldn't be testing anything new about fan-out, and fan-out plus an async lifecycle at the same time is two new concepts landing in one step, which is exactly what step 1's own discipline (and every step since) has avoided.

## What actually changes, and what doesn't

**Carried over from step 1, unchanged:**
- `CellState` (`OPEN`/`NEEDS_REPAIR`), and the deterministic, always-succeeding repair action.
- The agent's shape: sense before acting on a node, repair if `NEEDS_REPAIR`, never re-plan, never deviate from the order it was given.
- Single-agent, static, deterministic, known, discrete, fully-but-lazily observable — every property from step 1's table holds exactly as before. Nothing here reclassifies the environment; that only happens once `job-lifecycle/` adds a real lifecycle.

**New in this step:**
- Topology: a DAG (`requires`-only AND edges) instead of a grid.
- The belief state generalizes from a coordinate path to a topological order over the DAG's nodes.

## Reviewing `task_graph_solver` before deciding how

`task_graph_solver` already has AND-only `requires` and DAG validation, built and tested. Worth checking directly what's reusable before importing or subclassing anything:

- **Reusable as a pattern:** `requires`-only AND composition, and its validation (`TaskGraphEnvironment._validate_graph`'s cycle detection, unknown-dependency checks). `ready_nodes(satisfied) -> list[str]` — the AND-respecting frontier primitive. A genuinely useful consequence: an AND-only DAG has no alternative routes to choose between, so there's no A*-equivalent search step needed here at all — the topology itself already *is* the plan, the same way step 1's "Known: full topology exposed from the start" already implied for the grid.
- **Not reusable, wrong shape for this step regardless of lifecycle:** `attempt(node_id) -> AttemptOutcome` and everything that feeds it (`rmax`, `r_patience`, `pass_probability`, `_attempts_made`) model retry *economics* — a budget that can be exhausted, a probability of passing, escalation after consecutive failures. Step 1 deliberately kept repair a sure thing, one deterministic call, no budget to track. That choice doesn't change just because the environment is now a DAG. None of `task_graph_solver`'s five executors apply either — they all exist to decide *which node to attempt next*, under retry economics, a decision problem this agent doesn't have, since its order is already known.

**Decision:** a new, independent environment, matching the precedent `real_task_graph_solver/core/environment.py`'s `RealCheckEnvironment` already set — its own docstring states, verbatim, "Same public shape as `task_graph_solver`'s `TaskGraphEnvironment`," and it is not a subclass. Same move here: reuse the `requires`-validation and `ready_nodes()` *pattern*, bring across none of the retry-economics fields, keep step 1's `CellState`/repair contract exactly as it is.

## Environment properties

Unchanged from step 1's table in every row — restated here only to make explicit that nothing about moving to a DAG, on its own, touches any of them:

| Property | Value | Why unchanged |
|---|---|---|
| **Topology** | Known and fixed | Still fully specified up front — a DAG's edges are exactly as knowable in advance as a grid's walls |
| **Static/Dynamic** | Static during the walk | Nothing changes state *while* the agent is walking in this step; `inject_repairs()`-equivalent scenario setup still runs once, before the walk starts |
| **Single/Multi-agent** | Single-agent | No other agent exists in this step — that reclassification is `job-lifecycle/`'s, not this document's |
| **Deterministic/Stochastic** | Deterministic | Repair still always succeeds |
| **Episodic/Sequential** | Episodic | No history beyond the current node matters yet — sequential only becomes true once poll-count-while-waiting is a thing to track, which needs a lifecycle this step doesn't have |
| **Discrete** | Yes | Finite node set, two-valued state |
| **Observable** | Fully, but lazily | Unchanged from step 1 |

## Proposed API surface (signatures only — no implementation yet)

```python
@dataclass
class GraphNode:
    id: str
    requires: Tuple[str, ...] = ()
    # deliberately no pass_probability/rmax/r_patience - see "not reusable" above
```

```python
class PathGraphEnvironment:
    nodes: Dict[str, GraphNode]

    def __init__(self, nodes: Dict[str, GraphNode]):
        """Same requires-validation shape as TaskGraphEnvironment._validate_graph
        (cycle detection, unknown-dependency checks) - reused as a pattern,
        not imported."""

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Same AND-gating shape as TaskGraphEnvironment.ready_nodes(): the
        frontier of nodes whose requires are all satisfied and haven't
        themselves been satisfied yet."""

    def get_node_state(self, node_id: str) -> CellState:
        """Same contract as step 1's get_cell_state() - CellState is reused
        directly, unchanged, just keyed by node id instead of coordinate."""

    def inject_repairs(self, node_ids: List[str], order: List[str]) -> None:
        """Same contract as step 1's inject_repairs() - restricted to nodes
        present in the given order, for the same reason: every injected
        repair must be guaranteed to be walked over."""

    def repair_node(self, node_id: str) -> None:
        """Same contract as step 1's repair_cell(): deterministic,
        always succeeds."""
```

```python
class PathMaintenanceAgent:
    def __init__(self, environment: PathGraphEnvironment, order: List[str]):
        """`order` is the belief state, generalized: a topological ordering
        of the DAG's nodes (computed once - any valid one, ties broken by
        id for reproducibility, the same tie-break TopologicalExecutor
        already uses), taking the place of step 1's coordinate path. The
        class keeps its name and its walk() shape unchanged - only the
        domain type of one element changes, from a grid coordinate to a
        node id."""

    def walk(self) -> WalkResult:
        """Identical logic to step 1's walk(): sense each node in `order`
        before entering it, repair if NEEDS_REPAIR, never recompute or
        deviate from `order`. No new branching - CellState still has
        exactly two values."""
```

`WalkResult` is unchanged from step 1 — `path` becomes a list of node ids rather than coordinates, but the shape (`path`, `repairs_performed`, `success`) doesn't need a new field for this step.

## Where this lives

`path_maintenance/`, a new top-level package sibling to `maze_solver/` and `task_graph_solver/` — nothing about a DAG of nodes is spatial, so it doesn't belong under `maze_solver/agents/`. Step 1's code stays exactly where it is; nothing here proposes moving or generalizing it retroactively. `job-lifecycle/` builds its lifecycle additions on top of this package once it exists, rather than on the maze.

## Not decided

- **Exact scenario topology** — left to `scenario.md`. Needs at least one genuine AND-join (two-or-more-parent node) to actually demonstrate fan-out, which a purely linear chain wouldn't.
- **Whether `PathGraphEnvironment`/`GraphNode` are the right names**, versus something that reads less like a `task_graph_solver` echo — worth a second look once a scenario exists to write tests against.
