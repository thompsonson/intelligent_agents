# Infra Discovery: Environment Analysis (Step 2)

**Retrofit note:** split out of the original `environment_design.md`
(`documentation/infra-discovery/`), per
[`agent_design_process_extensions.md`](https://github.com/thompsonson/atomicguard/blob/claude/platform-topology-agent-eduh7h/docs/design/notes/agent_design_process_extensions.md)'s
proposed one-file-per-step convention. The original document bundled Steps
1 (PEAS) and 2 (properties) together; on inspection it turned out to
contain no owned Step 1 content at all - see
[`step1_environment_specification.md`](step1_environment_specification.md) for that
finding. This file keeps everything that actually *is* Step 2 (environment
properties) plus the ontology-adjacent analysis that doesn't cleanly sort
elsewhere - flagged inline, not silently kept.

## Purpose

`real_discovery/atomicguard_backed/` proved one narrow thing:
`discovery.agents.discovery_agent.DiscoveryAgent` still works, unmodified,
once `sense_edges()` is backed by a real, guard-checked
`atomicguard.ActionPair` instead of a frozen dataclass field. It
deliberately stayed a toy - one domain, one kind, one `check_action_pair`
per node, a flat `notifies` tuple, no persistence across runs.

This document analyzes the properties of a genuinely different, harder
environment: what would an environment actually look like for a genuine
**Infra Discovery Agent** - one built against the real ontology
`atomicguard`'s own design work has already settled
([`step0_schema.md`](step0_schema.md)/[`step0_ubiquitous_language.md`](step0_ubiquitous_language.md)
- this track's Step 0), not a simplified stand-in for it.

## Why `real_discovery/`'s node shape doesn't generalize

Worth stating plainly rather than silently replaced: `StatefulDiscoveryNode`
(`id: str`, one `check_action_pair`) is a special case of this ontology
where `domain`/`kind` happen to be constant and implicit, `state` happens to
be single-valued (`notifies`, computed fresh every sense, never
accumulated), and `legal_actions` happens to be exactly one action, always
available. None of those simplifications survive contact with the real
ontology:

- **`id` is only unique within `(domain, kind)`.** A Kubernetes `Pod` named
  `web-frontend` and a GitHub `job` named `web-frontend` are different
  nodes. Node identity is a compound key, not a bare string.
- **`legal_actions` is `DSA-CATALOGUE[(domain, kind)]`** - a type-level
  lookup table, not a field a node instance carries. What a node can do is
  determined by what *kind* it is, looked up centrally, not declared
  per-instance the way `check_action_pair` is.
- **`state` is multi-facet** - `{value, observed_at, sensed_by}` per
  independently-sensed, independently-timestamped observable property
  (SOSA/SSN-grounded, per the source document's ontology survey), not one
  blob a single sense call produces in full.

## Environment properties

Argued fresh against this ontology, not inherited from `discovery/`'s or
`atomicguard-bridge/`'s tables - inheriting them without checking is exactly
the mistake `atomicguard-bridge/environment_design.md` was rewritten to stop
making.

| Property | Value | Why |
|---|---|---|
| **Known/Unknown** | **Unknown at the instance level, Known at the type level** | Which real `(domain, kind, id)` triples exist, and how they connect, is unknown and discovered incrementally - same spirit as `discovery/`. But `kind` is "a closed type within that domain, declared by the domain" (source ontology doc) - the *vocabulary* of possible node/edge types is a fixed, pre-registered catalogue (`DSA-CATALOGUE`/`BRIDGE-CATALOGUE`), known in advance. Neither `discovery/` (nothing typed) nor `atomicguard-bridge/` (one implicit type) needed this two-level split |
| **Observable** | **Partially, and now partially *within* a node too** | Not just "which nodes exist" is partially observable - a *known* node can have some facets observed and others not (`rollout` sensed, `replica_readiness` not yet). `discovery/`'s "known vs. visited" binary doesn't capture this; a node here has a *set* of observed facets, growing independently |
| **Static/Dynamic** | **Genuinely Dynamic, not just "not structurally guaranteed static"** | `atomicguard-bridge/environment_design.md` could only say its fixtures happened to be static by choice of scenario. Here there's no such choice available: real infrastructure changes independent of the agent's own sensing - a Pod can be recreated between two sense calls on the same subject. This is `discovery/environment_design.md`'s own parked "growing edges" idea and the source ontology document's own unresolved "PLRTA*'s dynamic-environment gap," finally not avoidable by scenario design |
| **Deterministic/Stochastic** | **Stochastic** | Real API calls fail transiently, rate-limit, time out. `atomicguard-bridge/`'s `cat`-over-fixture determinism was a property of *that* scenario's choice, not something achievable here by construction - a real DSA invocation can produce a different outcome on retry for reasons outside the environment's control |
| **Episodic/Sequential** | **Both, at two different scopes - a real, source-flagged gap, not resolved here either** | Sequential *within* one episode (`pending` carries state turn to turn, same as `discovery/`'s `known`/`visited`). But `belief_state` persists *across* episodes - genuinely neither classical Episodic (each episode independent) nor classical Sequential (one continuous run) in the R&N sense the term sheet uses. The source document itself flags this as a gap against its own PEAS doc, not yet closed there either - not invented for this document, inherited as still-open |
| **Single/Multi-agent** | **Multi** | `platform_topology_peas_and_cli_actions.md`'s per-domain tables classify this **Multi** outright, for all three domains - GitHub's own scheduler and other automations, Kubernetes' controllers (ReplicaSet controller, kubelet, HPA, Argo Rollouts controller), GCP's control plane and every other identity with write access, are each named as independent agents acting on the same W the agent only observes. This multi-agent-ness is a major, plausibly dominant contributor to Dynamic (above), not an unrelated fact - though not its sole cause either, since scheduled reconciliation, TTL-based decay, or timeouts could make W dynamic without any other agent involved. Distinct in kind from `path_maintenance/job-lifecycle`'s multi-agent concurrency either way, which is about *other instances of this same kind of agent* cooperating on a shared plan, not independent external controllers this agent never coordinates with |
| **Discrete** | **Yes at the type level, genuinely unbounded at the instance level** | `DSA-CATALOGUE`'s domain/kind keys are a finite, declared set. But nothing bounds how many real `(domain, kind, id)` triples exist or how many edges connect them - unlike every prior environment in this repo (even `discovery/`'s own `pipeline_fanout_lite`, six nodes, fixed at construction). This is exactly why `IN-SCOPE(subject, Ψ)`'s boundedness is the central open soundness question in `atomicguard`'s own revision document - not a property-table abstraction, the actual thing `SELECT-NEXT`'s correctness depends on |

## `legal_actions`: a catalogue lookup, not a node field - and what that means for DSA selection

**Retrofit note:** borderline between this file and Step 0
(`step0_schema.md`/`step0_ubiquitous_language.md`) - it's explaining an ontology term's
behavior via reading the agent function's mechanism, which is arguably Step
3 territory. Kept here for now rather than forced into a single step; flagged
in the sizing summary as a real instance of content that doesn't sort
cleanly.

`atomicguard-bridge/algorithm_fit.md` left "DSA selection" as the most
significant open item, split into two readings: aggregation (multiple
sensing DSAs each reveal a different facet - probably run all) vs. genuine
selection (multiple acting DSAs compete - a real scoring problem). The
source ontology document's own pseudocode answers the sensing half
concretely, in a way worth stating plainly rather than re-deriving:
`RELEVANT(DSA-CATALOGUE[subject.domain, subject.kind], subject, Ψ,
belief_state)` enqueues *every* legal, not-yet-invoked DSA for a
newly-discovered subject into `pending` at once. Selection doesn't happen
per-node at discovery time - it happens once, uniformly, across the whole
flat `pending` pool, via `SELECT-NEXT`/`SCORE`. That confirms the
aggregation reading for sensing DSAs specifically, not by assertion but by
reading the mechanism directly (recorded as `D-003` in
[`decisions.md`](decisions.md)). The genuine-selection reading stays open
for acting DSAs, still deferred (sensing-first scope) in the source
document too.

## `belief_state`: a third thing, owned by neither the environment nor a single walk

**Retrofit note:** same borderline flag as above.

`discovery/`'s architecture collapses two roles that this ontology keeps
separate. `DiscoveryEnvironment` plays "the real world";
`DiscoveryAgent.walk()`'s local `known`/`visited`/`cleared` sets play "what's
believed so far" - but that belief is thrown away the moment `walk()`
returns, private to one call. The source document's own "Who owns
`pending`/`belief_state`" section is explicit that this doesn't work here:
`belief_state` must be **shared and persistent across episodes** (multiple
`Ψ`s, over time, about the same real infrastructure), entity-indexed by
`(domain, kind, id)`; only `pending` is legitimately private per-episode,
matching `discovery/`'s own scoping. Whatever plays the `DiscoveryAgent` role
here needs a real, external, durable store injected into it - not local
variables - the same way `WorkflowOrchestrator` takes an injected,
persistent `artifact_dag` rather than building one per call.

## Where this lives

A new top-level design track, `documentation/infra-discovery/` (this
retrofit is a sizing copy under `documentation/infra-discovery-retrofit/`,
not the live track) - sibling to `documentation/discovery/`,
`documentation/task-graph/`, `documentation/path-maintenance/`, not nested
under `discovery/`'s own `atomicguard-bridge/`, since this is a different
agent built against a genuinely different ontology, not a further step in
the same toy's arc.

## Related documents

- [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md) - the canonical definition of every term used above (Step 0).
- [`step1_environment_specification.md`](step1_environment_specification.md) - Step 1 (PEAS); combines the per-domain PEAS tables and CLI catalogue into one cross-domain statement.
- [`step3_agent_function.md`](step3_agent_function.md) - Step 3; the `AGENT-FUNCTION` pseudocode, translated into this track's own vocabulary.
- [`step4_algorithm_fit.md`](step4_algorithm_fit.md) - Step 4: whether `discovery/`'s DFS-with-retrace could ever fit this shape.
- [`step0_schema.md`](step0_schema.md) - the field-level `NodeId`/`Facet`/`Edge` reference and the registered `DSA-CATALOGUE`/`BRIDGE-CATALOGUE` vocabulary.
- [`examples.md`](examples.md) - the schema instantiated and diagrammed.
- [`step5_agent_program.md`](step5_agent_program.md) - Step 5: the buildable sequence this document's own open items are ordered into.
- [`decisions.md`](decisions.md) / [`findings.md`](findings.md) / [`open_questions.md`](open_questions.md) - the register files this document's original "Resolved design questions," findings, and "Not decided" sections were extracted into.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` - the ontology, PEAS grounding, and `AGENT-FUNCTION` pseudocode this document translates and checks against.
- `atomicguard`'s `docs/design/notes/platform_topology_peas_and_cli_actions.md` - the actual per-domain PEAS analysis this document's properties table is checked against.
