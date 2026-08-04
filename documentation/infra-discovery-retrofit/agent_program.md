# Infra Discovery: Agent Program (Step 5)

**Retrofit note:** renamed from the original `roadmap.md`
(`documentation/infra-discovery/`), per the step-to-file mapping in
`agent_design_process_extensions.md`. Content is otherwise the build
sequence as originally written, with the "Testing discipline" methodology
commitment extracted to [`decisions.md`](decisions.md) (`D-004`), and the
"Step 0: two decisions, not builds" and "Not decided" sections extracted to
[`open_questions.md`](open_questions.md) - pointers left in place. This
track has no per-step `scenario.md` yet either (unlike `discovery/`'s and
`atomicguard-bridge/`'s triads) - `roadmap.md`'s own "Not decided" already
said each step's `scenario.md` gets written when that step starts, not
speculatively now; still true, now recorded as its own line in the sizing
summary rather than left to infer.

## Purpose

`environment_analysis.md`, `schema.md`, `algorithm_fit.md`, and `examples.md`
have accumulated a real amount of open work - inherited open questions,
findings from cross-repo review, and (via `atomicguard`'s "Blue-sky
extensions worth writing down") nine candidate directions, none of it
ordered. This document applies the same discipline that actually got
`discovery/` built - one new mechanism proven per step, everything else
deliberately deferred, fixture-backed before real - to turn that
accumulation into a buildable sequence. No code yet; this is sequencing and
rationale, not implementation.

## Why there's no free "step 1" here

Every other arc in this repo's history got to start small because the
*next* step reused the *previous* step's algorithm unmodified -
`real_discovery/atomicguard_backed/`'s whole validating claim was that
`DiscoveryAgent` needed zero changes to run against real, subprocess-backed
nodes. `algorithm_fit.md` already closed that door for this environment:
`DiscoveryAgent`'s DFS-with-retrace depends on an adjacency/position
constraint this ontology doesn't have at all, and there's no fixed, finite
graph to prove full-exploration-in-bounded-moves over even if it did. Step
1 here has to be a genuinely new loop - the `AGENT-FUNCTION`/`pending`/
`SELECT-NEXT` shape from `atomicguard`'s own document (this process's Step
3; see [`agent_function.md`](agent_function.md), currently a stub), not a
variant of anything already built - which is exactly why it needs to be
kept as small as the discipline below can make it.

## Testing discipline: fixtures for behavior, properties for universal claims

See `D-004` in [`decisions.md`](decisions.md) for the decision itself
(property-based testing starts at Step 1, not deferred to Step 2). Summary:
both real bugs found in this design so far - `CLEARED`'s cycle-unsafety, the
bidirectional-propagation gap (both in [`findings.md`](findings.md)) - are
universal claims over an unbounded class of graphs, and each slipped past
every hand-traced fixture built so far, because a fixture only proves a
property for the one graph its author thought to draw. `hypothesis` is not
currently a dependency of this repo (checked); adding it is part of Step
1's own setup below, not a later addition.

## Step 0: two decisions - see `open_questions.md`

Extracted in full to [`open_questions.md`](open_questions.md) - both items
(`belief_state`'s implementation strategy; `Edge`'s shape) are posed as
forks with tradeoffs, never actually resolved in the original text, despite
the section's own heading calling them "two decisions." Left here as a
one-line pointer rather than silently dropped.

## Step 1: typed, multi-facet, bidirectional sensing - nothing else

**Proves:** compound `NodeId`, `DSA-CATALOGUE`-driven dispatch (a node's
`legal_actions` looked up by `(domain, kind)`, not carried per-instance),
`Facet` accumulation (multiple senses of the same subject contributing
different facets over time), and `RESOLVE-BRIDGES` checking *both*
`edge.to` and `edge.from` for novelty - the fix `atomicguard` shipped in
response to `environment_analysis.md`'s own finding (see `F-001` in
[`findings.md`](findings.md)), proven here in code for the first time
rather than only in pseudocode. A new, minimal flat pending-pool loop
(`pending`, `RELEVANT`, `INVOKE`) replaces `DiscoveryAgent` entirely - no
LIFO stack, no phases, no notion of "current position."

**Deliberately deferred, and why a fixture scenario can get away with deferring it:**
- **`requires`/`SWEEP-CLEARED`** - a scenario with no AND-joins at all
  doesn't exercise it, the same way `discovery/` steps 1-2 never exercised
  `requires=()` doing anything beyond trivially clearing.
- **Acting DSAs** - sensing-only, matching every source document's own
  scope throughout.
- **`IN-SCOPE`/budget bounding** - a small, hand-built, finite, acyclic
  scenario is trivially bounded by construction; the *soundness question*
  stays open (see `open_questions.md`), but nothing in Step 1 needs to
  answer it yet.
- **`RECORD-UNCATALOGUED`** - only matters if the scenario deliberately
  names an unregistered kind; Step 1's scenario doesn't.
