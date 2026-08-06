# Infrastructure Discovery Agent — Step 2 Implementation

Per [`documentation/infra-discovery/step5_agent_program.md`](documentation/infra-discovery/step5_agent_program.md)'s
build-sequence Step 2: **"`requires`/`SWEEP-CLEARED`, re-validated under
the flat loop."** `discovery/`'s step 3 already proved the readiness-sweep
mechanism once, inside a two-phase, adjacency-driven structure. This step
re-proves it as an iterative fixed-point pass running **every turn of
Step 1's flat pending-pool loop**, not between exploration phases — there
are no phases here.

Sibling to [`INFRA_DISCOVERY_STEP1.md`](INFRA_DISCOVERY_STEP1.md), which
this step builds on without modifying.

## What Changed

`belief_state.py` already had the storage-layer half from Step 1's own
scaffolding (`requires_by_node`, `cleared`, `sweep_cleared()`) — unused
until now. This step wires it into `agent_loop.py`:

- **`DSACatalogueEntry.is_sensing`** (default `True`) — the `IS-SENSING(dsa)`
  predicate `ELIGIBLE` needs. No acting DSAs exist yet (Step 5), so this is
  a structural no-op today, not a behavior change.
- **`InfraDiscoveryAgent.requires_catalogue`** + **`register_requires()`** —
  `requires` is **static, catalogue-declared** for this step (per
  `step5_agent_program.md`'s own line), not derived from a DSA's artifact
  content. `step()` looks this up per subject instead of the Step 1
  placeholder (`record_requires(subject, ())`, always empty).
- **`_eligible()`** — implements `step3_agent_function.md`'s `ELIGIBLE`
  pseudocode: sweeps `cleared` first, then filters `pending` to
  `IS-SENSING(dsa) or subject ∈ cleared`. `_select_next()` now only ever
  chooses from this filtered set, not raw `pending`.
- **`step()`** sweeps `cleared` **twice** per call on purpose: once at the
  top (see the bug below), once again inside `_eligible()` (matches the
  pseudocode's own `ELIGIBLE` sweeping unconditionally, cheap and
  idempotent either way).

## A Real Bug Caught While Implementing

First cut only swept inside `_eligible()`, called *before* each turn's
`RECORD-REQUIRES`. That means a subject recorded on the **final** turn of
an episode never got a subsequent sweep — `step()`'s `if not pending:
return "done"` check fires before another `_eligible()` call happens.
`cleared` lagged the true fixed point by exactly one turn, silently: an
AND-join target recorded last in a run would show up in
`belief_state.recorded_subjects()` but never in `cleared`, even though its
requires actually were satisfied.

Caught by `test_and_join_full_topology_clears_web_app` — the AND-join
target failed to appear in `cleared` at episode end. Fixed by sweeping
once more at the top of every `step()` call, before the `pending` check,
so a subject's requires get one final chance to resolve before "done"
reports.

## Fixture Scenario: `and_join_topology`

Translates `discovery/`'s `documentation/discovery/and-joins/scenario.md`
(`merge-gate.requires = (lint, integration-tests)`) into this ontology's
typed nodes:

```
github_actions/workflow_run/ci (root)
  -> github_actions/job/lint                  (triggers)
  -> gcp/CloudBuild_trigger/integration-tests  (triggers)
  -> kubernetes/Deployment/web-app             (applies-to)

kubernetes/Deployment/web-app.requires = (lint, integration-tests)
```

Every node is a distinct `(domain, kind)` pair on purpose. `DSACatalogueEntry`
binds one fixed fixture per registration — nothing in the current flat loop
parameterizes a DSA's content by subject id, so two sibling nodes needing
*different* content can't safely share a `(domain, kind)` key yet (D-003's
"run all applicable sensing DSAs" is for genuinely different DSAs on one
kind, not "another instance" of the same kind). Real infrastructure backs
this modeling choice up anyway: a lint check and an integration-test run
are plausibly different kinds (`github_actions/job` vs.
`gcp/CloudBuild_trigger`), not a shortcut.

`web-app` is discovered directly off the root — independent of the
lint/integration-test branches, mirroring a deploy step triggered in
parallel with CI checks — but can only enter `cleared` once *both*
branches have themselves cleared.

## What Works ✅

- [x] `requires` static catalogue lookup (`register_requires`), wired into `RECORD-REQUIRES`
- [x] `SWEEP-CLEARED` as an iterative fixed-point pass, called every turn of the flat loop
- [x] `ELIGIBLE` filtering (`IS-SENSING(dsa) or subject ∈ cleared`) — structural, matches sensing-only scope
- [x] AND-join fixture scenario: a fully-reachable, fully-sensed target still gated on `requires`
- [x] `D1` (monotonic clearance) property tests — `cleared` never shrinks, across arbitrary `requires` graphs including cycles
- [x] `D2` (cycle-safe clearance) property tests — `SWEEP-CLEARED` never crashes/hangs on cyclic `requires`; cyclic members never clear
- [x] `RECORD-UNKNOWABLE`/`RECORD-BLOCKED` propagation through `cleared` (a permanently-failed subject still counts as satisfied for anything requiring it)

## What's Explicitly Deferred (Per Design)

Per `step5_agent_program.md`, unchanged from Step 1's own list except
`requires`/`SWEEP-CLEARED` moving to done:

- [ ] Acting DSAs (only sensing) → Step 5
- [ ] `IN-SCOPE` / budget bounding → Step 3
- [ ] `RECORD-UNCATALOGUED` → Step 4
- [ ] Real stochastic behavior (fixtures are deterministic) → later

## A Pre-existing Gap Fixed in Passing

`simple_topology.py`'s `_cat_action_pair` hard-imported `atomicguard` with
no fallback — `test_agent_loop.py::test_agent_initialization` had been
silently broken (import error) since before this step, masking a second,
genuinely stale assertion (`len(agent.dsa_catalogue) == 3`, when the
scenario has registered 4 DSAs since the `ReplicaSet` DSA was added for
F-001 validation). Both fixed: the import now falls back to a
fixture-content mock, matching `agent_loop.py`'s own `__post_init__`/
`invoke()` precedent; the assertion now matches what the scenario actually
registers.

## Running the Tests

```bash
make test-infra-discovery
# or directly:
uv run pytest infra_discovery/tests/ -v
```

24 passed (up from 13 reachable in Step 1 — `hypothesis` was imported but
never actually installed; `uv pip install hypothesis` closed that gap).

## Next Steps (Step 3)

Per `step5_agent_program.md`: `IN-SCOPE` boundedness — only needed once a
scenario is deliberately built large or cyclic enough to require it. The
consumable-Ψ-budget mechanism (`IN-SCOPE(subject, Ψ) := belief_state.cost_spent
< Ψ.budget`) is the concrete direction; its own honest cost (bounds
*exploration*, not *correctness*) carries into that step's design doc.
