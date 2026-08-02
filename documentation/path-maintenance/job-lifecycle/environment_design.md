# Job Lifecycle: Environment Design (Step 2)

## Purpose

Step 1 (`../environment_design.md`) models a node as either `OPEN` or `NEEDS_REPAIR` — a state that's simply *true or false*, sensed once, fixed in one deterministic call. That fits a maze cell. It doesn't fit the real target this arc is walking toward: nodes that are **jobs** — a pre-commit hook, a CI run, a Kubernetes deployment — which don't just have a state, they have a *lifecycle*. A job is triggered, runs for a while, and only later resolves to success or failure. Step 1 has no way to represent "not finished yet," so it can't represent a job at all, only an instantaneous check.

This document is step 2: giving nodes that lifecycle, and giving `PathMaintenanceAgent` the ability to wait for it. It builds on step 1's environment and agent — the fixed belief-state path, the repair-on-failure branch — rather than replacing them.

## What actually changes, and what doesn't

**Still true, carried over from step 1 unchanged:**
- The belief-state path is still computed once and walked as-is. No plan/route recalculation.
- A `FAILED` node (this step's name for what step 1 called `NEEDS_REPAIR`) still gets repaired by the same deterministic, always-succeeding action step 1 already built. This step is not about making repair real — that's still later work, same as it was after step 1.

**New in this step:**
- A node's state is no longer binary. It has a lifecycle: `PENDING → IN_PROGRESS → {SUCCEEDED, FAILED}` (`SUCCEEDED`/`FAILED` are this step's names for step 1's `OPEN`/`NEEDS_REPAIR`).
- Something other than `PathMaintenanceAgent` drives that lifecycle forward. The agent never starts a job — it only ever senses where a job currently is in its lifecycle, and waits when it isn't finished.

## Terminology: retiring "Driver" for this environment

`documentation/d-star/` and `documentation/task-graph/` both use "Driver" for whatever calls `break_edge()`/`fix_task()` between an agent's moves — a name that's stuck without ever being examined closely. Looking at it directly: it's been quietly covering two different things.

1. **Scenario setup** — a notebook cell or test calling `env.inject_repairs(...)` once, before a run starts, to script a demonstration. This is not a PEAS participant at all — no goals, no autonomy, just test fixture data. Step 1's `inject_repairs()` is exactly this.
2. **Another autonomous system** — a CI runner, a Kubernetes controller, pre-commit tooling. These genuinely have their own goals and their own behavior; they are not a neutral setup mechanism, they're independent actors this environment doesn't control.

Step 1 only ever needed sense (1). Step 2 needs sense (2) for real, and AIMA already has a name for it that "Driver" was standing in for without earning: **another agent, in a multi-agent environment.** That's not a euphemism — it's a real reclassification of the environment (see below), and it's the textbook-correct move once the external thing changing state is itself goal-directed rather than scripted. "Driver" stays exactly as-is in `documentation/d-star/` and `documentation/task-graph/` — this is a naming decision scoped to `path-maintenance/`, not a repo-wide rename.

## Environment properties (step 2)

Using the same canonical AIMA property list `CLAUDE.md`'s own PEAS analyses and `documentation/d-star/environment_changes.md`'s table use — step 1's table used a slightly different, non-canonical axis set; this reconciles it:

| Property | Step 1 | Step 2 | Why |
|---|---|---|---|
| **Static/Dynamic** | Static during the walk (one discrete pre-walk mutation) | **Dynamic** | Other agents change node state *while* `PathMaintenanceAgent` is walking/waiting, not in one scripted event beforehand |
| **Single/Multi-agent** | Single-agent (the only other participant was scenario setup, not a PEAS agent) | **Multi-agent** | CI/pre-commit/k8s are themselves goal-directed, autonomous systems — genuinely other agents, not exogenous noise |
| **Deterministic/Stochastic** | Deterministic (repair always succeeds) | **Deterministic** | Kept simple, deliberately: a job's resolution (when, and to what outcome) follows a known, fixed rule per scenario, not a probability draw. Mirrors step 1's own choice to keep repair a sure thing rather than reaching for `task_graph_solver`-style `pass_probability` this early |
| **Episodic/Sequential** | Episodic (each cell's outcome doesn't depend on history beyond itself) | **Sequential** | How many times a node has already been sensed while `IN_PROGRESS` is meaningful history — the same shape as `task_graph_solver`'s "retry history matters" property, now applying to poll count instead of retry count |
| **Discrete/Continuous** | Discrete | Discrete, with a caveat | States stay discrete (four values instead of two). Time doesn't — polling can happen at any moment, not fixed ticks. Worth naming rather than leaving implicit, but not a full property flip |
| **Known/Unknown** | Known (full topology exposed from the start) | **Known** | The *rule* governing a job's resolution is configured and known to the scenario (same "known but seeded" shape as `task_graph_solver`'s `pass_probability`), even though `PathMaintenanceAgent` itself never reads that configuration — it only polls |
| **Observable** | Fully, but lazily | **Unchanged** | The agent could still query any node's current lifecycle state at any time; it still chooses to only check what it's about to act on. Multi-agent-ness changed *who* causes state change, not *what's visible* when asked |

