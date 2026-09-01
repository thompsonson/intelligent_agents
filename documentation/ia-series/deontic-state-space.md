---
title: "Deontic state space — norms are not beliefs"
summary: "Design draft (not canonical): the deontic complement of the Kind taxonomy as a fourth, sensed, environment-like space D. A Kind classifies a belief whose content is a goal or a fact; a belief-of-a-norm is never a Kind. Facts about D are exogenous senses; norms are non-belief entries in D; granted exits the Kinds by rule, not exception."
status: "design-draft"
type: "design"
categories: "ia-series, deontic, identity, belief-state"
---

# Deontic state space — norms are not beliefs

*Shared design draft, developed with the atomicguard session (2026-08-31). **Worded for validation —
a template / proposal, not an attestation.** It is the deontic complement of the Kind taxonomy: where
the Kind axis classifies justified held-beliefs, this note classifies *norms over action* and keeps
them strictly off the belief state.*

## The rule

A **Kind** classifies a belief whose content is a **goal or a fact**. A **belief-of-a-norm is never
a Kind** — and this is not special to `granted`. Every deontic modality splits into (a) a
Kind-bearing **fact** about an authority act or channel, and (b) a **norm entry** in the deontic
state space **D**:

| Modality | Fact (a belief) | Norm (in D) |
|---|---|---|
| Permission | `exogenous` — "the store indicated a grant for AP‑X at T" | permission entry |
| Obligation | `intent` — "the assigned task is G" (§2) | obligation entry |
| Prohibition | `exogenous` — "the store indicated a deny for AP‑X at T" | interdicted/deny entry |

`granted` does not exit as an exception — **the belief-of-a-norm never was a Kind.** It stays out by
**tense**: *"was permitted at T"* is a fact (a sense of D), *"may do X"* is a norm in D, never a
belief. **The comprehensive set == the belief-state set == 9 Kinds**: `static · exogenous · enacted ·
derived · imputed · verified · intent · attested · peer-asserted`.

## The fivefold (decided 2026-08-31, atomicguard)

The fourfold plus `intent`. The relocation of authority events keeps the model unambiguous; the goal
commitment is the fifth, structurally distinct line:

- **norms in force** → non-belief entries in **D** (may / must / must-not; scope; lifetime; revocation)
- **facts about D** → **`exogenous`** atoms ("the store said permitted / forbade / granted at T"),
  pulled at the pre-gate or pushed via interruption — a sensor interrupt is still sensing. Evidential
  only; freshness-bounded (`:stale-on`).
- **the agent's held goal commitment** → **`intent`** — justified by commissioning / Ψ (the goal
  channel, a component of the problem space `P = <Ψ, π, Γ>`); **`:scope episode`**; changed only by a
  `RECEIVE` (a new commissioning event), *never* by staleness. There is **no goal store to sense** —
  the goal is given once and held, not re-polled.
- **a human vouches a world state of affairs** → **`attested`** (reserved for world facts, not norm
  events)
- **the agent acted** → **`enacted`** ("AP ran at T, effects E")

**Why `intent` is `intent`, not `exogenous`** (atomicguard's reasoning, adopted): permission's fact-side
is `exogenous` because the agent literally senses the permission from D — "the store said permitted at
T" is the output of a sense operation against a register the authority owns. **The goal has no owning
register.** Absorbing `intent` into `exogenous` would be the same category error as leaving `granted`
in the beliefs, reversed — treating a *constitutive held commitment* as a *transient sensed
observation*. The asymmetry is correct: **permission and prohibition anchor on sensed events; obligation
anchors on the held `intent`** — permissions are external and sensed; the goal is constitutive and held.

The split keeps it parallel to everything else: the **norm** "must pursue G / must not halt" is the
obligation entry in D; the **fact** "the agent's assigned task is G" is the held belief `intent`.
And alongside the held `intent`, an audit atom may be kept — "the human assigned G at T" (sensed /
logged, exogenous-adjacent) — giving the goal its own three records: the *assignment event* (history) ·
the *held `intent`* (what preconditions read) · the *enacted* steps toward it.

## D as a fourth, sensed space

`S = S_workflow × S_env × W × D` (candidate `S_stochastic` rename — see Cascade). D has W's profile **on
the agent's side**: external (the human
owns it), **partially observable**, **non-monotonic** (a grant can vanish between checks). Two
asymmetries, stated so the model is not over-symmetrised:

- **authority mutates D; the agent only senses/receives it** (pull at `pre`, push via `RECEIVE`).
- The **named limitation**: a prohibition never sensed and never pushed can be violated — D's partial
  observability is real, exactly like the world's.

## Two-phase deontic sense

| Phase | What happens | Stored? |
|---|---|---|
| **(a) pre-gate** | a **transient** read of the **live** store → verdict (`{permitted?, obliged?, prohibited?}`), consumed at `pre` | **No** — transient-only is a *safety property*: a stored+reused pre-gate verdict is the cached-authorization hazard this model exists to avoid. May be logged to the execution DAG for observability, but never as a belief-state atom |
| **(b) result** | the observation that an action **was** allowed (or denied) at T → `exogenous` atom `allowed(agent, AP, at:=T)` | Yes — as a tense-locked, freshness-bounded `exogenous` fact. **Evidential only** |

Boundary discipline (atomicguard): the deontic **SENSE populates the inputs** the pre-predicate reads;
`pre` itself is predicate evaluation, not sensing. Sensing D is **I/O** (registry / policy service / OS
capability) — it crosses the sensor/effector boundary; any **check** of the read (token signature,
issuer recognised) is a **guard over captured output**. Purity intact; shape = sense → pre-guard → …

## Protocol property — stronger than staleness

> **A stored deontic atom never authorizes.** A *fresh world-sense* can satisfy a precondition; even a
> *fresh stored deontic atom* never can — only the **live pre-gate** does.

