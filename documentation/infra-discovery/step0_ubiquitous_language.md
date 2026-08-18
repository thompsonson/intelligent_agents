# Infra Discovery: Ubiquitous Language

## Purpose

Domain-Driven Design's Ubiquitous Language: one shared, agreed vocabulary, used consistently in design documents, conversation, and eventually code - not re-explained differently in each place it's used, and not allowed to silently become whatever a particular implementation's type system happens to call things. `step0_schema.md`'s first draft broke this discipline without meaning to: it let Python's dataclass names stand in for the vocabulary itself, rather than defining the vocabulary first and treating any particular implementation (Python, JSON-LD, otherwise) as a projection of it. This document is the fix - the single place every term this design track uses gets one canonical definition, cited back to where it was actually settled.

**How this gets used:** every other document in `documentation/infra-discovery/` should link *here* for a term's definition rather than re-defining it inline. If a term's meaning changes, it changes here first, and every document that used it stays correct by reference rather than needing its own edit.

## Ontology terms

| Term | Definition | Settled in |
|---|---|---|
| **Node** | Not a materialized class or object. A `(domain, kind, id)` key's *view* over `belief_state` - it comes into existence the moment some DSA is invoked against that key and returns an `Artifact`, assembled on read, never constructed or held directly. | `atomicguard`'s "The DSA invocation *is* the node"; `step0_schema.md`'s "Where a node's state actually lives" |
| **`NodeId`** | The compound identity `⟨domain, kind, id⟩`. `id` alone is not unique - only the full triple is. | `step0_schema.md` |
| **`domain`** | Which handler owns a node - `github_actions`, `kubernetes`, `gcp`, .... A registered key in `DSA-CATALOGUE`. | ontology source doc; `step0_schema.md` |
| **`kind`** | A closed type within a `domain`, declared by that domain, not global - `Deployment`, `job`, `Pod`, .... | ontology source doc |
| **`id`** | An identity string, unique only within `(domain, kind)`, not globally. | ontology source doc |
| **`state`** | A node's accumulated knowledge - `Dict[str, Facet]`, keyed by facet name, never a single value. | ontology source doc; `step2_environment_analysis.md`'s "Observable: Partially, and now partially *within* a node too" |
| **`Facet`** | One independently-sensed, independently-timestamped observable property: `{value, observed_at, sensed_by}`. SOSA/SSN-grounded (one Observation per property, not one flat value). | ontology source doc's ontology survey; `step0_schema.md` |
| **`legal_actions`** | What a node can do - always `DSA-CATALOGUE[(domain, kind)]`, a type-level lookup. Never a capability a node instance carries itself. | ontology source doc; `step4_algorithm_fit.md`'s "small steps" note |
| **`Edge`** | A discovered relationship claim: `⟨from, to, edge_type, evidence⟩`. `from`/`to` are `NodeId`s, not strings. Inferred, not directly observed. | ontology source doc; `step0_schema.md` |
| **`edge_type`** | A domain's own native verb (`owns`, `selects`, `contains`) or one of the small, fixed cross-domain **bridge verbs**: `applies-to` (the only one currently grounded in evidence), `exposes`, `triggers`, `publishes-to`, `observed-by`, `selects-from`, `depends-on-external` (named, not yet grounded). | ontology source doc; `step0_schema.md` |
| **`evidence`** | What artifact or observation produced an edge's claim - provenance, not the edge itself. | ontology source doc |

## Discovery-is-bidirectional terms

| Term | Definition | Settled in |
|---|---|---|
| **Bidirectional discovery** | The finding that a sensed node's artifact can reveal an edge where *it* is either `edge.from` or `edge.to` - nothing in the `Edge` tuple guarantees a fixed direction relative to which end was just sensed. | `findings.md` (F-001) |
| **`RECORD-UNCATALOGUED`** | Blue-sky, not yet built. A first-class status for a discovered node whose `kind` has no `DSA-CATALOGUE` entry at all - distinct from `RECORD-UNKNOWABLE`/`RECORD-BLOCKED`, makes a catalogue gap a visible worklist item instead of a silent `RELEVANT() = ∅`. | `atomicguard`'s blue-sky batch (`db07eec`); `worked_examples.md`'s `WE-003`; scheduled as `step5_agent_program.md` Step 4 |

