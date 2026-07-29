# Algorithm Fit: `release_pipeline`

## Purpose

`environment_design.md` specifies `RealCheckNode`/`RealCheckEnvironment`; `scenario.md` specifies the concrete graph and fixture states. This document walks through what each executor actually does when pointed at real `mypy`/`ruff`/`pytest`/`python -m build` calls instead of a simulated `pass_probability` - all four reused directly from `task_graph_solver.algorithms`, unmodified.

## `TopologicalExecutor` — pays for every real check, every time

Walks the ready frontier exactly as it always has: on `typing_broken`, it attempts `architecture-test`, `build-check`, and `lint` (all real, all PASS), then `type-check` (a real `mypy` failure - FATAL), then `unit-tests` (PASS). `release-ready`'s own command is never even attempted, since one of its five `requires` is fatal - it lands in `unreachable`, not `fatal`.

**Run this yourself:** `real_task_graph_solver/tests/test_release_pipeline.py::TestTopologicalExecutorRealChecks` reproduces this exact run for all four broken states. Animation: [`task_graph_solver/animations/real_guards_topological_typing_broken.gif`](../../../task_graph_solver/animations/real_guards_topological_typing_broken.gif).

## `AOStarExecutor` — real cost, for the first time

`h` composes exactly as `documentation/task-graph/experiments/01_ao_star_pr_merge_lite.md` describes (`own_attempts + max(h(child))`), except `own_attempts` is now a real, paid, deterministic subprocess call rather than a coin flip. Since every check here is a one-shot deterministic PASS/FATAL (no repair to retry toward), every leaf's `h` is exactly `1`, and `h["release-ready"] = 1 + max(h of the five children) = 2`.

The genuinely new thing this environment gives `AOStarExecutor` that no simulated scenario could: `env.time_spent(node_id)`, a real wall-clock measurement, populated alongside `h` rather than folded into it (`environment_design.md`'s "Resolved" note explains why it's kept separate). `mypy`'s cold-start overhead alone is real, measurable, and different in kind from `ruff`'s near-instant check - a distinction `h`'s attempt-count arithmetic can't see at all, but `time_spent` can.

**Run this yourself:** `TestAOStarExecutorRealCost::test_h_composes_from_real_retries_spent_and_time_spent_is_populated`.

## `DStarLiteExecutor` — real recovery, deliberately narrower than the goal

Break/fix sensing works against real checks exactly as it does against simulated ones: `env.break_task("type-check")` swaps the whole working tree to `typing_broken` (a real `mypy` failure on the next `attempt`); `env.fix_task("type-check")` swaps it back to `clean` (a real pass); `drain_changed_tasks()` senses the change and returns the node to consideration. `lint`, already satisfied before the break, is never re-attempted - real repair locality, not simulated.

**Why this test doesn't reach `release-ready`, and shouldn't yet:** `reset_to_state` swaps the *entire* working tree, so breaking and fixing `type-check` also wipes any `.status/*.ok` markers other checks had already written - not because those checks became unsatisfied, but because the reset mechanism can't touch only the one thing that changed. `DStarLiteExecutor`'s own `satisfied`/`fatal` bookkeeping is correct throughout (it never re-attempts a node it already believes is done) - but `release-ready`'s marker-based gate would, incorrectly, still report failure if the test tried to run all the way to it. So the test uses a smaller two-node subgraph (`type-check`, `lint`, no `release-ready`) instead - proving the real thing that's actually true (sensing and repair locality both work against real subprocess checks) without overclaiming recovery all the way to a goal this reset mechanism can't honestly support yet. A more surgical `reset_to_state` - touching only the files relevant to one manufactured state - would fix this properly; not attempted here, per `environment_design.md`'s note on the trade-off.

**Run this yourself:** `TestDStarLiteExecutorRealRecovery::test_recovers_from_a_break_on_an_independent_real_check`.

## `GuardFirstExecutor` — no meaningful demonstration here, as predicted

`environment_design.md` called this before any code was written: without a repair action, `check_invariant()` and `attempt()` run the identical subprocess and get the identical answer. There's nothing wrong with `GuardFirstExecutor` on this environment - it would work, and would cost exactly what `TopologicalExecutor` costs, since every check-then-maybe-attempt pair collapses into "run the same command twice in a row." Not every executor needs a demonstration on every environment; this is the one place in this repo's whole `task_graph_solver`/`real_task_graph_solver` work where that's true by construction, not by omission.

## `PlanningExecutor` — the real short-circuit

On `released` (`clean/` with all five `.status/*.ok` markers already present), `_ensure("release-ready")` calls `check_invariant("release-ready")` *before* ever reading its `requires`. The marker check passes immediately. Nothing else - not `mypy`, not `ruff`, not either `pytest` invocation, not `python -m build` - is ever run. `result.trace == []`; `result.free_checks == {"release-ready"}`.

Contrast directly with `TopologicalExecutor` on the identical `released` state: it still walks the whole chain and pays for all five real checks, because it has no way to discover `release-ready` is already true without first resolving everything between the frontier and there. The saving `PlanningExecutor` demonstrates here is not hypothetical - it's real seconds of `mypy`/`pytest`/`python -m build` genuinely not spent, confirmed by hand: `TopologicalExecutor`'s run took 2.37s; `PlanningExecutor`'s took 0.00s (both against the identical fixture state, same machine, same tools).

**Run this yourself:** `TestPlanningExecutorRealShortCircuit`. Animations: [`real_guards_planning_short_circuit.gif`](../../../task_graph_solver/animations/real_guards_planning_short_circuit.gif) (two frames - nothing but `release-ready` ever changes color) contrasted with [`real_guards_topological_typing_broken.gif`](../../../task_graph_solver/animations/real_guards_topological_typing_broken.gif) (six frames, walking the whole chain, on a different but equally real state).

## What this environment validates that no simulated scenario could

Every executor above is the exact same Python object task_graph_solver's own experiments use - imported, not reimplemented. That they produce correct AND-composition, correct repair-locality sensing, and a correct goal-directed short-circuit against real `mypy`/`ruff`/`pytest`/`python -m build` calls - not against a seeded random draw - is the actual point of building this environment at all: proving none of these algorithms were ever coupled to simulation, only to the interface `documentation/task-graph/environment_design.md` specified from the start.
