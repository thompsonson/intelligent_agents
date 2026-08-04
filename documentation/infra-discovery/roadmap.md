# Infra Discovery: Roadmap

## Purpose

`environment_design.md`, `schema.md`, `algorithm_fit.md`, and `examples.md` have accumulated a real amount of open work - inherited open questions, findings from cross-repo review, and (via `atomicguard`'s "Blue-sky extensions worth writing down") nine candidate directions, none of it ordered. This document applies the same discipline that actually got `discovery/` built - one new mechanism proven per step, everything else deliberately deferred, fixture-backed before real - to turn that accumulation into a buildable sequence. No code yet; this is sequencing and rationale, not implementation.

## Why there's no free "step 1" here

Every other arc in this repo's history got to start small because the *next* step reused the *previous* step's algorithm unmodified - `real_discovery/atomicguard_backed/`'s whole validating claim was that `DiscoveryAgent` needed zero changes to run against real, subprocess-backed nodes. `algorithm_fit.md` already closed that door for this environment: `DiscoveryAgent`'s DFS-with-retrace depends on an adjacency/position constraint this ontology doesn't have at all, and there's no fixed, finite graph to prove full-exploration-in-bounded-moves over even if it did. Step 1 here has to be a genuinely new loop - the `AGENT-FUNCTION`/`pending`/`SELECT-NEXT` shape from `atomicguard`'s own document, not a variant of anything already built - which is exactly why it needs to be kept as small as the discipline below can make it.

## Testing discipline: fixtures for behavior, properties for universal claims

Prompted by `atomicguard`'s own `a241844` (naming `D1`-`D4` as falsifiable invariants and recommending property-based testing for two of them) and the `roadmap.md` review that followed it - both worth generalizing beyond where they were first raised, not applied only there.

Both real bugs found in this design so far - `CLEARED`'s cycle-unsafety, the bidirectional-propagation gap - share a shape: each is a **universal claim over an unbounded class of graphs** (any `requires` graph, including cyclic ones; any edge direction, not just the one every worked example happened to use), and each slipped past every hand-traced fixture built so far, because a fixture only proves a property for the one graph its author thought to draw. That weakness isn't specific to `requires`/`CLEARED` - it's specific to *this kind of claim*, and this kind of claim shows up starting at Step 1, not first at Step 2.

**The criterion, applied per-claim, not per-step:** does this property claim to hold for *one specific, named scenario* (fine with a hand-fixture, the same worked-example discipline this whole repo already uses - exact move counts, exact walk traces, exact GIFs), or does it claim to hold for *the whole class of shapes the design is supposed to handle* (needs property-based testing - generate random instances of that class, including adversarial ones like cycles, and assert the property directly)? Concretely, starting from Step 1:

- **Step 1's bidirectional propagation** (`RESOLVE-BRIDGES` discovering novelty via either `edge.to` or `edge.from`) is exactly this shape - a claim about *any* edge/node configuration, not just the `ReplicaSet`/`Pod` example. Property-based testing (generating random small node/edge graphs, asserting propagation reaches whichever end is new regardless of direction) belongs in Step 1's own test suite from the start, alongside its hand-traced worked examples, not deferred until Step 2.
- **Step 2's `D1`/`D2`** (monotonic clearance, cycle-safe clearance) are `atomicguard`'s own named instances of the same pattern - generate random `requires` graphs, including cycles, and assert `cleared` only grows and a cycle always resolves to permanent non-clearance rather than a crash or hang.
- **`D3`** (acting-catalogue allowlist) is a structural/boundary claim, not a property over random input - fits this repo's existing boundary-test style (the kind `test_effector_boundaries.py` and siblings already use in `atomicguard`), whenever Step 5 introduces it.
- **`D4`** (acting freshness) needs a real clock and real re-sensing behavior to mean anything - doesn't fit either pattern cleanly until Step 5 has actual acting DSAs to check it against.

Worth naming honestly, not just applying forward: `discovery/`'s own merged, already-shipped "full exploration, bounded moves" claim (`backtracking-exploration/algorithm_fit.md`'s `2×|E|` bound) is a universal claim of exactly this shape too, and was only ever fixture-tested against `pipeline_fanout_lite` - one graph. Not proposed for retrofit here (that work is done, merged, out of scope); named so this arc is understood as the first place this gets done right from the start, not the first place the gap existed. `hypothesis` is not currently a dependency of this repo either (checked, matching the same finding on the `atomicguard` side) - adding it is part of Step 1's own setup, not a later addition.