## Proposed lifecycle and API surface (signatures only — no implementation yet)

```python
class JobState(Enum):
    PENDING = "pending"          # not yet started
    IN_PROGRESS = "in_progress"  # started, not yet resolved
    SUCCEEDED = "succeeded"      # step 1's OPEN
    FAILED = "failed"            # step 1's NEEDS_REPAIR
```

```python
class MazeEnvironment:  # or its step-2 environment, see "Not decided" below
    def get_job_state(self, cell: Tuple[int, int]) -> JobState:
        """Current lifecycle state. Never mutates anything - a pure sense,
        same contract as step 1's get_cell_state()."""

    def advance_jobs(self) -> None:
        """Moves every PENDING/IN_PROGRESS job on the path one step through
        its configured, deterministic lifecycle. Represents the other
        agents (CI, k8s, pre-commit) doing their own work between our
        agent's senses - not something PathMaintenanceAgent calls itself.
        Exactly who calls this (scenario setup stepping through a script,
        or something that stands for the other agents more literally) is
        open - see below."""
```

```python
class PathMaintenanceAgent:
    def walk(self) -> WalkResult:
        """Same walk as step 1, with one change: before treating a cell as
        SUCCEEDED or FAILED, keep sensing (get_job_state()) while it's
        PENDING or IN_PROGRESS. Still never starts a job, never recomputes
        or deviates from the path."""
```

`WalkResult` likely needs a new field recording how many senses were spent waiting per cell, the same way `task_graph_solver`'s `ExecutionResult` tracks retry cost — proposed, not settled.

## Not decided

- **Topology: stay in the maze, or move to `task_graph_solver`'s DAG?** A real pipeline (pre-commit → CI → k8s deploy, possibly with parallel checks) can fan out; the maze's single corridor can't represent that without contorting it. `task_graph_solver`'s `requires` is already AND-composition — "every node on the path must be `SUCCEEDED`-or-repaired-to-`SUCCEEDED`," exactly the composition a fanned-out pipeline needs. Genuinely open: build the job lifecycle once more on the linear maze path (cheapest, reuses step 1's tests and viz directly, but is throwaway work the moment fan-out is needed), or move straight to a small DAG scenario (2-3 nodes, one AND-join) since the linear case is a degenerate special case of it anyway. Leaning toward the DAG, since `task_graph_solver` already has the AND-`requires` structure and the `break_task`/`fix_task` Driver-hook shape built and tested — but not deciding this without discussing it explicitly, since it also means this step's home moves out of `maze_solver/agents/`.
- **What exactly resolves `advance_jobs()`, and who calls it.** For a deterministic, known lifecycle, the simplest version is scenario config saying "this job takes exactly N senses to leave `IN_PROGRESS`" — but whether that's driven by scenario setup stepping a script (step 1's `inject_repairs()` shape) or something modeling the other agents more literally is unresolved.
- **Whether `FAILED` exists yet, or only `SUCCEEDED`.** Reusing step 1's `repair_cell()` no-op for a sensed `FAILED` outcome costs nothing new to build and exercises both branches in a demo — but if the goal for this step is narrowly "prove the wait loop," `SUCCEEDED`-only might be the smaller, more honest slice. Leaning toward including `FAILED` since the repair path already exists and not exercising it would leave the GIF one-note, but flagging this as a real scope choice, not an obvious one.
- **`WalkResult`'s new field(s) for wait/poll cost** — shape TBD, see above.
