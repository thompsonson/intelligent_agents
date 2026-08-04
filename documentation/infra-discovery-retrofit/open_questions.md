# Infra Discovery: Open Questions

Consolidated from the "Not decided" sections of `environment_design.md`,
`algorithm_fit.md`, `schema.md`, `roadmap.md`, and `ubiquitous_language.md`
(the originals, in `documentation/infra-discovery/`), plus `roadmap.md`'s
"Step 0: two decisions" section, reclassified here rather than left
mislabeled - neither of its two items was ever actually decided.

**A real payoff of doing this consolidation, not a claim made in the
abstract:** three of the entries below (`OQ-002`, `OQ-003`) turned out to
be the same open question asked independently in three or four separate
documents, invisible while scattered - `belief_state`'s persistence backend
is asked in `environment_design.md`, `algorithm_fit.md`, *and* `schema.md`;
edge identity/de-duplication is asked in both `environment_design.md` and
`schema.md`. Nothing caught this while it lived as five separate "Not
decided" sections at the bottom of five separate documents. That's a
concrete sizing data point in favor of consolidation, not just a
convenience.

**A second payoff, found on a later review pass, not the first:**
`OQ-015` and `OQ-016` below were added after `findings.md`, `worked_examples.md`,
and `step4_algorithm_fit.md` were each found to claim this content already
lived here - it didn't. A consolidated file only earns "check here first"
if it's actually complete; the gap survived the original consolidation
pass and was only caught by checking those claims against this file
directly, not by trusting them.

## OQ-001: Node identity stability

Does an `id` reliably name the same real-world thing across sensing calls?
**Source:** `environment_design.md`, inherited from the source ontology
document's own open questions.

## OQ-002: `belief_state`'s concrete interface, index, and persistence backend

**Source:** raised independently in `environment_design.md`,
`algorithm_fit.md`, and `schema.md` - three separate documents, same
question, none referencing the other two's copy. Related but distinct from
`OQ-010` below (which is about *implementation strategy* - mutable store
vs. pure projection - a design-approach choice this question's "backend"
sits underneath).

## OQ-003: Edge identity, de-duplication, and staleness

