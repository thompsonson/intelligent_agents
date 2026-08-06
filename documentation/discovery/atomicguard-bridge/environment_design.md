# Bridging `discovery/` and `atomicguard`: Environment Design

## Purpose

`discovery/`'s three steps (forward sensing, backtracking, AND-joins) all run against `DiscoveryNode` - a frozen dataclass whose `notifies`/`requires` are static fields, fixed at construction. That's the right shape for the question those steps were built to answer (can an agent build up a topology it doesn't start out knowing), but it leaves the *node itself* inert: nothing about `DiscoveryNode` represents real, checkable state in the world, the way `real_task_graph_solver/atomicguard_backed/`'s `AtomicGuardCheckNode` does via a real, guard-checked `atomicguard.ActionPair`.

This document resolves a design conversation about closing that gap - not by simulating time (`ticks_elapsed`, considered and explicitly rejected mid-conversation), but by making a node's `notifies` genuinely read off the real world, the same way `AtomicGuardCheckEnvironment.check_invariant()` already reads a real check's pass/fail. The goal, in the words that settled it: *"the DSA is stateless as a whole - it reads the state of the world via the guards. The nodes will represent the state of the world."*

`scenario.md` covers the concrete topology and fixture choices; `algorithm_fit.md` covers whether `DiscoveryAgent`'s traversal algorithm still fits this environment and what, algorithmically, is deliberately left open. This document covers the environment's own properties and shape only.

## Environment properties

Same table shape as `discovery/environment_design.md`'s own - deltas called out explicitly rather than silently inherited, since inheriting them without checking is exactly the mistake this document exists to avoid repeating.

| Property | Value | Why |
|---|---|---|
| **Known/Unknown** | **Unknown - more genuinely than `discovery/`'s own** | `discovery/`'s environment holds the *complete* graph (nodes and edges both) in full at construction - `notifies` is a static field, hidden from the agent only by API convention (`sense_edges()` gates it, but the environment itself could enumerate everything trivially by reading `self.nodes`). Here, the environment holds the complete *node set* up front (`nodes: Dict[str, StatefulDiscoveryNode]`), but **no one** - not the agent, not the environment itself - knows a node's `notifies` until its `check_action_pair` actually runs. There's nothing to hide; it genuinely doesn't exist as data before it's sensed |
| **Observable** | **Partially** | Unchanged from `discovery/`: the agent can query any node id it already knows about, no enumeration, no "list all nodes" |
| **Static/Dynamic** | **Static, but not structurally guaranteed** | `discovery/`'s frozen dataclass makes staticness a hard guarantee - `notifies` cannot change, full stop. Here, staticness is a *property of this experiment's fixtures* (a `cat` over an unchanging file always returns the same content), not something `StatefulDiscoveryEnvironment` enforces. A real check backing a node could return different content on repeated invocation - this is `discovery/environment_design.md`'s own parked "growing edges" idea, now genuinely reachable rather than structurally excluded. Still not built here - see `algorithm_fit.md`'s open items |
| **Deterministic/Stochastic** | **Deterministic, same caveat as above** | This experiment's `cat`-over-fixture checks are deterministic by construction, not because the environment guarantees it the way `discovery/`'s frozen dataclass does. A real LLM-backed or flaky check would make this genuinely Stochastic |
| **Single/Multi-agent** | Single-agent | Unchanged |
| **Episodic/Sequential** | Sequential | Unchanged - which node to visit next depends on accumulated history, not just the current node in isolation |
| **Discrete** | **Yes, but sensing is no longer free** | Finite node set, finite possible edges, unit move cost - same as `discovery/`. The one thing that's different: `sense_edges()` now has a real cost (wall-clock time, a real subprocess call) that `discovery/`'s field-read structurally cannot have. This is exactly the property a visualization bug violated (see `algorithm_fit.md`'s "Sensing has real cost now" and PR #15's review discussion) - not a property-table abstraction, a real bug it would have prevented if checked against explicitly up front |

## Who owns what: the resolution

A long thread of the design conversation kept circling one question in different clothes: does the *node* own `sense_edges()`, or does the *environment*? The honest answer, arrived at by checking real `atomicguard` source rather than deciding from vibes:

- **A node's own, real, guard-checked state is genuinely local** - reading it doesn't require knowing anything about any other node. `check_action_pair` belongs to the node.
- **`requires`/cleared-tracking is genuinely cross-node** - "is `merge-gate` clearable" needs to know about `lint` and `integration-tests` too, information no single node can hold about itself. This has to stay agent/environment-level bookkeeping, not node-owned.

This isn't invented for this document - it's the exact shape `atomicguard`'s own `WorkflowStep`/`WorkflowState` split already uses in production: `requires` is declared, bundled with `action_pair`, at `WorkflowOrchestrator.add_step()` time (one object); *satisfaction* (`WorkflowState.guards: MappingProxyType[GuardId, bool]`) is a separate, externally-held, frozen structure the orchestrator manages. `StatefulDiscoveryNode` follows that precedent directly: `requires` is declared node config; `cleared` stays entirely `DiscoveryAgent`'s own bookkeeping, exactly as it already is for the plain `DiscoveryNode`.

The AtomicGuard team's own independent re-derivation (issue #370's resolution, commit `1a43a6f`) reached a parallel finding from a different angle: `discovery/`'s own `cleared` gate conflates "gate movement past a node" with "gate discovery of what it notifies," because of the toy's adjacency constraint. That's not a bug in `discovery/` (it's correct for what it was built to do), but it's independent confirmation that local-node-truth and cross-node-satisfaction are genuinely different things worth keeping apart here.

