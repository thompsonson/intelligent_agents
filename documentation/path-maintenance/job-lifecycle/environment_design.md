# Job Lifecycle: Environment Design (Step 3)

## Purpose

Step 2 (`../graph-topology/environment_design.md`) moves the environment from a maze to an AND-only DAG, but keeps step 1's node state exactly as it was: `OPEN`/`NEEDS_REPAIR`, sensed once, fixed in one deterministic call. That's still not what a real pipeline node is. A pre-commit hook, a CI run, a Kubernetes deployment doesn't just have a state, it has a *lifecycle* — triggered, running for a while, only later resolving to success or failure. Step 2 has no way to represent "not finished yet," so a `GraphNode` still isn't really a job, just a relabeled maze cell sitting on a DAG instead of a grid.

This document is step 3, built on top of step 2's DAG — not on step 1's maze directly, and not bundled with the topology move itself. Two new concepts (fan-out, and an async lifecycle) landing in one step would violate the same small-steps discipline step 1 and step 2 both followed; this step assumes step 2's `PathGraphEnvironment`/`GraphNode`/`ready_nodes()` already exist and adds exactly one new thing on top: a lifecycle, and the sensing/waiting it requires.

## What actually changes, and what doesn't

**Carried over from step 2, unchanged:**
- The DAG topology, `requires`-only AND edges, `ready_nodes()`.
- The belief state as a topological order, computed once, walked as-is. No plan/route recalculation.
- A `FAILED` node still gets repaired by the same deterministic, always-succeeding action step 1 already built. This step is not about making repair real — that's still later work.

**New in this step:**
- A node's state is no longer the two values step 1/step 2 shared. It has a lifecycle: `PENDING → IN_PROGRESS → {SUCCEEDED, FAILED}` (`SUCCEEDED`/`FAILED` are this step's names for `OPEN`/`NEEDS_REPAIR`).
- Something other than `PathMaintenanceAgent` drives that lifecycle forward. The agent never starts a job — it only ever senses where a job currently is in its lifecycle, and waits when it isn't finished.

## Terminology: retiring "Driver" for this environment

`documentation/d-star/` and `documentation/task-graph/` both use "Driver" for whatever calls `break_edge()`/`fix_task()` between an agent's moves — a name that's stuck without ever being examined closely. Looking at it directly: it's been quietly covering two different things.

1. **Scenario setup** — a notebook cell or test calling `env.inject_repairs(...)` once, before a run starts, to script a demonstration. This is not a PEAS participant at all — no goals, no autonomy, just test fixture data. Step 1 and step 2's `inject_repairs()` are exactly this.
2. **Another autonomous system** — a CI runner, a Kubernetes controller, pre-commit tooling. These genuinely have their own goals and their own behavior; they are not a neutral setup mechanism, they're independent actors this environment doesn't control.

Steps 1 and 2 only ever needed sense (1). This step needs sense (2) for real, and AIMA already has a name for it that "Driver" was standing in for without earning: **another agent, in a multi-agent environment.** That's not a euphemism — it's a real reclassification of the environment (see below), and it's the textbook-correct move once the external thing changing state is itself goal-directed rather than scripted. "Driver" stays exactly as-is in `documentation/d-star/` and `documentation/task-graph/` — this is a naming decision scoped to `path-maintenance/`, not a repo-wide rename.

## Environment properties (step 3)

Using the same canonical AIMA property list `CLAUDE.md`'s own PEAS analyses and `documentation/d-star/environment_changes.md`'s table use:

| Property | Steps 1-2 | Step 3 | Why |
|---|---|---|---|
| **Static/Dynamic** | Static during the walk (one discrete pre-walk mutation) | **Dynamic** | Other agents change node state *while* `PathMaintenanceAgent` is walking/waiting, not in one scripted event beforehand |
| **Single/Multi-agent** | Single-agent (the only other participant was scenario setup, not a PEAS agent) | **Multi-agent** | CI/pre-commit/k8s are themselves goal-directed, autonomous systems — genuinely other agents, not exogenous noise |
| **Deterministic/Stochastic** | Deterministic (repair always succeeds) | **Deterministic** | Kept simple, deliberately: a job's resolution (when, and to what outcome) follows a known, fixed rule per scenario, not a probability draw |
| **Episodic/Sequential** | Episodic (each node's outcome doesn't depend on history beyond itself) | **Sequential** | How many times a node has already been sensed while `IN_PROGRESS` is meaningful history — the same shape as `task_graph_solver`'s "retry history matters" property, now applying to poll count instead of retry count |
| **Discrete/Continuous** | Discrete | Discrete, with a caveat | States stay discrete (four values instead of two). Time doesn't — polling can happen at any moment, not fixed ticks. Worth naming rather than leaving implicit, but not a full property flip |
| **Known/Unknown** | Known (full topology exposed from the start) | **Known** | The *rule* governing a job's resolution is configured and known to the scenario, even though `PathMaintenanceAgent` itself never reads that configuration — it only polls |
| **Observable** | Fully, but lazily | **Unchanged** | The agent could still query any node's current lifecycle state at any time; it still chooses to only check what it's about to act on. Multi-agent-ness changed *who* causes state change, not *what's visible* when asked |

