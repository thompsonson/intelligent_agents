# AND-Joins: Environment Design (Discovery Step 3)

## Purpose

`backtracking-exploration/algorithm_fit.md` (step 2) let `DiscoveryAgent` reach every node reachable from `start`, but it treats every node as immediately actionable the moment it's sensed. That's wrong for a fan-in node like `merge-gate`: in the real pipeline this environment models, a merge can't actually proceed until *every* prerequisite branch — not just the first one the agent happened to walk — has finished. Step 2's own walk demonstrates the bug directly: it senses `deploy` at move 3, three moves before it ever touches `unit-tests`/`integration-tests` at all. `deploy` running before the tests have even been looked at is the concrete failure this step exists to fix.

This step adds `requires` back onto `DiscoveryNode` — pull-direction, the same shape `GraphNode`/`JobNode` already use — alongside the push-direction `notifies` step 1 built. Both fields live on the same node, the same way a real pipeline's config declares both what it needs and who it notifies in one file.

## What changes, and what doesn't

**Unchanged:** `DiscoveryEnvironment.get_move_cost()`, the movement rule (only into already-sensed `notifies`, retracing only for backtracking), `pipeline_fanout_lite`'s topology (reused, not modified — see `scenario.md`).

**Changes:**
- `DiscoveryNode` gains `requires: Tuple[str, ...] = ()`.
- `DiscoveryEnvironment` gains a second query, `sense_requires(node_id)`, and a construction-time cycle check over the `requires` sub-graph.
- `DiscoveryAgent` gains a third state beyond known/visited (see below), and its candidate-generation rule changes to respect it.
- `DiscoveryWalkResult` gains `blocked_nodes` — nodes that were sensed but never became eligible to proceed past.

## Three states, not two