## Step 0: two decisions, not builds

Both cheap to decide now, expensive to retrofit once code exists on top of the wrong one - settle before Step 1 starts, not during it.

1. **`belief_state`'s implementation strategy.** Mutable store (`RECORD`/`RECORD-EDGE` write into it directly, `cleared` built incrementally by `SWEEP-CLEARED`, matching the pseudocode as literally written) vs. `σ = proj(R)` (a pure, read-only projection over the sequence of `INVOKE` outcomes, reusing `atomicguard`'s own proven workflow-state pattern - the blue-sky idea, `db07eec`). The tension the blue-sky note itself flags - whether `SWEEP-CLEARED`'s incrementally-built `cleared` set is compatible with "nothing independently stored" - needs to be worked through, not assumed either way, before `schema.md`'s `belief_state` operations table gets implemented against one model or the other.
2. **`Edge`'s shape.** Plain `⟨from, to, edge_type, evidence⟩` tuple (as `schema.md` has it today, with edge identity/de-dup/staleness left as open questions) vs. `Facet`-style accumulated evidence - keyed by `(from, to, edge_type)`, `evidence` a growing list instead of a one-shot field (the other blue-sky idea). Adopting the second folds three of `schema.md`'s open items into one structural move; not adopting it means those three stay separately open into Step 1.

## Step 1: typed, multi-facet, bidirectional sensing - nothing else

**Proves:** compound `NodeId`, `DSA-CATALOGUE`-driven dispatch (a node's `legal_actions` looked up by `(domain, kind)`, not carried per-instance), `Facet` accumulation (multiple senses of the same subject contributing different facets over time), and `RESOLVE-BRIDGES` checking *both* `edge.to` and `edge.from` for novelty - the fix `atomicguard` shipped in response to `environment_design.md`'s own finding, proven here in code for the first time rather than only in pseudocode. A new, minimal flat pending-pool loop (`pending`, `RELEVANT`, `INVOKE`) replaces `DiscoveryAgent` entirely - no LIFO stack, no phases, no notion of "current position."

**Deliberately deferred, and why a fixture scenario can get away with deferring it:**
- **`requires`/`SWEEP-CLEARED`** - a scenario with no AND-joins at all doesn't exercise it, the same way `discovery/` steps 1-2 never exercised `requires=()` doing anything beyond trivially clearing.
- **Acting DSAs** - sensing-only, matching every source document's own scope throughout.
- **`IN-SCOPE`/budget bounding** - a small, hand-built, finite, acyclic scenario is trivially bounded by construction; the *soundness question* stays open, but nothing in Step 1 needs to answer it yet.
- **`RECORD-UNCATALOGUED`** - only matters if the scenario deliberately names an unregistered kind; Step 1's scenario doesn't.
- **Real Stochastic/Dynamic behavior** - `cat`-over-JSON fixtures again, matching `real_discovery/`'s own precedent: deterministic by scenario choice, not because the environment guarantees it (`environment_design.md`'s own properties-table distinction). Real `gh`/`kubectl`/`gcloud` DSAs, and everything `RmaxExhausted`-propagation implies, are out of scope until a later step deliberately picks them up.

**`SELECT-NEXT` for this step:** arbitrary/insertion order over `pending`. `SCORE` stays named-not-defined, exactly as every source document already leaves it - Step 1 doesn't need a real heuristic, only a loop that terminates on a small, bounded pool.

## Step 2: `requires`/`SWEEP-CLEARED`, re-validated under the flat loop

`discovery/`'s step 3 already proved the readiness-sweep mechanism once, inside a two-phase, adjacency-driven structure. Proving it again *without* that structure - `SWEEP-CLEARED` as an iterative fixed-point pass running every turn of a flat loop, not between exploration phases - is genuinely separate work, not a rerun. A fixture scenario reusing an AND-join shape (mirroring `and-joins/scenario.md`'s `(lint, integration-tests)` pattern, translated into this ontology's typed nodes) is the natural worked example - plus `D1`/`D2` property-based tests per "Testing discipline," above, since a hand-fixture alone is exactly the methodology that let the original `CLEARED` recursion bug through.

