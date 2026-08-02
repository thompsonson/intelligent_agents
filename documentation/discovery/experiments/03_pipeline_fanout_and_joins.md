# Experiment 3: `pipeline_fanout_lite` — AND-Joins Force the Right Order

**Run this yourself:** `discovery/tests/` reproduces every behavior in this experiment (`test_environment.py`, `test_discovery_agent.py`, `test_scenarios.py`, `test_discovery_view.py`, 54 tests total). Animation: [`pipeline_fanout_and_joins.gif`](../../../discovery/animations/pipeline_fanout_and_joins.gif).

## What this experiment demonstrates

Experiment 2's own walk is the bug this step exists to fix: `deploy` gets sensed at move 3, three moves before `unit-tests`/`integration-tests` are ever touched — `merge-gate` treated every node as immediately actionable the moment it was sensed. `and-joins/algorithm_fit.md` predicted, worked by hand and then verified by direct simulation after an earlier hand-tracing slip, exactly what happens once `merge-gate.requires = (lint, integration-tests)` and `DiscoveryAgent` actually respects it: 14 moves, 6 senses, `deploy` reached last. This experiment is that prediction, run for real.

## The walk, confirmed

```
result.path == [
    "commit", "lint", "merge-gate", "lint", "commit",
    "unit-tests", "integration-tests", "unit-tests", "commit",
    "lint", "merge-gate", "deploy", "merge-gate", "lint", "commit",
]
result.nodes_sensed == 6
result.total_cost == 14
result.blocked_nodes == []
result.goal_reached == True
```

Matches `algorithm_fit.md`'s worked trace exactly, including the corrected phase-2 hop count from the PR review (`deploy`'s immediate parent on the stack is `merge-gate`, not `lint` — a genuine transcription bug in the design doc, not in the code that implements it).

## `merge-gate`: sensed once, blocked, then cleared on a second visit

The single new fact this environment can now show that no earlier GIF could: a node that's fully known — its `notifies`, its `requires`, all of it — and still can't be acted on, because *it* isn't the problem, something it depends on hasn't happened yet. `merge-gate` is `visited` at move 3 (`sense_edges('merge-gate') → ('deploy',), requires ('lint', 'integration-tests')`) but stays `blocked` — rendered gold, distinct from both the grey "known" and green "cleared" states — until move 11, when the readiness sweep resumes there and finds both requirements satisfied. The caption at that exact frame says so directly: `'merge-gate' requires satisfied - cleared`.

## What to watch for in the GIF

Fifteen frames — one per `path` position:

- **Frames 0–2**: identical in shape to experiment 2's opening — `commit → lint → merge-gate` — except `merge-gate` renders **gold**, not green, the moment it's sensed. Its caption spells out why: `requires ('lint', 'integration-tests')`, and `integration-tests` isn't even on the board yet.
- **Frames 3–4**: backtrack `merge-gate → lint → commit`. Nothing new revealed; `merge-gate` stays gold throughout — visited, still blocked.
- **Frames 5–8**: the `unit-tests` branch, exactly as experiment 2 walked it — `unit-tests → integration-tests`, both turning green (cleared, `requires=()`), then backtracking out through `unit-tests` and `commit`.
- **Frames 9–10**: the readiness sweep's replayed route, `commit → lint → merge-gate` again — `lint` is already green (nothing to reveal), and at `merge-gate` the caption changes character entirely: not a sense, not a plain backtrack, but `'merge-gate' requires satisfied - cleared`. This is the frame the whole step is built around.
- **Frame 11**: `merge-gate → deploy`, `deploy` sensed for the first time — dark green, the goal, reached last rather than third.
- **Frames 12–14**: unwind all the way back to `commit` — `deploy → merge-gate → lint → commit` — nothing left blocked, nothing left to explore.

## What this experiment validates that the design docs alone could not

- **The readiness sweep's replayed route is exactly as cheap as the design claimed.** `nodes_sensed` stays at 6 through the entire second visit to `lint`/`merge-gate` — replaying a known route really does cost only move count, not a second round of sensing.
- **The three-state rendering (known/blocked/cleared/goal) reads correctly, and specifically doesn't lie about `merge-gate` being "done" before it is.** `test_blocked_node_never_appears_cleared_before_its_requires_do` asserts this directly against every frame, not just the ones this write-up shows.
- **Every prior scenario's behavior is provably unchanged.** All of experiment 1's and experiment 2's tests still pass unmodified against the same `DiscoveryAgent.walk()` this step rewrote — `requires=()` clears instantly for every node in those scenarios, so the new gating logic and readiness sweep are structurally present but never actually trigger.
- **The reachability-violation case isn't just a claim in `algorithm_fit.md`.** `build_pipeline_fanout_lite_with_orphan_requirement()` (adding `release-notes`, required but never notified by anyone) produces `blocked_nodes == ["merge-gate"]`, `goal_reached is False`, `deploy` never sensed — the exact numbers the design doc predicted, now backed by a real, assertable test rather than a hand trace.

## Related documents

- [`../and-joins/algorithm_fit.md`](../and-joins/algorithm_fit.md) — the readiness-sweep algorithm, the non-termination bug the naive extension hits, and the full worked trace this experiment matches move for move.
- [`../and-joins/environment_design.md`](../and-joins/environment_design.md) — `requires`, the three-state model, and why the reachability constraint is load-bearing.
- [`../and-joins/scenario.md`](../and-joins/scenario.md) — why `(lint, integration-tests)` specifically, and the shortcut-edge case this run also exercises (`unit-tests → merge-gate` directly, gated exactly the same as arriving via `lint`).
- [`02_pipeline_fanout_backtracking.md`](02_pipeline_fanout_backtracking.md) — step 2's run on the identical topology, minus gating; the direct contrast this experiment is built to make legible.
