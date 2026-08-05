# Algorithm Fit: Infra Discovery (Step 4)

**Retrofit note:** the "`CLEARED`'s cycle-safety" finding and the "Open, not
resolved" section from the original `algorithm_fit.md`
(`documentation/infra-discovery/`) have been extracted into
[`findings.md`](findings.md) and [`open_questions.md`](open_questions.md)
respectively - pointers left in place below. Everything else is unchanged;
this step's content was already correctly filed as `algorithm_fit.md`
before the retrofit (Step 4 was already 1:1 in the original structure).

## Purpose

`step2_environment_analysis.md` settled the shape: compound `(domain, kind, id)`
identity, catalogue-driven `legal_actions`, multi-facet accumulating
`state`, bidirectional edge discovery, a persistent `belief_state` external
to any one run. This document asks the question `atomicguard-bridge/algorithm_fit.md`
could answer cheaply (yes, unmodified, proven by a passing test) and this
one can't: does any traversal algorithm already in this repo fit this
environment at all? No proof is possible yet - there's no reference
implementation to hand-trace against, unlike every prior `algorithm_fit.md`
in this repo. What follows is the argument for what family fits and what's
still genuinely open, not a completed derivation.

## Why `DiscoveryAgent`'s DFS-with-retrace does not transfer here - argued directly, not assumed

`atomicguard`'s own revision document already settled this for the smaller
`atomicguard-bridge/` case, and the reasoning applies here even more
directly: *"`discovery/`'s LIFO parent stack exists solely because its
agent can only sense the node it's standing on and has to physically
retrace steps to reach an unexplored branch. `INVOKE(dsa, subject)` has no
such constraint."* `atomicguard-bridge/`'s environment kept the constraint
anyway, deliberately, as a "small step" - `StatefulDiscoveryEnvironment`
still has no notion of "current position," but `DiscoveryAgent.walk()`
imposes one on top of it (`current`, a parent stack) because that's the
algorithm being tested, not because the environment demands it.

This environment can't inherit that choice, for two independent reasons:

1. **No adjacency at all.** A `(domain, kind, id)` triple isn't "reached" by
   moving through anything - `INVOKE(dsa, subject)` is invoked directly the
   instant `subject` is known, regardless of what was invoked immediately
   before it, possibly in a completely different domain. There's no sense
   in which "backtracking" to a previous subject means anything.
