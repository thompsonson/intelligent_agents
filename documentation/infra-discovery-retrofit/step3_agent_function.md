# Infra Discovery: Agent Function (Step 3)

**Retrofit note:** previously a stub. Filled in from `atomicguard`'s
`topology_agent_function_requires_and_discovery_validation.md` ("Revised
pseudocode" section) — checked directly against that document, not
reconstructed from memory. Per the correction that prompted this: the hard
part (the actual percept→action pseudocode — `ELIGIBLE`, `SWEEP-CLEARED`,
`SELECT-NEXT`, `RELEVANT`, `IN-SCOPE`) already existed, complete, on
`atomicguard` PR #369 — and [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md)
already cites every one of these functions as `Settled in: revision doc`.
This file is a translation pass, not new design work — reproducing the
pseudocode in this track's own file rather than leaving it cited at second
hand, the same discipline [`step2_environment_analysis.md`](step2_environment_analysis.md)
already applied to the Node/Edge ontology from the same source document.

## Percepts

A DSA invocation's outcome, as this track's own vocabulary already has it
([`step0_schema.md`](step0_schema.md)):

- **An `Artifact`** — the sensed result. `belief_state.RECORD(subject, a)`
  merges whatever `Facet`(s) it represents into `subject`'s facet map (per
  `step0_schema.md`'s `RECORD` operation — not a full replace, prior facets
  from other DSAs survive).
- **`RmaxExhausted`** — the DSA's retry budget ran out without a passing
  guard. `belief_state.RECORD-UNKNOWABLE(dsa, subject)` — propagates:
  nothing requiring `subject` can ever clear (`D2`).
- **`EscalationRequired`/`StagnationDetected`** — the DSA's own escalation
  signal. `belief_state.RECORD-BLOCKED(dsa, subject, percept)` — same
  propagation as `RmaxExhausted`.
- **`Ψ` itself**, once, at episode start — not a per-turn percept, the fixed
  intention for the whole episode.

## Actions

The sole actuator is `INVOKE(dsa, subject)` — constructs a fresh, stateless
DSA bound to `dsa`'s `ActionPair`, runs it against `subject`
([`step0_ubiquitous_language.md`](step0_ubiquitous_language.md)'s `INVOKE`
entry). There is no "move" action, no notion of a current position — a DSA
is invoked directly against whatever `NodeId` is already known, the instant
it's known. The action *space* on any given turn is `pending` (the set of
not-yet-invoked `⟨dsa, subject⟩` pairs), narrowed to `eligible`
(`ELIGIBLE`, below) before `SELECT-NEXT` picks one.

## The pseudocode itself

Reproduced from `atomicguard`'s revision document, current as of its
`BRIDGE-CATALOGUE` end-mismatch fix (`fdc0f51`) and the `D1`–`D4` invariant
naming (`a241844`). Percepts and `INVOKE(dsa, subject)` as the sole actuator
as stated above.

