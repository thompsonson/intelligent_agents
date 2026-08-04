# Infra Discovery: Decisions

Lightweight ADR-style register, per
[`agent_design_process_extensions.md`](https://github.com/thompsonson/atomicguard/blob/claude/platform-topology-agent-eduh7h/docs/design/notes/agent_design_process_extensions.md).
One entry per decision actually made for this track - not open questions,
not things merely stated with confidence. Extracted from
`environment_design.md` and `roadmap.md` (the originals, in
`documentation/infra-discovery/`), not invented for this retrofit.

## D-001: Node identity is a compound key

**Status:** Decided
**Decision:** `NodeId` is `⟨domain, kind, id⟩`, not a bare string.
**Rules out:** treating `id` alone as globally unique, the way
`real_discovery/`'s `StatefulDiscoveryNode.id: str` did.
**Source:** follows directly from the source ontology (`Node = ⟨domain,
kind, id, state, legal_actions⟩`); not a judgment call. Originally recorded
in `environment_design.md`'s "Resolved design questions."

## D-002: `requires` and `legal_actions` are different mechanisms

**Status:** Decided
**Decision:** `requires`-style declared dependency config and
`legal_actions`-style catalogue lookup are kept as separate mechanisms, not
folded into one field.
**Rules out:** treating `legal_actions` as node-instance config the way
`atomicguard-bridge/`'s `requires: Tuple[str, ...]` was (static, per-node).
`legal_actions` here is derived from `(domain, kind)` via a shared
catalogue, not declared per instance.
**Source:** `environment_design.md`'s "Resolved design questions," per the
"Who owns what" precedent in `atomicguard-bridge/environment_design.md`.

## D-003: Sensing-DSA aggregation, not per-node selection

**Status:** Decided (sensing DSAs only - acting DSA selection stays an open question)
**Decision:** when more than one sensing DSA applies to a newly-discovered
subject, all of them get enqueued into `pending` at once
(`RELEVANT(DSA-CATALOGUE[subject.domain, subject.kind], ...)`) - selection
doesn't happen per-node at discovery time.
**Rules out:** a per-node "pick one DSA" selection step at discovery time
for sensing.
**Source:** read directly off the source ontology document's own
`RELEVANT`/`pending` mechanism, not asserted - `environment_design.md`'s
"`legal_actions`: a catalogue lookup, not a node field" section.

## D-004: Property-based testing starts at Step 1, not deferred to Step 2

**Status:** Decided
**Decision:** any claim that holds over an unbounded class of shapes (any
`requires` graph including cyclic ones; any edge direction) gets
property-based testing from the step it first appears in, alongside
hand-traced fixtures - not deferred to whichever step happens to name the
mechanism most directly.
**Rules out:** treating property-based testing as something only `D1`/`D2`
(Step 2's `requires`/`SWEEP-CLEARED` work) need; Step 1's bidirectional
propagation claim is the same shape and gets it too.
**Source:** `roadmap.md`'s "Testing discipline" section, prompted by
`atomicguard`'s `a241844`. Honestly scoped there, not retroactive:
`discovery/`'s own merged `2×|E|` bound has the identical gap and is
explicitly not proposed for retrofit.

## Related documents

- [`findings.md`](findings.md) - things discovered broken or missing, distinct from decisions.
- [`open_questions.md`](open_questions.md) - genuinely undecided items, including two that were originally mislabeled as decisions (`roadmap.md`'s "Step 0").
- [`step2_environment_analysis.md`](step2_environment_analysis.md), [`step4_algorithm_fit.md`](step4_algorithm_fit.md), [`step5_agent_program.md`](step5_agent_program.md) - the analysis documents these decisions were extracted from.
