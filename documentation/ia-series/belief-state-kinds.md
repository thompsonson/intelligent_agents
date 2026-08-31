---
title: "Belief State Kinds — the justification axis"
summary: "A Kind classifies a held belief by what justifies holding it. Formal statement of the nine Belief State Kinds — static, exogenous, enacted, derived, imputed, verified, intent, attested, peer-asserted — the justification axis for what an agent holds. Written to render equally as an IA-series post and a book chapter."
status: "research"
type: "term-sheet"
categories: "ia-series, ontology, belief-state"
---

# Belief State Kinds — the justification axis

*Term-sheet. A **Kind** classifies a belief by **what justifies the agent in holding it** — the
justification axis introduced in [IA 13](../13-ontologies/blog.md). This document is the formal
statement of the **Belief State Kinds**: the subset of the full Kind set whose truth-makers justify
*held world-beliefs*. It is written to serve equally as a series post and a book chapter — the
narrative carries the definitions; the tables carry the form.*

## Scope — the belief-state set

The full Kind set (the canonical term-sheet, `thompsonson/atomicguard`, `docs/design/notes/kind_taxonomy.md`)
is **10** Kinds under the broad reading. This document is scoped to the **9** that justify held
beliefs:

**`static · exogenous · enacted · derived · imputed · verified · intent · attested · peer-asserted`**

The tenth, **`granted`**, is **not a Belief State Kind.** Its truth-maker — the human's authority —
does not justify a belief about the world; it expresses an *authorization* (what the agent may do).
It lives on the **Identity** axis, developed separately ([`identity.md`](https://github.com/thompsonson/atomicguard/blob/docs/frontier-question/docs/design/notes/identity.md)).
Carrying it inside the justification axis is what made Identity and Belief State trip over each other;
separating the two is part of this document's scope. (The 10-Kind term-sheet keeps `granted` in the
set; here it is declared out of scope with a cross-reference, not deleted.)

Two things the Kind axis is deliberately **not**:

- **Not the channel axis** — how the belief *arrived* (sensed vs. reported). IA 13's two-channel
  framing smuggled a transport axis into the ontology; it stays off this one.
- **Not the freshness axis** — how *current* the copy is (`:fresh-for` / `:stale-on`). Justification
  names who makes the fact true; freshness declares when to re-sense or re-check. They are orthogonal.

## The axis, as an arc

A Kind is a *positive* justification, from strong to weak. None is "an absence": a weak justification
is still a justification. The arc this document follows:

1. **the world and logic** justify strongly — `static`, `exogenous`, `enacted`, `derived`;
2. **a model's trained prior** justifies weakly — `imputed` (the weakest on the axis, and the one
   policy *quarantines*);
3. **a deterministic guard** earns a claim against the world — `verified`;
4. **a human** vouches for or assigns the held fact — `intent`, `attested`;
5. **another agent** asserts it — `peer-asserted` (only ever unverified until the consumer checks).

## The nine Kinds

### World & logic — the four from IA 13, refined

**`static`** — true at setup, never changed by any action or sensing. Justified by designer
stipulation. Example: `domain(x)`. Kept as-is — PDDL canon; nothing gained by renaming.

**`exogenous`** — a fact whose dynamics are independent of the agent's actions; its truth is set by
the world at the moment of sensing, and it can drift the moment the world moves. Example: `node(id)`,
`ci-run(c)`, `host(h)`. The world is the justification; sensing is the channel.

**`enacted`** *(IA 13: `controllable`)* — a fact the agent **made true by its own action, at a
specific point in time**. The rename from IA 13's `controllable` carries the temporal sense:
`controllable` is a standing capability (atemporal), `enacted` is an act with a `when` — exactly the
provenance question. The published name stays as a permanent parenthetical. IA 13's test: the
effector's successful return entails the fact. Example: `occupies(agent, wt)`, `visited(node)`.

**`derived`** — **monotonic** entailment over other atoms; computed by the state model, never
asserted. Freshness composes: a derived head's bound is the minimum of its bodies'; stale signals
OR-compose. Example: `reachable(a,b)`, `is-leaf(n)`, and `MergeGate`
(`approval ∧ checks_green ∧ zero_unreplied ∧ no_stale_failure`). A *defeasible* default-rule
conclusion is not `derived` — see `assumed` (§Reserved).

### The model — where the parrot lives

**`imputed`** — a value a model supplied **from its trained prior**: a statistical, inductive
justification — the weakest on the axis. Enough to hold the value as a *proposal*; never enough to
depend on it. The honest home for the "stochastic parrot": generator output, the model's `"FINAL:"`
or self-assessed "merge-ready" *before any guard*.