## Step 3: `IN-SCOPE` boundedness

Only needed once a scenario is deliberately built large or cyclic enough to require it - Step 1's trivially-bounded fixture graph doesn't force this question. The consumable-Ψ-budget mechanism from the blue-sky batch (`IN-SCOPE(subject, Ψ) := belief_state.cost_spent < Ψ.budget`) is the concrete direction to reach for, with its own honest cost stated up front and carried into this step's own design doc when it's written: this bounds *exploration*, not *correctness* - a real, relevant node past budget is never discovered, and `ESCALATE`/`REPORT` need to say so rather than silently reporting as if the search were exhaustive.

## Step 4: `RECORD-UNCATALOGUED`

Needs a scenario with a deliberately-unregistered kind to have anything to prove against - `examples.md`'s `ReplicaSet` case (discovered as `edge.from` via a `Pod`'s real `ownerReferences`, no `DSA-CATALOGUE[(kubernetes, ReplicaSet)]` entry) is the concrete worked example already on record. Makes a catalogue gap a visible, reportable status distinct from `RECORD-UNKNOWABLE`/`RECORD-BLOCKED`, instead of a silent `RELEVANT() = ∅` indistinguishable from "fully explored."

## Step 5: acting - bundled, and kept last on purpose

Dry-run-as-its-own-sensing-shaped-`DSA-CATALOGUE`-entry, the acting-catalogue-hard-allowlist invariant, and the `CLEARED`-monotonicity/staleness fix (the TOCTOU-shaped finding: a subject cleared several sweeps ago may no longer match a genuinely Dynamic world by the time an acting DSA gets selected against it - candidate fix walks the same `REQUIRES` closure `SWEEP-CLEARED` already walks, checking freshness at every ancestor, not just the immediate subject) are bundled into one step because none of them individually means anything until acting exists at all. Every source document defers acting throughout its own scope; this arc defers it furthest on purpose, for the same reason - it's the step with the most unresolved risk (a real mutation, not a read) and the most benefit from everything above already being proven first.

## What doesn't get its own step

- **Node identity stability** (does an `id` reliably name the same real-world thing across sensing calls) - genuinely open, not blocking any step above; a hardening concern to revisit once real (not fixture) DSAs are in play, not before.
- **`SCORE`'s real feature set** (LLM tokens, blast-radius risk, rate limits, `learned_cost` from the blue-sky batch) - Step 5-adjacent at the earliest, since it only matters once `SELECT-NEXT`'s basic soundness (Step 3) is settled. Arbitrary order is enough until then.

## Not decided

- **Exact scenario topology per step.** This roadmap says what property each step's scenario needs to exercise (AND-joins for Step 2, an unregistered kind for Step 4, ...) - not the concrete fixture files, domains, or node counts. Each step's own `scenario.md`, written when that step starts, decides that - matching every prior arc's own discipline of writing `scenario.md` immediately before or alongside the code it justifies, not speculatively now.
- **Whether Step 0's two decisions get their own short design note or just get decided inline at Step 1's start.** Leaning toward a short note either way, given both have already surfaced real tensions worth recording (the `proj(R)`/`SWEEP-CLEARED` compatibility question especially) rather than deciding silently.

## Related documents

- [`ubiquitous_language.md`](ubiquitous_language.md) - the canonical definition of every term used above.
- [`environment_design.md`](environment_design.md) - the properties and node-ownership reasoning every step above builds on.
- [`schema.md`](schema.md) - the field-level types and registered vocabulary Step 1 implements against; the `Edge` shape Step 0's second decision is about.
- [`algorithm_fit.md`](algorithm_fit.md) - why `DiscoveryAgent` doesn't transfer (the reason this roadmap exists at all), `SWEEP-CLEARED`, and `IN-SCOPE`.
- [`examples.md`](examples.md) - the `ReplicaSet`/`Pod` worked example Step 4 is built to formalize.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - `AGENT-FUNCTION`'s pseudocode (the loop Step 1 implements a minimal version of), the "Blue-sky extensions worth writing down" section this roadmap sequences, and the `D1`-`D4` invariants (commit `a241844`) "Testing discipline," above, generalizes beyond Steps 2/3.
