# Infra Discovery: Handover for Implementation

**This is a kickoff document for whoever picks up implementation next** -
not a summary of the design (that's what the rest of this directory is
for), and not itself a register (nothing here should be treated as a new
decision, finding, or open question; if you make one while implementing,
it belongs in `decisions.md`/`findings.md`/`open_questions.md`, not here).

## Intention

Build an agent that discovers the graph of real infrastructure -
`github_actions`/`kubernetes`/`gcp` resources and the edges between them -
by invoking real, guard-checked `atomicguard.ActionPair`s through a real
`atomicguard.application.agent.DualStateAgent`, the same way
`real_discovery/atomicguard_backed/` already proved that pattern works for
a smaller, single-domain toy. This is the next step past that toy: a real
ontology (compound node identity, multi-facet state, a typed action
catalogue) instead of a simplified stand-in for it.

## Read in this order

1. [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md) - the vocabulary everything else assumes.
2. [`step1_environment_specification.md`](step1_environment_specification.md) - PEAS: what this agent perceives, acts on, and is measured against.
3. [`step0_schema.md`](step0_schema.md) - the actual field-level types (`NodeId`, `Facet`, `Edge`) and the registered `DSA-CATALOGUE`/`BRIDGE-CATALOGUE` vocabulary you build against.
4. [`step3_agent_function.md`](step3_agent_function.md) - the `AGENT-FUNCTION` pseudocode: percepts, the sole actuator (`INVOKE`), the full loop.
5. [`step5_agent_program.md`](step5_agent_program.md)'s **"Step 1: typed, multi-facet, bidirectional sensing - nothing else"** section - the actual scope to build. Stop there; don't read the whole build sequence as this step's job.

`step2_environment_analysis.md` and `step4_algorithm_fit.md` are worth
reading once, mainly for *why* - why the ontology has the shape it does,
why `discovery/`'s `DiscoveryAgent` doesn't transfer. Not needed to start
coding.

## What you're building (and only this, for now)

`step5_agent_program.md`'s Step 1 is the bounded starting scope, already
decided:

- Compound `NodeId` (`domain, kind, id`), not a bare string.
- `Facet` accumulation - multiple senses of the same subject contributing
  different facets over time (`{value, observed_at, sensed_by}` each).
- `DSA-CATALOGUE`-driven dispatch - a node's legal actions looked up by
  `(domain, kind)`, never carried per-instance.
- `RESOLVE-BRIDGES` checking **both** `edge.to` and `edge.from` for
  novelty - this is `F-001`, already fixed in the source pseudocode; don't
  reintroduce the one-directional version.
- A new, minimal **flat pending-pool loop** (`pending`, `RELEVANT`,
  `INVOKE`) replacing anything stack/phase/position-based. There is no
  "current position" in this agent - a DSA is invoked directly against
  whatever `NodeId` is already known, the instant it's known.

**Deliberately deferred** (per `step5_agent_program.md` - don't build these
into Step 1, even if it looks convenient to):

- `requires`/`SWEEP-CLEARED` (AND-joins) - Step 2.
- Acting DSAs (anything that mutates, not just reads) - Step 5, kept
  deliberately last, bundled with the acting-catalogue allowlist and the
  `CLEARED`-staleness fix.
- `IN-SCOPE`/budget bounding - Step 3. A small, hand-built, finite, acyclic
  scenario is trivially bounded by construction; don't build the general
  mechanism until a scenario actually needs it.
- `RECORD-UNCATALOGUED` - Step 4. Only matters once a scenario deliberately
  names an unregistered kind.
- Real Stochastic/Dynamic behavior - `cat`-over-JSON fixtures, exactly like
  `real_discovery/`'s own precedent: deterministic by scenario choice, not
  because the environment guarantees it.

## The precedent to copy, not reinvent

`real_discovery/atomicguard_backed/core/` already proved the core wiring
pattern - a node's sensing runs through a real `DualStateAgent`, not a
static field:

```python
from atomicguard.application.agent import DualStateAgent
from atomicguard.application.action_pair import ActionPair
from atomicguard.infrastructure.persistence.memory import InMemoryArtifactDAG

agent = DualStateAgent(
    action_pair=node.check_action_pair,
    artifact_dag=self._dag,
    rmax=0,               # see caveat below
    action_pair_id=node_id,
    workflow_id=self._workflow_id,
)
artifact = agent.execute(specification="")
```

Two things carry over directly, and one doesn't:

- **Carries over:** constructing a fresh, stateless `DualStateAgent` per
  invocation, bound to one `ActionPair`, reading the result off
  `Artifact.content`. `step3_agent_function.md`'s `INVOKE(dsa, subject)` is
  this exact call, generalized from one hardcoded `check_action_pair` per
  node to a `DSA-CATALOGUE[(domain, kind)]` lookup per invocation.
- **Carries over:** treating unknown-target validation as a sense-time
  concern, not a construction-time one - a target genuinely isn't knowable
  until the DSA naming it actually runs.
