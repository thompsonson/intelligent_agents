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

## Related documents

- [`decisions.md`](decisions.md) - settled decisions; two items here (`OQ-010`, `OQ-011`) were originally mislabeled as belonging there.
- [`findings.md`](findings.md) - resolved gaps/bugs, distinct from these still-open questions.
- [`step2_environment_analysis.md`](step2_environment_analysis.md), [`step4_algorithm_fit.md`](step4_algorithm_fit.md), [`step0_schema.md`](step0_schema.md), [`step5_agent_program.md`](step5_agent_program.md), [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md) - the analysis documents these questions were extracted from.
