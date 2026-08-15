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