## Where `notifies` lives now

Not a field. `StatefulDiscoveryNode` has no `notifies` attribute at all. `sense_edges(node_id)` runs the node's real `check_action_pair`, through a real `DualStateAgent` (`rmax=0` - one real call, no retry, the identical "free sensor" shape `AtomicGuardCheckEnvironment.check_invariant()` already established), and reads `notifies` off the returned `Artifact.content`, parsed as JSON. The node's real, current state - not a static declaration - determines what it reports.

A consequence worth being explicit about: **`sense_edges()` no longer validates its own targets at construction time.** `discovery/`'s `DiscoveryEnvironment.__init__` can check every `notifies` target exists, because the whole graph is handed in as data up front. Here, a target genuinely isn't knowable until the check that names it actually runs - so the equivalent check (`ValueError` on an unknown target) moved to `sense_edges()` itself, at sense time. This is a real, deliberate shift in when a malformed topology is caught (first sense, not construction), not an oversight.

## What's deliberately *not* built here: small steps

Per explicit instruction ("for me this is solely about making nodes stateful. small steps."), this experiment does not:

- **Add `repair_action_pair`.** A node either already reports something via its check, or `sense_edges()` propagates whatever the check itself raised (`RmaxExhausted`, uncaught - see `algorithm_fit.md`). No repair loop.
- **Discover new `ActionPair`s dynamically.** `StatefulDiscoveryEnvironment.__init__` still takes a full `nodes: Dict[str, StatefulDiscoveryNode]` up front, matching `AtomicGuardCheckEnvironment`'s own precedent exactly. "Construct new check `ActionPair`s on the fly from a catalogue as new subjects are discovered" is real and interesting, but a separate, later step.
- **Give a node more than one `check_action_pair`, or any way to choose among several.** Every node here has exactly one, unambiguous check - `sense_edges(node_id)` never has to decide *which* DSA to invoke, only whether to invoke the one it has. The real target design (`docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` in `atomicguard`, `DSA-CATALOGUE[(domain, kind)]`) allows more than one DSA per subject kind, which is a real, structurally different question - a *selection* algorithm, not an environment-shape one. Explicitly not resolved by this document; see `algorithm_fit.md`'s open items, kept open on purpose rather than foreclosed by this node shape.
- **Change anything about `discovery/` itself.** `DiscoveryNode`/`DiscoveryEnvironment`/`DiscoveryAgent` are untouched. This is a new environment (`StatefulDiscoveryEnvironment`) that happens to expose the identical public shape `DiscoveryAgent` already depends on.

## Built (TDD, `real_discovery/atomicguard_backed/`)

- **`core/domain.py` - `StatefulDiscoveryNode`.** `id`, `check_action_pair: ActionPair`, `requires: Tuple[str, ...] = ()`. No `notifies` field, no `repair_action_pair` field, no way to hold more than one check - see "small steps," above.
- **`core/environment.py` - `StatefulDiscoveryEnvironment`.** Same public shape as `discovery.core.environment.DiscoveryEnvironment` - `sense_edges()`, `sense_requires()`, `get_move_cost()`, nothing else. `sense_edges()` wraps `check_action_pair` in a real `DualStateAgent` (`rmax=0`) against a per-environment `InMemoryArtifactDAG`, parses `Artifact.content` as JSON for `notifies`, and validates each target against the known node set at sense time. `sense_requires()` returns the node's declared, static `requires`. `get_move_cost()` is the same flat `1`.
- **`visualization/discovery_view.py`.** Same public shape as `discovery/`'s own version - a separate module, not a shared import. See `algorithm_fit.md`'s "Sensing has real cost now" for the over-sensing bug this module's first version had, and how it was fixed.
- **Scenario and algorithm fit** - see `scenario.md` and `algorithm_fit.md` for what's built there.

## Not decided

- **What a genuinely failing/flaky check means for a discovery walk, and whether `requires` should be discovered per-instance instead of declared.** See `algorithm_fit.md`'s open items - both are algorithm-level questions, not environment-shape ones, and both connect directly to real, still-open questions in `atomicguard`'s own topology-agent design document.
- **Dynamic node discovery, and DSA selection per node.** Explicitly out of scope for this step (see "small steps," above); kept open, not foreclosed - see `algorithm_fit.md`.

## Related documents

- [`scenario.md`](scenario.md) - the concrete topology and fixture-file decisions.
- [`algorithm_fit.md`](algorithm_fit.md) - whether `DiscoveryAgent`'s algorithm actually fits this environment, the sensing-cost bug this document's own first draft didn't anticipate, and what's genuinely left open algorithmically (including DSA selection).
- [`../experiments/04_real_discovery_bridge.md`](../experiments/04_real_discovery_bridge.md) - the walk run for real, frame-by-frame, with GIF.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - the real target design this bridge experiment validates a slice of; its own `DSA-CATALOGUE`/`SELECT-NEXT` machinery is exactly where a multi-DSA-per-node selection algorithm would need to live.
