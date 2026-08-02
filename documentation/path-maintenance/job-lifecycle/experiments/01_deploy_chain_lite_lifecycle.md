# Experiment 1: `deploy_chain_lite` with a Lifecycle — Waiting, Not Just Sensing

**Run this yourself:** `path_maintenance/tests/` reproduces every behavior in this experiment (`test_job_environment.py`, `test_job_maintenance.py`, `test_job_graph_view.py`, plus `test_environment.py`/`test_path_maintenance.py`/`test_scenarios.py`/`test_graph_view.py` from step 2, 61 tests total). Animation: [`deploy_chain_lite_lifecycle.gif`](../../../../path_maintenance/animations/deploy_chain_lite_lifecycle.gif).

## What this experiment demonstrates

`environment_design.md` specified a `PENDING → IN_PROGRESS → SUCCEEDED/FAILED` lifecycle on top of step 2's DAG, with `PathMaintenanceAgent`'s `walk()` waiting through unresolved states instead of sensing once. `algorithm_fit.md` predicted the exact sequence of senses and the exact GIF frames on the same `deploy_chain_lite` graph, richer nodes. This experiment is that prediction, run for real — and it caught a real bug the design docs didn't anticipate, corrected before this writeup, not smoothed over.

## The scenario

Same 5-node graph as step 2, each node gaining `ticks_to_resolve`/`resolves_to`:

```python
nodes = {
    "pre-commit": JobNode(id="pre-commit"),
    "lint": JobNode(id="lint", requires=("pre-commit",), ticks_to_resolve=2),
    "unit-tests": JobNode(id="unit-tests", requires=("pre-commit",)),
    "merge": JobNode(id="merge", requires=("lint", "unit-tests")),
    "deploy": JobNode(id="deploy", requires=("merge",), ticks_to_resolve=1, resolves_to=JobState.FAILED),
}
```

## A real bug, caught by the first test run

`scenario.md`'s hand-computed walkthrough assumed each node's tick clock only matters once the agent reaches it. The first implementation of `advance_jobs()` ticked *every* unresolved node in the whole graph on each call — which meant `deploy`'s clock was already advancing during `lint`'s wait loop, before `deploy`'s own prerequisite (`merge`) had even resolved. `test_matches_scenario_md_totals` caught it immediately: `deploy` resolved in 1 sense instead of the predicted 2.

Fixed by gating `advance_jobs()` on `ready_nodes(satisfied)` — the same AND-gating frontier `PathGraphEnvironment` already uses — so only nodes whose prerequisites are actually satisfied advance. Realistic, too: a Kubernetes deploy can't be "in progress" before the CI merge that triggers it. `environment_design.md` and `scenario.md` were updated to match; no other numbers in either doc needed to change, since the corrected behavior is exactly what `scenario.md` had assumed all along.

A second, smaller issue surfaced the same way: `repair_node()`'s internal validation called the public `get_job_state()`, which meant instrumenting `get_job_state()` for the GIF's event recording double-counted every repair as an extra sense. Fixed by giving `JobGraphEnvironment` a private `_resolve_state()` that both the public sensor and `repair_node()`'s internal check use — `repair_node()` no longer goes through the instrumentable path at all.

## The walk, confirmed

```
('arrive', 'lint', PENDING)
('advance',)
('arrive', 'lint', IN_PROGRESS)
('advance',)
('arrive', 'lint', SUCCEEDED)
('arrive', 'unit-tests', SUCCEEDED)
('arrive', 'merge', SUCCEEDED)
('arrive', 'deploy', PENDING)
('advance',)
('arrive', 'deploy', FAILED)
('repair', 'deploy')
```

`result.repairs_performed == ["deploy"]`, `result.senses_performed == {"lint": 3, "unit-tests": 1, "merge": 1, "deploy": 2}` — exactly `scenario.md`'s hand-computed totals, now that the bug is fixed. 11 events for 4 sensed nodes: 7 senses, 3 `advance_jobs()` calls, 1 repair.

## What to watch for in the GIF

Twelve frames, matching `algorithm_fit.md`'s prediction:

- **Frame 0**: `pre-commit` already dark green with the agent's star, exactly like step 2 — the start, not something arrived at.
- **Frames 1-4**: `lint` visibly cycles through three colors — white (`pending`) → gold (`in_progress`) → green (`succeeded`) — the first node in this whole arc whose color changes more than once before settling. Frame 2's `advance_jobs()` frame shows no color change (ticks are invisible until the next sense reveals them) but gets its own caption, distinguishing "time passing" from "checking status."
- **Frame 5**: `unit-tests` resolves in a single frame, no intermediate color — instant, sitting right next to `lint`'s multi-frame journey, the same side-by-side contrast `deploy_chain_lite`'s step-2 experiment established, now doing double duty for lifecycle timing as well as outcome.
- **Frame 6**: `merge` turns green in one frame too, only once both parents (`lint`, now green; `unit-tests`, already green) have resolved — the AND-join proof from step 2, unchanged by adding a lifecycle.
- **Frames 7-11**: `deploy` shows white (`pending`) before turning red — a node sensed and *not yet known to need repair*, a genuinely new visual moment nothing in steps 1-2 could produce, since their `NEEDS_REPAIR` was always immediately visible on first sense — then dark green after `repair_node()`.

## What this experiment validates that the design docs alone could not

- **The `advance_jobs()` readiness-gating bug is real, not hypothetical** — caught by a single assertion in the first test run, not discovered by inspection. Recorded in `environment_design.md` rather than silently fixed.
- **`repair_node()`'s internal validation can leak into instrumented event counts** if it goes through the same public method being instrumented — a subtlety neither step 1 nor step 2 exposed, since their `repair_cell()`/`repair_node()` already happened to check private state directly rather than calling their own public sensor.
- **The color-depth convention (`future → pending → in_progress → clear`, `pending → needs_repair → repaired`) reads correctly in real rendered output**, not just as a plan — `lint`'s three-frame journey is the first real proof that "one hue deepening" communicates progress the way `algorithm_fit.md` intended.
- **`senses_performed` gives step 3 something steps 1-2 never had**: a number, not just an event, quantifying how much waiting each node actually took — `lint` (3) vs. `unit-tests`/`merge` (1 each) is now a real, assertable fact about the run, not just a visual impression from the GIF.

## Related documents

- [`../environment_design.md`](../environment_design.md) — the design this experiment implements, including both corrections.
- [`../scenario.md`](../scenario.md) — the tick numbers and hand-computed walkthrough this run confirms.
- [`../algorithm_fit.md`](../algorithm_fit.md) — the GIF predictions this experiment matches frame for frame.
- [`../../graph-topology/experiments/01_deploy_chain_lite.md`](../../graph-topology/experiments/01_deploy_chain_lite.md) — step 2's equivalent, same graph, no lifecycle.
