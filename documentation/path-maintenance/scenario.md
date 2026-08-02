# Path Maintenance Scenario

## Purpose

`environment_design.md` specifies the primitives (`CellState`, `get_cell_state()`, `inject_repairs()`, `repair_cell()`, `PathMaintenanceAgent.walk()`). This document pins down one concrete, reproducible run built from those primitives — the actual "maze" this environment will be demonstrated on, mirroring `documentation/task-graph/scenario.md`'s role for its own environment.

Unlike `task_graph_solver`'s scenarios, this one isn't a hand-authored graph — `MazeEnvironment` generates its topology procedurally from `mazelib`'s `Sidewinder` algorithm. "The scenario" here is therefore the `Config` that makes generation reproducible, plus a rule for which path cells get injected as `NEEDS_REPAIR` — expressed relative to the path's length, not as hardcoded coordinates, so the rule still makes sense if the maze parameters ever change.

## Scenario: `maintenance_lite`

```python
config = Config(maze_size=5, maze_id=7, show_exploration=False)
```

With this seed, `AStarSearch(env).search(env.start, env.end)` produces a 17-cell belief path — a corridor with exactly one turn, small enough to read at a glance and to animate frame-by-frame without the GIF becoming unwieldy:

```
(1,1) (1,2) (1,3) (1,4) (1,5) (1,6) (1,7)              <- east leg (indices 0-6)
                                      (2,7)
                                      (3,7)
                                      (4,7)
                                      (5,7)
                                      (6,7)
                                      (7,7)
                                      (8,7)
                                      (9,7)
                                (9,8) (9,9)             <- south leg + short jog (indices 7-16)
```

Start `(1,1)` = index 0, goal `(9,9)` = index 16.

## Repair injection rule

Two cells, one on each leg, chosen as roughly the 1/3 and 2/3 points of the path (`round(len(path)/3)` and `round(2*len(path)/3)`), excluding index 0 (start — nothing to sense on a cell the agent begins on) and the final index (goal — repairing on arrival isn't more informative than repairing one step earlier):

| Index | Cell | Leg |
|---|---|---|
| 6 | `(1, 7)` | end of the east leg, just before the turn |
| 11 | `(6, 7)` | midway down the south leg |

```python
env.inject_repairs(cells=[path[6], path[11]], path=path)
```

Two injected cells, not one, so the walk demonstrates the agent repairing more than once and the GIF has more than a single interesting event — and not more than two, so each repair's before/after is still individually easy to follow rather than blurring into a pattern.

## What this scenario is for

- **Smoke test** that `inject_repairs()`'s path-only validation, `get_cell_state()`, and `repair_cell()` all compose correctly end to end.
- **The animation source** for the experiment doc and GIF referenced in `environment_design.md`'s pending work — `PathMaintenanceAgent(env, path).walk()` against this exact config and injection is the run `path_maintenance_view.animate_walk()` will render.
- **A deterministic regression case** for `maze_solver/tests/`: `maze_id=7` at `maze_size=5` always produces this exact 17-cell path (confirmed by hand — see the table above), so a test can assert on `result.repairs_performed == [path[6], path[11]]` without re-deriving indices at test time.

## Not decided

- Whether a second scenario is worth adding once the trivial case is proven out — e.g. a maze with a branch point close to an injected-repair cell, to make visually clear that the agent does *not* route around a `NEEDS_REPAIR` cell the way a re-planning agent would. Not needed for the first demonstration, since step 1 has no alternative routing behavior to contrast against yet — worth revisiting once/if a plan-repair step exists to compare it with.
