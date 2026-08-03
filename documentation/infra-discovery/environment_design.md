# Infra Discovery: Environment Design

## Purpose

`real_discovery/atomicguard_backed/` proved one narrow thing: `discovery.agents.discovery_agent.DiscoveryAgent` still works, unmodified, once `sense_edges()` is backed by a real, guard-checked `atomicguard.ActionPair` instead of a frozen dataclass field. It deliberately stayed a toy - one domain, one kind, one `check_action_pair` per node, a flat `notifies` tuple, no persistence across runs.

This document starts from a different, harder question: what would an environment actually look like for a genuine **Infra Discovery Agent** - one built against the real ontology `atomicguard`'s own design work has already settled, not a simplified stand-in for it? Source of truth, quoted rather than paraphrased from memory: `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md`, "Node and Edge ontology" section:

```
Node = ⟨domain, kind, id, state, legal_actions⟩
Edge = ⟨from, to, edge_type, evidence⟩
```

Nothing here is implemented yet. This document is Steps 1-2 of the Agent Design Process (Environment Specification and Analysis) for that ontology, applied concretely enough to become code later - the same discipline `discovery/environment_design.md` and `atomicguard-bridge/environment_design.md` followed, not skipped this time.

## Why `real_discovery/`'s node shape doesn't generalize

Worth stating plainly rather than silently replaced: `StatefulDiscoveryNode` (`id: str`, one `check_action_pair`) is a special case of this ontology where `domain`/`kind` happen to be constant and implicit, `state` happens to be single-valued (`notifies`, computed fresh every sense, never accumulated), and `legal_actions` happens to be exactly one action, always available. None of those simplifications survive contact with the real ontology:

