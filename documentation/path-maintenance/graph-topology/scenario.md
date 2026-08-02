# Scenario: `deploy_chain_lite`

## Purpose

`environment_design.md` specifies the primitives (`GraphNode`, `requires`, `PathGraphEnvironment`). This document specifies one concrete graph built from them — small enough to read at a glance, but with a genuine AND-join, since a purely linear chain wouldn't demonstrate the one thing this step exists to add: fan-out.

## The graph

```
pre-commit ──▶ lint ────────┐
      │                     ▼
      └───────▶ unit-tests ─▶ merge ──▶ deploy
```

| Node | requires |
|---|---|
| `pre-commit` | — |
| `lint` | `(pre-commit)` |
| `unit-tests` | `(pre-commit)` |
| `merge` | `(lint, unit-tests)` |
| `deploy` | `(merge)` |

Five nodes, one AND-join (`merge`, two parents) — the smallest graph that has a real fan-in at all. `pre-commit` fans out to two independent checks; `merge` is only ready once *both* have resolved. This is deliberately the same size/shape instinct `task_graph_solver/environment_design.md`'s own scenarios used (`repair_packages_lite` as the trivial linear case before `pr_merge_lite`'s real fan-in) — except this graph skips straight to having one AND-join, since the linear case (no fan-out at all) is exactly what step 1's maze corridor already proved.

## Belief state: the topological order

No search is needed to compute it — per `environment_design.md`, an AND-only DAG has no alternative routes to choose between, so "the plan" is just a topological order over the graph, computed once, ties broken by node id (the same tie-break `TopologicalExecutor` already uses for its frontier):

```python
order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
```

Reasoning: `ready_nodes({})` returns only `pre-commit` (nothing else has its dependency satisfied yet). Once satisfied, `ready_nodes({"pre-commit"})` returns `["lint", "unit-tests"]` — both become ready simultaneously; sorted alphabetically, `lint` before `unit-tests`. Once both are satisfied, `merge` becomes ready, then `deploy`.

## Repair injection

Two nodes, mirroring `maintenance_lite`'s "two injections, not one, not many" choice — enough to show repair happening more than once without individual before/after transitions blurring together:

```python
env.inject_repairs(["lint", "deploy"], order)
```

- **`lint`** — one parent of the AND-join, not the whole join. Demonstrates that a fan-in node's readiness genuinely depends on *both* parents individually resolving, not on the join node itself being checked.
- **`deploy`** — the final node. Demonstrates a repair at the very end of the walk, mirroring `maintenance_lite`'s own choice not to only exercise repair mid-walk.

Deliberately not `merge` itself or `unit-tests`: one clean parent-of-a-join repair and one clean final-node repair is enough to prove the mechanism works identically to step 1's, on a graph shape step 1 couldn't represent at all. A third or fourth injection wouldn't demonstrate anything new about fan-out specifically.

## What this scenario is for

- **Smoke test** that `PathGraphEnvironment`'s `requires`-validation, `ready_nodes()`, `get_node_state()`/`inject_repairs()`/`repair_node()` all compose correctly on a graph with a real AND-join, not just a linear chain.
- **The animation source** for this step's experiment doc, once built.
- **A deterministic regression case**: the topology and the injected nodes are fixed, not seeded/random — a test can assert `result.repairs_performed == ["lint", "deploy"]` (in walk order) directly.

## Not decided

- Whether a second scenario is worth adding once this one is proven — e.g. a graph where an AND-join's *second* parent (not the first-in-order one) is the one that needs repair, to show the join still waits correctly regardless of which parent was walked first. Not needed for this first cut.
