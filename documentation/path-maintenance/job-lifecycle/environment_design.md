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

## Resolved: topology moves to a DAG, in a new environment

A real pipeline (pre-commit → CI → k8s deploy, possibly with parallel checks) fans out; the maze's single corridor can't represent that without contorting it. Composition across the fanned-out nodes is AND — "every node on the path must be `SUCCEEDED`-or-repaired-to-`SUCCEEDED`" — the same semantics `task_graph_solver`'s `requires` already gives `TaskGraphEnvironment`. This step moves off the maze.

**Reviewed `task_graph_solver` directly before deciding how.** Its DAG *structure* is the right size; its execution *model* is not, and reusing it wholesale would be over-complicated for what this step needs:

- **Reusable as-is:** `requires`-only AND composition and its validation (`_validate_graph`'s cycle/unknown-dependency checks), and `ready_nodes(satisfied) -> list[str]` — the AND-respecting frontier primitive. A nice consequence: an AND-only DAG has no alternative routes to choose between, so there's no A*-equivalent search step needed at all here — the topology itself already *is* the plan, which is what "Known: full topology exposed from the start" already implied.
- **Wrong shape, not reusable:** `attempt(node_id) -> AttemptOutcome` conflates *starting* a job and *getting its resolved outcome* into one synchronous call — there's no percept for "started, not resolved yet" anywhere in `AttemptOutcome`'s three values (`PASS`/`RETRY`/`FATAL`, all already-terminal). `rmax`/`r_patience`/`pass_probability`/`_attempts_made` are all retry-*economics* that don't apply now that this step is deterministic and known, with no retry budget. All five existing executors (`TopologicalExecutor` included) are solving *which node to attempt next*, under retry economics — a decision problem `PathMaintenanceAgent` doesn't have, since its order is already known.
- **Missing entirely, from every environment in this repo so far, including the real `atomicguard`-backed one:** a lifecycle sensor. `check_invariant()` is the closest existing thing, but it's boolean and resolves instantly (one probability draw). Every real Guard already built (`ruff`, `mypy`, `python -m build`) is a synchronous subprocess call — none of them models "sense now, get told it's not resolved yet, sense again later."

**Decision:** a new, independent environment — not a `TaskGraphEnvironment` subclass, not an import. There's already a precedent for exactly this move: `real_task_graph_solver/core/environment.py`'s `RealCheckEnvironment` docstring states, verbatim, "Same public shape as `task_graph_solver`'s `TaskGraphEnvironment`" — an independent class matching the API shape, not inheriting it. Same move here: reuse the `requires`-validation and `ready_nodes()` *pattern*, drop everything retry-economics-shaped, add the lifecycle sensor that doesn't exist anywhere yet.

## Proposed lifecycle and API surface (signatures only — no implementation yet)

```python
class JobState(Enum):
    PENDING = "pending"          # not yet started
    IN_PROGRESS = "in_progress"  # started, not yet resolved
    SUCCEEDED = "succeeded"      # step 1's OPEN
    FAILED = "failed"            # step 1's NEEDS_REPAIR
```

```python
@dataclass
class JobNode:
    id: str
    requires: Tuple[str, ...] = ()
    # deliberately no pass_probability/rmax/r_patience/retry_flavor - see
    # "wrong shape, not reusable" above. This step is deterministic and
    # known; there is no retry budget to track.
```

```python
class JobGraphEnvironment:
    nodes: Dict[str, JobNode]

    def __init__(self, nodes: Dict[str, JobNode], config: JobGraphConfig):
        """Same requires-validation shape as TaskGraphEnvironment._validate_graph
        (cycle detection, unknown-dependency checks) - reused as a pattern,
        not imported."""

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Same AND-gating shape as TaskGraphEnvironment.ready_nodes(): the
        frontier of nodes whose requires are all satisfied and haven't
        themselves resolved yet."""

    def get_job_state(self, node_id: str) -> JobState:
        """Current lifecycle state. Never mutates anything, consumes no
        budget - a pure sense, same contract as step 1's get_cell_state()."""

    def advance_jobs(self) -> None:
        """Moves every PENDING/IN_PROGRESS node one step through its
        configured, deterministic lifecycle. Represents the other agents
        (CI, k8s, pre-commit) doing their own work between our agent's
        senses - not something PathMaintenanceAgent calls itself. Exactly
        who calls this (scenario setup stepping through a script, or
        something that stands for the other agents more literally) is
        open - see below."""

    def repair_job(self, node_id: str) -> None:
        """Deterministic repair of a FAILED node: same no-op-that-always-
        succeeds contract as step 1's repair_cell()."""
```

```python
class PathMaintenanceAgent:
    def __init__(self, environment: JobGraphEnvironment, order: List[str]):
        """`order` is the belief state, generalized: a topological ordering
        of the DAG's nodes (computed once, ties broken by id for
        reproducibility - same tie-break TopologicalExecutor already uses),
        taking the place of step 1's coordinate path. The class keeps its
        name and its walk() shape - only the domain type of one element
        changes, from a grid coordinate to a node id. "The path of a change
        through infra" is still the right framing; it's just a topological
        order instead of an A*-computed route now."""

    def walk(self) -> WalkResult:
        """Same walk as step 1, generalized from coordinates to node ids,
        with one change: before treating a node as SUCCEEDED or FAILED,
        keep sensing (get_job_state()) while it's PENDING or IN_PROGRESS.
        Processes `order` strictly one node at a time, sequentially - no
        concurrent handling of multiple in-progress nodes in this step (see
        "Not decided"). Still never starts a job, never recomputes or
        deviates from `order`."""
```

`WalkResult` likely needs a new field recording how many senses were spent waiting per node, the same way `task_graph_solver`'s `ExecutionResult` tracks retry cost — proposed, not settled.

## Where this lives

Not `maze_solver/` — nothing about a DAG of jobs is spatial. Following the same precedent `task_graph_solver` itself set ("a new toy environment built around that shape directly, instead of retrofitting the maze's... model onto something that's structurally different"): a new top-level package, `path_maintenance/`, sibling to `maze_solver/` and `task_graph_solver/`. Step 1's code stays exactly where it is in `maze_solver/agents/` — it's genuinely maze-specific and already shipped; nothing here proposes moving or generalizing it retroactively. `PATH_MAINTENANCE.md` already documents both under one umbrella and doesn't need to change shape, just gain a second "System Architecture" section once this exists.

## Not decided

- **What exactly resolves `advance_jobs()`, and who calls it.** For a deterministic, known lifecycle, the simplest version is scenario config saying "this job takes exactly N senses to leave `IN_PROGRESS`" — but whether that's driven by scenario setup stepping a script (step 1's `inject_repairs()` shape) or something modeling the other agents more literally is unresolved.
- **Whether `FAILED` exists yet, or only `SUCCEEDED`.** Reusing step 1's repair pattern for a sensed `FAILED` outcome costs nothing new to build and exercises both branches in a demo — but if the goal for this step is narrowly "prove the wait loop," `SUCCEEDED`-only might be the smaller, more honest slice. Leaning toward including `FAILED` since the repair path already exists and not exercising it would leave the GIF one-note, but flagging this as a real scope choice, not an obvious one.
- **Sequential-but-single-threaded walk, confirmed for this step only.** `walk()` processes `order` one node at a time even though the DAG can have several ready nodes at once — deliberately not dispatching/polling multiple in-progress nodes concurrently yet, since that needs real time-modeling (whose poll happens when) this step doesn't have a reason to build. Worth flagging explicitly since it's the one place "the DAG can fan out" and "the agent still walks a single fixed order" are in tension — resolved for now by picking one topological order and treating it exactly like step 1's path, fan-out and all being resolved into a line before the agent ever sees it.
- **`WalkResult`'s new field(s) for wait/poll cost** — shape TBD, see above.
- **`path_maintenance/` as the new package name** — proposed, not confirmed.
