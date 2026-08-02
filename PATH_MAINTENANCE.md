# Path Maintenance Agent: Documentation

This is a sibling document to [`README.md`](README.md) and [`TASK_GRAPH_SOLVER.md`](TASK_GRAPH_SOLVER.md), in the same spirit and structure, for a third variation on the same underlying question: an agent that commits to a path once, then keeps the nodes along it healthy — as opposed to `README.md`'s agents (which only ever find a path) or `TASK_GRAPH_SOLVER.md`'s (which execute a DAG of guarded tasks with no spatial path at all).

`maze_solver`'s grid gives `PathMaintenanceAgent` its route the same way it gives every other algorithm in this repo its route — a single A* search, run once. What's new is what happens after: instead of stopping at the goal, the agent walks that route and checks each cell along it, repairing any it finds broken. The real motivation is a topological system — GitHub CI/CD, Kubernetes, generic platform health — where an agent traverses a known graph, checks each node's state, repairs what's wrong, and escalates to a human when it can't. This is the first, deliberately narrow step toward that: node repair only, no route recalculation, no real (fallible) repair yet, no escalation. See [`documentation/path-maintenance/environment_design.md`](documentation/path-maintenance/environment_design.md) for the full scoping rationale, including two things this is explicitly *not* (D* Lite-style route repair, and POMDP-style belief tracking).

## Environment Setup

```bash
# Same uv-based workflow as the maze_solver setup in README.md
uv venv
source .venv/bin/activate
uv pip install networkx matplotlib pandas mazelib imageio seaborn ipython pytest

# Run the test suite
uv run pytest maze_solver/tests/ -v
# or: make test-maze-solver
```

No real jobs, subprocesses, or infra ever run — this stays a toy grid maze. Every cell's `NEEDS_REPAIR` state is injected by scenario setup, and `repair_cell()` is a deterministic no-op that always succeeds. See [`documentation/path-maintenance/environment_design.md`](documentation/path-maintenance/environment_design.md)'s Environment Analysis for the full reasoning.

## System Architecture

```
maze_solver/
├── core/
│   ├── environment.py      # MazeEnvironment - existing grid/graph, plus
│   │                          CellState, get_cell_state(), inject_repairs(),
│   │                          repair_cell()
│   └── results.py          # WalkResult (path, repairs_performed, success)
├── agents/
│   └── path_maintenance.py # PathMaintenanceAgent.walk()
├── visualization/
│   └── path_maintenance_view.py  # event-driven GIF: record_walk()/animate_walk(),
│                                    mirrors task_graph_solver's graph_view.py
├── animations/
│   └── path_maintenance_lite.gif
└── tests/
    ├── test_environment.py
    ├── test_path_maintenance.py
    └── test_path_maintenance_view.py
```

## Class Overview

### `CellState`

```python
class CellState(Enum):
    OPEN = "open"
    NEEDS_REPAIR = "needs_repair"
```

Walls are not a `CellState` — they stay encoded in `MazeEnvironment.grid`/`.graph` exactly as before, permanent by construction. Only already-open cells can be `NEEDS_REPAIR`.

### `MazeEnvironment` additions

```python
def get_cell_state(self, cell: Tuple[int, int]) -> CellState: ...
def inject_repairs(self, cells: List[Tuple[int, int]], path: List[Tuple[int, int]]) -> None: ...
def repair_cell(self, cell: Tuple[int, int]) -> None: ...
```

`inject_repairs()` is restricted to cells already on the given path, validated at the call — every injected repair is guaranteed to be one the agent's fixed walk will actually reach.

### `PathMaintenanceAgent`

```python
class PathMaintenanceAgent:
    def __init__(self, environment: MazeEnvironment, path: List[Tuple[int, int]]): ...
    def walk(self) -> WalkResult: ...
```

Walks `path` in order, one cell at a time. Never calls a search algorithm, never recomputes or deviates from `path`. Before entering each cell it senses `get_cell_state()`; if `NEEDS_REPAIR`, calls `repair_cell()` first.

### `WalkResult`

