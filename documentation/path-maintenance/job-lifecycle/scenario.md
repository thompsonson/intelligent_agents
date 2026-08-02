# Scenario: `deploy_chain_lite`, with a lifecycle

## Same topology, richer nodes

No new graph — `deploy_chain_lite`'s exact 5-node topology (`pre-commit`, `lint`, `unit-tests`, `merge`, `deploy`), unchanged, consistent with this repo's standing rule against inventing new domain vocabulary for a new capability demonstration (the same instinct `guard-first/scenario.md` followed, reusing `pr_merge_lite` unmodified). Each `GraphNode` becomes a `JobNode`, gaining `ticks_to_resolve`/`resolves_to`:

| Node | requires | `ticks_to_resolve` | `resolves_to` |
|---|---|---|---|
| `pre-commit` | — | 0 | `SUCCEEDED` |
| `lint` | `(pre-commit)` | 2 | `SUCCEEDED` |
| `unit-tests` | `(pre-commit)` | 0 | `SUCCEEDED` |
| `merge` | `(lint, unit-tests)` | 0 | `SUCCEEDED` |
| `deploy` | `(merge)` | 1 | `FAILED` |

Chosen so every value of `JobState` is exercised at least once across the walk, and — the same "side by side contrast" trick `deploy_chain_lite`'s own `scenario.md` used for `lint`/`unit-tests` — the two nodes in the second generation now contrast on lifecycle *timing* as well as outcome: `lint` takes real waiting, `unit-tests` resolves instantly, sitting right next to each other in the layered layout.

## Walking through the ticks by hand

`order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]` (identical to step 2's — an AND-only DAG's topological order doesn't depend on node state, only on `requires`, which hasn't changed).

`pre-commit` (`order[0]`) is never sensed, same convention as steps 1-2.

**`lint`** (`ticks_to_resolve=2`):
1. `get_job_state("lint")` → ticks elapsed `0` → `PENDING`
2. `advance_jobs()` → ticks elapsed `1`
3. `get_job_state("lint")` → `0 < 1 < 2` → `IN_PROGRESS`
4. `advance_jobs()` → ticks elapsed `2`
5. `get_job_state("lint")` → `2 >= 2` → `SUCCEEDED`

Three senses, two `advance_jobs()` calls, no repair.

**`unit-tests`** (`ticks_to_resolve=0`):
1. `get_job_state("unit-tests")` → `0 >= 0` → `SUCCEEDED` immediately

One sense, no waiting — resolves exactly like a step 2 node with no lifecycle at all.

**`merge`** (`ticks_to_resolve=0`): identical shape to `unit-tests` — resolves on first sense. The AND-join's own gating already happened when `order` was computed; `merge` having no lifecycle drama of its own keeps that mechanism visually and logically separate from the new lifecycle capability, the same separation `deploy_chain_lite/algorithm_fit.md` drew between "the AND-join is enforced once, when `order` is computed" and "the agent just walks it."

**`deploy`** (`ticks_to_resolve=1`, `resolves_to=FAILED`):
1. `get_job_state("deploy")` → ticks elapsed `0` → `PENDING`
2. `advance_jobs()` → ticks elapsed `1`
3. `get_job_state("deploy")` → `1 >= 1` → `FAILED`
4. `repair_node("deploy")` called

Two senses, one `advance_jobs()` call, one repair — the fullest combination: waiting *and* failing.

## Totals

`result.repairs_performed == ["deploy"]`. `result.senses_performed == {"lint": 3, "unit-tests": 1, "merge": 1, "deploy": 2}`. `result.success is True`.

## What this scenario is for

- **Smoke test** that `JobGraphEnvironment`'s tick bookkeeping, `advance_jobs()`, and `repair_node()`'s `FAILED`-only precondition all compose correctly.
- **Exercises every `JobState` value at least once**: `PENDING` (`lint` sense 1, `deploy` sense 1), `IN_PROGRESS` (`lint` sense 2), `SUCCEEDED` (`lint`, `unit-tests`, `merge`), `FAILED` (`deploy`, then repaired).
- **A deterministic regression case**: a test can assert `senses_performed` and `repairs_performed` directly, no seeded randomness involved.

## Not decided

- Whether a second scenario is worth adding once this one is proven — e.g. one where an AND-join's parent is itself still `IN_PROGRESS` when the agent would otherwise be ready to check the join, to make the "the join's gating already happened at order-computation time, not at walk time" point sharper. Not needed for this first cut, since `merge`'s own resolution already demonstrates the join without needing to contrive that timing.
