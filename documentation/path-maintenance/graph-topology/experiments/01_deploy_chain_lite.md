# Experiment 1: `deploy_chain_lite` — Node Repair on a Fan-Out DAG

**Run this yourself:** `path_maintenance/tests/` reproduces every behavior in this experiment (`test_environment.py`, `test_path_maintenance.py`, `test_scenarios.py`, `test_graph_view.py`, 32 tests total). Animation: [`deploy_chain_lite.gif`](../../../../path_maintenance/animations/deploy_chain_lite.gif).

## What this experiment demonstrates

`environment_design.md` specified exactly one change from step 1: the environment becomes an AND-only DAG instead of a spatial grid, with node state staying the plain `OPEN`/`NEEDS_REPAIR` step 1 already built. `algorithm_fit.md` predicted, node by node, what `PathMaintenanceAgent` would do on `deploy_chain_lite` — this experiment is that prediction, run for real, matching it exactly.

## The scenario

```python
nodes = build_deploy_chain_lite()   # pre-commit -> lint, unit-tests -> merge -> deploy
env = PathGraphEnvironment(nodes)
order = deploy_chain_lite_order()   # ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
env.inject_repairs(["lint", "deploy"], order)
```

`test_scenarios.py::test_hand_written_order_matches_computed_topological_order` confirms `scenario.md`'s hand-written order is actually correct — computed independently via `ready_nodes()`, not just asserted.

## The walk, confirmed

```
('arrive', 'lint', NEEDS_REPAIR)
('repair', 'lint')
('arrive', 'unit-tests', OPEN)
('arrive', 'merge', OPEN)
('arrive', 'deploy', NEEDS_REPAIR)
('repair', 'deploy')
```

`result.repairs_performed == ["lint", "deploy"]`, `result.success is True` — matching `algorithm_fit.md`'s predicted table exactly, including that `pre-commit` (`order[0]`) never appears as an `arrive` event at all: the agent starts there rather than arriving at it, the same convention step 1's maze start cell established. Six events for four sensed nodes (`lint`, `unit-tests`, `merge`, `deploy`) — two repairs, two clean arrivals.

## What to watch for in the GIF

Seven frames, matching `algorithm_fit.md`'s prediction frame for frame:

- **Frame 0**: `pre-commit` already dark-green-bordered with the agent's star on it — not "future" — since it's the start, already implicitly passed. `lint`/`unit-tests` sit side by side in the same generation (confirming `_layered_layout`'s topological-generation grouping works correctly on a real fan-out), `merge` drawn as a **square**, `deploy` at the far right.
- **Frame 1** (`arrive 'lint' → needs_repair`): `lint` turns red.
- **Frame 2** (`repair_node('lint')`): red → dark green.
- **Frame 3** (`arrive 'unit-tests' → open`): turns green cleanly — no repair — sitting right next to `lint`'s dark green, the contrast between "needed repair" and "didn't" visible in one frame without reading a caption.
- **Frame 4** (`arrive 'merge' → open`): the AND-join turns green **only now** — after both `lint` and `unit-tests` have resolved, not before. This is the one thing this scenario exists to prove that step 1's maze corridor structurally could not: a node's readiness genuinely depending on more than one predecessor, both individually confirmed rather than assumed.
- **Frame 5** (`arrive 'deploy' → needs_repair`) → **frame 6** (`repair_node('deploy')`): the second red-then-dark-green pair, at the very end of the walk.

## What this experiment validates that the design docs alone could not

- **The AND-join genuinely gates on both parents, in real rendered output** — `test_and_join_not_ready_until_both_parents_satisfied`/`test_and_join_ready_once_both_parents_satisfied` prove it at the environment level; the GIF's frame 4 is the same fact, visible.
- **`_layered_layout` (rebuilt independently, not imported from `task_graph_solver`) correctly places two same-generation nodes side by side** on a graph with a real fan-out, not just the trivial one-node-per-generation case.
- **The "exactly one change from step 1" claim holds under an actual run**, not just in the design doc's prose: `agents/path_maintenance.py`'s `walk()` is the same method, unmodified in logic, differing only in the type annotation of `order`'s elements.
- **The event-driven visualization pattern (`record_walk`/`animate_walk`) ports cleanly a third time** — first `task_graph_solver`'s DAG, then `maze_solver`'s grid, now `path_maintenance`'s DAG again, this time genuinely independent code (no import from either sibling package) rather than a shared module.

## Related documents

- [`../environment_design.md`](../environment_design.md) — the design this experiment implements.
- [`../scenario.md`](../scenario.md) — `deploy_chain_lite` in full, including why these two nodes at these two positions.
- [`../algorithm_fit.md`](../algorithm_fit.md) — the walkthrough and GIF predictions this experiment confirms.
- [`../../experiments/01_maintenance_lite.md`](../../experiments/01_maintenance_lite.md) — step 1's equivalent experiment, on the maze.
