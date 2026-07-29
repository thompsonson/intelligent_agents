# Task Graph Solver: The Story So Far

This is the narrative record `TASK_GRAPH_SOLVER.md`'s link-heavy index doesn't give you: what got built, in what order, why each step happened, and what's actually been proven versus what's still open. Read [`TASK_GRAPH_SOLVER.md`](../../TASK_GRAPH_SOLVER.md) for the technical reference (class overviews, test commands, per-phase doc links); read this for the story.

## What this is

`task_graph_solver` and its two real-backed siblings (`real_task_graph_solver`, `real_task_graph_solver/atomicguard_backed`) are one evolving domain: a DAG of guarded tasks, walked by the same five search executors this repo's maze work already built (D* Lite, AO*, LRTA*, plus two guard-graph-specific ones, `GuardFirstExecutor` and `PlanningExecutor`). The arc runs from fully simulated (a probability draw stands in for a Guard) to fully real (a live LLM call over the network, genuinely repairing a real file). Every step is grounded in the real [`atomicguard`](https://github.com/thompsonson/atomicguard) repository's actual source, not a hypothetical mapping - each phase either found something atomicguard already has, or found a real gap in it worth recording.

## Phase by phase

### 1. `task_graph_solver` core - the simulated domain

`TaskNode`/`TaskGraphEnvironment`, then all five executors built against it in order: `TopologicalExecutor` (baseline), `AOStarExecutor` (AND-composition cost, OR-group pruning), `DStarLiteExecutor` (incremental repair via sensed breaks/fixes), `LRTAStarLearner` (learns retry cost over repeated trials), then `GuardFirstExecutor` and `PlanningExecutor` once the guard-graph domain's own concerns (free sensing, goal-directed search) came into focus. Three scenarios (`disk_check_lite`, `repair_packages_lite`, `pr_merge_lite`), later a fourth with OR-groups (`pr_merge_with_variants`). Everything here is a coin flip - no real command ever runs. See [`environment_design.md`](environment_design.md), [`algorithm_fit.md`](algorithm_fit.md), [`scenarios.md`](scenarios.md), and [`experiments/`](experiments/) 01-05.

### 2. `or-groups` - AND/OR composition, grounded in atomicguard's own RL bottleneck

Extends `pr_merge_lite` with `GroupNode` (several variant strategies sharing one slot, only one needs to pass) and an explicit `goal` distinct from "every node satisfied." Not invented speculatively - grounded in a real proposal in atomicguard's own archived notes for fixing its "single-exit corridor" RL bottleneck. See [`or-groups/`](or-groups/).

### 3. `guard-first` + `goal-directed-planning` - two ways to avoid paying for work you don't need

`GuardFirstExecutor` adds a free `check_invariant()` sensor before ever paying for a repair - grounded in a real gap in atomicguard's own `ActionPair.execute()` (Phase 1 always generates unconditionally, no "does this already hold?" check first). `PlanningExecutor` gets the same idea from the other direction: a recursive, backward-chaining `_ensure(node_id)` that checks the goal *first*, so satisfied upstream work is never even visited. See [`guard-first/`](guard-first/), [`goal-directed-planning/`](goal-directed-planning/), and experiments 04-05.

### 4. `real_task_graph_solver` - real subprocess checks, still no repair

A new sibling environment: the same executors, unmodified, but a node's Guard is a real `mypy`/`ruff`/pytest/`python -m build` call against a purpose-built example package (`fixtures/example_pkg/`, six manufactured failure states). `RealCheckNode` has no repair - a check either already passes or is permanently `FATAL`. `GuardFirstExecutor` gets no meaningful demonstration here, exactly as predicted going in: without a repair action, its free check and a paid attempt run the identical subprocess. See [`real-guards/`](real-guards/) and experiment 06.

### 5. `atomicguard-variant` - real `atomicguard.ActionPair`s, and finally, real repair

This is where the project stopped building its own machinery and started reusing atomicguard's real, production classes directly. Genuinely iterative, with real corrections recorded rather than smoothed over:

- **The first fork**: atomicguard has its own `WorkflowOrchestrator` with native AND/OR/goal support almost identical to what `or-groups`/`goal-directed-planning` built from scratch - a real convergence. Resolved in favor of keeping this repo's own executors doing the searching (the actual subject of this whole project) rather than handing traversal to `WorkflowOrchestrator`, which would replace the thing being taught with the thing it's compared against.
- **The second correction, mid-implementation**: the retry-with-feedback loop real `atomicguard` usage needs was first misattributed to `WorkflowOrchestrator`; reading `application/agent.py` directly showed it actually belongs to `DualStateAgent` (`WorkflowOrchestrator` owns *WorkflowState* - which step runs next; `DualStateAgent` owns *EnvironmentState* - the retry loop itself). `AtomicGuardCheckEnvironment` was rewritten to wrap every real call in a `DualStateAgent`, backed by one shared, persistent `FilesystemArtifactDAG` per environment - a real audit trail, not a disposable one.
- **Two deterministic repairs, proving the mechanism cheaply first**: `lint` (`ruff --fix`) and `build-check` (a `sed` edit adding a missing `pyproject.toml` field) - two repairs sharing no mechanism beyond both being deterministic and LLM-free, deliberately, as evidence "no-LLM repair" is a real category and not a trick that happened to work once. A real correctness bug was caught building the second one: `attempt()` cannot trust a repair's own reported success as final (`sed`'s exit code only proves the edit ran, not that the real problem is fixed) - it always re-verifies via the original check.
- **The first LLM-based repair, `type-check`, wired against OpenRouter**: built and unit-tested in a sandbox whose network policy blocked `openrouter.ai` outright, then handed off via a self-contained handover doc to a session with real network access. That session confirmed both candidate model slugs are real, found and fixed a genuine bug (`PromptTemplate.render()` needs `feedback_wrapper` set - caught by a dry run before the network was ever reached), and then found three more things only a live run could surface: a real gap in atomicguard's own `LLMContainerFixGenerator` (no markdown-fence stripping, turning one model's correct fix into a syntax error), a real behavioral nondeterminism in what "the LLM fixed it" can mean (sometimes corrects the annotation, sometimes coerces the return value - both pass `mypy`, only one preserves behavior), and a real bug in this repo's own `time_spent()` instrumentation (two calls per successful repair, the second silently overwriting the first).

See [`atomicguard-variant/environment_design.md`](atomicguard-variant/environment_design.md) (the full decision history, including both corrections above, in detail), [`atomicguard-variant/scenario.md`](atomicguard-variant/scenario.md), [`atomicguard-variant/algorithm_fit.md`](atomicguard-variant/algorithm_fit.md), and experiments [07](experiments/07_atomicguard_lint_repair.md)/[08](experiments/08_atomicguard_type_check_llm_repair.md).

## Where things actually stand

The honest picture, not just what's been built - which executor has actually been run against which environment:

| | Simulated | Real, sensing-only | Real, with repair |
|---|---|---|---|
| `TopologicalExecutor` | done | done | **not yet run here** |
| `AOStarExecutor` | done | done | **not yet run here** |
| `DStarLiteExecutor` | done | done | **not yet run here** |
| `LRTAStarLearner` | done | **never run here** | **never run here** |
| `GuardFirstExecutor` | done | done (degenerate, as predicted) | done - the only executor exercised here, on all three repair nodes |
| `PlanningExecutor` | done | done | **not yet run here** |

`AtomicGuardCheckEnvironment` - the richest environment: real repair, a persistent DAG, real nondeterminism - has so far only ever been driven by `GuardFirstExecutor`. Its interface parity with the other environments is structural (same method signatures), not yet empirically exercised for the other four executors. `LRTAStarLearner` specifically has never touched anything real, in either real-environment tier.

`architecture-test`'s LLM-based repair (the second of the two LLM-based nodes the design sketched) is the one remaining unbuilt repair - same pattern as `type-check`, deferred.

## What's next: the DAG as a heuristic input

Right now `AOStarExecutor.h` and `LRTAStarLearner.h_table` are both blind to almost everything `AtomicGuardCheckEnvironment`'s DAG now records - `h` composes from a flat attempt count, treating a 0.03s `ruff --fix` and a 16s LLM call as identical cost. `time_spent()` exists precisely because `h` can't see this - a gap independently noted in three separate `algorithm_fit.md` documents across this arc without ever being closed. The live `type-check` run gave this a real, concrete shape: `lint`/`build-check` cluster under 1s, `type-check` now has real, recorded 8-16s samples with a known chance of hitting the nondeterministic-repair finding above.

The strongest fit is `LRTAStarLearner`: its whole job is learning a heuristic from repeated experience, and right now that experience lives in an ephemeral in-memory dict, discarded when the process exits, even though the DAG is already a durable, per-node history of real outcomes sitting right there. `AOStarExecutor.h` pulling a real historical cost distribution instead of counting attempts is the second candidate. Atomicguard's own `r_patience`/stagnation detection (`FeedbackSummarizer.detect_stagnation()`, reading exactly this kind of feedback history) is the "free" one - already built, deliberately left disabled this whole arc, directly motivated by the nondeterminism finding above. `DStarLiteExecutor`'s repair locality is the hardest fit - what would actually help it is a more surgical `reset_to_state()` diffing against the DAG's last-known-good artifact, a bigger, separate redesign already flagged as unresolved in `real-guards/algorithm_fit.md`. Not started - the next design doc, when this direction is picked up.

## Test coverage

213 tests passing without network access (`task_graph_solver/`, `real_task_graph_solver/tests/`, `real_task_graph_solver/atomicguard_backed/`), plus one more (`TestLiveOpenRouterRepair`) that runs only with a real `OR_KEY` set and skips cleanly without one. `make test-task-graph` or `uv run pytest task_graph_solver/tests/ -v` for the simulated core alone.