- **`id` is only unique within `(domain, kind)`.** A Kubernetes `Pod` named `web-frontend` and a GitHub `job` named `web-frontend` are different nodes. Node identity is a compound key, not a bare string.
- **`legal_actions` is `DSA-CATALOGUE[(domain, kind)]`** - a type-level lookup table, not a field a node instance carries. What a node can do is determined by what *kind* it is, looked up centrally, not declared per-instance the way `check_action_pair` is.
- **`state` is multi-facet** - `{value, observed_at, sensed_by}` per independently-sensed, independently-timestamped observable property (SOSA/SSN-grounded, per the source document's ontology survey), not one blob a single sense call produces in full.

## Environment properties

Argued fresh against this ontology, not inherited from `discovery/`'s or `atomicguard-bridge/`'s tables - inheriting them without checking is exactly the mistake `atomicguard-bridge/environment_design.md` was rewritten to stop making.

| Property | Value | Why |
|---|---|---|
| **Known/Unknown** | **Unknown at the instance level, Known at the type level** | Which real `(domain, kind, id)` triples exist, and how they connect, is unknown and discovered incrementally - same spirit as `discovery/`. But `kind` is "a closed type within that domain, declared by the domain" (source ontology doc) - the *vocabulary* of possible node/edge types is a fixed, pre-registered catalogue (`DSA-CATALOGUE`/`BRIDGE-CATALOGUE`), known in advance. Neither `discovery/` (nothing typed) nor `atomicguard-bridge/` (one implicit type) needed this two-level split |
| **Observable** | **Partially, and now partially *within* a node too** | Not just "which nodes exist" is partially observable - a *known* node can have some facets observed and others not (`rollout` sensed, `replica_readiness` not yet). `discovery/`'s "known vs. visited" binary doesn't capture this; a node here has a *set* of observed facets, growing independently |
| **Static/Dynamic** | **Genuinely Dynamic, not just "not structurally guaranteed static"** | `atomicguard-bridge/environment_design.md` could only say its fixtures happened to be static by choice of scenario. Here there's no such choice available: real infrastructure changes independent of the agent's own sensing - a Pod can be recreated between two sense calls on the same subject. This is `discovery/environment_design.md`'s own parked "growing edges" idea and the source ontology document's own unresolved "PLRTA*'s dynamic-environment gap," finally not avoidable by scenario design |
| **Deterministic/Stochastic** | **Stochastic** | Real API calls fail transiently, rate-limit, time out. `atomicguard-bridge/`'s `cat`-over-fixture determinism was a property of *that* scenario's choice, not something achievable here by construction - a real DSA invocation can produce a different outcome on retry for reasons outside the environment's control |
| **Episodic/Sequential** | **Both, at two different scopes - a real, source-flagged gap, not resolved here either** | Sequential *within* one episode (`pending` carries state turn to turn, same as `discovery/`'s `known`/`visited`). But `belief_state` persists *across* episodes - genuinely neither classical Episodic (each episode independent) nor classical Sequential (one continuous run) in the R&N sense the term sheet uses. The source document itself flags this as a gap against its own PEAS doc, not yet closed there either - not invented for this document, inherited as still-open |
| **Single/Multi-agent** | **Single-agent in the PEAS sense; not single-*actor*** | No other *agent* is part of this problem's own formalization. But real infrastructure is mutated concurrently by real actors outside this agent's control (a human, CI/CD, other automation) - a background-dynamics fact entangled with Dynamic, above, not the same axis `path_maintenance/job-lifecycle`'s actual multi-agent concurrency sits on. Worth naming separately so it isn't silently folded into either property and lost |
| **Discrete** | **Yes at the type level, genuinely unbounded at the instance level** | `DSA-CATALOGUE`'s domain/kind keys are a finite, declared set. But nothing bounds how many real `(domain, kind, id)` triples exist or how many edges connect them - unlike every prior environment in this repo (even `discovery/`'s own `pipeline_fanout_lite`, six nodes, fixed at construction). This is exactly why `IN-SCOPE(subject, Ψ)`'s boundedness is the central open soundness question in `atomicguard`'s own revision document - not a property-table abstraction, the actual thing `SELECT-NEXT`'s correctness depends on |

## Nodes and edges, translated (signatures only - no implementation)

```python
@dataclass(frozen=True)
class NodeId:
    """domain/kind/id, matching the ontology's compound identity exactly -
    id alone is not unique, only (domain, kind, id) is."""
    domain: str   # which handler owns it - github_actions, kubernetes, gcp, ...
    kind: str     # closed type within that domain - Deployment, Pod, workflow_run, ...
    id: str       # unique within (domain, kind) only


@dataclass(frozen=True)
class Facet:
    """One independently-sensed, independently-timestamped observable
    property - SOSA/SSN's Observation shape, per the source ontology
    document's survey. A node's `state` is Dict[str, Facet], not one value."""
    value: Any
    observed_at: datetime
    sensed_by: str  # which DSA produced this facet


@dataclass(frozen=True)
class Edge:
    """from_/to are NodeIds, not strings - see "Discovery is bidirectional,"
    below, for why this can't assume from_ is always "the node that was
    just sensed" the way discovery/'s push-only notifies does."""
    from_: NodeId
    to: NodeId
    edge_type: str
    evidence: str  # what artifact/observation produced this claim
```

Deliberately **not** sketched here: `DSA-CATALOGUE`/`BRIDGE-CATALOGUE`'s concrete shape, or `belief_state`'s interface. Both are genuinely undecided - see "Not decided," below - and sketching a shape prematurely risks exactly the kind of unargued commitment `atomicguard-bridge/`'s first draft made by skipping this document's own discipline.

## Discovery is bidirectional - and the source ontology's own propagation logic doesn't handle it yet

This is the finding this document exists to record precisely, not just gesture at. The source document's worked example only ever shows a node's own artifact revealing an edge pointing *away from itself*: sensing a GitHub `job` reveals `applies-to → (kubernetes, Deployment, ...)` - `from` is the sensed node, `to` is new. Nothing in the `Edge` tuple itself requires that direction. A node's artifact could just as easily reveal that some other, not-yet-known node points *at* it - e.g. sensing a `kubernetes.Service` reveals it is `selects-from`'d by an `Ingress` that hasn't been discovered yet, where the *sensed* node is `to`, and the *new* node is `from`.

The source document's own `AGENT-FUNCTION` pseudocode only propagates one way:

```
for edge in RESOLVE-BRIDGES(a):
    belief_state.RECORD-EDGE(edge)
    pending ← pending ∪ RELEVANT(BRIDGE-CATALOGUE[edge.edge_type], edge.to, Ψ, belief_state)
```

If the newly-discovered end of `edge` is `edge.from` rather than `edge.to`, this line never enqueues anything for it - that whole direction of discovery silently doesn't happen. `discovery/`'s toy can't expose this (`notifies` is push-only by construction, there's no `requires`-shaped discovery, only declaration); `atomicguard-bridge/` can't either (one domain, one implicit edge direction). This environment is the first place it's structurally possible for `RESOLVE-BRIDGES(a)` to produce an edge in *either* direction from the same artifact, and the propagation logic needs to check both ends - `RELEVANT(..., edge.to, ...)` when `to` is new, and the identical call against `edge.from` when `from` is new instead. Not resolved here (this is a design document, not a patch to `atomicguard`'s own doc) - recorded precisely so it isn't silently inherited as "already handled" the way `atomicguard-bridge/`'s first draft silently inherited a bug from `discovery/`'s visualization.

## `legal_actions`: a catalogue lookup, not a node field - and what that means for DSA selection

`atomicguard-bridge/algorithm_fit.md` left "DSA selection" as the most significant open item, split into two readings: aggregation (multiple sensing DSAs each reveal a different facet - probably run all) vs. genuine selection (multiple acting DSAs compete - a real scoring problem). The source ontology document's own pseudocode answers the sensing half concretely, in a way worth stating plainly rather than re-deriving: `RELEVANT(DSA-CATALOGUE[subject.domain, subject.kind], subject, Ψ, belief_state)` enqueues *every* legal, not-yet-invoked DSA for a newly-discovered subject into `pending` at once. Selection doesn't happen per-node at discovery time - it happens once, uniformly, across the whole flat `pending` pool, via `SELECT-NEXT`/`SCORE`. That confirms the aggregation reading for sensing DSAs specifically, not by assertion but by reading the mechanism directly. The genuine-selection reading stays open for acting DSAs, still deferred (sensing-first scope) in the source document too.

## `belief_state`: a third thing, owned by neither the environment nor a single walk

`discovery/`'s architecture collapses two roles that this ontology keeps separate. `DiscoveryEnvironment` plays "the real world"; `DiscoveryAgent.walk()`'s local `known`/`visited`/`cleared` sets play "what's believed so far" - but that belief is thrown away the moment `walk()` returns, private to one call. The source document's own "Who owns `pending`/`belief_state`" section is explicit that this doesn't work here: `belief_state` must be **shared and persistent across episodes** (multiple `Ψ`s, over time, about the same real infrastructure), entity-indexed by `(domain, kind, id)`; only `pending` is legitimately private per-episode, matching `discovery/`'s own scoping. Whatever plays the `DiscoveryAgent` role here needs a real, external, durable store injected into it - not local variables - the same way `WorkflowOrchestrator` takes an injected, persistent `artifact_dag` rather than building one per call.

## Resolved design questions

- **Node identity is a compound key, `NodeId(domain, kind, id)`, not `str`.** Follows directly from the ontology; not a judgment call.
- **`requires`-style declared config and `legal_actions`-style catalogue lookup are different mechanisms, not one field.** `atomicguard-bridge/`'s `requires: Tuple[str, ...]` was static, node-declared config (matching `WorkflowStep.requires`). `legal_actions` here is not analogous - it's derived from `(domain, kind)` via a shared catalogue, not declared per node instance. Keeping these conceptually separate, per "Who owns what" precedent in `atomicguard-bridge/environment_design.md`.
- **Sensing DSA aggregation, not per-node selection, for the "more than one DSA per node" question** - resolved for the sensing half only, by reading the source document's own `RELEVANT`/`pending` mechanism directly (see above). Acting DSA selection stays open.

## Not decided

- **Node identity stability and edge statefulness** - both inherited directly from the source ontology document's own "Open questions, not yet resolved" (its exact wording: does `id` reliably name the same real-world thing across sensing calls; is an edge a fact recorded once, or does it need its own staleness). Bidirectional discovery adds a new wrinkle to the second one, not present in the source document: if the *same* relationship can be discovered from either end at different times (once push-style from the `from` node, later pull-style from the `to` node), does a second, independent discovery strengthen confidence in the edge, or is it a duplicate needing de-duplication? Not resolved here.
- **The bidirectional propagation gap in `RESOLVE-BRIDGES`/`pending`** - named precisely above, not fixed. Fixing it is either a correction to how this document's own future pseudocode reads `edge.from`/`edge.to`, or (if this environment is ever built against `atomicguard`'s real orchestrator loop rather than a new one) a real finding to raise upstream, the way issues #370/#371 were.
- **`belief_state`'s concrete interface, index, and persistence backend.** Named as a real requirement above (shared, persistent, entity-indexed); not designed. The source document itself leaves this to its own "Step 5 (Agent Program)," not yet done there either.
- **`DSA-CATALOGUE`/`BRIDGE-CATALOGUE`'s concrete shape in this repo's terms.** Deliberately not sketched in the signatures above - premature before deciding what real (or fixture-backed) domains this environment will actually be built against.
- **What concrete scenario this gets validated against.** `atomicguard-bridge/`'s `pipeline_fanout_lite` reuse doesn't fit here - fixed six-node topology, one implicit domain. A `scenario.md` needs its own decision about whether to reuse `atomicguard`'s own catalogued domains (`github_actions`/`kubernetes`/`gcp`, per the source document's Step 3 tables) against real fixtures, or something smaller and repo-local. Not written yet.