- **Real Stochastic/Dynamic behavior** - `cat`-over-JSON fixtures again,
  matching `real_discovery/`'s own precedent: deterministic by scenario
  choice, not because the environment guarantees it
  (`environment_analysis.md`'s own properties-table distinction). Real
  `gh`/`kubectl`/`gcloud` DSAs, and everything `RmaxExhausted`-propagation
  implies, are out of scope until a later step deliberately picks them up.

**`SELECT-NEXT` for this step:** arbitrary/insertion order over `pending`.
`SCORE` stays named-not-defined, exactly as every source document already
leaves it - Step 1 doesn't need a real heuristic, only a loop that
terminates on a small, bounded pool.

## Step 2: `requires`/`SWEEP-CLEARED`, re-validated under the flat loop

`discovery/`'s step 3 already proved the readiness-sweep mechanism once,
inside a two-phase, adjacency-driven structure. Proving it again *without*
that structure - `SWEEP-CLEARED` as an iterative fixed-point pass running
every turn of a flat loop, not between exploration phases - is genuinely
separate work, not a rerun. A fixture scenario reusing an AND-join shape
(mirroring `and-joins/scenario.md`'s `(lint, integration-tests)` pattern,
translated into this ontology's typed nodes) is the natural worked example
- plus `D1`/`D2` property-based tests per "Testing discipline," above,
since a hand-fixture alone is exactly the methodology that let the original
`CLEARED` recursion bug through.

## Step 3: `IN-SCOPE` boundedness

Only needed once a scenario is deliberately built large or cyclic enough to
require it - Step 1's trivially-bounded fixture graph doesn't force this
question. The consumable-Ψ-budget mechanism from the blue-sky batch
(`IN-SCOPE(subject, Ψ) := belief_state.cost_spent < Ψ.budget`) is the
concrete direction to reach for, with its own honest cost stated up front
and carried into this step's own design doc when it's written: this bounds
*exploration*, not *correctness* - a real, relevant node past budget is
never discovered, and `ESCALATE`/`REPORT` need to say so rather than
silently reporting as if the search were exhaustive.

## Step 4: `RECORD-UNCATALOGUED`

Needs a scenario with a deliberately-unregistered kind to have anything to
prove against - `examples.md`'s `ReplicaSet` case (discovered as
`edge.from` via a `Pod`'s real `ownerReferences`, no
`DSA-CATALOGUE[(kubernetes, ReplicaSet)]` entry) is the concrete worked
example already on record. Makes a catalogue gap a visible, reportable
status distinct from `RECORD-UNKNOWABLE`/`RECORD-BLOCKED`, instead of a
silent `RELEVANT() = ∅` indistinguishable from "fully explored."

## Step 5: acting - bundled, and kept last on purpose

Dry-run-as-its-own-sensing-shaped-`DSA-CATALOGUE`-entry, the
acting-catalogue-hard-allowlist invariant, and the
`CLEARED`-monotonicity/staleness fix (the TOCTOU-shaped finding: a subject
cleared several sweeps ago may no longer match a genuinely Dynamic world by
the time an acting DSA gets selected against it - candidate fix walks the
same `REQUIRES` closure `SWEEP-CLEARED` already walks, checking freshness at
every ancestor, not just the immediate subject) are bundled into one step
because none of them individually means anything until acting exists at
all. Every source document defers acting throughout its own scope; this arc
defers it furthest on purpose, for the same reason - it's the step with the
most unresolved risk (a real mutation, not a read) and the most benefit
from everything above already being proven first.

## What doesn't get its own step

- **Node identity stability** (does an `id` reliably name the same
  real-world thing across sensing calls) - genuinely open, not blocking any
  step above; a hardening concern to revisit once real (not fixture) DSAs
  are in play, not before.
- **`SCORE`'s real feature set** (LLM tokens, blast-radius risk, rate
  limits, `learned_cost` from the blue-sky batch) - Step 5-adjacent at the
  earliest, since it only matters once `SELECT-NEXT`'s basic soundness
  (Step 3) is settled. Arbitrary order is enough until then.

## Related documents

- [`ubiquitous_language.md`](ubiquitous_language.md) - the canonical definition of every term used above (Step 0).
- [`environment_analysis.md`](environment_analysis.md) - Step 2; the properties and node-ownership reasoning every step above builds on.
- [`schema.md`](schema.md) - Step 0; the field-level types and registered vocabulary Step 1 implements against.
- [`algorithm_fit.md`](algorithm_fit.md) - Step 4; why `DiscoveryAgent` doesn't transfer, `SWEEP-CLEARED`, and `IN-SCOPE`.
- [`agent_function.md`](agent_function.md) - Step 3; currently a stub, but the loop this document's Step 1 implements a minimal version of belongs there once written.
- [`examples.md`](examples.md) - the `ReplicaSet`/`Pod` worked example Step 4 (of the build sequence) is built to formalize.
- [`decisions.md`](decisions.md) / [`findings.md`](findings.md) / [`open_questions.md`](open_questions.md) - the register files this document's "Testing discipline," "Step 0," and "Not decided" sections were extracted into.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - `AGENT-FUNCTION`'s pseudocode, the "Blue-sky extensions worth writing down" section this document sequences, and the `D1`-`D4` invariants.
