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

## Resolved: who calls `advance_jobs()`, and how a job's lifecycle actually progresses

The original sketch of this design had a real gap, worth recording rather than quietly fixing: `get_job_state()` was specified as a pure sense (never mutates), and `advance_jobs()` was specified as "not something `PathMaintenanceAgent` calls itself" — but `walk()` is a single, blocking call, the same shape as steps 1-2's. If nothing calls `advance_jobs()` while the agent is waiting inside that one call, a `PENDING`/`IN_PROGRESS` node would never resolve and `walk()` would spin forever. Something has to call it, from inside the loop the agent is already running.

**Resolution:** `walk()`'s wait loop calls `advance_jobs()` itself, between senses:

```python
state = env.get_job_state(node_id)
while state in (JobState.PENDING, JobState.IN_PROGRESS):
    env.advance_jobs()
    state = env.get_job_state(node_id)
```

This corrects the earlier claim directly — the agent *does* call `advance_jobs()`. It doesn't contradict the multi-agent framing: `advance_jobs()` represents time passing, during which other agents (CI, k8s, pre-commit) do their own work, entirely outside the agent's control — which node resolves, when, and to what outcome is fixed by each `JobNode`'s own configuration, not chosen by `PathMaintenanceAgent`. The agent calling the method that lets time pass is a mechanical necessity of a single-threaded, deterministic simulation (the same reason a test fakes and manually advances a clock, without implying the code under test controls real time) — not a claim that the agent is doing the other agents' work. `get_job_state()` stays genuinely pure: it never changes what `advance_jobs()` hasn't already caused.

**Worth being honest about:** this toy simulation measures time in ticks-per-`advance_jobs()`-call, not wall-clock concurrency — a known simplification, the same category as `task_graph_solver`'s deterministic-but-seeded `pass_probability` standing in for real nondeterminism. The `Dynamic`/`Multi-agent` properties below describe what the design is modeling and motivated by, not a claim that this simulation is genuinely concurrent.

## Resolved: `FAILED` is in scope

Included, not deferred to a later step: the repair path already exists (steps 1-2 built it), reusing it here costs nothing new, and exercising both branches (`SUCCEEDED` and `FAILED`) is the only way the GIF shows more than one kind of frame.

## Proposed lifecycle and API surface (signatures only — no implementation yet)

Builds directly on step 2's `PathGraphEnvironment`/`GraphNode` — same `requires`/`ready_nodes()` pattern, node state generalized from `CellState`'s two values to `JobState`'s four. Additive to `path_maintenance/`, not a modification of step 2's already-shipped `CellState`/`GraphNode`/`PathGraphEnvironment`/`PathMaintenanceAgent` — those stay exactly as they are, the same way step 1's maze code stayed untouched when step 2 was built:

```python
class JobState(Enum):
    PENDING = "pending"          # not yet started (ticks_elapsed == 0)
    IN_PROGRESS = "in_progress"  # started, not yet resolved
    SUCCEEDED = "succeeded"      # steps 1-2's OPEN
    FAILED = "failed"            # steps 1-2's NEEDS_REPAIR
```

```python
@dataclass
class JobNode:
    id: str
    requires: Tuple[str, ...] = ()
    ticks_to_resolve: int = 0    # 0 = resolves on the very first sense, no waiting
    resolves_to: JobState = JobState.SUCCEEDED  # must be SUCCEEDED or FAILED
    # deliberately no pass_probability/rmax/r_patience - see graph-topology/
    # environment_design.md. Deterministic and known: resolves_to and
    # ticks_to_resolve are fixed per node, not drawn from a distribution.
```

```python
class JobGraphEnvironment:
    nodes: Dict[str, JobNode]

    def __init__(self, nodes: Dict[str, JobNode]):
        """Same requires-validation shape as step 2's PathGraphEnvironment -
        reused as a pattern, not imported."""

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Identical to step 2's - the frontier of nodes whose requires are
        all satisfied and haven't themselves resolved yet."""

    def get_job_state(self, node_id: str) -> JobState:
        """Current lifecycle state, purely a function of ticks elapsed vs.
        ticks_to_resolve (and whether repair_node() has been called) -
        never mutates anything itself."""

    def advance_jobs(self, satisfied: Set[str]) -> None:
        """Increments the tick counter for every ready-and-unresolved node
        (ready_nodes(satisfied), the same AND-gating frontier
        PathGraphEnvironment uses) - not every node in the graph. A node
        whose requires aren't satisfied yet can't be "in progress" in any
        real pipeline, and ticking it anyway let a downstream node
        silently resolve during an upstream node's wait loop - caught by
        a test while implementing, not designed in from the start. Called
        by PathMaintenanceAgent.walk()'s wait loop, not by scenario
        setup - see "Resolved" above."""

    def repair_node(self, node_id: str) -> None:
        """Deterministic repair of a FAILED node: same no-op-that-always-
        succeeds contract as steps 1-2's repair. Raises if the node is not
        currently FAILED."""
```

```python
class PathMaintenanceAgent:  # new module: agents/job_maintenance.py -
    def walk(self) -> JobWalkResult:  # not a modification of step 2's class
        """Senses each node in `order` (except order[0], same start-cell
        convention as steps 1-2); while PENDING/IN_PROGRESS, calls
        advance_jobs() and senses again. Once resolved, repairs if FAILED.
        Processes `order` strictly one node at a time, sequentially - no
        concurrent handling of multiple in-progress nodes in this step (see
        "Not decided"). Still never recomputes or deviates from `order`."""
```

```python
@dataclass(frozen=True)
class JobWalkResult:
    path: List[str]
    repairs_performed: List[str]
    senses_performed: Dict[str, int]  # per node, how many get_job_state() calls it took to resolve
    success: bool
```

New result type, not a modification of step 1-2's `WalkResult` - same reasoning as keeping `PathMaintenanceAgent` a new class in a new module.

## Where this lives

Inside `path_maintenance/`, the same package step 2 establishes — new modules (`core/domain.py`/`core/environment.py` gain additive classes, `agents/job_maintenance.py` and `core/results.py`'s `JobWalkResult` are new files/additions), not modifications to step 2's classes.

## Not decided

- **Sequential-but-single-threaded walk, confirmed for this step only.** `walk()` processes `order` one node at a time even though the DAG can have several ready nodes at once — deliberately not dispatching/polling multiple in-progress nodes concurrently yet, since that needs real time-modeling (whose poll happens when) this step doesn't have a reason to build.
- **Exact scenario numbers** (which nodes get which `ticks_to_resolve`/`resolves_to`) — left to `scenario.md`.