## Proposed lifecycle and API surface (signatures only — no implementation yet)

Builds directly on step 2's `PathGraphEnvironment`/`GraphNode` — same `requires`/`ready_nodes()`, node state generalized from `CellState`'s two values to `JobState`'s four:

```python
class JobState(Enum):
    PENDING = "pending"          # not yet started
    IN_PROGRESS = "in_progress"  # started, not yet resolved
    SUCCEEDED = "succeeded"      # steps 1-2's OPEN
    FAILED = "failed"            # steps 1-2's NEEDS_REPAIR
```

```python
@dataclass
class JobNode:
    id: str
    requires: Tuple[str, ...] = ()
    # same shape as step 2's GraphNode - deliberately no pass_probability/
    # rmax/r_patience. This step is deterministic and known; there is no
    # retry budget to track.
```

```python
class JobGraphEnvironment:
    nodes: Dict[str, JobNode]

    def __init__(self, nodes: Dict[str, JobNode], config: JobGraphConfig):
        """Same requires-validation shape as step 2's PathGraphEnvironment -
        reused as a pattern, not imported."""

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Identical to step 2's - the frontier of nodes whose requires are
        all satisfied and haven't themselves resolved yet."""

    def get_job_state(self, node_id: str) -> JobState:
        """Current lifecycle state. Never mutates anything, consumes no
        budget - a pure sense, same contract as step 2's get_node_state(),
        just returning JobState instead of CellState."""

    def advance_jobs(self) -> None:
        """Moves every PENDING/IN_PROGRESS node one step through its
        configured, deterministic lifecycle. Represents the other agents
        (CI, k8s, pre-commit) doing their own work between our agent's
        senses - not something PathMaintenanceAgent calls itself. Exactly
        who calls this (scenario setup stepping through a script, or
        something that stands for the other agents more literally) is
        open - see below."""

    def repair_node(self, node_id: str) -> None:
        """Deterministic repair of a FAILED node: same no-op-that-always-
        succeeds contract as steps 1-2's repair."""
```

```python
class PathMaintenanceAgent:
    def walk(self) -> WalkResult:
        """Same walk as step 2, with one change: before treating a node as
        SUCCEEDED or FAILED, keep sensing (get_job_state()) while it's
        PENDING or IN_PROGRESS. Processes `order` strictly one node at a
        time, sequentially - no concurrent handling of multiple in-progress
        nodes in this step (see "Not decided"). Still never starts a job,
        never recomputes or deviates from `order`."""
```

`WalkResult` likely needs a new field recording how many senses were spent waiting per node, the same way `task_graph_solver`'s `ExecutionResult` tracks retry cost — proposed, not settled.

## Where this lives

Inside `path_maintenance/`, the same package step 2 establishes — this step adds a new module alongside step 2's, it does not need its own top-level package.

## Not decided

- **What exactly resolves `advance_jobs()`, and who calls it.** For a deterministic, known lifecycle, the simplest version is scenario config saying "this job takes exactly N senses to leave `IN_PROGRESS`" — but whether that's driven by scenario setup stepping a script (step 1's `inject_repairs()` shape) or something modeling the other agents more literally is unresolved.
- **Whether `FAILED` exists yet, or only `SUCCEEDED`.** Reusing the existing repair pattern for a sensed `FAILED` outcome costs nothing new to build and exercises both branches in a demo — but if the goal for this step is narrowly "prove the wait loop," `SUCCEEDED`-only might be the smaller, more honest slice. Leaning toward including `FAILED` since the repair path already exists and not exercising it would leave the GIF one-note, but flagging this as a real scope choice, not an obvious one.
- **Sequential-but-single-threaded walk, confirmed for this step only.** `walk()` processes `order` one node at a time even though the DAG can have several ready nodes at once — deliberately not dispatching/polling multiple in-progress nodes concurrently yet, since that needs real time-modeling (whose poll happens when) this step doesn't have a reason to build.
- **`WalkResult`'s new field(s) for wait/poll cost** — shape TBD, see above.

## Explicitly out of scope for this document right now

This is step 3's design, written ahead of step 2's implementation. Nothing here should be built before step 2 (`../graph-topology/`) has its own `scenario.md`/`algorithm_fit.md` and a working `PathGraphEnvironment` — this document exists to record the shape of the next step, not to be started early.