- **Re-check:** none. Re-running the generator produces a different value, not a refresh.
- **Quarantined by policy.** An `imputed` fact MAY NOT satisfy a precondition or feed any downstream
  logic. Its bound is `:scope ap-attempt` — it exists only within one action-pair attempt. **The
  guard is the sole bridge out:** `imputed` → a deterministic guard passes → `verified`; otherwise it
  is discarded within the attempt.
- **Uncertainty annotation.** An `imputed` fact carries an uncertainty annotation —
  Dempster–Shafer belief/plausibility mass, or logprob confidence — as **metadata on the copy, not a
  truth-maker**. It quantifies *how weak* the trained-prior justification is without turning it into
  a truth-determinant.
- **D3 reading.** AtomicGuard's "the generator channel stays out of the predicate-Kind system"
  means "out of the *load-bearing* system," not "out of the belief state." Generator output enters as
  `imputed`; the quarantine keeps it off every load-bearing path.
- **Name.** From statistics: an imputed value is a model-filled stand-in for missing data, flagged
  as not-observed. Not `stochastic` — the axis names the justification (a trained prior), not the
  process.

### The guard — earning it against the world

**`verified`** — a fact a **deterministic, I/O-free guard** has checked against captured world
output (test results, exit codes, a diff, a sensed artifact). Formally: the output of `a_guard` or
`a_guard_eff` passing.

- **Re-check:** re-run the guard. `:fresh-for` applies.
- **Not `derived`:** there is an *operation against the world*, not an entailment — and a `⊥` verdict
  that is not a logical contradiction.
- **Not `enacted`:** the agent *proposed* the claim; the guard *earned* it. The generator's
  successful return does not entail "the tests pass."
- **Requires a deterministic guard.** A guard that calls an LLM-judge produces `imputed`, not
  `verified`. A guard that *waits for a human* is legitimate but admits `intent`/`attested` (and
  `granted` on the Identity side), not `verified`.
- **Origin:** the response-validation gap — what OQ-001 resolved as "its own Kind": `MergeGate`
  stays `derived` (a boolean composition); the individual checks feeding it are `verified`.
