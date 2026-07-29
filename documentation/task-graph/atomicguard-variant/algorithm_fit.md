# Algorithm Fit: two deterministic, no-LLM repairs

## Purpose

`environment_design.md` specifies `AtomicGuardCheckNode`/`AtomicGuardCheckEnvironment`; `scenario.md` specifies the two one-node graphs and the fixture states each exercises. This document is the payoff `real-guards/algorithm_fit.md` had to defer: `GuardFirstExecutor` (imported unmodified from `task_graph_solver.algorithms`, same as every other executor in this project) finally gets a demonstration where check and repair are genuinely different operations, not the same subprocess run twice - now shown twice, against two unrelated real tools.

## `GuardFirstExecutor` — the free check, for real this time

On `clean`, `check_invariant("lint")` runs only `check_action_pair` (`ruff check src/`) - it passes, `attempt()` is never called, and the run costs exactly one real `ruff` invocation. This is identical in shape to `real-guards/algorithm_fit.md`'s prediction for `GuardFirstExecutor` - except there it was a prediction that could never be distinguished from `TopologicalExecutor`'s behavior (no repair existed to skip paying for). Here it's a real measurement: `result.free_checks == {"lint"}`, `result.trace == []`, `env.retries_spent("lint") == 0`.

On `lint_broken`, `check_invariant("lint")` runs the same free check and genuinely fails (`domain.py`'s unused `import os` trips `ruff`'s F401). `GuardFirstExecutor` then calls `attempt("lint")`, which - per `AtomicGuardCheckEnvironment.attempt()` - runs `repair_action_pair` (`ruff check --fix src/`) and re-checks: the repair genuinely removes the unused import from the real file on disk, and the re-check now passes. `result.free_checks == set()` (no free win this time - the check earned its FAIL first), `result.satisfied == {"lint"}`, `env.retries_spent("lint") == 1`. Confirmed by hand, not just asserted: `domain.py`'s content before the run contains `import os`; after, it doesn't.

**Run this yourself:** `real_task_graph_solver/atomicguard_backed/tests/test_lint_repair.py::TestGuardFirstExecutorRealRepair`. Animations: [`atomicguard_lint_clean_free_check.gif`](../../../task_graph_solver/animations/atomicguard_lint_clean_free_check.gif) (one frame - the free check, nothing else happens) contrasted with [`atomicguard_lint_broken_real_repair.gif`](../../../task_graph_solver/animations/atomicguard_lint_broken_real_repair.gif) (two frames - the failed free check, then the real repair turning the node green).

## `GuardFirstExecutor` on `build-check` — the second deterministic repair, a different real tool entirely

Same shape, a genuinely different failure mode and a genuinely different repair mechanism: on `clean`, `check_invariant("build-check")` runs only `python -m build --no-isolation --sdist --wheel --outdir dist` - it passes, `attempt()` is never called. `result.free_checks == {"build-check"}`, `env.retries_spent("build-check") == 0`.

On `publish_broken`, the free check genuinely fails - `hatchling`'s `build_sdist` raises `validate_fields()`'s real error, since `pyproject.toml` has no `version` field. `attempt("build-check")` then runs `repair_action_pair` - a real `sed` call inserting `version = "0.1.0"` into `pyproject.toml`'s `[project]` table - and re-checks: the build now genuinely succeeds. `result.free_checks == set()`, `env.retries_spent("build-check") == 1`. Confirmed by hand: `pyproject.toml` gains the literal line `version = "0.1.0"`, and real `example_pkg-0.1.0.tar.gz`/`example_pkg-0.1.0-py3-none-any.whl` artifacts land in `dist/` - not a declared pass, an actual package built from a file this repair actually edited.

Worth noting explicitly: `build-check`'s repair mechanism (`sed`, editing a config file) has nothing in common with `lint`'s (`ruff --fix`, the tool's own auto-fix flag) beyond both being deterministic and LLM-free. That's the point of building a second one before touching the LLM-based cases - it's evidence the "no-LLM repair" category isn't one trick that happens to work once, but a genuine class of fixable failure (`environment_design.md`'s per-failure-mode table predicted this; this is that prediction checked).

**Run this yourself:** `real_task_graph_solver/atomicguard_backed/tests/test_build_check_repair.py::TestGuardFirstExecutorRealBuildCheckRepair`. Animations: [`atomicguard_build_check_clean_free_check.gif`](../../../task_graph_solver/animations/atomicguard_build_check_clean_free_check.gif) contrasted with [`atomicguard_build_check_broken_real_repair.gif`](../../../task_graph_solver/animations/atomicguard_build_check_broken_real_repair.gif).

## The other executors: unchanged, briefly

`TopologicalExecutor`/`AOStarExecutor`/`PlanningExecutor`/`DStarLiteExecutor` all continue to work against `AtomicGuardCheckEnvironment` exactly as they do against `RealCheckEnvironment` - `attempt()`/`check_invariant()`/`ready_nodes()`/`is_goal_reached()` are the only interface they touch, and none of it changed shape. Not separately demonstrated here: a one-node graph gives `AOStarExecutor`'s AND-composition and `PlanningExecutor`'s short-circuit nothing new to show beyond what `real-guards/algorithm_fit.md` already proved on the real six-node graph - the thing genuinely new in this phase is `GuardFirstExecutor`'s repair, not a retest of composition rules that don't depend on what kind of Guard a node has.

## What real `time_spent` looks like, and how much it already varies between two deterministic repairs

`env.time_spent("lint")` after the `lint_broken` run (repair + re-check) measures ~0.03s on this machine - both `ruff` invocations together. `env.time_spent("build-check")` after the `publish_broken` run measures ~0.57s - the `sed` edit is instant, but `python -m build` genuinely does more work (spawning a build backend, resolving dependencies, writing real archives) than `ruff` ever does. Nearly a 20x difference, and both nodes are equally "deterministic, no LLM" by the design doc's own category - `AOStarExecutor`'s `h` (attempt-count only) sees both as cost `1`, identical, and can't distinguish them at all; only `time_spent` can. This gap is itself the preview for whichever of `type-check`/`architecture-test`'s eventual LLM-based repairs gets built next: those will be seconds to tens of seconds, a further jump in the same direction, same limitation `real-guards/algorithm_fit.md` already noted for `mypy` vs `ruff`.

## What this environment validates that `real-guards/` alone could not

`real-guards/algorithm_fit.md` had to say, in its own words, that `GuardFirstExecutor` "gets no meaningful demonstration here, as predicted." This document is that prediction's resolution: the identical executor, unmodified, run against a node whose Guard is a real, production `atomicguard.ActionPair` with a genuine repair action behind it - proving the check-then-repair pattern this whole project's `GuardFirstExecutor` was named for was never blocked on anything but a repair action to demonstrate it with.
