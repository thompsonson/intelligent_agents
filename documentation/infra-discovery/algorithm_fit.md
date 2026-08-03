# Algorithm Fit: Infra Discovery

## Purpose

`environment_design.md` settled the shape: compound `(domain, kind, id)` identity, catalogue-driven `legal_actions`, multi-facet accumulating `state`, bidirectional edge discovery, a persistent `belief_state` external to any one run. This document asks the question `atomicguard-bridge/algorithm_fit.md` could answer cheaply (yes, unmodified, proven by a passing test) and this one can't: does any traversal algorithm already in this repo fit this environment at all? No proof is possible yet - there's no reference implementation to hand-trace against, unlike every prior `algorithm_fit.md` in this repo. What follows is the argument for what family fits and what's still genuinely open, not a completed derivation.

## Why `DiscoveryAgent`'s DFS-with-retrace does not transfer here - argued directly, not assumed

`atomicguard`'s own revision document already settled this for the smaller `atomicguard-bridge/` case, and the reasoning applies here even more directly: *"`discovery/`'s LIFO parent stack exists solely because its agent can only sense the node it's standing on and has to physically retrace steps to reach an unexplored branch. `INVOKE(dsa, subject)` has no such constraint."* `atomicguard-bridge/`'s environment kept the constraint anyway, deliberately, as a "small step" - `StatefulDiscoveryEnvironment` still has no notion of "current position," but `DiscoveryAgent.walk()` imposes one on top of it (`current`, a parent stack) because that's the algorithm being tested, not because the environment demands it.

This environment can't inherit that choice, for two independent reasons:

1. **No adjacency at all.** A `(domain, kind, id)` triple isn't "reached" by moving through anything - `INVOKE(dsa, subject)` is invoked directly the instant `subject` is known, regardless of what was invoked immediately before it, possibly in a completely different domain. There's no sense in which "backtracking" to a previous subject means anything.
2. **`backtracking-exploration/algorithm_fit.md`'s own bound doesn't apply, for a reason beyond the adjacency-cost point already made in `atomicguard-bridge/`.** That bound (`2×|E|`, full exploration guaranteed) assumes a *finite, fixed* graph worth fully exploring. This environment's properties table says otherwise on both counts: `Discrete` is "unbounded at the instance level," and "full exploration" isn't even the right goal - `Ψ` scopes the search (matching the source ontology document's own reason frontier-based exploration doesn't fit either: *"our intention Ψ is given and scopes the search; we're not building a complete map for its own sake"*). There's no fixed, finite thing to prove bounded-and-complete exploration over the way `discovery/`'s toy has.

## What the source document already grounds this in, checked directly rather than re-derived

`topology_sensing_dsa_belief_state_and_agent_function.md`'s own "Grounding in robot/AI search literature" section did this literature survey already - restated here because it's the actual answer, not because it needs re-deriving:

- **D\* Lite** - assumes a *known, fixed vertex set*, only edge traversability unknown. Doesn't fit: new nodes (Pods, workflow runs) can exist that weren't known in advance, at all.
- **LRTA\*** - *no map at all*. Senses only locally, bounded lookahead via a heuristic, updates the heuristic at the state it's leaving, moves, repeats. **This is the fit**, per the source document's own reasoning: what's known ahead of time is the local action vocabulary per type (`DSA-CATALOGUE`), not the graph shape - exactly LRTA\*'s "know what's available from here, not what the whole graph looks like."
- **Frontier-based exploration** - map-building is the objective itself. Doesn't fit: `Ψ` scopes and terminates the search; there's no reason to keep exploring past what `Ψ` needs.

Concretely, the candidate algorithm isn't a variant of `DiscoveryAgent.walk()` at all - it's the source document's own `AGENT-FUNCTION` pseudocode: a `pending` pool of `⟨dsa, subject⟩` pairs, `SELECT-NEXT(pending, belief_state) = argmax SCORE(...)`, no position, no backtracking, no phases. `discovery/`'s three PRs validated the *readiness* half of a relative (the `requires`/`CLEARED` mechanism, per `atomicguard-bridge`'s own revision-document review); they never validated `SELECT-NEXT` itself, and neither does anything built in this repo so far.

## The soundness question this environment inherits, not one it raises new

`atomicguard`'s revision document's own "Exploration completeness is genuinely open" section already states the actual open problem, and it applies to this environment exactly as written there, not as a new finding: whether plain `argmax SCORE` over `eligible` is sound at all depends entirely on whether `IN-SCOPE(subject, Ψ)` can be proven to bound the total reachable-and-relevant set.

- **If bounded** - a real `max_depth`/`max_width` ceiling on `Ψ` - the eligible-and-in-scope portion of `pending` is finite, and greedy `argmax`, run to exhaustion, eventually invokes everything in it. Structurally the same shape as `discovery/`'s own bounded-by-node-count termination argument, generalized to "bounded by `IN-SCOPE`'s limit" instead of "bounded by the literal graph."
- **If not bounded** - greedy `SELECT-NEXT` isn't sound; something with a fairness guarantee is needed (aging scores, round-robin, or an explicit exhaust-`pending`-before-considering-new-arrivals discipline - structurally a revival of `discovery/`'s own phase structure, for scheduling fairness rather than the adjacency reason that structure existed for originally).