Step 2 had `known` (named in some sensed node's `notifies`) and `visited` (sensed). This step adds **`cleared`**: a node whose own `requires` are all themselves `cleared` — trivially true the instant a node with `requires=()` is sensed, which is every node in every scenario before this one, so nothing about step 1 or step 2's behavior changes for graphs that don't use `requires` at all.

The distinction matters because `visited` alone conflates two different things once `requires` exists: "I looked at this node" and "this node is actually done." A node can be `visited` — sensed, its own `notifies`/`requires` known — without being `cleared`, if its prerequisites aren't satisfied yet. Only a `cleared` node's `notifies` are walkable, and only a `cleared` node counts toward satisfying anyone else's `requires`. This is deliberately the same shape as `PathGraphEnvironment`/`JobGraphEnvironment`'s `satisfied` set — a node that's merely been glanced at doesn't count, only one that's actually finished does — applied here to a node with no other state to track completion with.

## Sensing: two queries, not one

The obvious real-world framing — a pipeline's config declares both `needs:` and its trigger in one file — argues for revealing both in a single query. That's not the choice here: `sense_edges()` keeps its existing signature and meaning (`notifies` only), and a new `sense_requires(node_id)` is added alongside it, called at the same point `DiscoveryAgent` first senses a node (so `nodes_sensed` still means exactly what it already means — distinct `sense_edges()` calls — and `requires` data just comes along for free at the same moment). This is a reversal of an earlier lean toward a combined query, made after actually looking at the shipped code: every prior step in this repo is additive — new fields, new methods, never a changed signature on something already shipped (`CellState`/`GraphNode`/`PathGraphEnvironment` all stayed untouched when `job-lifecycle` built on top of `graph-topology`). Changing `sense_edges()`'s return shape would break that discipline for a cosmetic gain in real-world-metaphor purity.

## The reachability constraint — the one that actually matters

Step 1 had a similar-looking caveat ("exactly one reachable terminal, or the goal is ambiguous") and it was a nicety — get it wrong and a test would show a slightly-odd result. This one is not a nicety: **if a `requires` target is never named in *any* node's `notifies`, it can never be discovered, and the node that requires it can never clear — a silent, permanent deadlock**, not an ambiguous result. `requires` and `notifies` are two independent edge sets; naming a node in a `requires` list doesn't make it walkable, only a `notifies` chain does.

Since `DiscoveryEnvironment` doesn't know `start_id` (agent-owned, per the position-tracking resolution in the base `environment_design.md`), it cannot validate "every `requires` target is reachable from `start`" at construction time — that has to be a scenario-design discipline, stated loudly rather than assumed. `scenario.md` is responsible for satisfying it; `DiscoveryWalkResult.blocked_nodes` (below) is how a scenario that gets it wrong fails visibly instead of silently.

What the environment *can* still validate at construction, independent of `start_id`: a cycle in the `requires` sub-graph (`A` requires `B`, `B` requires `A`) is unsatisfiable regardless of exploration order — reusing `path_maintenance/core/environment.py`'s `_validate_requires_graph()` cycle-detection *as a pattern* (mirrored, not imported, matching every prior cross-package precedent in this repo), applied only to `requires`, not `notifies` — `notifies` cycles stay legal, exactly as `DiscoveryEnvironment.__init__`'s existing docstring already states.

## What a permanently-blocked node looks like in the result

`DiscoveryWalkResult` gains `blocked_nodes: List[str]` — every `visited` node that never made it into `cleared` by the time the walk terminated. For a correctly-built scenario this is always empty; it exists so a scenario that violates the reachability constraint above produces a loud, assertable test failure (`blocked_nodes == ["merge-gate"]`, say) instead of a walk that just quietly never reaches part of the graph with no explanation.

## Environment properties

Unchanged from the base `environment_design.md`'s table in every row — `requires` adds a second edge set and a completion notion, but doesn't touch Known/Unknown, Observable, Static/Dynamic, Single-agent, Deterministic, Sequential, or Discrete. Restated here only to make explicit that nothing about AND-gating flips any of them, the same restatement `graph-topology/environment_design.md` did for its own step.

## Proposed API surface (additive; signatures only)

```python
@dataclass(frozen=True)
class DiscoveryNode:
    id: str
    notifies: Tuple[str, ...] = ()
    requires: Tuple[str, ...] = ()  # new; pull-direction, mirrors GraphNode/JobNode
```

```python
class DiscoveryEnvironment:
    def __init__(self, nodes: Dict[str, DiscoveryNode]):
        """Existing notifies-target validation, unchanged, plus a new
        cycle check over the requires sub-graph only (pattern mirrored
        from path_maintenance's _validate_requires_graph, not imported).
        No reachability check - see "The reachability constraint" above;
        that's a scenario responsibility, not a constructor one."""

    def sense_edges(self, node_id: str) -> Tuple[str, ...]:
        """Unchanged from steps 1-2."""

    def sense_requires(self, node_id: str) -> Tuple[str, ...]:
        """New. Same no-arrival-check contract as sense_edges() - the
        environment doesn't track position, so it has no way to gate
        this either."""

    def get_move_cost(self, from_id: str, to_id: str) -> int:
        """Unchanged."""
```

```python
@dataclass(frozen=True)
class DiscoveryWalkResult:
    path: List[str]           # unchanged
    nodes_sensed: int          # unchanged - still counts sense_edges() calls only
    goal_reached: bool         # unchanged
    total_cost: int            # unchanged
    blocked_nodes: List[str]   # new - visited but never cleared
```

`DiscoveryAgent`'s own signature doesn't change (`__init__(environment, start_id)`, `walk() -> DiscoveryWalkResult`) — what changes is internal to `walk()`, and that's exactly the part not yet settled (see below).

## Where this lives

Same package, `discovery/` — additive to `core/domain.py`, `core/environment.py`, `core/results.py`, and `agents/discovery_agent.py`, none of which get replaced, matching every prior step's discipline in this repo.

## Not decided

- **The traversal algorithm itself.** Step 2's LIFO-parent-stack backtracking is not obviously sufficient once a node can be sensed-but-blocked and later become clearable *after* the walk has already backtracked past it entirely — worked through in detail in `algorithm_fit.md`, which is where this gets resolved, not here.
- **Exact scenario `requires`** — left to `scenario.md`, including how it interacts with `pipeline_fanout_lite`'s existing three-parent fan-in at `merge-gate`.