2. **`backtracking-exploration/algorithm_fit.md`'s own bound doesn't apply,
   for a reason beyond the adjacency-cost point already made in
   `atomicguard-bridge/`.** That bound (`2×|E|`, full exploration
   guaranteed) assumes a *finite, fixed* graph worth fully exploring. This
   environment's properties table says otherwise on both counts: `Discrete`
   is "unbounded at the instance level," and "full exploration" isn't even
   the right goal - `Ψ` scopes the search (matching the source ontology
   document's own reason frontier-based exploration doesn't fit either:
   *"our intention Ψ is given and scopes the search; we're not building a
   complete map for its own sake"*). There's no fixed, finite thing to
   prove bounded-and-complete exploration over the way `discovery/`'s toy
   has.

## What the source document already grounds this in, checked directly rather than re-derived

`topology_sensing_dsa_belief_state_and_agent_function.md`'s own "Grounding
in robot/AI search literature" section did this literature survey already -
restated here because it's the actual answer, not because it needs
re-deriving:

- **D\* Lite** - assumes a *known, fixed vertex set*, only edge
  traversability unknown. Doesn't fit: new nodes (Pods, workflow runs) can
  exist that weren't known in advance, at all.
- **LRTA\*** - *no map at all*. Senses only locally, bounded lookahead via a
  heuristic, updates the heuristic at the state it's leaving, moves,
  repeats. **This is the fit**, per the source document's own reasoning:
  what's known ahead of time is the local action vocabulary per type
  (`DSA-CATALOGUE`), not the graph shape - exactly LRTA\*'s "know what's
  available from here, not what the whole graph looks like."
- **Frontier-based exploration** - map-building is the objective itself.
  Doesn't fit: `Ψ` scopes and terminates the search; there's no reason to
  keep exploring past what `Ψ` needs.

Concretely, the candidate algorithm isn't a variant of `DiscoveryAgent.walk()`
at all - it's the source document's own `AGENT-FUNCTION` pseudocode (Step
3; see [`step3_agent_function.md`](step3_agent_function.md) for this track's own
translation): a `pending` pool of `⟨dsa, subject⟩` pairs,
`SELECT-NEXT(pending, belief_state) = argmax SCORE(...)`, no position, no
backtracking, no phases. `discovery/`'s three PRs validated the *readiness*
half of a relative (the `requires`/`CLEARED` mechanism, per
`atomicguard-bridge`'s own revision-document review); they never validated
`SELECT-NEXT` itself, and neither does anything built in this repo so far.

## The soundness question this environment inherits, not one it raises new

`atomicguard`'s revision document's own "Exploration completeness is
genuinely open" section already states the actual open problem, and it
applies to this environment exactly as written there, not as a new finding:
whether plain `argmax SCORE` over `eligible` is sound at all depends
entirely on whether `IN-SCOPE(subject, Ψ)` can be proven to bound the total
reachable-and-relevant set.

- **If bounded** - a real `max_depth`/`max_width` ceiling on `Ψ` - the
  eligible-and-in-scope portion of `pending` is finite, and greedy
  `argmax`, run to exhaustion, eventually invokes everything in it.
  Structurally the same shape as `discovery/`'s own bounded-by-node-count
  termination argument, generalized to "bounded by `IN-SCOPE`'s limit"
  instead of "bounded by the literal graph."
- **If not bounded** - greedy `SELECT-NEXT` isn't sound; something with a
  fairness guarantee is needed (aging scores, round-robin, or an explicit
  exhaust-`pending`-before-considering-new-arrivals discipline -
  structurally a revival of `discovery/`'s own phase structure, for
  scheduling fairness rather than the adjacency reason that structure
  existed for originally).

Not resolved here, same as it isn't resolved in the document it's inherited
from (see [`open_questions.md`](open_questions.md)). Worth flagging
precisely why this environment can't dodge it the way `atomicguard-bridge/`
implicitly did: `atomicguard-bridge/`'s `pipeline_fanout_lite` is six nodes,
trivially bounded by construction, so `IN-SCOPE`-style boundedness was never
actually tested by anything built so far. This environment's own properties
table says `Discrete: ... genuinely unbounded at the instance level` - the
untested case is the default case here, not an edge case.

## Related documents

- [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md) - the canonical definition of every term used above (Step 0).
- [`step2_environment_analysis.md`](step2_environment_analysis.md) - Step 2; the node/edge shape and environment properties this fit argument is checked against.
- [`step3_agent_function.md`](step3_agent_function.md) - Step 3; the pseudocode this document reasons about, stated in full.
- [`step0_schema.md`](step0_schema.md) - the field-level reference for `belief_state`'s own operations (`RECORD`, `RECORD-EDGE`, `cleared`) this document's `SWEEP-CLEARED` discussion assumes.
- [`worked_examples.md`](worked_examples.md) - `WE-003`'s `ReplicaSet`/`Pod` case works through exactly the `BRIDGE-CATALOGUE`/`RELEVANT` gap named in `open_questions.md`, concretely.
- [`step5_agent_program.md`](step5_agent_program.md) - Step 5; why this document's own "no adjacency, no reused loop" finding means Step 1 (of the build sequence, not this process's Step 1) has to be built from scratch.
- [`findings.md`](findings.md) - the `CLEARED` cycle-safety finding, extracted from this document.
- [`open_questions.md`](open_questions.md) - the "Open, not resolved" section, extracted from this document.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` - the LRTA*/D*-Lite/frontier-exploration literature survey, the `AGENT-FUNCTION` pseudocode, and the full cost-feature enumeration this document defers to rather than repeats.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - `IN-SCOPE`/`SELECT-NEXT` soundness, and the `CLEARED` recursion the cycle-safety finding was found in.
- [`../discovery/backtracking-exploration/algorithm_fit.md`](../discovery/backtracking-exploration/algorithm_fit.md) - the DFS-with-retrace bound this document argues does not transfer, and why.
- [`../discovery/atomicguard-bridge/algorithm_fit.md`](../discovery/atomicguard-bridge/algorithm_fit.md) - the smaller step where `DiscoveryAgent`'s algorithm *did* still fit, and exactly which simplifications made that true.
