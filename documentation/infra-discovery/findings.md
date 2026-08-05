# Infra Discovery: Findings

Concrete gaps or bugs discovered while doing analysis for this track -
distinct from [`decisions.md`](decisions.md) (settled, closed) and
[`open_questions.md`](open_questions.md) (never resolved, no lean implied).
A finding is open until something resolves it; both entries below have
been.

## F-001: `RESOLVE-BRIDGES`/`pending` propagation only checked `edge.to`, never `edge.from`

**Found:** while writing `environment_design.md`'s "Discovery is
bidirectional" section.
**Failing case:** the source ontology document's own `AGENT-FUNCTION`
pseudocode only ever enqueued `RELEVANT(..., edge.to, ...)`. If a sensed
node's artifact revealed an edge where *it* was `edge.to` and the new node
was `edge.from` (e.g. sensing a `Pod` reveals its owning `ReplicaSet` via
`ownerReferences`, the child naming the parent), that whole direction of
discovery silently never happened - no crash, no error, just a node that
never gets discovered.
**Status:** Fixed in `atomicguard` (PR #369) commit `c6a9f697` (`RELEVANT`
now called for both `edge.to` and `edge.from`). A follow-on bug the fix
itself introduced - `BRIDGE-CATALOGUE[edge.edge_type]` reused unchanged for
both ends, when its only grounded rule (`applies-to`) was defined
specifically in terms of `edge.to` - was found and fixed separately in
commit `fdc0f51` (`BRIDGE-CATALOGUE[edge_type]` made a function of the end
being resolved).
**Worked example:** [`worked_examples.md`](worked_examples.md) `WE-003` (`ReplicaSet`/`Pod`) - and its own further, still-open finding (no `DSA-CATALOGUE` entry exists for `ReplicaSet` at all) is tracked separately as `OQ-015` in [`open_questions.md`](open_questions.md), not conflated with this one.

## F-002: `CLEARED`'s recursive pseudocode is cycle-unsafe

**Found:** while reviewing `atomicguard` commit `67c1635`, checked against
real `WorkflowState.is_satisfied()` (`domain/models.py:337`, a flat O(1)
lookup, safe by construction) and `discovery/`'s own actual code
(membership check against an already-built set, never recursive).
**Failing case:** the pseudocoded `CLEARED(subject) = RECORDED(subject) and
all(CLEARED(r) for r in REQUIRES(subject))` would stack-overflow on a
cyclic `requires` declaration, where the real `WorkflowOrchestrator`
equivalent instead deadlocks cleanly (`None`, reported `FAILED`). Flagged
in `algorithm_fit.md` as a live risk for this track specifically, not a
hypothetical import: real infrastructure dependency graphs (unlike
`discovery/`'s hand-authored, construction-time-validated toy topology) are
discovered at runtime, with no equivalent validation available before a
cycle could occur.
**Status:** Fixed in `atomicguard` (PR #369) commit `0703574` with
`SWEEP-CLEARED`, an iterative fixed-point pass maintaining `cleared` as a
monotonically-growing set, membership-check only, matching the safe
pattern above rather than the unsafe recursive one.

## F-003: `step1_environment_specification.md`'s Performance-measure row overclaimed its own source fidelity

**Found:** during a requested scrutiny pass on `step1_environment_specification.md`
before treating this track's structure as ready to replace the live
`documentation/infra-discovery/` - checked every quote and paraphrase
against `platform_topology_peas_and_cli_actions.md` directly, not assumed
accurate because the rest of the file checked out.
**Failing case:** the row's original text claimed the "correctly
attributing failure to the specific node in the chain" requirement was
"inherited directly from §3's own GKE-handoff caveat, not new here." §3's
actual caveat - "for GKE-backed resources, correctly handing off to the
Kubernetes PEAS above rather than duplicating it" - is an instruction about
how *that analysis document* should be authored (don't re-derive K8s's own
PEAS when covering GKE-hosted resources), not a runtime failure-attribution
requirement. The rest of `step1`'s file checked out almost entirely
verbatim against the source (its three Percepts bullets are exact
quotes) - which is exactly why this one row's overclaim was worth catching
rather than assuming the pattern held throughout.
**Status:** Fixed - the row now states plainly that the failure-attribution
claim is a reasonable extension of §3's scoping note, not something §3
already said.

## Related documents

- [`decisions.md`](decisions.md) - settled decisions, distinct from findings.
- [`open_questions.md`](open_questions.md) - genuinely undecided items, including duplicate mentions of both findings' surrounding context (e.g. `algorithm_fit.md`'s original "Open, not resolved" section referenced `CLEARED`'s fix as still-relevant context, not as an unresolved item itself - consolidated here to avoid the same content appearing as both a finding and an open question).
- [`step1_environment_specification.md`](step1_environment_specification.md), [`step2_environment_analysis.md`](step2_environment_analysis.md), [`step4_algorithm_fit.md`](step4_algorithm_fit.md) - the analysis documents these findings were extracted from.
