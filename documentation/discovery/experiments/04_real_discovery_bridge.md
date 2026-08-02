# Experiment 4: Real, `atomicguard`-Backed Nodes — Same Walk, Real Sensing

**Run this yourself:** `real_discovery/atomicguard_backed/tests/` reproduces every behavior in this experiment (`test_domain.py`, `test_environment.py`, `test_scenarios.py`, `test_discovery_agent_integration.py`, `test_discovery_view.py`, 31 tests total, every one of them against real subprocess calls, no mocking). Animation: [`pipeline_fanout_real_discovery.gif`](../../../real_discovery/atomicguard_backed/animations/pipeline_fanout_real_discovery.gif).

## What this experiment demonstrates

Experiment 3 proved AND-joins force the right order on `DiscoveryNode`, a frozen dataclass whose `notifies`/`requires` are static fields. This experiment asks a different question: does `discovery.agents.discovery_agent.DiscoveryAgent` still work, completely unmodified, if a node's `notifies` isn't a field at all — if it's read fresh, every time, off a real `atomicguard.Artifact` a real `DualStateAgent` produces by actually running a real subprocess?

It does. `StatefulDiscoveryNode` carries a real `check_action_pair` (a `cat` over a real JSON fixture file, wrapped in the same `SubprocessGenerator`+`ExitCodeGuard`+`ActionPair` machinery `real_task_graph_solver/atomicguard_backed/` already proved). `StatefulDiscoveryEnvironment.sense_edges()` runs it through a real `DualStateAgent` (`rmax=0`, the same "free sensor" shape `AtomicGuardCheckEnvironment.check_invariant()` established) and parses `notifies` off the artifact's real content. Nothing about `DiscoveryAgent.walk()` changed to make this work — its only environment dependencies (`sense_edges`/`sense_requires`/`get_move_cost`) are exactly this environment's public shape.

## The walk, confirmed identical to experiment 3

```
result.path == [
    "commit", "lint", "merge-gate", "lint", "commit",
    "unit-tests", "integration-tests", "unit-tests", "commit",
    "lint", "merge-gate", "deploy", "merge-gate", "lint", "commit",
]
result.nodes_sensed == 6
result.total_cost == 14
result.blocked_nodes == []
result.goal_reached == True
```

Move for move, identical to experiment 3's gated walk over `discovery/`'s own `DiscoveryEnvironment` — `tests/test_discovery_agent_integration.py` asserts this directly, running both environments over the identical topology and comparing every field of the result, rather than just eyeballing matching numbers.

## What's different this time, underneath

Every one of those 6 senses is a real subprocess call (`cat real_discovery/atomicguard_backed/fixtures/pipeline_fanout_lite/<node>.json`), routed through a real `DualStateAgent`, recorded in a real `InMemoryArtifactDAG` — not a dataclass field lookup. `merge-gate`'s `requires = ("lint", "integration-tests")` is declared, static node config (matching `atomicguard`'s own `WorkflowStep` precedent), never itself sensed — satisfaction tracking (`cleared`) stays entirely `DiscoveryAgent`'s own bookkeeping, exactly as before.

## What to watch for in the GIF

Same 15 frames, same shape as experiment 3's GIF — the point being made *is* the sameness:

- **Frames 0–2**: `commit → lint → merge-gate` — `merge-gate` renders gold (blocked) the moment it's sensed, `requires ('lint', 'integration-tests')` neither yet cleared.
- **Frames 3–4**: backtrack `merge-gate → lint → commit`.
- **Frames 5–8**: the `unit-tests → integration-tests` branch, both clearing (green), then backtracking out.
- **Frames 9–10**: the readiness sweep's replayed route, `commit → lint → merge-gate` again — at `merge-gate`, `'merge-gate' requires satisfied - cleared`.
- **Frame 11**: `merge-gate → deploy`, sensed for the first time, dark green — the goal, reached last.
- **Frames 12–14**: unwind back to `commit`.

## What this experiment validates that experiment 3 alone could not

- **`DiscoveryAgent`'s "only three environment methods" claim is real, not just true by inspection.** Running it against an environment with a genuinely different internal implementation — real subprocess calls instead of field reads — and getting an identical walk is a much stronger proof than reading the source and noting it only calls three methods.
- **The node-ownership split holds up under real, guard-checked state.** `check_action_pair` (local, node-owned in spirit) and `requires` (declared, but satisfaction is cross-node, environment/agent-tracked) map cleanly onto `atomicguard`'s own `WorkflowStep`/`WorkflowState` split — this experiment is that mapping, exercised end to end rather than argued from reading `atomicguard`'s source.
- **Visualization reuses the same node-state vocabulary (known/blocked/cleared/goal) without reusing code.** `real_discovery/atomicguard_backed/visualization/discovery_view.py` is a separate module, not an import from `discovery/` — the one place it has to differ is `build_networkx_graph()`, which builds its picture from `known_edges`, data the walk itself already sensed via `_walk_frames()`'s replay, rather than reading a static `.notifies` field the way the plain version does. Everything downstream of that (`render()`, `animate_walk()`) is unchanged in shape.
- **A real mistake, worth recording rather than quietly fixing.** The first version of this module ported `discovery/`'s own `build_networkx_graph(env)` almost verbatim - including its habit of peeking at every node in `env.nodes` to get a stable layout, harmless there because `.notifies` is a free field read. Here, that peek is a real `sense_edges()` call: `animate_walk()` was making 90 real subprocess calls for this 15-frame/6-node walk (every frame re-sensing every node), instead of the 6 the walk itself needed - a real violation of this package's own "nothing gets sensed except through the walk" principle, not just wasted work, and a silent widening of a failing check's blast radius to nodes the walk never visited. Caught in PR review, fixed by threading `_walk_frames()`'s own already-sensed `known_edges` through to `render()`/`build_networkx_graph()` instead of re-deriving them. Confirmed directly: the whole animation now makes exactly 6 real senses, not 90 (`env._dag.get_all()` after `animate_walk()` has exactly 6 entries).

## Related documents

- [`../atomicguard-bridge/environment_design.md`](../atomicguard-bridge/environment_design.md) — the node-ownership resolution, the "small steps" scope, and the sense-time-not-construction-time validation tradeoff this experiment's fixtures exercise.
- [`03_pipeline_fanout_and_joins.md`](03_pipeline_fanout_and_joins.md) — the plain-`DiscoveryEnvironment` run this experiment matches move for move.
- [`../../task-graph/atomicguard-variant/environment_design.md`](../../task-graph/atomicguard-variant/environment_design.md) — where `check_invariant()`'s `rmax=0` "free sensor via `DualStateAgent`" pattern, reused here for `sense_edges()`, was first established.
