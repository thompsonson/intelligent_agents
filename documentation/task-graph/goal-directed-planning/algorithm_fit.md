# Algorithm Fit: `PlanningExecutor`

## Purpose

`environment_design.md` specifies the recursive `ensure()` algorithm; `scenario.md` specifies the two graphs. This document walks through what each existing executor does differently on those same two graphs, so the contrast is concrete rather than asserted.

## Scenario A (`pr_merge_lite`, released already true): `GuardFirstExecutor` vs. `PlanningExecutor`

Both executors reach the same answer (`success=True`, `released` satisfied via a free check) by radically different routes:

| | `GuardFirstExecutor` | `PlanningExecutor` |
|---|---|---|
| Direction of travel | Forward, from the frontier (`ci-check` first) | Backward, from `goal` (`released` first) |
| Nodes ever checked or attempted | All 8 | 1 (`released`) |
| Paid repair attempts | 7 (every node except `released`) | 0 |
| Why | Walk-as-you-go can only check the node it's currently standing on — it has no way to know `released` is already true without first walking everything between here and there | `_ensure("released")` calls `check_invariant("released")` *before* ever reading `released.requires` — the chain upstream is never a parameter to `_ensure` at all |

This is the sharper version of the point `guard-first/algorithm_fit.md` flagged but didn't need for its own scenario: not "the free check is cheaper than a paid attempt" (true for both executors, on the one node that has it) but "an entire upstream chain can be skipped in one check, not walked and cheaply-checked seven times." That's a capability `GuardFirstExecutor` structurally cannot have, no matter how many nodes get a nonzero `invariant_pass_probability` — it only ever checks the node in front of it.

## Scenario B (`pr_merge_with_variants`): `AOStarExecutor` vs. `PlanningExecutor`

| | `AOStarExecutor` | `PlanningExecutor` |
|---|---|---|
| Visits `check-disk` (true orphan) | **Yes** — it's ready from the start (no `requires`), and `AOStarExecutor` walks the forward frontier same as `TopologicalExecutor` | **No** — never a parameter to `_ensure`; nothing on the path back from `released` ever names it |
| Prunes losing OR-siblings once `actions-ready` is satisfied | Yes — `_is_prunable` | Yes — `_ensure_group`'s short-circuit, same effect, top-down instead of forward-frontier |
| `not_needed` after a run | `{losing variants}` (`check-disk` is separately `satisfied`, since it was attempted and passed) | `{losing variants}` (`check-disk` doesn't appear in *any* result set — never `satisfied`, `fatal`, `unreachable`, or `not_needed`, just never visited) |

The OR-group row is identical between the two — this is the "one algorithm, not two" point from `environment_design.md` made concrete: `PlanningExecutor` didn't need new pruning logic for groups, `_ensure_group`'s short-circuit falls out of the same recursion that gives it goal-directed scope. The orphan row is where they genuinely differ, and it's the same difference Scenario A showed: `AOStarExecutor` still has no way to know `check-disk` doesn't matter without attempting it first.

## `TopologicalExecutor` and `DStarLiteExecutor` — unaffected, correctly

Neither changes on either scenario. `TopologicalExecutor` remains the naive baseline it's always been — walks everything, prunes nothing, skips nothing. `DStarLiteExecutor`'s sensing loop answers a different question (has something changed since I gave up on it) than either scenario here is testing (is something already true, or does it matter to the goal at all) — combining sense-then-plan with D* Lite's incremental re-sensing is flagged as open in `environment_design.md`'s "Not decided" section, not attempted here.

## What to watch for in the GIFs

- [`planning_short_circuit.gif`](../../../task_graph_solver/animations/planning_short_circuit.gif) — **two frames, total.** Frame 0: the whole graph white (nothing touched yet). Frame 1: only `released` turns cyan, captioned `check_invariant(released) → true`. Nothing else in the graph ever changes color, because nothing else is ever visited. Compare directly against [`guard_first_pr_merge_lite.gif`](../../../task_graph_solver/animations/guard_first_pr_merge_lite.gif)'s sixteen frames on the identical scenario.
- [`planning_goal_directed_scope.gif`](../../../task_graph_solver/animations/planning_goal_directed_scope.gif) — `check-disk` and two of the three `apply-actions-*` variants stay white for the entire animation. One honest cosmetic note: `actions-ready` (the OR-group itself) also renders as a plain white circle, indistinguishable from a not-yet-touched node — it's never attempted directly (no Guard exists for a group), so it has no other status to show. Distinguishing "a group construct, never directly attemptable by design" from "a plain node nobody got to yet" visually is a real gap, not modeled here; the surrounding prose (and `not_needed`/orphan absence from every result set) is the honest source of truth, not the render alone.
