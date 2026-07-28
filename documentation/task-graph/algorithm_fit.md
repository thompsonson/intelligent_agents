# Algorithm Fit: Which Algorithm, Which Scenario

## Purpose

`environment_design.md` specifies the environment; `scenarios.md` specifies three concrete graphs of increasing structural complexity. This document maps the algorithms already designed elsewhere in this repo onto the scenario they actually fit, and — just as importantly — states where each one stops applying. The task graph environment exists specifically because the maze couldn't produce an AND-join without artificial construction; this document is where that distinction has to be made precise rather than gestured at.

## The mapping

| Algorithm | Fits | Doesn't fit | Why |
|---|---|---|---|
| **Topological execution** (plain, no search) | All three scenarios | — | The baseline: attempt whatever's `ready_nodes()` returns, in any valid order, no heuristic, no learning. Equivalent role to running BFS on the maze before trying A* — proves the environment and executor loop work before any algorithm-specific behavior is layered on |
| **AO\*** (AND-OR graph search) | `pr_merge_lite` (has two real AND-joins: `merged`, `released`) | `disk_check_lite`, `repair_packages_lite` (no AND-joins — AO* degenerates to plain search on these, correct but pointless) | The only algorithm in this repo's design work built for AND-composition. `merged`'s two-way join is the right first target — small enough to hand-verify, structurally identical to `released`'s three-way join |
| **D\* Lite / LPA\*** | `disk_check_lite`, `repair_packages_lite` (both are single linear chains — the degenerate case where AND-of-one and OR-of-one coincide) | `pr_merge_lite`, specifically its two AND-joins | `documentation/d-star/beyond_the_maze.md` already found D* Lite's heuristic-guidance advantage is largely cosmetic over a DAG (no natural admissible heuristic, same problem here as over a CI/CD graph) — its incremental-repair mechanism is still real and demonstrable if a scenario's `break_task`/`fix_task` Driver hook is exercised on `repair_packages_lite`. Do **not** force D* Lite over `pr_merge_lite` as a whole; it has no way to represent "wait for all three deploys," and silently ignoring two of the three `requires` edges to make it fit would misrepresent what the algorithm actually does |
| **LRTA\* / RTDP** | `repair_packages_lite` (cleanest — isolates `retry_flavor="repair"` on one node), `pr_merge_lite`'s `apply-actions` node in isolation | Learning a blended `h(s)` across nodes of different `retry_flavor` (see `environment_design.md`'s per-flavor data point) | This is the environment purpose-built to make the `documentation/lrta/beyond_the_maze.md` finding concrete: retries only mean "learnable cost" for `retry_flavor="repair"` nodes. `repair_packages_lite`'s `repair` node is the single cleanest example of that signal anywhere in this repo, real or toy — one node, one flavor, no fan-in to confuse the picture |

## Combinations worth naming, not building yet

- **AO\* for the graph structure, LRTA\* for the leaf-node cost estimates.** `pr_merge_lite`'s `apply-actions` node sits underneath an AND-join (`merged`) — AO* would need *some* cost estimate for that subtree to make its own choice, and LRTA*-style learning is exactly what could supply it, the same way `documentation/lrta/beyond_the_maze.md` proposed learning `h(apply-action-list)` in the real system. This is the natural "both algorithms at once" demo, but it's a second-pass combination, not a v1 requirement — each algorithm should be demonstrated correctly in isolation on a scenario it actually fits before combining them.
- **D\* Lite's repair mechanism on `repair_packages_lite` with a Driver-triggered break.** Small enough to be the direct toy-scale echo of the maze's bridge scenario, just on a 2-node AND-chain instead of a grid — worth building as a sanity check that the environment's `break_task`/`fix_task` hook (currently just a signature in `environment_design.md`) actually behaves the way the maze's `break_edge`/`fix_edge` does.

## Explicit non-goals

- No algorithm here is meant to solve `pr_merge_lite` end to end by itself. The honest state of the art, per this table, is: topological execution to prove the graph runs, AO* for the two AND-joins, LRTA* for `apply-actions`' cost specifically. A single unified "here's the algorithm for the whole thing" is not what this repo's design work supports, and claiming otherwise would repeat the overclaiming pattern already corrected once in the Atomic Action Pair critique (`documentation/lrta/beyond_the_maze.md`'s "Purpose" section).
- This document doesn't introduce any new algorithm beyond what's already tracked in `documentation/d-star/related_algorithms.md` (AO* was added there when the fan-in problem was first found). It exists to route existing designs to the right scenario, not to expand the algorithm backlog further.

## Suggested build order

1. `disk_check_lite` + topological execution — validates the environment and executor loop with zero algorithmic complexity in the way.
2. `repair_packages_lite` + LRTA*/RTDP — the cleanest demonstration of the "retries are learnable cost" story from `documentation/lrta/beyond_the_maze.md`, now actually runnable instead of only described.
3. `repair_packages_lite` + D* Lite (with a Driver break/fix) — the toy-scale echo of the maze bridge, confirms the environment's dynamic hook works before trusting it in a bigger graph.
4. `pr_merge_lite`'s `merged` join + AO* — smallest real AND-join, hand-verifiable.
5. `pr_merge_lite`'s `released` join + AO* — the three-way version, the actual motivating case from the real `atomicguard` stress test.
6. (Later, optional) AO* + LRTA* combined on `pr_merge_lite`'s `apply-actions` subtree, per the "combinations worth naming" section above.

## Resolved (were "Not decided")

- **Visualization**: `task_graph_solver/visualization/graph_view.py` and `learning_curve.py` — a fresh module, not a reuse of `maze_solver`'s grid-based `_plot_maze` machinery, which genuinely doesn't fit AND-join nodes. DAG nodes are drawn as circles or squares (AND-joins) via `networkx`, animated frame-by-frame via `imageio` the same way `maze_solver`'s dashboards do, plus a separate line-chart renderer for LRTA*'s per-trial convergence (a fundamentally different kind of output than a DAG state).
- **Build order as a task list**: steps 1–6 above are all implemented (Phases 1–7 in commit history, `git log --oneline task_graph_solver/`). Worked, grounded walkthroughs of three of them exist in [`documentation/task-graph/experiments/`](experiments/) — see `01_ao_star_pr_merge_lite.md` (step 4/5 above), `02_d_star_lite_pr_merge_lite.md` (step 3, extended to `pr_merge_lite`), and `03_lrta_star_convergence.md` (step 2).

## Not decided

- Whether AO* + LRTA* combined (step 6) is worth building, given the "broader direction" discussion it needs first (seeding `AOStarExecutor`'s node selection from a prior `LRTAStarLearner.h_table` only helps fail-fast ordering among ready siblings, never choosing to skip a required node — there's no OR-escape hatch in an AND-only graph).