## Where this lives

A new top-level design track, `documentation/infra-discovery/`, sibling to `documentation/discovery/`, `documentation/task-graph/`, `documentation/path-maintenance/` - not nested under `discovery/`'s own `atomicguard-bridge/`, since this is a different agent (per the framing that started this document: "not a generic discovery agent, rather an Infra Discovery Agent") built against a genuinely different ontology, not a further step in the same toy's arc. No code package name proposed yet - premature before `algorithm_fit.md` and a concrete scenario decision.

## Related documents

- [`algorithm_fit.md`](algorithm_fit.md) - whether `discovery/`'s DFS-with-retrace could ever fit this shape (it can't, argued directly), and what family of algorithm the source document's own LRTA*-grounding points toward instead.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` - the ontology, PEAS grounding, and `AGENT-FUNCTION` pseudocode this document translates and checks against.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - the `requires`/AND-join revision, and the `DSA-CATALOGUE`/`SELECT-NEXT` open questions `atomicguard-bridge/algorithm_fit.md` already cited.
- [`../discovery/atomicguard-bridge/environment_design.md`](../discovery/atomicguard-bridge/environment_design.md) / [`algorithm_fit.md`](../discovery/atomicguard-bridge/algorithm_fit.md) - the smaller, prior step this document deliberately doesn't generalize from by inheritance; every simplification that step made is named above as a simplification, not silently carried forward.
