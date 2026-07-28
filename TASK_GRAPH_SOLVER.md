# Task Graph Solver: Documentation

This is a sibling document to [`README.md`](README.md), in the same spirit and structure, for a different environment: **`task_graph_solver`**, a toy simulation of DS-PDDL-style guard-graph workflows (GitHub PR merges, disk checks, package repair — anything shaped like [`atomicguard`](https://github.com/thompsonson/atomicguard)'s `examples/sysadmin/`), built to run and watch D* Lite, LRTA*, and AO* actually execute, rather than only read about them.

Where `maze_solver`'s environment is a grid — an agent occupies one cell, choosing which neighbor to move to (an OR-choice) — `task_graph_solver`'s environment is a DAG of guarded tasks connected by **AND**-only `requires` edges: a task is ready only once *every* one of its dependencies has succeeded. That's the one structural feature the maze can't produce without deliberately constructing it, and it's the reason this whole module exists — see [`documentation/task-graph/environment_design.md`](documentation/task-graph/environment_design.md) for the full design rationale.

## Environment Setup

```bash
# Same uv-based workflow as the maze_solver setup in README.md
uv venv
source .venv/bin/activate
uv pip install pytest networkx matplotlib imageio

# Run the test suite
uv run pytest task_graph_solver/tests/ -v
# or: make test-task-graph
```

No real `gh`/`bash` commands ever run — every task's outcome is a simulated draw from a configured probability. See [`documentation/task-graph/environment_design.md`](documentation/task-graph/environment_design.md)'s Environment Analysis for why.

## System Architecture

```
task_graph_solver/
├── core/
│   ├── config.py          # TaskGraphConfig - just the RNG seed
│   ├── domain.py           # TaskNode, AttemptOutcome
│   ├── environment.py      # TaskGraphEnvironment
│   └── results.py          # ExecutionResult
├── algorithms/
│   ├── topological.py      # TopologicalExecutor - baseline, no heuristic, no repair
│   ├── ao_star.py           # AOStarExecutor - AND-composition cost tracking
│   ├── d_star_lite.py       # DStarLiteExecutor - incremental repair via sensed breaks/fixes
│   └── lrta_star.py         # LRTAStarLearner - learns retry cost over repeated trials
├── scenarios/
│   ├── disk_check_lite.py       # 1 node, no edges - the trivial baseline
│   ├── repair_packages_lite.py  # 2-node linear chain - cleanest LRTA*/D* Lite demo
│   └── pr_merge_lite.py         # 8 nodes, two AND-joins - the motivating case
└── visualization/
    ├── graph_view.py        # DAG rendering + GIF animation (networkx + matplotlib + imageio)
    └── learning_curve.py    # LRTA* convergence line chart
```

Full build order and the algorithm-to-scenario mapping: [`documentation/task-graph/algorithm_fit.md`](documentation/task-graph/algorithm_fit.md).

## Class Overview

### TaskNode

```python
@dataclass
class TaskNode:
    """A guarded task: one node in a task graph.

    Modeled on a DS-PDDL Action Pair (Guard + Generator + Effector), simplified
    to what a simulation needs. `kind` and `retry_flavor` are independent
    fields on purpose: conflating them (e.g. assuming "acting" always means
    "repair" flavor) was the mistake documentation/lrta/beyond_the_maze.md had
    to correct once already, when a pure local generation step turned out to
    be neither straightforwardly sensing nor acting in the real system's sense.

    Attributes:
        id: Unique identifier within a TaskGraphEnvironment.
        kind: "sensing" (idempotent, read-only) or "acting" (world-mutating).
        retry_flavor: What a retry at this node actually means - "sensing"
            (absorbing transient infra flakiness), "generation" (an LLM
            output failed local format validation), or "repair" (a real
            world-mutating action was attempted and failed). Only "repair"
            retries are real learnable cost for an LRTA*-style agent.
        pass_probability: Per-attempt chance of a Guard pass.
        rmax: Total attempt budget before this node is declared FATAL.
        r_patience: Consecutive-failure threshold that escalates to FATAL
            before rmax is exhausted. Must be strictly less than rmax,
            mirroring the invariant found in atomicguard's own source
            (application/workflow.py, "Extension 09").
        requires: AND-dependencies - every id here must be satisfied before
            this node is ready to attempt. There is no OR-equivalent.
    """
```

### TaskGraphEnvironment

```python
class TaskGraphEnvironment:
    """Simulated DAG of guarded tasks with AND-only `requires` edges.

    No real commands run - every node's outcome is drawn from its configured
    `pass_probability`. Mirrors MazeEnvironment's separation of concerns: the
    environment knows node validity/cost/readiness, but does not track which
    nodes an agent has already satisfied - that's the algorithm's job.

    Methods:
        ready_nodes(satisfied): AND-gated frontier - nodes whose requires
            are all in `satisfied` and aren't themselves satisfied yet.
        attempt(node_id): One simulated attempt; consumes retry budget
            unless the node is Driver-broken.
        retries_spent(node_id): Attempts made so far.
        break_task(node_id) / fix_task(node_id): Driver hook, mirrors
            MazeEnvironment's break_edge/fix_edge.
        drain_changed_tasks(): The 'sense' step an incremental-repair agent
            polls once per move - mirrors drain_changed_edges().
    """
```

Constructing one validates the graph up front: `requires` referencing an unknown node, or any cycle (direct, self-referential, or longer), raises `ValueError` rather than silently deadlocking.

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    """Result of running an algorithm over a TaskGraphEnvironment to completion.

    Attributes:
        success: True only if every node in the graph ended up satisfied.
        satisfied: Nodes that reached PASS.
        fatal: Nodes that reached FATAL.
        unreachable: Nodes that never became ready because at least one of
            their `requires` ended up in `fatal` - distinct from `fatal`
            itself, since these were never attempted at all.
        trace: Ordered (node_id, outcome) pairs for every attempt made.
    """
```

### The four algorithms

| Class | What it adds over the baseline | Scenario it targets |
|---|---|---|
| `TopologicalExecutor` | Nothing - attempts whatever's ready, sorted by id, no learning, no repair | All three scenarios; the smoke-test baseline |
| `AOStarExecutor` | `h`, a cost-to-solve estimate per solved node, composed as `own_attempts + max(h(child) for child in requires)` — the AND-composition rule from [`search_algorithms/ao_star.md`](search_algorithms/ao_star.md) | `pr_merge_lite`'s `merged` and `released` joins |
| `DStarLiteExecutor` | Senses Driver `break_task`/`fix_task` calls via `drain_changed_tasks()` and returns a previously-FATAL node to consideration if it was fixed - the thing `TopologicalExecutor` structurally cannot do | `repair_packages_lite` and `pr_merge_lite`, wherever a Driver break/fix is exercised |
| `LRTAStarLearner` | Learns `h_table` for `retry_flavor="repair"` nodes only, over repeated trials via an `env_factory(trial_index)` callable | `repair_packages_lite`'s `repair` node - the cleanest isolation of the "repair-attempt retry is learnable cost" signal |

Each one's honest scope boundary is documented in its own docstring and in [`documentation/task-graph/algorithm_fit.md`](documentation/task-graph/algorithm_fit.md) - none of them claims to solve `pr_merge_lite` end to end by itself.

## Scenarios

- **`disk_check_lite`** — 1 node, no edges, no repair path. Modeled on `atomicguard/examples/sysadmin/workflows-guard/disk_check.dspddl`.
- **`repair_packages_lite`** — `repair` (acting, repair-flavor) → `verify` (sensing, requires `repair`). Modeled on `repair_packages.dspddl`.
- **`pr_merge_lite`** — 8 nodes, two AND-joins (`merged` requires 2 children, `released` requires 3). Modeled on the `pr_merge` workflow family, with `released`'s fan-in deliberately made explicit (three `requires` edges) rather than hidden inside one opaque script the way the real system's `downstream-ci-passed` guard does — see [`documentation/lrta/beyond_the_maze.md`](documentation/lrta/beyond_the_maze.md).

Full detail: [`documentation/task-graph/scenarios.md`](documentation/task-graph/scenarios.md).

## Visualization Examples

Same idea as `README.md`'s animated graph GIFs for BFS/DFS/Greedy/A* — watching an algorithm's state evolve step by step, rather than reading a final answer. `task_graph_solver`'s DAG has two features the maze's grid doesn't: **AND-join nodes are drawn as squares** instead of circles, and node color reflects live status (white = pending, green = satisfied, red = fatal, gray = unreachable).

### AO* solving `pr_merge_lite`

![AO* solving pr_merge_lite](task_graph_solver/animations/ao_star_pr_merge_lite.gif)

All eight nodes resolve in 8 steps. Watch `merged` (a square) wait for both `ci-check` and `apply-actions` before turning green, and `released` (a square) wait for all three deploy branches — the AND-composition this environment exists to demonstrate, not asserted in prose but actually executing.

**Step-by-step walkthrough with the exact `h` arithmetic at each node:** [`documentation/task-graph/experiments/01_ao_star_pr_merge_lite.md`](documentation/task-graph/experiments/01_ao_star_pr_merge_lite.md).

### D* Lite: break a node, watch it recover

![D* Lite break and fix on pr_merge_lite](task_graph_solver/animations/d_star_lite_pr_merge_lite.gif)

The Driver breaks `apply-actions` *before* it's ever attempted. `ci-check` and `generate-actions` proceed independently and turn green regardless. `apply-actions` turns red (fatal) the moment it's attempted while broken, which blocks `merged` and everything downstream — they turn gray (blocked by a fatal ancestor, not merely pending), not attempted at all. The Driver then fixes `apply-actions`; `DStarLiteExecutor` senses the change, returns it to consideration, and the whole graph completes. Critically: `ci-check`, already green before the break, is never touched again — the repair is local, not a full replan. Contrast with `TopologicalExecutor` run against the identical break: it has no sensing loop, so a fix arriving after its run has already finished is simply invisible to it — see `test_topological_executor_cannot_recover_from_a_fix_after_the_fact` in `task_graph_solver/tests/test_scenarios.py`.

**Step-by-step walkthrough, including the Driver/Agent sequence diagram and the `TopologicalExecutor` contrast:** [`documentation/task-graph/experiments/02_d_star_lite_pr_merge_lite.md`](documentation/task-graph/experiments/02_d_star_lite_pr_merge_lite.md).

### LRTA*: learning a node's true cost over repeated trials

![LRTA* convergence](task_graph_solver/animations/lrta_star_convergence.png)

**Trial-by-trial walkthrough of the update rule, including why trial 1 doesn't start at the true worst case:** [`documentation/task-graph/experiments/03_lrta_star_convergence.md`](documentation/task-graph/experiments/03_lrta_star_convergence.md).

A node with `pass_probability=0.3` (rmax=8) run through `LRTAStarLearner` for 25 trials. `h(repair)` starts at 4 (an early, lucky sequence of failures), jumps to 7 the first time a worse trial is actually observed, and then holds — the `max` update rule (`h(s) ← max(h(s), retries_spent(s))`) means the estimate can only grow, never shrink, and it stops moving once the true worst case has been seen. This is the same node used throughout `documentation/lrta/beyond_the_maze.md`'s repair-cost discussion, now actually learned rather than only described.

## Testing

```bash
make test-task-graph
# or directly:
uv run pytest task_graph_solver/tests/ -v
```

75 tests as of this writing, covering: graph validation (unknown deps, cycles), AND-gating and unreachable propagation, cost composition (AO*), repair locality (D* Lite, including on AND-join siblings), learned-cost convergence (LRTA*), and the visualization/animation code itself (smoke tests against real algorithm runs, not just static assertions).

## Design documentation

This module is design-doc-first, same discipline as the D* Lite maze work:

- [`documentation/task-graph/environment_design.md`](documentation/task-graph/environment_design.md) — the core primitives
- [`documentation/task-graph/scenarios.md`](documentation/task-graph/scenarios.md) — the three toy graphs
- [`documentation/task-graph/algorithm_fit.md`](documentation/task-graph/algorithm_fit.md) — which algorithm targets which scenario, and the explicit build order
- [`search_algorithms/ao_star.md`](search_algorithms/ao_star.md) — the AO* algorithm reference (notation, pseudocode, properties)
- [`documentation/d-star/`](documentation/d-star/) and [`documentation/lrta/`](documentation/lrta/) — the maze-side D* Lite/LRTA* design work and the real-`atomicguard` stress tests that motivated this whole module
- [`documentation/task-graph/or-groups/`](documentation/task-graph/or-groups/) — **design-stage, not yet implemented.** Extends `pr_merge_lite` (same topology, not a new domain) with OR-groups (`apply-actions` split into three variant strategies sharing one slot, only one needs to pass) and an explicit goal distinct from "every node satisfied" — grounded in `atomicguard`'s own real proposal for fixing its "single-exit corridor" RL bottleneck (`docs/archive/notes/2026-02-25T18-multi-path-rl-design.md`). This is what finally gives `AOStarExecutor` a real OR-choice to make; `DStarLiteExecutor` gets its existing repair-locality capability applied to a whole group instead of one node, not a new "reroute" capability — corrected in `or-groups/algorithm_fit.md` after an earlier overclaim
