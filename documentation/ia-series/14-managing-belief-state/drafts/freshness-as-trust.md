# Freshness as trust — provisional positioning

*Draft. Supporting note for IA 14. Not part of the series. Written after the Doyle/atomicguard review; provisional — may change as the belief-state work develops.*

## The reframing

Freshness is not "how fast a fluent changes" — that phrasing makes it a bare world fact. It is **trust**: the agent's declared stance that a *source* will give a correct value for this predicate, for some interval.

Two-sided:

- **The bound (doctrine)** — the agent's trust policy: *"I trust effector E's copy of `ci-green` for 5 min."* Agent-side; an epistemic stance, not an objective world property.
- **The metadata (`sensed_at`, `sensed_by`, verdict)** — the evidence the trust points to: when the copy was sensed, by which effector, with what verdict.

## Position relative to the belief state (at this point in time)

- Trust lives as **metadata on the epistemic copy** (agent ontology) — **never a world atom**. Unchanged from IA 14.
- What shifts: the **doctrine's Kind**. IA 14 currently says the bound is "a fact about the world (how fast a fluent changes) — static or derived — world content." Under the trust reading that is **not fully right**: the bound is the agent's trust judgment, informed by the world's behavior but not identical to it. It drifts toward **agent ontology**.

The sharp line moves:
- Before: *the world ontology declares the bound.*
- Now: *the agent declares its trust bound, informed by how the world behaves.*

## What the current IA 14 wording needs

The post's sentence framing the declared bound as world content should be revisited under this reading. Leave the post as-is until the positioning settles; this draft is the flag.

## Open items

- The doctrine's **Kind is left open** pending the developing Kind taxonomy: is a trust bound controllable (agent-declared), a new Kind, or something else? Not resolved here.
- Trust is relational — in *a source* for *a fact*. Whether the source dimension needs its own structure (a per-effector trust record) is deferred.
- Relation to **response validation (RV)**: the guard validates a response against the world; trust governs whether a *held copy* is still relied upon. Distinct, adjacent — the guard is where a justification's failure is detected, trust is how long a justification is treated as holding.

## Threads that feed this

- IA 14 — the freshness axis as declared doctrine + recorded metadata.
- Atomicguard `docs/design/notes/belief_state_freshness_axis.md` — `:fresh-for` / `:stale-on`; derived heads inherit min; stale OR-compose.
- Doyle AITR-581 §1.7.2.5 — reasoned deliberation over reasons vs scalar utility; a trust bound is a declared, revisable *reason*, not a scalar.
- Atomicguard `masters_project_plan.md:59` — the logprobs "confident and wrong" rejection: a scalar confidence with no external check is the failure mode; trust-as-declared-reason avoids collapsing to a scalar.
- `drafts/stochastic-reasoning-kind.md` — the reserved Kind; confidence as decision signal, never truth-maker.

## Promise Theory threads (for later)

Draft material for a later post, surfaced by the atomicguard review (via the Mark Burgess correspondence). Promise Theory gives two primitives that map one-to-one onto the freshness-axis machinery, plus a reframe worth digging into.

- **The reframe:** the belief state is the record of promises sensed and verified, not a model of the world. The consumer bears responsibility for verifying that a promise was fulfilled.
- **Primitives → axes:**
  - **promise / assessment** (observer-declared bound, `:fresh-for N`) — the world ontology's freshness doctrine;
  - **verification** (binary guard verdict) — the agent ontology's check.
- **Fixed-point formulation (the strongest link):** a belief is at its fixed point when re-sensing returns the same copy (verified); `:fresh-for N` is how far a copy may drift before re-sense; a failed re-sense leaves the belief fixed — INVALIDATE-not-changed. (Burgess fixed-point equations; CFEngine idempotence.)
- **The Burgess caveat (a decision for later):** Promise Theory uses *assessment* by observers, not *verification* — a promise is not a guarantee (Burgess 2015); promise-keeping is subjective and per-observer, verification is binary and objective. Open question for the doctrine: adopt the per-observer assessment framing (truer to PT, strengthens the world-ontology side) or keep the declared bound without the per-observer caveat (simpler)?
- **Coherence vs calibration:** coherent beliefs can be systematically wrong (De Finetti); coherence was solved, calibration never — the guard is the external check. Bears on the reserved stochastic-reasoning Kind: reported-channel beliefs can be coherent-but-wrong; no internal mechanism calibrates them.

**Notes in lestash:**
- [12688 — "Please also add promise theory"](https://pop-mini.monkey-ladon.ts.net:8444/api/items/12688) — own note; adding PT to the rational-agents definitions.
- [12689 — Promise Theory concepts (autonomous agents, voluntary cooperation)](https://pop-mini.monkey-ladon.ts.net:8444/api/items/12689) — the primitive set.
- [14267 — whether Burgess specifies promise/verification in different state spaces](https://pop-mini.monkey-ladon.ts.net:8444/api/items/14267) — he does not; the assessment-vs-verification caveat.
- [20852 — "trying to be faithful to Mark Burgess"; promises not guarantees](https://pop-mini.monkey-ladon.ts.net:8444/api/items/20852) — own note; the promise ≠ guarantee line.
- [24920 — Mark Burgess's LinkedIn post: PT "must be at the core of LLM-based..."](https://pop-mini.monkey-ladon.ts.net:8444/api/items/24920) — the direct Burgess exchange.

**Atomicguard files to dig into later** (atomicguard provided file paths, not note links): `docs/design/notes/mark_burgess_correspondence.md` (fixed-point equations; assessment-vs-verification; autonomy as causal independence), `docs/design/notes/system_characteristics.md` (Stability Invariant = fixed point), `docs/design/notes/dual_state_conversation_nov2025.md` (guard-as-sensing-action), `docs/theory/domain_definitions.md` (consumer bears responsibility for verification), `docs/masters_report.md` (R as observable state), `docs/theory/notation/human_guards_notation.md` (guard-is-promise).