- Foundational reference: the *Dual-State Architecture* ([arXiv:2512.20660](https://arxiv.org/abs/2512.20660)) —
  *"Guard functions act as sensing actions that project opaque LLM outputs onto observable workflow
  state."* `verified` is the Kind of a fact once that projection has occurred.

### The human, held — two faces *(held, not world)*

**`intent`** — the human's **assigned goal**, held by the agent and reasoned from. Comes from Ψ (the
goal specification); the agent never invents it. Bound: `:scope episode` — a re-issued goal is a new
episode.

- **Net-new to the synthesis** — no source defines an `intent` Kind. It is *motivated* by TORPID's
  "form intentions from the given goal" (`dev`-fleet §2), which is deliberation-loop language, not a
  predicate Kind. Included because the held goal is in scope and its truth-maker (the human's will)
  is distinct from the other eight.

**`attested`** — a human asserts **a state of affairs**, on their own epistemic authority: signs off
a release, vouches "this output is correct." Trust-based; holds until withdrawn.

- **Two things a human can do.** *Reviewing an artifact for quality* ("is this patch good?") is
  escalation — it yields context, not a verdict. *Vouching for a scoped fact* ("the release is signed
  off") is a binary authority determination. `attested` is the Kind of the second; the first produces
  no `attested` fact, only context.
- **Not SPIFFE.** SPIFFE workload attestation is identity enrollment — its output is `granted`, not a
  fact-vouch (see the Identity boundary).

### Inter-agent

**`peer-asserted`** — a fact **another agent claimed**. The consuming agent must verify it itself —
re-sense, or run a guard — to promote it; a promoted fact then takes the Kind of *how it was
verified* (`exogenous` or `verified`). It is never auto-promoted by trust. There is deliberately **no
`peer-validated`**: trusting a peer's execution is itself an assessment, and Promise Theory rules out
silently inheriting a peer's faults — *a promise is not a guarantee*.

## Lifecycle and bounds

| Kind | Bound mechanism |
|---|---|
| `static` | none — immutable |
| `exogenous` | `:fresh-for N` (wall-clock) / `:stale-on <signal>` |
| `enacted` | none by time; retracted by `e_undo` / cascade invalidation |
| `derived` | composed — min of bodies' bounds; stale OR-composes |
| `imputed` | `:scope ap-attempt` — guard passes → `verified`, else discarded (+ an uncertainty annotation on the copy) |
| `verified` | `:fresh-for N` — re-run the guard |
| `intent` | `:scope episode` |
| `attested` | none declared — until withdrawn |
| `peer-asserted` | unverified until self-promoted |

Three bound *families*: **re-sensable** (`:fresh-for` — `exogenous`, `verified`, `derived` by
composition), **declared-authority** (`:scope` — `imputed`, `intent`), **none** (`static`, `enacted`,
`attested`, `peer-asserted` until promoted).

## Entry and promotion paths

- `imputed` → *deterministic guard passes* → `verified` — **the sole bridge out**
- `imputed` → *attempt ends, guard has not passed* → discarded
- `peer-asserted` → *consumer re-senses* → `exogenous`
- `peer-asserted` → *consumer runs a deterministic guard* → `verified`
- *(nothing)* → *a human, at escalation or through a wait-guard* → `intent` / `attested` (these enter
  as their own facts — they are not promotions of an `imputed` fact; a human vouching for model
  output is quality review, i.e. context, not a Kind transition)
- `verified` → *guard re-run fails, or cascade* → INVALIDATE
- `attested` → *human withdraws the vouch* → INVALIDATE

## Reserved and rejected

- **`assumed`** — *reserved.* The defeasible output of an explicit **non-monotonic default rule**
  ("assume `bird → flies` unless `penguin`"). The framework has no explicit default rules; for an
  LLM agent, what looks like assuming *is* the model imputing from training priors → `imputed`.
  Retraction machinery (INVALIDATE) is already present. Add `assumed` only if explicit default rules
  are introduced.
- **`peer-validated`** — *rejected.* Violates Promise Theory's consumer-verifies principle.
- **A model-confidence Kind** — *rejected: it is an annotation, not a Kind.* Model uncertainty
  (Dempster–Shafer belief/plausibility, logprob confidence) rides on an `imputed` fact as metadata on
  the copy; it never earns a truth-maker and therefore no Kind.
- **Channel-based names** (`sensed`, `reported`) — *rejected.* They reintroduce the transport axis.
- **`stochastic`** as a name for `imputed` — *rejected.* Off-axis (names the process, not the
  justification) and collides with the POMDP "probability distribution" sense.
- **`granted`** — *relocated, not rejected.* The human's authority belongs to the Identity axis
  (`:expires-at`, `approved`, `tokenGranted`, SPIFFE output); it is out of scope for the Belief State
  Kinds.

## Provenance

- **Canonical term-sheet:** `thompsonson/atomicguard` → `docs/design/notes/kind_taxonomy.md`
  ([PR #383](https://github.com/thompsonson/atomicguard/pull/383)) — the 10-Kind set, source-fidelity
  review, and decision log. This document is its belief-state scoping.
- **Published origin:** [IA 13](https://matt.thompson.gr/2026/08/13/ia-series-n-ontologies-doctrine.html)
  (2026-08-13) — the four original Kinds and the justification axis. `controllable` → `enacted` here
  is a refinement, carried with the permanent parenthetical; the published post is the origin, not an
  error to be corrected.
- **IA 14 draft** (`feat/ia-series-drafts`) — the reserved fifth Kind, resolved as `imputed`.
- **Reconciliations** — `dev`#124 (`attested` split; internally inconsistent §6/§5.2), OQ-001
  (`verified`), AtomicGuard D3 (reading (a)); full detail in the canonical term-sheet §6.
- **Frozen evidence:** verbatim captures in `atomicguard` → `docs/design/notes/sources/`.

## Decision log

- **§0 scope — DECIDED (2026-08-31):** broad for the full set — 10 Kinds, everything the agent
  holds.
- **D3 reading — DECIDED (2026-08-31), reading (a):** generator output enters the belief state as
  `imputed`, quarantined by policy (`:scope ap-attempt`, no precondition, no downstream), carrying an
  uncertainty annotation (DST Bel/Pl, logprob) as metadata — not a truth-maker. The guard is the lone
  bridge out; else discarded.
- **Belief-state split — DECIDED (2026-08-31, this document):** Belief State Kinds = the **9**;
  `granted` moves to the Identity axis (`identity.md`). Carrying it in the justification axis fused
  Identity and Belief State.
- **Names:** `enacted` with permanent `(IA 13: controllable)` parenthetical; `imputed` kept over
  `stochastic`; `verified` (was `guard-validated`) over the RV gap; `intent` net-new.

## External references

- Thompson, M. *The Dual-State Architecture for Reliable LLM Agents.* [arXiv:2512.20660](https://arxiv.org/abs/2512.20660) — guard functions as sensing actions; the foundational reference for `verified`.
- Chitnis, R. & Lozano-Pérez, T. *Learning Compact Models for Planning with Exogenous Processes.* [arXiv:1909.13870](https://arxiv.org/abs/1909.13870) — `exogenous` state variables.
- Edelkamp, S. & Hoffmann, J. *PDDL2.2.* (2004) — `derived` predicates.
- Burgess, M. *In Search of Certainty.* O'Reilly, 2015 — Promise Theory; `peer-asserted` and the no-`peer-validated` rule.