Whether `Edge` needs its own `observed_at`/`sensed_by`; whether two
independent discoveries of the same relationship (once from `from`'s
artifact, later from `to`'s) collapse into one `Edge` or stay two
timestamped observations. **Source:** raised in both `environment_design.md`
and `schema.md`; sharpened by the bidirectional-discovery finding (`F-001`
in [`findings.md`](findings.md)) in the first, restated independently in
the second.

## OQ-004: `DSA-CATALOGUE`/`BRIDGE-CATALOGUE`'s concrete shape in this repo's terms

Deliberately not sketched in `schema.md`'s type signatures - premature
before deciding what real (or fixture-backed) domains this environment will
actually be built against. **Source:** `environment_design.md`.

## OQ-005: What concrete scenario this gets validated against, and its per-step topology

`atomicguard-bridge/`'s `pipeline_fanout_lite` reuse doesn't fit here -
fixed six-node topology, one implicit domain. Partially narrowed by
`topology_source_comparison_cartography_fix_bespoke.md`: bespoke DSAs
against the catalogued domains, not Cartography/Fix Inventory wholesale.
`step5_agent_program.md`'s own build sequence says what property each step's
scenario needs to exercise (AND-joins for Step 2, an unregistered kind for
Step 4, ...) without picking concrete fixture files, domains, or node
counts - each step's own `scenario.md`, written when that step starts, per
the same discipline every prior arc in this repo followed. **Source:**
`environment_design.md`'s "what concrete scenario" item and `roadmap.md`'s
"exact scenario topology per step" item - the same open question, phrased
once at the environment level and once at the build-sequence level.

## OQ-006: `SCORE`'s real feature set

Generator-side token/latency/non-determinism costs, effector-side
idempotency/blast-radius/dry-run costs, known-in-advance vs. learned,
subject-dependent variance within one DSA type - already enumerated in the
source document's own "Cost features" section, not re-derived, still
entirely undemonstrated in any code in either repo. **Source:**
`algorithm_fit.md`; also named in `step5_agent_program.md`'s "What doesn't get
its own step" as Step-5-adjacent.

## OQ-007: `IN-SCOPE(subject, Ψ)` boundedness

The central open soundness question: whether plain `argmax SCORE` over
`eligible` is sound at all depends entirely on whether `IN-SCOPE` can be
proven to bound the total reachable-and-relevant set. If bounded, greedy
`SELECT-NEXT` run to exhaustion is sound; if not, something with a fairness
guarantee is needed. **Source:** `algorithm_fit.md`, inherited from
`atomicguard`'s revision document's "Exploration completeness is genuinely
open" section.

## OQ-008: What a genuinely failing/flaky DSA invocation does to `pending`/`SELECT-NEXT`

This track's own properties table (`step2_environment_analysis.md`) already
declares `Deterministic/Stochastic: Stochastic` - a failing sense is the
expected case, not an edge case - and nothing in the source document's
`RECORD-UNKNOWABLE`/`RECORD-BLOCKED` propagation has been checked against a
real implementation yet either. **Source:** `algorithm_fit.md`.

## OQ-009: Whether the ontology's `@context` (or the vocabulary generally) is ever registered at a real, dereferenceable IRI

Whether that registration reuses OpenTelemetry Resource Semantic Convention
terms per-property where one already exists. **Source:** raised in both
`schema.md` (about its own `@context`) and `ubiquitous_language.md` (about
whether the glossary itself should become a `@context`) - related but not
identical: `step0_schema.md`'s structural notation question is now answered
(it is JSON-LD-shaped) - a decision recorded on the `atomicguard` side of
this design conversation, not as an entry in this track's own
`decisions.md`; `ubiquitous_language.md`'s own glossary-as-`@context`
question is still fully open.

## OQ-010: `belief_state`'s implementation strategy - mutable store vs. `σ = proj(R)`

Mutable store (`RECORD`/`RECORD-EDGE` write into it directly, `cleared`
built incrementally by `SWEEP-CLEARED`, matching the pseudocode as
literally written) vs. a pure, read-only projection over the sequence of
`INVOKE` outcomes, reusing `atomicguard`'s own proven workflow-state pattern
(the blue-sky idea, `db07eec`). The tension the blue-sky note itself flags
- whether `SWEEP-CLEARED`'s incrementally-built `cleared` set is compatible
with "nothing independently stored" - needs to be worked through, not
assumed either way, before `schema.md`'s `belief_state` operations table
gets implemented against one model or the other. **Source:** `roadmap.md`'s
"Step 0" section - originally titled "two decisions," reclassified here
since neither item was actually resolved in the source text.

## OQ-011: `Edge`'s shape - plain tuple vs. `Facet`-style accumulated evidence

Plain `⟨from, to, edge_type, evidence⟩` tuple (as `schema.md` has it today)
vs. `Facet`-style accumulated evidence, keyed by `(from, to, edge_type)`,
`evidence` a growing list instead of a one-shot field (the other blue-sky
idea). Adopting the second folds `OQ-003` into one structural move; not
adopting it leaves `OQ-003` separately open. **Source:** `roadmap.md`'s
"Step 0" section, same reclassification as `OQ-010`.

## OQ-012: Whether Step 0 (of the build sequence, not this process's Step 0) gets its own short design note

Whether `OQ-010`/`OQ-011` get a dedicated short design note when decided,
or get decided inline at the build sequence's own Step 1 start. **Source:**
`roadmap.md`'s "Not decided" section - itself only decidable once `OQ-010`/
`OQ-011` actually get resolved, which this retrofit doesn't do.

## OQ-013: Facet value typing

`Any` in `schema.md`'s current schema is honest, not a placeholder for
something already decided - different facets have structurally different
value shapes (`conclusion` an enum string; `replica_readiness` a `{ready,
desired}` pair). Whether to type each facet name's value shape per-kind, or
stay untyped and push validation into each DSA's own guard. **Source:**
`schema.md`.

## OQ-014: Whether code, once it exists, enforces the vocabulary automatically

Linting variable/class names against `ubiquitous_language.md`, vs. relying
on review discipline alone, the way this repo's other packages do today.
**Source:** `ubiquitous_language.md`.

## OQ-015: What `RELEVANT` does when a lookup hits an unregistered `kind`

Concretely: `worked_examples.md`'s `WE-003` - `ReplicaSet` is discovered as
`edge.from` via a `Pod`'s real `ownerReferences`, but
`DSA-CATALOGUE[(kubernetes, ReplicaSet)]` doesn't exist, so
`RELEVANT(BRIDGE-CATALOGUE[owns](edge.from), edge.from, Ψ, belief_state)`
has nowhere to go. Two ways this could go, neither decided: (a) discovery
genuinely stops one hop short, `ReplicaSet` recorded as an edge endpoint
but never itself sensed; (b) the sensing DSA is authored to resolve past
unregistered intermediate kinds itself, so the edge discovered skips
`ReplicaSet` entirely. **This is the gap `RECORD-UNCATALOGUED` (blue-sky,
`db07eec`) is meant to eventually make a visible status instead of a silent
`RELEVANT() = ∅`** - scheduled as `step5_agent_program.md` Step 4.
**Gap found during review, not originally captured here:** `findings.md`
(F-001), `worked_examples.md`, and `step4_algorithm_fit.md` all state that this
question "is tracked... in `open_questions.md`" - it wasn't, until this
entry. **Source:** `worked_examples.md`'s `WE-003`, "Where this gets genuinely
hard."

## OQ-016: Acting-DSA selection, when more than one applies to a subject

`D-003` in [`decisions.md`](decisions.md) settles the sensing half
(aggregation - enqueue all applicable sensing DSAs at once); the
genuine-selection reading (multiple *acting* DSAs compete for the same
subject, a real scoring problem) stays open, deferred along with acting
generally (sensing-first scope, every source document). **Gap found during
review:** referenced twice in `step2_environment_analysis.md` ("the
genuine-selection reading stays open for acting DSAs") and once in
`decisions.md`'s own `D-003` status line, but never previously given its
own entry here. **Source:** `step2_environment_analysis.md`'s "`legal_actions`:
a catalogue lookup, not a node field" section, inherited from
`atomicguard-bridge/algorithm_fit.md`'s original "DSA selection" open item.

## OQ-017: `RECORD-REQUIRES` doesn't auto-enqueue its own targets - the reachability risk is not auto-solved

**Gap found by checking `step3_agent_function.md`'s reproduced pseudocode
against the real source line by line, not by inference.** The real
`AGENT-FUNCTION` pseudocode's `RECORD-REQUIRES(subject, REQUIRES-OF(dsa,
subject, a))` line carries a load-bearing comment in the source, stripped
during reproduction along with the rest of the pseudocode's inline
commentary: an earlier draft auto-enqueued every `requires` target into
`pending` to close this gap by construction, and it was deliberately
walked back - "nothing validates that as correct or necessary." The actual
risk, stated plainly in the source: **"a `requires` target named in some
DSA's `REQUIRES-OF` output but never independently discovered via
`RESOLVE-BRIDGES`/`DSA-CATALOGUE` dispatch would deadlock silently, and
nothing here currently prevents that."** `discovery/`'s own and-joins step
treats this as "the reachability constraint" - a scenario-design discipline
the graph author has to get right by hand, not a guarantee the algorithm
provides. This track inherits the identical exposure and, until this
entry, had nothing saying so. **Source:** `atomicguard`'s
`topology_agent_function_requires_and_discovery_validation.md`, "Still
open" section ("The reachability risk is not auto-solved").

## OQ-018: Does `requires`/`cleared` ever need to gate sensing, not just acting?

`ELIGIBLE`'s current policy default (reproduced in `step3_agent_function.md`)
is that sensing DSAs always pass regardless of `cleared`, and only acting
DSAs are gated by `subject ∈ cleared`. The source document states this as
"a policy default... not a fact `discovery/` establishes" and names the
question of whether sensing ever needs the same gate as deferred, not
ruled out. **Gap found the same way as `OQ-017`** - present in the real
pseudocode's commentary, absent from this track's translation. **Source:**
`atomicguard`'s `topology_agent_function_requires_and_discovery_validation.md`,
"Still open" section.

## OQ-019: Where this agent's code eventually lands - `atomicguard`, `intelligent_agents`, or a new repo

Lower stakes than `OQ-017`/`OQ-018` - an administrative question, not a
design-soundness one - but the source document names it explicitly as
still open, and this track (one of the three named candidates) has nothing
saying so. **Source:** `atomicguard`'s
`topology_agent_function_requires_and_discovery_validation.md`, "Still
open" section ("Repo placement").

## Related documents

- [`decisions.md`](decisions.md) - settled decisions; two items here (`OQ-010`, `OQ-011`) were originally mislabeled as belonging there.
- [`findings.md`](findings.md) - resolved gaps/bugs, distinct from these still-open questions.
- [`step2_environment_analysis.md`](step2_environment_analysis.md), [`step4_algorithm_fit.md`](step4_algorithm_fit.md), [`step0_schema.md`](step0_schema.md), [`step5_agent_program.md`](step5_agent_program.md), [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md), [`worked_examples.md`](worked_examples.md) - the analysis documents these questions were extracted from.