```
function AGENT-FUNCTION(percept) returns an action
    persistent: Ψ, the fixed intention for this episode
                pending, set of not-yet-invoked ⟨dsa, subject⟩ pairs
                belief_state, reference to the shared, persistent world-belief store

    if percept contains Ψ:
        state.Ψ ← Ψ
        pending ← { ⟨dsa, root⟩ : root ∈ ROOTS(Ψ), dsa ∈ DSA-CATALOGUE[root.domain, root.kind] }

    elif percept is the outcome of ⟨dsa, subject⟩:
        if percept is an Artifact a:
            belief_state.RECORD(subject, a)
            belief_state.RECORD-REQUIRES(subject, REQUIRES-OF(dsa, subject, a))

            for edge in RESOLVE-BRIDGES(a):                # free — pattern-matched from a, no new DSA
                belief_state.RECORD-EDGE(edge)
                pending ← pending ∪ RELEVANT(BRIDGE-CATALOGUE[edge.edge_type](edge.to), edge.to, Ψ, belief_state)
                pending ← pending ∪ RELEVANT(BRIDGE-CATALOGUE[edge.edge_type](edge.from), edge.from, Ψ, belief_state)
            pending ← pending ∪ RELEVANT(DSA-CATALOGUE[subject.domain, subject.kind], subject, Ψ, belief_state)
        elif percept is RmaxExhausted:
            belief_state.RECORD-UNKNOWABLE(dsa, subject)
        elif percept is EscalationRequired or StagnationDetected:
            belief_state.RECORD-BLOCKED(dsa, subject, percept)

    if DECIDABLE(Ψ, belief_state):
        action ← REPORT(Ψ, belief_state)
    else:
        eligible ← ELIGIBLE(pending, belief_state)
        if eligible = ∅:
            action ← ESCALATE(Ψ, belief_state)
        else:
            ⟨dsa, subject⟩ ← SELECT-NEXT(eligible, belief_state)
            pending ← pending − {⟨dsa, subject⟩}
            action ← INVOKE(dsa, subject)

    return action

function ELIGIBLE(pending, belief_state) returns a set of pairs
    belief_state.SWEEP-CLEARED()
    return { ⟨dsa, subject⟩ ∈ pending : IS-SENSING(dsa) or subject ∈ belief_state.cleared }

function belief_state.SWEEP-CLEARED()
    # Iterative fixed-point, cycle-safe (D2). cleared is monotonic (D1) —
    # a subject enters exactly once, by membership check, never recursion.
    changed ← true
    while changed:
        changed ← false
        for subject in belief_state.RECORDED-SUBJECTS() − belief_state.cleared:
            if all(r ∈ belief_state.cleared for r in belief_state.REQUIRES(subject)):
                belief_state.cleared.add(subject)
                changed ← true

function DECIDABLE(Ψ, belief_state) returns a boolean
    return GUARD-EVALUABLE(Ψ, belief_state)

function SELECT-NEXT(eligible, belief_state) returns a pair
    return argmax_{⟨dsa,subject⟩ ∈ eligible} SCORE(dsa, subject, belief_state)
    # UNVALIDATED for this or any track — see "What's still open," below.

function RELEVANT(dsa_set, subject, Ψ, belief_state) returns a set of pairs
    return { ⟨dsa, subject⟩ : dsa ∈ dsa_set
                             ∧ ⟨dsa, subject⟩ ∉ pending
                             ∧ ¬belief_state.RECORDED(dsa, subject)
                             ∧ IN-SCOPE(subject, Ψ) }

function IN-SCOPE(subject, Ψ) returns a boolean
    # Named, not defined. The real soundness question — see OQ-007.

function REPORT(Ψ, belief_state) returns an action
    return REPLY-TO-USER(EVALUATE(Ψ, belief_state))

function ESCALATE(Ψ, belief_state) returns an action
    return REPLY-TO-USER(UNDECIDABLE, belief_state.EVIDENCE-FOR(Ψ))
```

`SCORE`/`ROOTS`/`REQUIRES-OF` remain named, not defined, matching the source
document's own stance — Step 5 (of this build sequence; see
[`step5_agent_program.md`](step5_agent_program.md)) territory, not this
one's.

## Cost features — named in the source, not yet checked against this track's three domains

The source document's "Cost features" section enumerates generator-side
(tokens, latency, non-determinism, rate limits) and effector-side
(blocking-vs-snapshot, idempotency, irreversibility, `e_undo` cost,
`e_dryrun` as a cheap pre-check, blast-radius risk, timeout) cost features
for `SCORE` to eventually weigh. None of these have been checked against
this track's actual three domains yet — e.g. whether `gh run watch`'s
blocking wait behaves differently from `kubectl wait`'s for `SCORE`'s
purposes, or whether `gcloud`'s per-service inconsistent status vocabulary
(§3's own finding) adds a real, track-specific cost term beyond what the
source document's generic list already names. Not attempted here — `OQ-006`
tracks this as still open.

## What's still open here — inherited, not new to this file

Everything the source document itself leaves open stays open by writing
this file — translating the pseudocode doesn't resolve any of it:

- **`SELECT-NEXT`/`IN-SCOPE` soundness** (`OQ-007`) — plain best-first
  search, unvalidated for termination/completeness, in this track or any
  other.
- **Whether `requires` is static (catalogue-declared) or discovered
  per-instance** — genuinely open, inherited directly.
- **`SCORE`'s real feature set** (`OQ-006`, above).

## Related documents

- [`step4_algorithm_fit.md`](step4_algorithm_fit.md) — Step 4; the fit argument that reasons *about* this pseudocode without previously having this file to reason from.
- [`step2_environment_analysis.md`](step2_environment_analysis.md) — Step 2; `RESOLVE-BRIDGES`/bidirectional propagation, the finding this file's `RESOLVE-BRIDGES` loop already reflects the fix for.
- [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md) — every term above, already cited as `Settled in: revision doc` before this file existed.
- [`decisions.md`](decisions.md) — `D1`–`D4`, the invariants `SWEEP-CLEARED`/`ELIGIBLE` above depend on.
- [`open_questions.md`](open_questions.md) — `OQ-006`, `OQ-007`, and the `requires` staticness question, all inherited unresolved.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` — the source of the pseudocode above, including its own commentary this file doesn't reproduce in full.
