# Task Graph Environment: Design

## Purpose

`maze_solver/`'s environment is a grid: nodes are cells, edges connect adjacent cells, and an agent occupies exactly one node at a time, choosing which neighbor to move to next (an OR-choice among alternatives). The `atomicguard` stress tests (`documentation/d-star/beyond_the_maze.md`, `documentation/lrta/beyond_the_maze.md`) found that real guard-graph workflows — GitHub PR merges, but also disk checks, cert checks, package repair, backup verification, all sitting in `atomicguard`'s `examples/sysadmin/` — don't have that shape at all. They're DAGs of prerequisite steps: a step's `:requires` lists the other steps that must **all** have already succeeded (AND-composition), and there's no "pick whichever neighbor is cheapest" choice anywhere in the corpus. `task_graph_solver` is a new toy environment built around that shape directly, instead of retrofitting the maze's OR-graph model onto something that's structurally different.

This document specifies the environment. `scenarios.md` specifies concrete graphs built from it. `algorithm_fit.md` maps algorithms already designed elsewhere in this repo onto the scenarios where they actually apply.

## Environment Analysis

| Element | Description |
|---|---|
| **Performance** | Execute a task graph to completion (all nodes satisfied) as cheaply as possible, where "cheaply" is measured in retry cost, not path length |
| **Environment** | A DAG of guarded tasks with AND-dependency edges; no real commands run — every task's outcome is simulated |
| **Actuators** | Attempt a task (consumes a simulated retry budget); for acting tasks, this is a genuine world-mutation in the domain being modeled (simulated, not executed) |
| **Sensors** | Per-task pass/retry/fatal outcome, retry count actually spent, which prerequisites are currently satisfied |

## Environment properties

| Property | Value | Why |
|---|---|---|
| **Topology** | Known and fixed | The DAG structure (which tasks, which `:requires` edges) is defined by the scenario up front — this mirrors the real `.dspddl` files, which are static declarations, not discovered at runtime |
| **Task outcomes** | Stochastic, seeded | Each attempt at a task draws pass/retry/fatal from a configured probability, so behavior is reproducible for teaching (fixed seed) but not a hardcoded script |
| **Static vs. dynamic** | Static by default, dynamic as an opt-in Driver hook | Most scenarios don't need exogenous change — the retry/cost story is interesting on its own. A `break_task`/`fix_task` hook (same shape as the maze's `break_edge`/`fix_edge`) exists for scenarios that specifically want to demonstrate D* Lite-style repair, but isn't exercised by default |
| **Sequential** | Yes | Retry history matters — a task's remaining budget depends on attempts already spent, same as the maze's move history mattering once a bridge can break |
| **Discrete** | Yes | Finite task set, finite retry budget per task |

## Core primitives

### Node: a guarded task

Every node is shaped like a DS-PDDL Action Pair, simplified to what a simulation needs — no real `Generator`/`Effector` implementation, just the parameters that determine simulated behavior:

```python
@dataclass
class TaskNode:
    id: str
    kind: Literal["sensing", "acting"]       # idempotent (read-only) vs world-mutating
    retry_flavor: Literal["sensing", "generation", "repair"]
    pass_probability: float                   # per-attempt chance of a Guard pass
    rmax: int                                 # workflow-level retry budget
    r_patience: int | None = None             # escalate-early threshold, must be < rmax
    requires: tuple[str, ...] = ()            # AND-dependencies — ALL must be satisfied first
```

`kind` and `retry_flavor` are deliberately separate fields, not inferred from each other. `beyond_the_maze.md`'s three-flavors finding was precisely that these don't line up automatically: a sensing-kind task usually has `retry_flavor="sensing"`, but `generate-action-list` in the real corpus is neither a sensing nor an acting *effector* in the traditional sense — it's a generation step with its own retry semantics (`retry_flavor="generation"`), and conflating it with either of the other two was the mistake the earlier analysis had to correct. Keeping both fields explicit makes that mistake impossible to reintroduce silently.

### Edge: `requires`, AND only

```python
requires: tuple[str, ...]
```

A node is *ready* to attempt only once every id in `requires` has reached a passed state. There is no OR-equivalent — no "ready once any one of these has passed." This matches the DS-PDDL grammar exactly (`requires: tuple[str, ...]` in `atomicguard`'s AST, confirmed by reading the parser), not an approximation of it. Where a maze-like OR-choice is wanted for contrast (to run D* Lite/A*/LRTA* meaningfully), scenarios achieve it by being a single linear chain — the degenerate case where "AND of one thing" and "OR of one thing" are the same, discussed further in `algorithm_fit.md`.

### Simulated task execution

No `bash`/`gh` calls, no real files, no real repos. One attempt at a node:

```python
def attempt(node: TaskNode, rng: Random) -> AttemptOutcome:
    """Draw a simulated outcome for one attempt at `node`.
    Returns PASS, RETRY, or FATAL. Consumes one unit of `node`'s retry budget.
    Escalates to FATAL early if r_patience consecutive similar failures occur,
    even if rmax attempts remain — mirrors atomicguard's Extension 09 invariant
    (r_patience < rmax), found in application/workflow.py while reading the
    real system, not invented for this design."""
```

```python
class TaskGraphEnvironment:
    nodes: dict[str, TaskNode]
    # ... existing methods unchanged in spirit from MazeEnvironment: a graph, a way
    # to query readiness, a way to attempt a node

    def ready_nodes(self, satisfied: set[str]) -> list[str]:
        """Nodes whose `requires` are fully contained in `satisfied` and haven't
        themselves been satisfied yet — the frontier of things that could be
        attempted next."""

    def attempt(self, node_id: str) -> AttemptOutcome:
        """One simulated attempt at `node_id`. Records retry cost."""

    def break_task(self, node_id: str) -> None:
        """Optional Driver hook: force a previously-passable task to fail permanently.
        Not exercised unless a scenario specifically wants D* Lite-style repair."""

    def fix_task(self, node_id: str) -> None:
        """Inverse of break_task."""
```

## Comparison: maze environment vs. task graph environment

| | `MazeEnvironment` | `TaskGraphEnvironment` |
|---|---|---|
| Edge semantics | OR — pick one neighbor among several | AND — a node needs *all* its `requires` satisfied |
| What an "agent" does | Occupies one cell, moves to an adjacent cell | Picks a ready node to attempt (topological frontier, possibly several ready at once) |
| Cost model | Uniform step cost (or terrain-varying, per `search_algorithms/README.md`'s muddy-terrain example) | Per-node retry cost, drawn from a configured probability, tagged with a retry flavor |
| Dynamism | Static by default; a bridge can be designated to break/fix | Static by default; a task can be designated to break/fix (same Driver pattern) |
| Natural algorithm family | D* Lite / A* / LRTA* — all OR-choice, `min`-over-successors | AO* — AND/OR composition; D* Lite/LRTA* only apply to single-chain scenarios (see `algorithm_fit.md`) |

## Not decided

- Whether `attempt()` should be allowed to retry a node whose `requires` are satisfied but which itself already reached `FATAL` — real DS-PDDL treats a fatal Guard as terminal for that workflow run; the toy environment should probably match that rather than inventing a resurrection mechanic, but it's worth stating explicitly before writing the executor loop.
- Whether cost/retry data should be queryable per-node only, or also aggregated per-`retry_flavor` — the latter is what `algorithm_fit.md`'s LRTA* mapping actually needs (learn only from `retry_flavor="repair"` observations), so the environment's data model should probably expose that split natively rather than making every algorithm re-derive it.