```python
@dataclass(frozen=True)
class WalkResult:
    path: List[Tuple[int, int]]
    repairs_performed: List[Tuple[int, int]]
    success: bool
```

## Scenario (step 1)

`maintenance_lite`: `Config(maze_size=5, maze_id=7)`, a 17-cell corridor with one turn, two path-relative injected repairs (at roughly the 1/3 and 2/3 points). Chosen for a legible demo — not so few injections that repair only happens once, not so many that individual before/after transitions blur together. Full detail: [`documentation/path-maintenance/scenario.md`](documentation/path-maintenance/scenario.md).

## Visualization Example (step 1)

`path_maintenance_view.py` mirrors `task_graph_solver/visualization/graph_view.py`'s event-driven pattern (`record_walk()`/`animate_walk()`) rather than `maze_solver`'s frontier-based `SearchAlgorithmDashboard` — a fixed walk has no frontier to show. Cell color and the agent's position marker are kept as separate visual channels; a repaired cell renders a distinct dark green from a cell that was always open, so "was broken, now fixed" stays visible rather than blending into "was always fine." The GIF never reveals a `NEEDS_REPAIR` cell before the agent actually senses it — the visualization doesn't leak information the agent doesn't have.

Full walkthrough with frame-by-frame commentary: [`documentation/path-maintenance/experiments/01_maintenance_lite.md`](documentation/path-maintenance/experiments/01_maintenance_lite.md).

## System Architecture (step 2)

```
path_maintenance/          # new top-level package - independent of maze_solver,
│                             the same way task_graph_solver is
├── core/
│   ├── domain.py           # CellState (redefined, not imported), GraphNode
│   ├── environment.py      # PathGraphEnvironment - requires-validation, ready_nodes(),
│   │                          get_node_state(), inject_repairs(), repair_node()
│   └── results.py          # WalkResult (path, repairs_performed, success)
├── agents/
│   └── path_maintenance.py # PathMaintenanceAgent.walk() - identical logic to step 1's,
│                              generalized from Tuple[int, int] to str
├── scenarios/
│   └── deploy_chain_lite.py  # build_deploy_chain_lite(), deploy_chain_lite_order()
├── visualization/
│   └── graph_view.py       # networkx DiGraph, layered topological layout,
│                              record_walk()/animate_walk() - rebuilt independently,
│                              not imported from task_graph_solver
├── animations/
│   └── deploy_chain_lite.gif
└── tests/
    ├── test_environment.py
    ├── test_path_maintenance.py
    ├── test_scenarios.py
    └── test_graph_view.py
```

`GraphNode`/`PathGraphEnvironment` reuse `task_graph_solver`'s `requires`-validation and `ready_nodes()` *pattern* (cycle detection, AND-gating), rebuilt locally rather than imported or subclassed — matching the precedent `real_task_graph_solver`'s `RealCheckEnvironment` already set for "same public shape, independent class." None of `task_graph_solver`'s retry economics (`pass_probability`/`rmax`/`r_patience`/`attempt()`/its five executors) came across — this step is deterministic and known, with no retry budget. Full reasoning: [`documentation/path-maintenance/graph-topology/environment_design.md`](documentation/path-maintenance/graph-topology/environment_design.md).

## Scenario (step 2)

`deploy_chain_lite`: `pre-commit → lint, unit-tests → merge → deploy`, five nodes with one AND-join (`merge`, two parents) — the smallest graph with a genuine fan-in, deliberately skipping the pure-linear case since step 1's maze corridor already proved that shape. Topological order computed once, no search needed (an AND-only DAG has no alternative routes to choose between). Two injected repairs (`lint`, `deploy`). Full detail: [`documentation/path-maintenance/graph-topology/scenario.md`](documentation/path-maintenance/graph-topology/scenario.md).

## Visualization Example (step 2)

`graph_view.py` moves from step 1's `imshow` grid to a `networkx` `DiGraph`, laid out left-to-right by topological generation (there's no grid to draw once nodes aren't spatial). AND-join nodes render as squares, everything else as circles — the same convention `task_graph_solver/visualization/graph_view.py` uses. Same color/agent-marker separation as step 1's viz, same `record_walk()`/`animate_walk()` event-driven shape.

