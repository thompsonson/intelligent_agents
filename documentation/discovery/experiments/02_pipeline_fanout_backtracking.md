# Experiment 2: `pipeline_fanout_lite` — Backtracking Reaches Everything

**Run this yourself:** `discovery/tests/` reproduces every behavior in this experiment (`test_discovery_agent.py`, `test_scenarios.py`, `test_discovery_view.py`). Animation: [`pipeline_fanout_backtracking.gif`](../../../discovery/animations/pipeline_fanout_backtracking.gif).

## What this experiment demonstrates

Experiment 1 left `unit-tests`/`integration-tests` permanently stranded — known, never visited — because step 1's `DiscoveryAgent` had no way back to a skipped branch. `backtracking-exploration/algorithm_fit.md` predicted, hand-worked over a 17-row trace, exactly what happens once the agent can retrace its own path: 10 moves, 6 senses, every node visited. This experiment is that prediction, run for real, on the identical `pipeline_fanout_lite` topology — no new scenario needed.

## The walk, confirmed

```
result.path == [
    "commit", "lint", "merge-gate", "deploy",
    "merge-gate", "lint", "commit",
    "unit-tests", "integration-tests", "unit-tests", "commit",
]
result.nodes_sensed == 6
result.goal_reached == True
result.total_cost == 10
```

Matches `algorithm_fit.md`'s worked table exactly, including the two details that table called out by name: `merge-gate` appears twice in `path` (reached from both branches) but is only ever *sensed* once — the second arrival finds nothing new and immediately backtracks, so `nodes_sensed` stays at 6 rather than climbing to 7 or 8. And `total_cost == 10` matches the move count exactly, since `pipeline_fanout_lite` uses the environment's flat `get_move_cost() == 1` — confirming the doc's claim that every backtrack step is a real, counted move, not a free rewind.

## `unit-tests` and `integration-tests`: no longer stranded

The single change a viewer can see directly: the two nodes experiment 1's GIF left grey forever are green by the final frame here. Nothing about the environment changed to make this possible — `DiscoveryNode`, `DiscoveryEnvironment`, `sense_edges()` are byte-for-byte what experiment 1 used. The only thing that changed is that `DiscoveryAgent` is now allowed to walk back to `commit` once the `lint` branch is exhausted, and does.

## What to watch for in the GIF

Eleven frames — one per `path` position, backtracks included:

- **Frames 0–3**: identical to experiment 1's GIF — `commit → lint → merge-gate → deploy`, `unit-tests` sitting grey the whole time. Up to this point the two runs are indistinguishable.
- **Frame 3** (`sense_edges('deploy')`): `deploy` turns dark green, the goal — but unlike experiment 1, the walk doesn't stop here.
- **Frames 4–6** (`backtrack to 'merge-gate'` → `backtrack to 'lint'` → `backtrack to 'commit'`): no new colors — every node these frames land on is already green — but the agent marker visibly retraces its steps back down the `lint` branch. This is the frame range with no equivalent anywhere else in this repo: revisiting an already-fully-known node on purpose.
- **Frame 7** (`sense_edges('unit-tests')`): `unit-tests` finally turns green; `integration-tests` appears for the first time, grey.
- **Frame 8** (`sense_edges('integration-tests')`): `integration-tests` turns green. Its own `notifies` (`merge-gate`) reveals nothing new — `merge-gate` was already known from the other branch.
- **Frames 9–10** (`backtrack to 'unit-tests'` → `backtrack to 'commit'`): the walk unwinds all the way back to the start with nothing left to reach, and stops there — not at `deploy`, and not because anything failed.

## What this experiment validates that the design docs alone could not

- **The `2×|edges|` bound isn't just asymptotic reasoning — it holds on this exact graph.** 10 moves against 6 edges, comfortably under 12. `algorithm_fit.md`'s literature discussion argued this in the abstract; this run is the concrete instance.
- **Caching genuinely prevents re-sensing, not just in theory.** `nodes_sensed == 6` rather than `11` (one per path position) confirms `DiscoveryAgent` really does answer a revisit from its own memory of a node's `notifies`, not by calling `sense_edges()` again — the same "no arrival check needed because nothing enforces it" trust the environment already placed in the agent in step 1, now load-bearing for a second, independent reason (avoiding redundant sensing, not just avoiding an unneeded permission check).
- **The visualization's event model had to change to show this, and now shows something no earlier GIF in this repo could**: an agent revisiting a node it already fully understands, for no reason other than to get somewhere new. `_walk_frames()` replays `result.path` directly rather than an instrumented sense-call trace (see `discovery_view.py`'s module docstring) specifically because backtracking decouples "how many times the agent moved" from "how many times it learned something new" — the first GIF's one-frame-per-sense approach could never have rendered frames 4–6 above at all.

## Related documents

- [`../backtracking-exploration/algorithm_fit.md`](../backtracking-exploration/algorithm_fit.md) — the traversal policy, the DFS-vs-BFS-vs-learned comparison, and the 17-row hand-worked trace this experiment matches move for move.
- [`01_pipeline_fanout_lite.md`](01_pipeline_fanout_lite.md) — step 1's run on the identical topology; the direct contrast this experiment is built to make legible.
- [`../environment_design.md`](../environment_design.md) / [`../scenario.md`](../scenario.md) — the unchanged primitives and topology this experiment reuses rather than duplicates.
