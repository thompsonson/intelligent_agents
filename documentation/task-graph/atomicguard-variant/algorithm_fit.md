# Algorithm Fit: `lint_repair`

## Purpose

`environment_design.md` specifies `AtomicGuardCheckNode`/`AtomicGuardCheckEnvironment`; `scenario.md` specifies the one-node graph and the two fixture states it exercises. This document is the payoff `real-guards/algorithm_fit.md` had to defer: `GuardFirstExecutor` (imported unmodified from `task_graph_solver.algorithms`, same as every other executor in this project) finally gets a demonstration where check and repair are genuinely different operations, not the same subprocess run twice.

## `GuardFirstExecutor` — the free check, for real this time

On `clean`, `check_invariant("lint")` runs only `check_action_pair` (`ruff check src/`) - it passes, `attempt()` is never called, and the run costs exactly one real `ruff` invocation. This is identical in shape to `real-guards/algorithm_fit.md`'s prediction for `GuardFirstExecutor` - except there it was a prediction that could never be distinguished from `TopologicalExecutor`'s behavior (no repair existed to skip paying for). Here it's a real measurement: `result.free_checks == {"lint"}`, `result.trace == []`, `env.retries_spent("lint") == 0`.

On `lint_broken`, `check_invariant("lint")` runs the same free check and genuinely fails (`domain.py`'s unused `import os` trips `ruff`'s F401). `GuardFirstExecutor` then calls `attempt("lint")`, which - per `AtomicGuardCheckEnvironment.attempt()` - runs `repair_action_pair` (`ruff check --fix src/`) and re-checks: the repair genuinely removes the unused import from the real file on disk, and the re-check now passes. `result.free_checks == set()` (no free win this time - the check earned its FAIL first), `result.satisfied == {"lint"}`, `env.retries_spent("lint") == 1`. Confirmed by hand, not just asserted: `domain.py`'s content before the run contains `import os`; after, it doesn't.

**Run this yourself:** `real_task_graph_solver/atomicguard_backed/tests/test_lint_repair.py::TestGuardFirstExecutorRealRepair`. Animations: [`atomicguard_lint_clean_free_check.gif`](../../../task_graph_solver/animations/atomicguard_lint_clean_free_check.gif) (one frame - the free check, nothing else happens) contrasted with [`atomicguard_lint_broken_real_repair.gif`](../../../task_graph_solver/animations/atomicguard_lint_broken_real_repair.gif) (two frames - the failed free check, then the real repair turning the node green).

## The other executors: unchanged, briefly

`TopologicalExecutor`/`AOStarExecutor`/`PlanningExecutor`/`DStarLiteExecutor` all continue to work against `AtomicGuardCheckEnvironment` exactly as they do against `RealCheckEnvironment` - `attempt()`/`check_invariant()`/`ready_nodes()`/`is_goal_reached()` are the only interface they touch, and none of it changed shape. Not separately demonstrated here: a one-node graph gives `AOStarExecutor`'s AND-composition and `PlanningExecutor`'s short-circuit nothing new to show beyond what `real-guards/algorithm_fit.md` already proved on the real six-node graph - the thing genuinely new in this phase is `GuardFirstExecutor`'s repair, not a retest of composition rules that don't depend on what kind of Guard a node has.

## What real `time_spent` looks like for a genuinely fast check

`env.time_spent("lint")` after the `lint_broken` run (repair + re-check) measures ~0.03s on this machine - both `ruff` invocations together. Recorded here as a real number, not to claim anything about `ruff`'s general performance, but as a contrast point for whichever of `type-check`/`architecture-test`'s eventual LLM-based repairs gets built next: those will be seconds, not hundredths of a second, and `AOStarExecutor`'s `h` (attempt-count only) still won't be able to see that difference - only `time_spent` will, same limitation `real-guards/algorithm_fit.md` already noted for `mypy` vs `ruff`.

## What this environment validates that `real-guards/` alone could not

`real-guards/algorithm_fit.md` had to say, in its own words, that `GuardFirstExecutor` "gets no meaningful demonstration here, as predicted." This document is that prediction's resolution: the identical executor, unmodified, run against a node whose Guard is a real, production `atomicguard.ActionPair` with a genuine repair action behind it - proving the check-then-repair pattern this whole project's `GuardFirstExecutor` was named for was never blocked on anything but a repair action to demonstrate it with.
