---
title: "Kind taxonomy — what determines the truth of a held belief"
summary: "The IA-series Kind taxonomy — research reproduction of the canonical term-sheet. A Kind classifies a held belief by what justifies it. Nine Kinds across world, logic, model, human, and inter-agent justification — reconciling IA 13/14, the dev fleet, investigation-agents, and AtomicGuard D3 into one set. granted is not a Kind — it is a norm entry in the deontic state space D."
status: "research"
type: "term-sheet"
categories: "ia-series, ontology, belief-state"
---

# Kind taxonomy — what determines the truth of a held belief

*Research-series reproduction. A **Kind** classifies a belief by **what justifies the agent in
holding it** — the justification axis introduced in
[IA 13](../13-ontologies/blog.md). This appendix is the **research copy** of the Kind set;
the **canonical version lives in `thompsonson/atomicguard`** →
[`docs/design/notes/kind_taxonomy.md`](https://github.com/thompsonson/atomicguard/blob/docs/frontier-question/docs/design/notes/kind_taxonomy.md)
([PR #383](https://github.com/thompsonson/atomicguard/pull/383)) — bypassing this copy for
anything load-bearing or versioned. It reconciles four threads that developed the axis
separately — IA 13/14, `dev`#124, `investigation-agents` OQ-001, AtomicGuard D3 — into one
set. The DS-PDDL `:kind` enum in AtomicGuard encodes this set; the `dev` fleet consumes it
instead of re-deriving Kinds in `dev-agent-ontology.md` §6. This is the IA-series origin of
the thread; it is not a second canonical.*

**Status of every earlier item is decided.** §0 (scope) and §7.2 (the D3 reading) were decided
(broad; reading (a)) on 2026-08-31; §7.3, §7.4, §7.5, §7.6 are resolved in this term-sheet
(§7 — decision log); §7.7 (canonical home) was initially assigned to this document on
2026-08-31 and **reversed the same day** — the canonical home is `atomicguard`
(§7 item 7); this copy is the research-series reproduction.

## §0. Scope — everything the agent holds (9 Kinds)

**The Kind axis classifies everything the agent holds** — world-beliefs *and* its assigned goal —
not only facts about the world state W. Authority is **not** a Kind axis: norms (may / must /
must-not) are non-belief entries in the deontic state space **D**, sensed at `pre`, never held as
beliefs. The set is **9**: `static`, `exogenous`, `enacted`, `derived`, `imputed`, `verified`,
`intent`, `attested`, `peer-asserted`. `intent` and `attested` are *(held, not world)*.

> **Deontic split (2026-08-31 → 09-01).** `granted` is **not a Kind** — *"may do X"* is not a fact
> with a truth-maker, it is issued. A Kind classifies a belief whose content is a goal or a fact;
> a belief-of-a-norm never was a Kind. `granted` becomes an **entry in the deontic state space
> `D`** — a permission/deny record with provenance (issuer, scope, granted-at, expires-at) — read
> at the `pre`-gate by a transient live sense, never cached as a belief atom. A *fact about* `D`
> ("the store said permitted at T") is **`exogenous`**, evidential-only, never itself authorizing.
> Tense is the discriminator: *"was permitted at T"* (fact) vs *"may do X"* (norm). `intent`
> **stays** — the held goal is a belief; the *obligation* to pursue it is the norm in `D`.
> Design: [`deontic-state-space.md`](deontic-state-space.md); scoped treatment:
> [`belief-state-kinds.md`](belief-state-kinds.md). **The comprehensive set == the belief-state
> set == the same 9.**

Two points carry from the decision record:

- **The goal and the vouched fact are not one family.** `intent` is the held goal (Ψ, constitutive,
  `:scope episode`, changed only by `RECEIVE`, never by staleness); `attested` is a human vouching
  a *world* fact. `granted` is not among the Kinds — it is a norm entry in D.
- **A platform-sensed approval is an `exogenous` fact about the authority channel — not an
  authorization Kind.** The norm (the permission) lives in D; the sensed observation is
  evidential-only and never authorizes (the deontic-sense protocol property: a stored deontic atom
  can never satisfy a precondition; only the live pre-gate does). See `deontic-state-space.md`.

## §1. The axis

- A Kind answers **"what justifies the agent in holding this belief?"** — its justification
  structure (IA 13: *"Kind is the justification — what entitles the agent to hold it."*).
  Every Kind names a *positive* justification, from strong (the world; entailment) to weak
  (a model's trained prior — `imputed`). None is "an absence"; a weak justification is still
  a justification, and the policy quarantine on `imputed` (§2 — no precondition, no downstream,
  guard-only exit) follows from *how weak* it is, not from there being none.
- It is **not** *how the belief arrived* (sensed vs. reported — the channel/transport axis,
  kept off this axis deliberately; see the [stochastic-reasoning-kind
  draft](https://github.com/thompsonson/intelligent_agents/blob/feat/ia-series-drafts/documentation/ia-series/14-managing-belief-state/drafts/stochastic-reasoning-kind.md)).
- It is **not** *how current the copy is* — that is the freshness axis. Justification and
  freshness are orthogonal: one names who makes the fact true, the other declares when to
  re-sense or re-check. (Freshness is declared metadata on the epistemic copy,
  `:fresh-for` / `:stale-on`, never an atom — the IA 14 result.)
- Two sub-questions organise the set: **(a) what justifies holding it?** and **(b) can the
  agent re-check it, and how is its lifetime bounded?**

## §2. The Kinds

| Kind | Justification — what entitles holding it | Re-check / bound | Canon |
|---|---|---|---|
| `static` | designer stipulation, at setup | none — immutable | PDDL static predicates |
| `exogenous` | the world, as sensed | re-sense; `:fresh-for` | Chitnis & Lozano-Pérez 2019; IA 13 |
| `enacted` *(IA 13: `controllable`)* | the agent's own action, at a time | held; provenance carries `enactedAt`; retracted by `e_undo` / cascade | IA 13 |
| `derived` | monotonic entailment over other atoms | recompute; inherits min of bodies' bounds | PDDL 2.2; Datalog IDB; situation calculus |
| `imputed` | the model's **trained prior** — a statistical, inductive justification (weakest on the axis); carries an uncertainty annotation (DST Bel/Pl, logprob) as metadata | `:scope ap-attempt` — quarantined; guard passes → `verified`, else discarded | statistics ("imputed value"); the stochastic-parrot / Stochastic Illusion thread |
| `verified` | a deterministic guard checking a claim against the world | re-run the guard; `:fresh-for` | Thompson, *Dual-State Architecture* ([arXiv:2512.20660](https://arxiv.org/abs/2512.20660)); `investigation-agents` OQ-001 option (c); the [RV] gap |
| `intent` *(held, not world)* | the human's expressed **will** — the assigned goal | `:scope episode` | **net-new** — motivated by `dev`-fleet §2 TORPID language, not sourced as a Kind |
| `attested` *(held, not world)* | the human's **epistemic vouching** — a state of affairs asserted on the human's authority | none declared — holds until withdrawn | this synthesis (split from `dev`#124's broadened `attested`) |
| `peer-asserted` | another agent's claim | unverified until the consumer self-promotes it | Promise Theory (Burgess) — a promise is not a guarantee |

*Note — `granted` was the tenth row until 2026-09-01. It is now a norm entry in the deontic
state space `D`, not a Kind (`§0`); a *fact about* D is `exogenous`. See
[`deontic-state-space.md`](deontic-state-space.md).*

### World & logic — the IA 13 four, refined

**`static`** — true at setup, never changed by any action or sensing. Justified by: designer
stipulation. Example: `domain(x)`. Kept as-is: PDDL canon, nothing gained by renaming.

**`exogenous`** — a fact whose dynamics are independent of the agent's actions; its truth is set
by the world at the moment of sensing, and it can drift the moment the world moves. Example:
`node(id)`, `ci-run(c)`, `host(h)`. The truth-maker is the world; *sensing* is the channel and
stays off this axis.

**`enacted`** *(IA 13: `controllable`)* — a fact the agent **made true by its own action, at a
specific point in time**. Renamed from `controllable` for the temporal sense: `controllable` is a
standing capability (atemporal), `enacted` is an act with a `when`, which is exactly the
provenance/freshness-metadata question. The temporal distinction is worth keeping; the
parenthetical carries the published IA 13 name permanently (§7.3). IA 13 test: the effector's
successful return entails the fact. Example: `occupies(agent, wt)`, `visited(node)`.

**`derived`** — **monotonic** entailment over other atoms; computed by the state model, never
asserted. Freshness composes: a derived head's bound is the minimum of its bodies'; stale signals
OR-compose. Example: `reachable(a,b)`, `is-leaf(n)`, and `MergeGate`
(`approval ∧ checks_green ∧ zero_unreplied ∧ no_stale_failure`). A *defeasible* default-rule
conclusion would **not** be `derived` — see `assumed` in §3.

### Model-supplied

**`imputed`** — a value a model supplied **from its trained prior**: a statistical, inductive
justification — the weakest on the axis. Enough to hold the value as a *proposal*; never enough
to depend on it. The honest home for the "stochastic parrot": generator output, the model's
`"FINAL:"` / self-assessed "merge-ready" *before any guard*.

- Re-check: none. Re-running the generator produces a *different* value, not a refresh.
- **Quarantined by policy.** An `imputed` fact MAY NOT satisfy a precondition or feed any
  downstream logic. Its bound is `:scope ap-attempt` — it exists only within one action-pair
  attempt. **The guard is the sole bridge out:** `imputed` → a deterministic guard passes →
  `verified`; otherwise it is discarded within the attempt. (A *policy* quarantine on a
  justification-bearing Kind — not an "absence", not carceral — see §1.)
- **Uncertainty annotation.** An `imputed` fact carries an uncertainty annotation —
  Dempster–Shafer belief/plausibility mass, or logprob confidence — as **metadata on the copy,
  not a truth-maker**. It quantifies *how weak* the trained-prior justification is without
  turning it into a truth-determinant. This is AtomicGuard D3's "don't overclaim
  truth-determination" concern, and DST Bel/Pl is where that concern originated.
- Name: from statistics — an *imputed value* is a model-filled stand-in for missing data, flagged
  as not-observed. Chosen over `stochastic` because the axis names the *justification* (the
  trained prior, quantified as uncertainty), not *how the value was produced* (a stochastic
  process — the channel axis). Glossed in prose as "where the stochastic parrot lives."
- **On AtomicGuard D3** (*"the generator channel stays out of the predicate-Kind system"*) —
  **reading (a):** D3 means "the generator channel stays out of the *load-bearing* system," not
  "out of the belief state." Generator output enters the belief state as `imputed`; the
  `:scope ap-attempt` bound plus the no-precondition / no-downstream constraint guarantee it never
  reaches a load-bearing path. The guard remains the sole bridge to a fact anything may depend on.

### Guard-earned

**`verified`** — a fact a **deterministic, I/O-free guard** has checked against captured world
output (test results, exit codes, a diff, a sensed artifact). Formally: the output of `a_guard`
(base AP) or `a_guard_eff` (extended AP) passing.

- Foundational reference: Thompson, M., *The Dual-State Architecture for Reliable LLM Agents*
  ([arXiv:2512.20660](https://arxiv.org/abs/2512.20660), Dec 2025 / rev. Mar 2026) — *"Guard
  functions act as sensing actions that project opaque LLM outputs onto observable workflow
  state, enabling a dual-state decomposition."* `verified` is the Kind of a fact once that
  projection has occurred: a stochastic output (`imputed`) checked by a deterministic guard
  against a postcondition becomes an observable, re-checkable fact.
- Re-check: re-run the guard. `:fresh-for` applies.
- **Requires a deterministic guard that checks a claim against the world.** A guard that calls an
  LLM-judge is not deterministic — its output is `imputed`, not `verified`. A guard that *waits
  for a human* (vouch / assign / confirm) is a legitimate guard but not a world-check — by what it
  waits for it yields a norm in **D** (no Kind), `attested`, or `intent`, never `verified` (see
  the Human section's wait-guard note).
- Distinct from `derived`: there is an *operation against the world*, not an entailment, and a `⊥`
  verdict that is not a logical contradiction.
- Distinct from `enacted`: the agent *proposed* the claim; the guard *earned* it against the
  world. The generator's successful return does **not** entail "the tests pass."
- This is `investigation-agents` OQ-001 option (c): the response-validation gap made a Kind.
  `MergeGate` stays `derived` (a boolean composition); the individual checks feeding it are
  `verified`.
- Earlier name in the frontier note: `guard-validated`; shortened to `verified` for the enum.
  The mechanism is in the definition.

### Human — two faces *(held, not world)*

Will and knowledge — grouped only because the truth-maker is a human in each case, otherwise
distinct: `intent` is the held goal; `attested` is the vouched world fact (§0). Each can enter the
belief state two ways: **by escalation** (the DSA raises to a human, who supplies it as context on
the way back), or **through a wait-guard** — a guard whose `check()` is *"has the human vouched /
assigned / confirmed X?"* and which passes once that fact exists. The second is a legitimate
pattern, not the human-review anti-pattern (see `attested`): a wait-guard gates on a **scoped
authority yes/no**, not on a subjective judgement of an artifact's quality.

A wait-guard does **not** produce a `verified` fact — it is a synchronisation point, not a
deterministic world-check. It **splits by what it waits for**: a *norm* ("may I?") waits on the
deontic state space **D** and yields **no Kind**; a *fact-vouch* yields `attested`; a *goal
assignment* yields `intent`. The human, not the guard, is the justification.

**`intent`** — the human's **assigned goal**, held by the agent and reasoned from. Comes *from* Ψ.
The agent never invents it. Bound: the episode; a re-issued goal is a new episode.

**Net-new to this synthesis** — no source capture defines an `intent` Kind. It is *motivated* by
TORPID's "form intentions from the given goal" (`dev`-fleet §2), which is deliberation-loop
language, not a predicate Kind. Included because §0 (broad) puts the held goal in scope and its
truth-maker (the human's will) is distinct from the other nine.

**`granted` — moved out of the Kind set (2026-09-01).** A human authorises *what the agent may
do*: it is a **norm entry in the deontic state space `D`** (permission/deny, with provenance:
issuer, scope, granted-at, expires-at), read at the `pre`-gate by a transient live sense, never
cached as a belief atom. The authorization layer owns `D`. What *can* enter the belief state is a
**fact about** `D` — the observed `approved(request)` / `tokenGranted(agent, token)` are
**`exogenous` senses of the authority channel**. See §0 and §7.8, and
[`deontic-state-space.md`](deontic-state-space.md). This resolves `dev`#124's long-standing
inconsistency the other way from the intermediate reading: §6's "broadened attested" was wrong to
make it a belief, and §5.2's `controllable` was half right — the authorization is not a Belief
Kind; the observed `approved` / `tokenGranted` is an `exogenous` fact about the authority store.

**`attested`** — a human asserts **a state of affairs**, on their own epistemic authority: signs
off a release, vouches "this output is correct." Trust-based; holds until withdrawn.

- **Distinguish two things a human can do.** *Reviewing an artifact for quality* ("is this patch
  good?") is escalation — it yields *context*, not a verdict, and a guard built to block the loop
  on that subjective judgement is the anti-pattern. *Vouching for a scoped fact* ("the release is
  signed off", "the customer approved") is a binary authority determination — and a guard **may**
  legitimately block until it exists (wait-guard above). `attested` is the Kind of the fact in the
  second case; the first case produces no `attested` fact, only context.
- **Not** the SPIFFE sense of "attestation." SPIFFE workload attestation is an
  *identity-enrollment mechanism* — the SPIRE agent proves properties about a workload so the
  server issues it a credential; the output ("this workload may hold identity X") is a
  **permission — a `D` norm entry** (§7.8) — not a human vouching for a state of affairs. Same
  word, disjoint concept.

### Inter-agent

**`peer-asserted`** — a fact **another agent claimed**. The consuming agent must verify it itself
— re-sense, or run a guard — to promote it; a promoted fact then takes the Kind of *how the
consumer verified it* (`exogenous` or `verified`). It is **never auto-promoted by trust**. There
is deliberately **no `peer-validated`**: a peer's guard verdict is still only `peer-asserted` to
the consumer, because trusting the peer's execution is itself an assessment the consumer makes,
and Promise Theory rules out the silent inheritance of the peer's faults ("a promise is not a
guarantee"; the consumer bears responsibility for verification).

## §3. Reserved and rejected

- **`assumed`** — *reserved.* The defeasible output of a designer-authored **non-monotonic
  default rule** ("assume `bird → flies` unless `penguin`"). The framework has no explicit default
  rules; for an LLM agent, what looks like assuming *is* the model imputing from training priors →
  `imputed`. Doyle's reasoned-assumptions *machinery* (retraction) is already present as
  INVALIDATE. Add `assumed` only if explicit default rules are introduced.
- **`peer-validated`** — *rejected.* Violates Promise Theory's consumer-verifies principle.
- **A model-confidence / uncertainty Kind** — *rejected — it is an annotation, not a Kind.* Model
  uncertainty (Dempster–Shafer belief/plausibility, logprob confidence) rides on an `imputed` fact
  as **metadata on the copy** (see §2). It quantifies how weak the trained-prior justification is;
  it is never a truth-maker, so it earns no Kind and no separate layer.
- **`historical` / `event`** — *not needed.* A past-instant fact is `exogenous` with
  `:stale-on never`.
- **`stipulated` / `contractual`** — *not needed yet.* A negotiated cross-party agreement is
  closest to a **`D` norm entry** (declared authority/consent, `:expires-at`) rather than `static`
  (designer stipulation at setup); it is filed here as "not needed" only because renegotiation
  (`dev`'s D-004) is rare. If it becomes frequent, model it as an agreement entry in `D`, not a
  new Kind.
- **Channel-based names** (`sensed`, `reported`) — *rejected.* They reintroduce the transport axis
  IA 14 explicitly removed.
- **`stochastic`** as the name for `imputed` — *rejected.* Off-axis (names the process, not the
  justification) and collides with the POMDP "probability distribution" sense. Retained as the
  prose framing in `imputed`'s definition.

## §4. Lifecycle bounds by Kind

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
composition), **declared-authority** (`:scope` — `intent`, `imputed`), **none** (`static`,
`enacted`, `attested`, `peer-asserted` until promoted). (A permission's lifetime is a property of
its **`D` norm entry** — `:expires-at` in D, not a belief-state bound; see §0 and §7.8.)

## §5. Entry and promotion paths

Two guard shapes matter here: a **deterministic world-checker** (produces `verified`) and a
**human wait-guard**, which splits by what it waits for: a *norm* ("may I?") waits on the deontic
state space **D** and yields **no Kind**; a *fact-vouch* yields `attested`; a *goal assignment*
yields `intent`. The guard is a gate, not a validator.

- `imputed` → *deterministic guard passes* → `verified` — **the sole bridge out**
- `imputed` → *attempt ends, guard has not passed* → discarded
- `peer-asserted` → *consumer re-senses* → `exogenous`
- `peer-asserted` → *consumer runs a deterministic guard* → `verified`
- *(nothing)* → *a human vouches a world fact or assigns a goal, at escalation or through a
  wait-guard* → `attested` / `intent` (these enter as their own facts — they are **not**
  promotions of an `imputed` fact; a human vouching for model output is quality review, i.e.
  escalation/context, not a Kind transition)
- *(D)* → *agent senses `D` at the `pre`-gate* → optionally an `exogenous` atom "the store said
  permitted at T" (evidential-only; never authorizes)
- *(a permission in `D`)* → *past `:expires-at`, or the authority revokes* → the `D` entry is
  removed; the next `pre`-gate sense fails. **No belief-state INVALIDATE and no cascade** — a norm
  change cannot unmake an `enacted` fact.
- `verified` → *guard re-run fails, or cascade* → INVALIDATE
- `attested` → *human withdraws the vouch* → INVALIDATE

## §6. How this reconciles the four threads

| Thread | Its position | Resolution here |
|---|---|---|
| **IA 13** | four Kinds: `controllable`, `exogenous`, `static`, `derived` | kept, refined — `controllable` → `enacted`; the four are the "world & logic" group |
| **IA 14 / `stochastic-reasoning-kind` draft** | a fifth Kind `attested`/`self-attested` **reserved**, for the model's `"FINAL:"` | resolved: the model's output is `imputed` — a real, justification-bearing Kind (the trained prior, quantified as an uncertainty annotation), quarantined by policy; the guard passes it to `verified`, or it is discarded within the attempt |
| **`dev`#124** | §6 *narrative* promotes `attested` to live and broadens it to model reasoning **or** human approval/token — but §5.2's predicate table still says `controllable` for `approved`/`tokenGranted` (**internally inconsistent**) | reconcile against §6: `attested` (human fact-vouch) and `intent` (goal — net-new) are Kinds; the model case → `imputed`; the human **authority/token** case is a **norm**, not a Kind — it went to `granted` (2026-08-31) and then to a deontic-space **`D`** entry (2026-09-01, §7.8). The §5.2 `controllable` classification is noted, not adopted |
| **`investigation-agents` OQ-001** | guard-verified state: `derived` vs. agent-assessment vs. its own determination | option (c): its own Kind, `verified`. `MergeGate` stays `derived` (a composition); its inputs are `verified` |
| **AtomicGuard D3** | "the generator channel stays out of the predicate-Kind system" | **reading (a)** — D3 means "stays out of the *load-bearing* system," not "out of the belief state." Generator output enters as `imputed` (with an uncertainty annotation); the `:scope ap-attempt` bound + no-precondition/no-downstream constraint keep it off every load-bearing path; the guard is the sole bridge to `verified` |

## §7. Decision log

*All items decided; no open item remains.*

1. **§0 scoping — DECIDED (2026-08-31): broad, everything-held.** Originally 10 Kinds; **9 since
   2026-09-01** — `granted` moved to the deontic state space `D` (item 8). See §0.
2. **D3 reading — DECIDED (2026-08-31): reading (a).** D3 means "the generator channel stays out
   of the *load-bearing* system," not "out of the belief state." Generator output enters as
   `imputed`, quarantined by policy (`:scope ap-attempt`, no precondition, no downstream),
   carrying an uncertainty annotation (DST Bel/Pl, logprob) as metadata — not a truth-maker. The
   guard is the sole bridge out: `imputed` → guard passes → `verified`, or discarded within the
   attempt. See §2 `imputed`.
3. **`enacted` rename cost — DECIDED here: keep `enacted` with a permanent parenthetical.**
   IA 13 is published with `controllable`, so the cross-reference stays — but the temporal
   distinction (`controllable` = atemporal capability; `enacted` = an act with a `when`) is real
   provenance metadata and worth keeping. The `(IA 13: controllable)` parenthetical is carried in
   the term-sheet (§2) and in any DS-PDDL enum that ships `enacted`.
4. **`attested` vs SPIFFE — DECIDED: keep `attested`.** The apparent collision is superficial.
   SPIFFE "attestation" is an identity-enrollment / permission mechanism — its output is a
   **permission** (a `D` norm entry, §7.8), not a fact-vouch — so the concepts are disjoint and a
   SPIFFE-literate reader is not misled. See §2 `attested`.
5. **`imputed` name — DECIDED: keep `imputed`.** The §1 reframe settles it: the axis names
   *justification*, so `imputed` (the trained prior, quantified as an uncertainty annotation) is
   on-axis and `stochastic` (the process) is not. `stochastic` stays in the gloss.
6. **`peer-asserted` in scope now? — DECIDED here: in the concept set from the start.**
   Multi-agent belief-sharing (dev-fleet, investigation-agents) is real, and omitting the Kind
   would break the set's completeness (a peer claim must land somewhere). The *enum staging* is a
   port concern: the AtomicGuard DS-PDDL `:kind` enum may add it later when a peer channel is
   deployed; the concept layer includes it now.
7. **Canonical home — REVERSED (2026-08-31): `atomicguard`, not this repo.** Originally
   assigned here as an IA-series term-sheet; that was a mislabelling — this repo is the
   research origin, not a canonical source. The canonical term-sheet is `thompsonson/atomicguard`
   → `docs/design/notes/kind_taxonomy.md` ([PR #383](https://github.com/thompsonson/atomicguard/pull/383));
   AtomicGuard keeps the DS-PDDL `:kind` enum that encodes the set; the `dev` fleet consumes it
   instead of re-deriving Kinds in `dev-agent-ontology.md` §6. This document remains the
   research-series reproduction and points at the canonical.
8. **`granted` exits the Kind set — DECIDED (2026-09-01, via the deontic thread).** A permission is
   a **norm**, not a belief: *"may do X"* is not a fact with a truth-maker, it is issued. So
   `granted` is **not a Kind**. It becomes an entry in the **deontic state space `D`** — a
   permission/deny record with provenance (issuer, scope, granted-at, expires-at) — read at the
   `pre`-gate by a transient live sense and never cached as a belief atom. The authorization layer
   owns `D`. A *fact about* D ("the store said permitted at T") is `exogenous`, evidential-only,
   never itself authorizing. Tense is the discriminator: "was permitted at T" (fact) vs "may do X"
   (norm). `intent` **stays** — the held goal is a belief; the obligation to pursue it is the norm
   in `D`. **Consequences:** the set is 9; the DS-PDDL `:kind` enum drops to 9; `identity.md` §5
   reframes `granted` as a `D` norm entry. Design:
   [`deontic-state-space.md`](deontic-state-space.md) (PR #23).

**Addendum — source-fidelity review (2nd review of the atomicguard doc @ `07cec24`, fixed in
`77f3b05`, mirrored here) + deontic split (2026-09-01):** two provenance claims corrected — (a)
`dev`#124's `attested` broadening was not clean: its §6 prose broadens `attested` to human
approval/token, but its §5.2 predicate table still classifies `approved`/`tokenGranted` as
`controllable`; the **deontic split** resolves it — the authorization is a norm in **`D`**, the
observed `approved`/`tokenGranted` are **`exogenous` senses of the authority channel**, `attested`
stays for world-fact vouching — neither §6's broadened-belief nor §5.2's `controllable` stands;
(b) `intent` has **no verbatim anchor** — no source defines an `intent` Kind; it is **net-new**
synthesis, motivated by TORPID's "form intentions from the given goal"; its status as its own Kind
(not `exogenous`) is the decided fivefold (atomicguard, 2026-08-31). Minor: a negotiated
cross-party agreement is nearer a **`D` norm entry** than `static` (§3).

## §8. Sources

The synthesis was developed against verbatim captures frozen in
`thompsonson/atomicguard` → `docs/design/notes/sources/`:

- [`ia13-ontologies-doctrine__blog.md`](https://github.com/thompsonson/atomicguard/blob/main/docs/design/notes/sources/ia13-ontologies-doctrine__blog.md) — the four Kinds and the justification axis
- [`ia14-draft__stochastic-reasoning-kind.md`](https://github.com/thompsonson/atomicguard/blob/main/docs/design/notes/sources/ia14-draft__stochastic-reasoning-kind.md) — the reserved fifth Kind, now resolved as `imputed`
- [`dev124__dev-agent-ontology.md`](https://github.com/thompsonson/atomicguard/blob/main/docs/design/notes/sources/dev124__dev-agent-ontology.md) — §6 prose broadens `attested` (model or human approval/token); §5.2 table still says `controllable` for those — internally inconsistent; reconciled against §6
- [`invagents__open-questions.md`](https://github.com/thompsonson/atomicguard/blob/main/docs/design/notes/sources/invagents__open-questions.md) — OQ-001, resolved as `verified`
- [`invagents__schema.md`](https://github.com/thompsonson/atomicguard/blob/main/docs/design/notes/sources/invagents__schema.md) — `MergeGate`-as-`derived` framing

The synthesis record itself is `atomicguard` → `docs/design/notes/kind_taxonomy.md`
([PR #383](https://github.com/thompsonson/atomicguard/pull/383), commit `77f3b05`) — which is
also the **canonical term-sheet**, since updated to the **9-set** on 2026-09-01 via
[PR #390](https://github.com/thompsonson/atomicguard/pull/390) (`df08ead`, `granted` → deontic
space `D`, §7.8) — with the frontier record at
`docs/design/notes/frontier_question_guard_verified_kind.md`.

**External references:**

- Thompson, M. *The Dual-State Architecture for Reliable LLM Agents.* [arXiv:2512.20660](https://arxiv.org/abs/2512.20660) (Dec 2025 / rev. Mar 2026) — guard functions as sensing actions projecting opaque LLM outputs onto observable state; the foundational reference for `verified` (and the `imputed` → `verified` promotion).
- Chitnis, R. & Lozano-Pérez, T. *Learning Compact Models for Planning with Exogenous Processes.* [arXiv:1909.13870](https://arxiv.org/abs/1909.13870) (2019) — `exogenous` state variables.
- Edelkamp, S. & Hoffmann, J. *PDDL2.2.* (2004) — `derived` predicates.
- Burgess, M. *In Search of Certainty.* O'Reilly, 2015 — Promise Theory; `peer-asserted` and the no-`peer-validated` rule.