- **Doesn't carry over as-is:** `rmax=0`. `real_discovery/`'s free-sensor
  shape fit a local, cheap, deterministic `cat`-over-fixture check.
  `step2_environment_analysis.md`'s properties table calls this
  environment genuinely **Stochastic** - real `gh`/`kubectl`/`gcloud` calls
  fail transiently, rate-limit, time out - so a real (non-zero) `rmax` per
  DSA is the honest default once you're past `cat`-over-fixture scenarios.
  What the actual number should be isn't decided anywhere in this
  track - pick something for the fixture scenario and record it as a
  decision if it's not obvious, don't silently inherit `0`.

## One thing to resolve before writing any code

**`OQ-019`: where does this code live** - `atomicguard`, `intelligent_agents`,
or a new repo? Named explicitly in the source document's own "Still open"
section, still unresolved here. Administrative, not a design-soundness
question, but genuinely blocking - you can't `git init` or pick an import
path without an answer. Resolve this first, not as an afterthought once
code already exists somewhere.

## Two risks the source document flags as unsolved - not solved by any design work in this track

Both were found by checking `step3_agent_function.md`'s reproduced
pseudocode against the real source line by line - the source's own inline
commentary named them; the translation into this track's vocabulary
dropped the comments and, with them, the warnings:

- **`OQ-017` - the reachability risk is not auto-solved.** `RECORD-REQUIRES`
  does *not* auto-enqueue its own targets into `pending`. A `requires`
  target named in some DSA's output but never independently discovered via
  `RESOLVE-BRIDGES`/`DSA-CATALOGUE` dispatch **deadlocks silently** -
  nothing in the pseudocode prevents it. This was tried once (auto-enqueue
  on `RECORD-REQUIRES`) and deliberately walked back - "nothing validates
  that as correct or necessary." Every scenario you build has to get
  reachability right by hand; the algorithm doesn't guarantee it.
- **`OQ-018` - sensing may need gating too, not just acting.** `ELIGIBLE`'s
  current default lets sensing DSAs run regardless of `cleared`, gating
  only acting DSAs. The source states this as a policy default, not a
  settled fact, and leaves the sensing case explicitly deferred. Don't
  read the current pseudocode's silence on this as "sensing is definitely
  ungated by design" - it's "ungated because nobody's decided otherwise
  yet."

Neither blocks Step 1 (no acting exists yet, and Step 1's fixture graphs
are hand-built small enough that reachability is trivially satisfiable by
construction) - but both should stay live in your head past Step 1, not
get treated as closed because they're not blocking today.

## How to use the registers

Check before deciding, don't re-derive:

- [`decisions.md`](decisions.md) - `D-001`-`D-006` are already settled.
  Don't re-litigate compound `NodeId`, `requires` vs. `legal_actions` as
  separate mechanisms, sensing-DSA aggregation, or property-based testing
  scope - they're checked against the real source, not just asserted.
- [`findings.md`](findings.md) - `F-001`-`F-005` are bugs already found
  and fixed in the design (bidirectional propagation, `CLEARED`
  cycle-safety, and three retrofit-introduced errors this track corrected
  in itself). Don't reintroduce any of them while translating pseudocode
  into code.
- [`open_questions.md`](open_questions.md) - 19 entries, genuinely
  undecided. Check here before assuming something's settled just because
  it reads confidently in prose - that's the exact failure mode this
  track's own register convention exists to prevent.
- [`worked_examples.md`](worked_examples.md) - concrete instances to test
  against, not just illustrations. `WE-003` (`Pod`/`ReplicaSet`
  `ownerReferences`) is the standing worked example for the
  bidirectional-propagation fix and the eventual `RECORD-UNCATALOGUED`
  scenario (Step 4).

## Testing discipline

`D-004`: property-based testing starts at Step 1, not deferred to Step 2 -
the bidirectional-propagation claim (`F-001`) is a universal claim over an
unbounded class of edge directions, the same shape as `D1`/`D2`'s
`requires`-graph claims, and a hand-traced fixture alone already let one
real bug (`F-001`) through once. `hypothesis` is not currently a dependency
of this repo; adding it is part of Step 1's own setup, not a later
addition.

## Definition of done for Step 1

A flat `pending`/`RELEVANT`/`INVOKE` loop, running against a small,
hand-built, fixture-backed scenario, that:

- Discovers nodes via real (or realistically fixture-backed)
  `DualStateAgent` invocations, dispatched through `DSA-CATALOGUE`, not a
  hardcoded per-node check.
- Accumulates `Facet`s per node across independently-timestamped sense
  calls (`WE-002`'s shape).
- Discovers edges in both directions (`WE-001`'s forward case and
  `WE-003`'s backward case both need to work).
- Has at least one property-based test over edge direction, per `D-004`.

Everything past that is Step 2 onward - see `step5_agent_program.md` for
the full sequence once Step 1 is real.
