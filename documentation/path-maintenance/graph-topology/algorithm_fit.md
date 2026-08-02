# Algorithm Fit: Graph Topology

## Purpose

`environment_design.md` specifies `GraphNode`/`PathGraphEnvironment`; `scenario.md` specifies `deploy_chain_lite`. This document is short by design, for the same reason `documentation/task-graph/guard-first/algorithm_fit.md` was: only one agent is being introduced here, and no algorithm choice is being made. It still earns its place by doing three things worth pinning down before any code exists: confirming the one new capability against the concrete scenario, restating why nothing already in this repo is the right fit (now with real node names instead of the abstract version in `environment_design.md`), and predicting what the visualization needs to show.

## `PathMaintenanceAgent` — the one capability, walked through on `deploy_chain_lite`

Unmodified from step 1 in every way except the domain type of one element (`Tuple[int, int]` → `str`). Given `order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]` and `inject_repairs(["lint", "deploy"], order)`:

| Step | Node | Sensed state | Action |
|---|---|---|---|
| 1 | `pre-commit` | `OPEN` | move on |
| 2 | `lint` | `NEEDS_REPAIR` | `repair_node("lint")`, then move on |
| 3 | `unit-tests` | `OPEN` | move on |
| 4 | `merge` | `OPEN` | move on |
| 5 | `deploy` | `NEEDS_REPAIR` | `repair_node("deploy")`, then move on |

`result.repairs_performed == ["lint", "deploy"]`, `result.success is True`. Note what `walk()` does *not* do at step 4: it never checks whether `merge`'s two parents are "genuinely" both resolved before treating `merge` as reachable — it doesn't need to, because `order` was already computed to respect `requires` (`merge` only appears after both `lint` and `unit-tests`). The AND-join is enforced once, when `order` is computed, not re-checked at every step — the same division of labor step 1 had between "A* computes a valid route" and "the agent just walks it."

## Why not `task_graph_solver`'s executors

Restated concretely, against this scenario, rather than in the abstract (`environment_design.md`'s "Reviewing `task_graph_solver`" section made the general case):

- **`TopologicalExecutor`** would call `env.attempt("lint")`, which returns an `AttemptOutcome` drawn from `pass_probability` and consumes retry budget. There is no `pass_probability` configured for `lint` here — repair is a certainty, not a draw. Forcing this scenario through `TopologicalExecutor` would mean inventing `pass_probability=1.0`/`rmax=1` for every node, which doesn't add anything, it just simulates determinism through a probability that never varies — noise around a fact that's already known.
- **`AOStarExecutor`** adds AND-composition *cost tracking* (which branch of an OR-group is cheaper) — but `deploy_chain_lite` has no OR-groups, only one AND-join, and there's no cost to optimize; `PathMaintenanceAgent` isn't choosing between alternatives at `merge`, it's just waiting for both parents.
- **`DStarLiteExecutor`**/**`GuardFirstExecutor`**/**`PlanningExecutor`** all solve a genuinely different question — incremental re-planning, free-check-before-repair, goal-directed backward search — none of which applies when the order is fixed and known before the walk starts.

## Why not step 1's `PathMaintenanceAgent`, unmodified, pointed at this graph

It can't be, structurally: step 1's `walk()` takes `path: List[Tuple[int, int]]` and calls `env.get_cell_state(cell)`/`env.repair_cell(cell)`, both keyed by grid coordinate. There's no coordinate for `merge` — the change here isn't behavioral, it's that the domain type every signature is written against has to generalize from a 2-tuple to a string id. Confirms `environment_design.md`'s claim that this is "exactly one change from step 1," visible concretely: every other line of `walk()`'s logic is identical.

## What the visualization needs to do differently

Worth flagging now, before any code: `maze_solver`'s `path_maintenance_view.py` draws an `imshow` grid — there is no grid here. The right model is `task_graph_solver/visualization/graph_view.py`'s approach instead: a `networkx` DiGraph, laid out left-to-right by topological generation (`_layered_layout`), nodes colored by state. `deploy_chain_lite` is a good test of that layout function specifically, since `lint`/`unit-tests` sit in the same generation (both depend only on `pre-commit`) and should render side by side, with `merge` visibly waiting on both.

### What to watch for in the GIF (predicted, not yet built)

Five nodes moving through the same color convention step 1 established (green = `OPEN`, red = `NEEDS_REPAIR`, dark green = repaired) plus the layered left-to-right structure `graph_view.py` already has:

- **Frame 0**: `pre-commit` alone at the far left, everything else unresolved.
- **`lint` turns red, then dark green** — the first repair, visibly on one of the two side-by-side nodes in the second generation, not the other.
- **`unit-tests` turns green cleanly** — no repair, sitting right next to `lint` in the layout, making the contrast between "needed repair" and "didn't" visible in one frame without a caption.
- **`merge` only turns green once both its parents have** — the AND-join's visual proof, the one thing this scenario exists to show that step 1's maze never could.
- **`deploy` turns red, then dark green** — the second repair, at the very end.

## Related documents

- [`../environment_design.md`](../environment_design.md) — step 1's design, unmodified by this step.
- [`documentation/task-graph/environment_design.md`](../../task-graph/environment_design.md) — where `requires`/`ready_nodes()`'s pattern comes from.
- [`documentation/task-graph/guard-first/algorithm_fit.md`](../../task-graph/guard-first/algorithm_fit.md) — the precedent for a short `algorithm_fit.md` when only one agent is introduced.
