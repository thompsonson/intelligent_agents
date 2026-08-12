Direct answer to your fork: **neither side alone is right — and the two repos you've been drawing from actually disagree with each other on this, which is worth knowing before you pick.**

## The disagreement, stated plainly

- **The `dev` repo's `environment-analysis.md`** treats ontology as *discovered inside* Environment Analysis: *"The loaded ontology... is what makes the environment structurally known... It is static (loaded at startup), which is why it is an environment property, not a PEAS row of its own."* Ontology there is a *property you assess* ("Structurally Known / Observationally Unknown"), not a step you complete first.
- **The atomicguard proposal you just had me review** puts Ontology at **Step 0, before PEAS**, precisely because its corpus survey found ontology work happening in every document anyway, just unnamed and "presupposed by Steps 1 and 3."

Both are right about something real, and the disagreement is worth preserving rather than papering over — because your own archive shows *both* patterns actually happened to you, at different times.

## What your own practice says, and it cuts against a clean answer

Your **"Ontology, ontology, ontology"** post (Aug 10) is the tell: workflow → MDP-property action → independent-action workflow → Schema.org THINGS → graph of believed states → "now I need an ontology!" That's ontology arrived at **last**, discovered retroactively through building, not authored first. Same shape in **IA10**: you built the goal-decomposition model, then discovered mid-build that you'd conflated two state spaces — the fix (S_workflow/S_env) was a vocabulary correction made *after* the Agent Function step, not before it. Your lived process has consistently been **spiral, not waterfall**: sketch something, hit a naming/structure gap, formalize the missing ontology piece, continue.

A Step 0 that has to *fully complete* before Step 1 starts would misrepresent how you actually work — and would read as false to anyone who's followed the archive this far.

## What I'd actually recommend

Keep both, reconciled by making Step 0 **iterative and re-enterable** rather than a one-time gate, and letting Step 2 keep the job of *scoring* it:

1. **Step 0 — Ontology / Vocabulary** *(new, living document, not a gate)*. A first pass happens before PEAS — you can't write "Environment: PRs, CI runs, merge gates" without already having decided those are the entities that matter, so *some* ontology commitment always precedes PEAS even when unstated (this is the atomicguard proposal's strongest point, and it's correct). But Step 0 stays open for revision every time a later step exposes a gap — explicitly marked as re-enterable, so "I discovered I need an ontology" after Step 3 (your actual Aug 10 experience) is a normal, expected loop-back, not a process violation.
   - Worth splitting into two files, following the precedent `intelligent_agents`' infra-discovery track already set (their own D-006): **schema** (types/predicates/D3-kind structure) and **ubiquitous language** (naming, shared vocabulary — the DDD-flavored half I flagged in the PR review). They're different failure modes: a schema gap is "I'm missing a predicate," a vocabulary gap is "two docs use the same word for different things."
   - One caution to build in from the PR review: name explicitly that this is the *data* ontology (what the agent reasons about), not the *definitional* ontology (how the agent loop itself is defined) — the `dev` repo's still-open v1/v2/v3 question. Conflating the two here would be the exact cross-repo misreading that prompted the atomicguard proposal in the first place.

2. **Step 1 — Environment Specification (PEAS)** — unchanged in shape, but now its Environment/Sensors/Actuators rows should *cite* Step 0's named predicates/types rather than restate them in fresh prose. That's a real tightening: PEAS becomes checkable against the ontology instead of free text that might drift from it.

3. **Step 2 — Environment Analysis (properties)** — unchanged, but this is explicitly where ontology's *adequacy* gets scored, keeping the `dev` repo's insight intact: "Structurally Known / Observationally Unknown" is the property that asks "is Step 0 actually complete relative to what Step 1 needs?" If the answer's no, that's the loop-back trigger to Step 0, named as such rather than silently patched.

4. **Step 3 — Agent Function** — unchanged, but persistent-state variables should be classified against Step 0's D3 kinds (controllable/exogenous/static/derived) as part of writing the function — this is the exercise I suggested a few turns back for understanding the agent function through PDDL, now made a standing part of the process rather than a one-off exercise.

5. **Step 4 — Agent Type Selection** — adopt the atomicguard proposal's sharpened output: literature grounding against named alternatives + an explicit soundness argument, not a menu pick. Your own `algorithm_fit.md` pattern already does this in practice; worth stating as the expected bar.

6. **Step 5 — Agent Program** — unchanged.

Plus, optionally, the four registers (decisions/findings/open_questions/blue_sky) per design track — but I'd treat that as a **separate, heavier "engineering practice" tier**, not something that needs to bloat the Term Sheet post itself. The term sheet is a teaching artifact with real pedagogical value in staying lean (five clean steps is part of why it's citable); the registers matter more for atomicguard/dev-scale multi-document design tracks than for a blog post introducing the vocabulary.

**So, concretely for the Term Sheet update:** I'd add Step 0 as a named addition (six steps now), state explicitly that it's revisited rather than gate-completed, and leave the registers out of this post — those belong in a follow-up (maybe the natural "IA 12") about *process discipline at scale*, which would also be the natural place to work in the DDD/Bounded-Context framing and the "why did I only realize I needed this after building three things first" story, since that's a better, truer narrative than presenting Step 0 as something you'd have known to do from the start.