Full walkthrough with frame-by-frame commentary: [`documentation/path-maintenance/graph-topology/experiments/01_deploy_chain_lite.md`](documentation/path-maintenance/graph-topology/experiments/01_deploy_chain_lite.md).

## System Architecture (step 3)

```
path_maintenance/
├── core/
│   ├── domain.py           # + JobState (4 values), JobNode (ticks_to_resolve, resolves_to) -
│   │                          additive, CellState/GraphNode from step 2 untouched
│   ├── environment.py      # + JobGraphEnvironment - get_job_state() (pure sense),
│   │                          advance_jobs(satisfied) (ready-gated), repair_node().
│   │                          _validate_requires_graph()/_ready_nodes() factored out
│   │                          and shared with step 2's PathGraphEnvironment
│   └── results.py          # + JobWalkResult (path, repairs_performed, senses_performed, success) -
│                              new type, WalkResult from step 2 untouched
├── agents/
│   └── job_maintenance.py  # new module: PathMaintenanceAgent.walk() with a wait loop -
│                              step 2's agents/path_maintenance.py untouched
├── visualization/
│   └── job_graph_view.py   # + pending/in_progress colors, reuses graph-topology's
│                              build_networkx_graph()/_layered_layout() directly (structural,
│                              works for any node type with .requires)
├── animations/
│   └── deploy_chain_lite_lifecycle.gif
└── tests/
    ├── test_job_environment.py
    ├── test_job_maintenance.py
    └── test_job_graph_view.py
```

Every step-3 addition is additive to step 2's package - no existing class was modified, only new modules/new classes alongside them, the same discipline that kept step 1's `maze_solver` code untouched when step 2 was built.

## Scenario (step 3)

`deploy_chain_lite`'s exact step-2 topology, each node gaining `ticks_to_resolve`/`resolves_to`: `lint` takes 2 ticks (3 senses: `PENDING → IN_PROGRESS → SUCCEEDED`), `unit-tests`/`merge` resolve instantly, `deploy` takes 1 tick and resolves to `FAILED` (2 senses, then repaired). Exercises every `JobState` value at least once. Full detail: [`documentation/path-maintenance/job-lifecycle/scenario.md`](documentation/path-maintenance/job-lifecycle/scenario.md).

A real bug was caught building this: `advance_jobs()` originally ticked every unresolved node in the whole graph, letting `deploy` silently resolve during `lint`'s wait loop, before `deploy`'s own prerequisite (`merge`) had resolved. Fixed to only tick nodes returned by `ready_nodes(satisfied)` - see the scenario doc and [`experiments/01_deploy_chain_lite_lifecycle.md`](documentation/path-maintenance/job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md) for the full story.

## Visualization Example (step 3)

`job_graph_view.py` adds two colors on top of step 2's four: `pending` (white) and `in_progress` (gold) — one hue deepening, the same "one hue, two depths" convention `clear`/`repaired` and `future`/`needs_repair` already established. An `advance_jobs()` call gets its own frame, captioned distinctly from a sense, so "time passing" is visually distinguishable from "checking status."

Full walkthrough with frame-by-frame commentary: [`documentation/path-maintenance/job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md`](documentation/path-maintenance/job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md).

## Testing

- Step 1: 21 tests, `maze_solver/tests/` — the first test suite `maze_solver` has had; its pre-existing search algorithms predate this repo's TDD convention and remain notebook-driven.
- Step 2: 32 tests, `path_maintenance/tests/`.
- Step 3: 29 more tests, also `path_maintenance/tests/` (61 total in that package).

```bash
uv run pytest maze_solver/tests/ path_maintenance/tests/ -v
# or: make test-maze-solver test-path-maintenance
```

## Design documentation