## DSA / dispatch terms

| Term | Definition | Settled in |
|---|---|---|
| **DSA** | A `DualStateAgent` bound to exactly one `ActionPair` for its whole lifetime - a stateless, bounded-retry invocation. Decides nothing about what runs next; that's `pending`/`SELECT-NEXT`'s job, not the DSA's. | ontology source doc's "What a DSA actually is" |
| **`DSA-CATALOGUE`** | `Dict[(domain, kind), DSA set]` - the registered, type-level vocabulary of what can legally be invoked. A flat lookup table, not an object with a method. | ontology source doc; `step0_schema.md` (real domains/kinds reused verbatim from `atomicguard`) |
| **`BRIDGE-CATALOGUE`** | Maps an `edge_type` to the DSA set it unlocks at a given end of that edge. As of `atomicguard` commit `fdc0f51`, a *function* of the end being resolved (`BRIDGE-CATALOGUE[edge_type](end)`), not one value reused for both `edge.to` and `edge.from`. | ontology source doc; revision doc's fix history |
| **`IS-SENSING(dsa)`** | Whether a DSA has no effector (sensing, always eligible) vs. an effector present (acting, gated by `ELIGIBLE`). | revision doc's pseudocode |
| **`RESOLVE-BRIDGES(a)`** | Free - pattern-matches edge evidence directly off an `Artifact` a DSA already fetched. No new DSA invocation. | ontology source doc |
| **`INVOKE(dsa, subject)`** | The sole actuator. Constructs a fresh, stateless DSA bound to `dsa`'s `ActionPair`, runs it against `subject`. | ontology source doc |
| **subject** | A `NodeId` currently being sensed or acted on - the argument to `INVOKE`. | revision doc's pseudocode |
| **`Artifact`** | `atomicguard`'s real output of an `ActionPair` execution. A node's sensed state *is* its artifact content, not something separately modeled. | ontology source doc; `atomicguard-bridge/environment_design.md` |

## `belief_state` / agent-loop terms

| Term | Definition | Settled in |
|---|---|---|
| **`belief_state`** | The shared, persistent, entity-indexed (`domain, kind, id`) world-belief store. Not the environment (which is the real infrastructure itself); not local per-walk bookkeeping the way `discovery/`'s `known`/`visited`/`cleared` sets are - genuinely external, surviving across episodes. | ontology source doc's "Who owns `pending`/`belief_state`"; `step2_environment_analysis.md`'s "`belief_state`: a third thing" |
| **`pending`** | The set of not-yet-invoked `⟨dsa, subject⟩` pairs. Private, per-episode - unlike `belief_state`, never shared across two different `Ψ`s. | ontology source doc |
| **`Ψ`** (intention) | The fixed goal for one episode, delivered once, immutable for its duration. | ontology source doc |
| **`RECORD`/`RECORD-EDGE`/`RECORD-REQUIRES`/`RECORD-UNKNOWABLE`/`RECORD-BLOCKED`** | `belief_state`'s write operations - a sensed artifact, a discovered edge, a declared/discovered dependency set, a permanently-failed sense, an escalated/stagnated DSA, respectively. | revision doc's pseudocode; `step0_schema.md`'s operations table |
| **`requires`** | A subject's declared or discovered prerequisite set - pull-direction, mirrors `atomicguard`'s own `WorkflowStep.requires`. Whether it's static (catalogue-declared) or discovered per-instance is genuinely open. | revision doc |
| **`cleared`** | The monotonically-growing set of subjects whose own `requires` are all themselves in `cleared`. Once a subject enters, it never leaves (`D1`). | revision doc; `step4_algorithm_fit.md` |
| **`SWEEP-CLEARED`** | The iterative fixed-point pass that maintains `cleared` by membership check only, never recursion - replaced the original recursive `CLEARED(subject)` definition, which was cycle-unsafe (`D2`). | revision doc's fix history (`07035745`) |
| **`ELIGIBLE`** | Filters `pending` to pairs that are safe to act on this turn: sensing DSAs always pass; acting DSAs need `subject ∈ cleared`. | revision doc's pseudocode |
| **`RELEVANT`** | De-duplicates and scope-checks a candidate `⟨dsa, subject⟩` pair before it's added to `pending` - not already pending, not already recorded, and `IN-SCOPE`. | revision doc's pseudocode |
| **`IN-SCOPE(subject, Ψ)`** | Named, not defined. The real open soundness question - whether it can be proven to bound the total reachable-and-relevant set determines whether plain `SELECT-NEXT` is sound at all. | revision doc's "Exploration completeness is genuinely open" |
| **`SELECT-NEXT`** | `argmax SCORE(...)` over `eligible` - picks the next pair to invoke. Plain best-first search, unvalidated for termination/completeness. | revision doc |
| **`SCORE`** | Named, not defined - Step 5, a tuning question once `SELECT-NEXT`'s basic soundness is granted. | revision doc; ontology source doc's "Cost features" |
| **`DECIDABLE`/`REPORT`/`ESCALATE`** | The agent loop's terminal branches - `Ψ` can be evaluated now; report the answer; or `pending`/`eligible` is exhausted and `Ψ` still can't be decided, escalate with the evidence gathered so far. | ontology source doc |

