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

## Scenario

`maintenance_lite`: `Config(maze_size=5, maze_id=7)`, a 17-cell corridor with one turn, two path-relative injected repairs (at roughly the 1/3 and 2/3 points). Chosen for a legible demo — not so few injections that repair only happens once, not so many that individual before/after transitions blur together. Full detail: [`documentation/path-maintenance/scenario.md`](documentation/path-maintenance/scenario.md).

## Visualization Example

`path_maintenance_view.py` mirrors `task_graph_solver/visualization/graph_view.py`'s event-driven pattern (`record_walk()`/`animate_walk()`) rather than `maze_solver`'s frontier-based `SearchAlgorithmDashboard` — a fixed walk has no frontier to show. Cell color and the agent's position marker are kept as separate visual channels; a repaired cell renders a distinct dark green from a cell that was always open, so "was broken, now fixed" stays visible rather than blending into "was always fine." The GIF never reveals a `NEEDS_REPAIR` cell before the agent actually senses it — the visualization doesn't leak information the agent doesn't have.

Full walkthrough with frame-by-frame commentary: [`documentation/path-maintenance/experiments/01_maintenance_lite.md`](documentation/path-maintenance/experiments/01_maintenance_lite.md).

## Testing

21 tests, `maze_solver/tests/` — the first test suite this module has had; `maze_solver/`'s pre-existing search algorithms predate this repo's TDD convention and remain notebook-driven.

```bash
uv run pytest maze_solver/tests/ -v
# or: make test-maze-solver
```

## Design documentation

- [`documentation/path-maintenance/environment_design.md`](documentation/path-maintenance/environment_design.md) — step 1's full design: Environment Analysis, properties, API surface, resolved decisions, explicit non-goals.
- [`documentation/path-maintenance/scenario.md`](documentation/path-maintenance/scenario.md) — the `maintenance_lite` scenario.
- [`documentation/path-maintenance/experiments/01_maintenance_lite.md`](documentation/path-maintenance/experiments/01_maintenance_lite.md) — the confirmed run, frame-by-frame, with the embedded GIF.
- [`documentation/path-maintenance/job-lifecycle/environment_design.md`](documentation/path-maintenance/job-lifecycle/environment_design.md) — **design in progress, not yet implemented.** Step 2: nodes as jobs with a real lifecycle (`PENDING → IN_PROGRESS → SUCCEEDED/FAILED`) driven by other autonomous agents (CI, pre-commit, k8s) rather than a single scripted mutation, and the wait loop `PathMaintenanceAgent` needs to sense completion instead of an instantaneous check. Reclassifies the environment as dynamic and multi-agent — see that document for the full property-by-property reasoning and what's still genuinely undecided (topology: stay in the maze, or move to `task_graph_solver`'s AND-DAG once real fan-out is in scope).
- [`documentation/d-star/`](documentation/d-star/) and [`documentation/task-graph/atomicguard-variant/`](documentation/task-graph/atomicguard-variant/) — related but explicitly out of scope so far: D* Lite/LPA* route repair (this agent's route never changes) and real, fallible `atomicguard` repair (this agent's repair is still a deterministic no-op). Both are named destinations for later steps in `environment_design.md`'s "relationship to other docs" section, not dependencies of what's built today.

## Implementation status

- **Step 1 (node repair on a fixed path): implemented.** `CellState`, `MazeEnvironment` additions, `PathMaintenanceAgent`, visualization, 21 tests, one confirmed scenario with GIF. PR: [#10](https://github.com/thompsonson/intelligent_agents/pull/10).
- **Step 2 (job lifecycle, multi-agent sensing): design in progress.** Environment properties and terminology settled (dynamic, multi-agent, deterministic, sequential, known); topology (stay in the maze vs. move to `task_graph_solver`'s DAG) and the exact lifecycle-resolution mechanism are still open — see `job-lifecycle/environment_design.md`'s "Not decided" section.