This is a deliberate, **non-authorizing** constraint; it kills the revoke-race (no cached
"allowed@now−5ms" slips through after a revoke at now−2ms). Representation = `exogenous`; the
re-sense-always property is a protocol rule. Whether it additionally earns its own `:kind` note or
stays a documented gate property is **atomicguard's enum call** — lean: **document on the protocol,
do not mint a Kind**, unless the type system is specifically wanted to *enforce* non-authorization
(optionally a provenance flag `sensed-from-D` on the atom).

## Three-records audit

There are two append-only records per authorization-relevant action (the "three-records" discipline
with `attested` for human world-vouches):

| Record | Justification | Answers |
|---|---|---|
| `enacted` — "AP_k ran at T, effects E" | the agent's own action | **did the agent act?** |
| `exogenous` — "the store said permitted for AP_k at T" | sensed from D | **was the agent authorized when it acted?** |
| `attested` — "a human vouched world-fact φ" | a human's epistemic authority | **did a human vouch a world state?** |

Keeping only the `enacted` audit forces inferring authorization from "the gate did not block" —
weaker, and it loses the grant's provenance at that moment (issuer, scope, expiry). **Pragmatic
scope:** keep the phase-(b) atom only where an authorization audit matters — irreversible actions,
effector APs that mutate W, escalation-relevant steps. Read-only APs discard the transient verdict.

## Revocation and the wait-guard — on D, not beliefs

- **Revocation mutates D only.** There is no cached `granted` predicate to `INVALIDATE`, and no belief
  cascade: *a norm change cannot unmake an enacted fact* (you did deploy; still true). Authority acts
  accrue as monotonic `exogenous` history ("granted at T", "revoked at T2" — both senses of D); D
  reflects "not currently permitted." Consistent with the DSA rule that the world cannot invalidate
  workflow state — a norm change cannot invalidate a fact.
- **Wait-guard splits by what it waits for:** norm (*"may I?"*) → blocks on **D** until the entry is
  in force; yields **no Kind**. Fact-vouch (*"is this right?"*) → yields **`attested`**. Goal
  assignment → yields **`intent`** (§2 — the held goal commitment).

## Worked pre-gate walk-through

**Scenario.** AP‑17 is an effector that deploys the artifact. Its `pre` requires `permitted?(AP-17)`.
The authority owns D; a change window grants the agent permission for AP-17 until 23:00.

1. **Sense.** The deontic SENSE reads the live store: `permitted(true) · obliged(false) · prohibited(false)`,
   scope `deploy · until 23:00`, token signed by the commissioning authority.
2. **Guard-check the read.** A pure guard verifies the token signature + issuer of the *captured sense*
   (the stored deontic atom's provenance), not the permission itself. Verdict `⊤`.
3. **`pre` evaluates.** `permitted?(AP-17) ⊤`, other preconditions satisfied → the gate opens. The
   verdict is consumed; it is not stored, not readable back as a belief.
4. **Run.** AP-17 executes; effects recorded as `enacted("AP-17 ran at T", effects)`.
5. **Store the result observation.** `exogenous: allowed(agent, AP-17, at:=T)` — tense-locked,
   evidential-only, `:stale-on` (the store may change at any moment). It is **never** an input to a
   future gate.
6. **23:05 — a revocation lands** (a second store event; pushed or sensed at the next gate). D now
   shows `permitted(false)`. The `exogenous` history gains "revoked at T2"; `allowed(agent, AP-17,
   at:=T)` remains true of T and authorizes nothing. A next run of AP-17 senses `prohibited`/not
   permitted → its `pre` closes. **No belief was invalidated; only D changed.**
7. **Read-only branch.** If AP‑17 had been a read-only planner step, phase (b) is skipped; the
   transient verdict is discarded (and optionally logged to the execution DAG for observability).

This validates the model against the DSA machinery: the sense is a sensor read, the check is a pure
guard over captured output, `pre` evaluates sensed inputs, and the belief state never contains the
norm.

## Cascade (listed, not performed in this pass)

- `kind_taxonomy.md`: §0 broad set 10 → **9**; `granted` row moves to the authorization layer.
- `identity.md`: `granted` as a Kind → norm entry in D (permission/deny provenance schema: issuer,
  scope, granted-at, expires-at).
- dev-fleet ontology §5.2: `approved` / `tokenGranted` → `exogenous` senses of the authority channel
  (dissolves the §6/§5.2 inconsistency — §5.2's "not a *belief* Kind" instinct was half right).
- DS-PDDL `:kind` enum → the 9; the authorization layer owns D.
- **Notation sweep (proposed by atomicguard, executed separately):** rename DSA's `S_env` →
  `S_stochastic` (reframing the dual as deterministic vs stochastic) — target
  `S = S_workflow × S_stochastic × W × D`. Not part of this design's activation; listed for the sweep.

## References

Driven by (see `deontic-axis-scratchpad.md`, branch `docs/deontic-axis-scratchpad`, and the atomicguard
position note `deontic_axis_sep2026.md`): SEP *Deontic Logic* (McNamara & Van De Putte, 2021);
SEP *Rights* / Hohfeld (Wenar 2025; Hohfeld 1913/1919); Bratman, *Intention, Plans, and Practical
Reason* (1987); von Wright (1951); Hart (1961); Chisholm (1963); Andrighetto, Governatori, Noriega &
van der Torre (eds.), *Normative Multi-Agent Systems*, Dagstuhl Follow-Ups Vol. 4 (2013); RFC 8693;
Thompson, *The Dual-State Architecture* (arXiv:2512.20660); `thompsonson/atomicguard` →
`identity.md` / `kind_taxonomy.md`; `thompsonson/dev` register Q30.