Not resolved here, same as it isn't resolved in the document it's inherited from. Worth flagging precisely why this environment can't dodge it the way `atomicguard-bridge/` implicitly did: `atomicguard-bridge/`'s `pipeline_fanout_lite` is six nodes, trivially bounded by construction, so `IN-SCOPE`-style boundedness was never actually tested by anything built so far. This environment's own properties table says `Discrete: ... genuinely unbounded at the instance level` - the untested case is the default case here, not an edge case.

## A gap this environment would inherit for real, not hypothetically: `CLEARED`'s cycle-safety

Flagged during review of `atomicguard`'s revision document (commit `67c1635`): its `CLEARED(subject)` pseudocode is a naive recursive function (`RECORDED(subject) and all(CLEARED(r) for r in REQUIRES(subject))`), unlike real `WorkflowState.is_satisfied()`'s O(1) flat lookup (`domain/models.py:337`) - which is safe against a `requires` cycle only because it's never recursive; satisfaction is set explicitly, once, not recomputed by walking the graph. A cyclic `requires` declaration would make real `WorkflowOrchestrator._find_applicable()` deadlock cleanly (`None`, reported `FAILED`); it would make the pseudocoded `CLEARED()` stack-overflow instead.

This isn't a hypothetical import for this environment - it's a live one. Real infrastructure dependency relationships are exactly AND-join-shaped (don't check an `Ingress` until its `Service` is ready; don't check a `Service` until its `Deployment` is ready) and, unlike `discovery/`'s hand-authored toy topology, real dependency graphs discovered from live infrastructure are a real place for a genuine cycle to show up unintentionally (two services each depending on the other during a migration, say) - with no equivalent of `discovery/`'s construction-time full-graph validation available, since the graph isn't known until it's discovered. If this environment's algorithm ever needs `requires`/`CLEARED`-style gating (likely, given how naturally infra dependencies fit that shape), it needs to inherit an *iterative*, cycle-safe `cleared`-as-a-monotonically-growing-set implementation - matching `discovery/`'s own actual code, not the recursive pseudocode - not assume the gap was already closed elsewhere.

## Open, not resolved

- **`SCORE`'s real feature set** - already enumerated in the source document's own "Cost features" section (generator-side token/latency/non-determinism costs, effector-side idempotency/blast-radius/dry-run costs, known-in-advance vs. learned, subject-dependent variance within one DSA type) - not re-derived here, and still entirely undemonstrated in any code, in this repo or `atomicguard`'s.
- **`IN-SCOPE(subject, Ψ)` boundedness** - the central soundness question, restated above, not resolved.
- **The bidirectional edge-propagation gap** - named in `environment_design.md`, not fixed: `RESOLVE-BRIDGES`/`pending` propagation needs to check both `edge.from` and `edge.to` for novelty, not just `edge.to`.
- **`belief_state`'s persistence mechanism** - named as a hard requirement in `environment_design.md`, not designed.
- **`CLEARED` cycle-safety, if/when `requires`-style gating is added** - named above; not designed, since `requires`-style gating itself isn't decided yet for this environment.
- **What a genuinely failing/flaky DSA invocation does to `pending`/`SELECT-NEXT`.** `atomicguard-bridge/algorithm_fit.md` left this open for a single, always-succeeding fixture check; this environment's own properties table already declares `Deterministic/Stochastic: Stochastic` - a failing sense is the expected case here, not an edge case, and nothing in the source document's `RECORD-UNKNOWABLE`/`RECORD-BLOCKED` propagation has been checked against a real implementation yet either.

## Related documents

- [`environment_design.md`](environment_design.md) - the node/edge shape and environment properties this fit argument is checked against.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` - the LRTA*/D*-Lite/frontier-exploration literature survey, the `AGENT-FUNCTION` pseudocode, and the full cost-feature enumeration this document defers to rather than repeats.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - `IN-SCOPE`/`SELECT-NEXT` soundness, and the `CLEARED` recursion the cycle-safety gap above was found in.
- [`../discovery/backtracking-exploration/algorithm_fit.md`](../discovery/backtracking-exploration/algorithm_fit.md) - the DFS-with-retrace bound this document argues does not transfer, and why.
- [`../discovery/atomicguard-bridge/algorithm_fit.md`](../discovery/atomicguard-bridge/algorithm_fit.md) - the smaller step where `DiscoveryAgent`'s algorithm *did* still fit, and exactly which simplifications made that true.