- [`documentation/path-maintenance/environment_design.md`](documentation/path-maintenance/environment_design.md) — step 1's full design: Environment Analysis, properties, API surface, resolved decisions, explicit non-goals.
- [`documentation/path-maintenance/scenario.md`](documentation/path-maintenance/scenario.md) — the `maintenance_lite` scenario.
- [`documentation/path-maintenance/experiments/01_maintenance_lite.md`](documentation/path-maintenance/experiments/01_maintenance_lite.md) — the confirmed run, frame-by-frame, with the embedded GIF.
- [`documentation/path-maintenance/graph-topology/environment_design.md`](documentation/path-maintenance/graph-topology/environment_design.md) — **implemented.** Step 2: exactly one change from step 1 — the environment becomes an AND-only DAG (`requires` edges, reusing `task_graph_solver`'s validation/`ready_nodes()` pattern, not its retry-economics-shaped `attempt()`/executors) instead of a spatial grid. Node state is still step 1's plain `OPEN`/`NEEDS_REPAIR` — no lifecycle yet, that's step 3. Scenario: [`deploy_chain_lite`](documentation/path-maintenance/graph-topology/scenario.md), a 5-node graph with one AND-join (`merge`, two parents). Contrast against `task_graph_solver`'s executors and GIF predictions, confirmed against the real run: [`algorithm_fit.md`](documentation/path-maintenance/graph-topology/algorithm_fit.md), [`experiments/01_deploy_chain_lite.md`](documentation/path-maintenance/graph-topology/experiments/01_deploy_chain_lite.md).
- [`documentation/path-maintenance/job-lifecycle/environment_design.md`](documentation/path-maintenance/job-lifecycle/environment_design.md) — **implemented.** Step 3, built on top of step 2's DAG: nodes as jobs with a real lifecycle (`PENDING → IN_PROGRESS → SUCCEEDED/FAILED`) driven by other autonomous agents (CI, pre-commit, k8s) rather than a single scripted mutation, and a wait loop `PathMaintenanceAgent` uses to sense completion instead of an instantaneous check. Reclassifies the environment as dynamic and multi-agent. Scenario, GIF predictions, and the confirmed real run (including a bug found and fixed along the way): [`scenario.md`](documentation/path-maintenance/job-lifecycle/scenario.md), [`algorithm_fit.md`](documentation/path-maintenance/job-lifecycle/algorithm_fit.md), [`experiments/01_deploy_chain_lite_lifecycle.md`](documentation/path-maintenance/job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md).
- [`documentation/d-star/`](documentation/d-star/) and [`documentation/task-graph/atomicguard-variant/`](documentation/task-graph/atomicguard-variant/) — related but explicitly out of scope so far: D* Lite/LPA* route repair (this agent's route never changes) and real, fallible `atomicguard` repair (this agent's repair is still a deterministic no-op). Both are named destinations for later steps in `environment_design.md`'s "relationship to other docs" section, not dependencies of what's built today.

## Implementation status

- **Step 1 (node repair on a fixed path): implemented.** `CellState`, `MazeEnvironment` additions, `PathMaintenanceAgent`, visualization, 21 tests, one confirmed scenario with GIF. PR: [#10](https://github.com/thompsonson/intelligent_agents/pull/10) (merged).
- **Step 2 (AND-DAG topology, still binary state): implemented.** New `path_maintenance/` package (independent of `maze_solver`, same way `task_graph_solver` is): `GraphNode`/`PathGraphEnvironment`, `PathMaintenanceAgent` generalized from coordinates to node ids, a graph-based (`networkx`) visualization, 32 tests, `deploy_chain_lite` confirmed with GIF.
- **Step 3 (job lifecycle, multi-agent sensing): implemented.** `JobState`/`JobNode`/`JobGraphEnvironment` (additive to step 2's package, nothing modified), a wait-loop `PathMaintenanceAgent` in a new module, `JobWalkResult`, a `pending`/`in_progress`-aware visualization, 29 more tests, `deploy_chain_lite` with a lifecycle confirmed with GIF. One real bug caught and fixed while implementing: `advance_jobs()` originally ticked every unresolved node regardless of readiness — see `job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md`.