## This design track's own vocabulary

| Term | Definition | Settled in |
|---|---|---|
| **`D1`-`D4`** | Four named, contrib-scoped, falsifiable invariants: `D1` monotonic clearance, `D2` cycle-safe clearance, `D3` acting-catalogue allowlist, `D4` acting freshness (checked across a subject's full `requires` ancestor closure, not just the subject itself). Distinct IDs from the core framework's `E1`/`E3`/Invariant 2 on purpose - these are agent-function-specific claims, not additions to the formal model. | `atomicguard` commit `a241844` |
| **Step 0-5** | `step5_agent_program.md`'s build sequence - one new mechanism proven per step, fixture-backed before real, acting deferred furthest (Step 5). | `step5_agent_program.md` |
| **"small steps"** | The explicit, user-set scoping discipline governing every step: build only what proves the one mechanism a step exists to prove, defer everything else on record rather than silently. | design-conversation origin; `atomicguard-bridge/environment_design.md`; `step5_agent_program.md` |
| **blue-sky extensions** | Candidate directions recorded but not validated or chosen - carry no more weight than a possibility until a step actually builds and tests one. | `atomicguard`'s "Blue-sky extensions worth writing down" (`db07eec`) |
| **Testing discipline (fixtures vs. properties)** | Per-claim, not per-step: a claim about one named scenario gets a hand-fixture (this repo's existing worked-example discipline); a claim over an unbounded class of shapes (any `requires` graph, any edge direction) gets property-based testing, starting wherever the first such claim appears - Step 1, not deferred to Step 2. | `decisions.md` (D-004) |

## Not decided

- **Whether this glossary's terms should themselves eventually be expressed as a JSON-LD `@context`** (mapping each term here to a stable identifier, potentially reusing OpenTelemetry's real resource-semantic-convention vocabulary where one already exists for a concept) rather than staying prose-and-table form. `step0_schema.md` has since been restructured around its own `@context` (the ontology's structural shape - `NodeId`/`Facet`/`Edge`); this glossary itself moving to the same notation is a separate, still-open question - not decided here.
- **Whether code, once it exists, enforces this vocabulary automatically** (e.g., linting variable/class names against this glossary) or relies on review discipline alone, the way this repo's other packages do today.

## Related documents

- [`step0_schema.md`](step0_schema.md) - the field-level structural definitions; should be read as *implementing* the terms defined here, not defining them independently.
- [`step2_environment_analysis.md`](step2_environment_analysis.md) / [`step4_algorithm_fit.md`](step4_algorithm_fit.md) / [`worked_examples.md`](worked_examples.md) / [`step5_agent_program.md`](step5_agent_program.md) - every term above is drawn from these five documents plus the cited `atomicguard` sources; this document doesn't introduce new concepts, it consolidates ones already settled elsewhere.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` and `topology_agent_function_requires_and_discovery_validation.md` - the primary source for most terms above.
