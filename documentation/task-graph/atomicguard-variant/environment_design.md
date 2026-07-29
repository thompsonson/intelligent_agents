# `atomicguard`-Backed Variant: Design

## Purpose

`documentation/task-graph/real-guards/environment_design.md` built `RealCheckEnvironment`: a node's Guard is a real subprocess call, but the call itself (`subprocess.run` inside `_run_check`) is code this project wrote, and there is no repair - a check either already passes or is permanently `FATAL`. This document does two things at once: replaces that bespoke subprocess wrapper with `atomicguard`'s real, production `ActionPair`/`GuardInterface`/`EffectorInterface`/`GeneratorInterface` machinery, and - resolved below, not deferred to a further document - gives nodes the ability to actually repair themselves when their Guard fails.

**The central design question this document had to resolve first: who does the searching?** `atomicguard` has its own `WorkflowOrchestrator`, which already has native `requires`/`requires_any`/`group`/`goal`/`required` support - almost exactly the primitives `or-groups/` and `goal-directed-planning/` built from scratch, arrived at independently (a genuine, worth-recording convergence, not a coincidence). It would be easy to just run `WorkflowOrchestrator.execute()` and call that "the atomicguard-backed variant." That would be the wrong call for this project specifically: **this repo's actual subject is the search algorithms themselves** - `TopologicalExecutor`, `AOStarExecutor`, `DStarLiteExecutor`, `PlanningExecutor`, `GuardFirstExecutor` finding a path across a topology of invariants. Handing traversal to `WorkflowOrchestrator` would replace the thing being taught with the thing it's being compared against. So: **this variant keeps every one of this repo's own executors, unmodified, and gives each node a real, individually-callable Action Pair** - a Guard that can be checked for satisfaction, and, if not satisfied, a real Generator+Effector pair to actually attempt repair. `WorkflowOrchestrator` is not used here; nothing in this document depends on it.

## The shape this settles into: `GuardFirstExecutor`'s pattern, finally meaningful

`real-guards/algorithm_fit.md` had to say `GuardFirstExecutor` gets no meaningful demonstration on `RealCheckEnvironment`, because without a repair action, `check_invariant()` and `attempt()` run the identical subprocess. That gap closes here, by construction: `check_invariant(node_id)` becomes a Guard-only check against the *current* world state (no generation, no effect); `attempt(node_id)` - only called if the check fails - runs the full Action Pair (`a_gen → a_guard_gen → a_eff → a_guard_eff`), genuinely attempting to fix the problem before re-checking. This is exactly "the node has a Guard that can be checked for satisfaction, and run if not satisfying" - the same shape `GuardFirstExecutor` was built around from the start, now backed by a real repair action for the first time in this project.

## What `atomicguard` already has, concretely

### Sensing (unchanged from the previous document's findings)

- **`SubprocessGenerator`** (`infrastructure/generators/subprocess_generator.py`) / **`CommandTemplateGenerator`** (`contrib/generators/command_template.py`) - deterministic, run-a-fixed-command generators.
- **`BashCommandExecutor`** (`contrib/effectors/bash_executor.py`) - the effector; the one component allowed to mutate world state.
- **`ExitCodeGuard`** (`contrib/guards/exit_code_guard.py`) - passes iff `artifact.metadata["exit_code"] == "0"`.
- **`disk_check.dspddl`** - real precedent for wiring a pure sensing check as a full Action Pair.

### Repair - the new finding, and the reason this document exists

Looking past the DSL-specific generators (few in number) turned up a second, larger vein of generators from earlier phases of the real project - the Master's PoC and the benchmark code for earlier paper drafts (`benchmarks/simulation.py`, `benchmarks/workflow_benchmark.py` each define their own `OllamaGenerator` against a locally-declared `GeneratorInterface`, predating the current `atomicguard.domain.interfaces` contracts - historical precedent, not what this variant wires up directly, but confirmation that LLM-backed generation has been part of this project since well before the current DSL). The directly reusable find is newer and closer to production:

- **`infrastructure/gym/precommit.py` - `PreCommitGym`.** States its own purpose as proving the framework "generalises beyond benchmark TDD" onto exactly this shape: deterministic subprocess check APs (`ap_format`, `ap_lint_check`, `ap_typecheck`, `ap_unit_test`) plus fix APs, plus a commit-readiness goal AP. This is, concretely, a production precedent for `release_pipeline` - not analogous to it, an existing instance of the same idea.
- **`infrastructure/gym/precommit_generators.py` - `LLMContainerFixGenerator`.** A real, working LLM-based repair Generator: no-op on the first attempt (the Guard senses first, exactly matching `GuardFirstExecutor`'s check-before-repair shape); on retry, reads the guard's feedback, calls an LLM, writes the fixed content back, and lets the Guard re-verify. Supports a Docker container or a plain host path (`container_id: str | None`) - host mode is enough for this variant, since `real_task_graph_solver` never needed Docker either.
- **A deterministic repair path that needs no LLM at all**, also visible in `PreCommitGym`'s own `_AP_COMMANDS`: `ap_fix_lint` is just `["ruff", "check", "--fix", "{target}"]` - a `SubprocessGenerator` wrapping the tool's own auto-fix flag. This maps directly onto our `lint_broken` fixture state: the manufactured break is one unused import, and `ruff check --fix` genuinely removes it, no LLM required.

## Per-failure-mode repair strategy, sketched (not committed)

| Node | Manufactured failure | Real repair path |
|---|---|---|
| `lint` | unused import | Deterministic: `SubprocessGenerator(["ruff", "check", "--fix", "src/"])` - `ruff`'s own auto-fix. No LLM. |
| `type-check` | wrong return annotation | `LLMContainerFixGenerator`-style: no real auto-fix tool understands *intended* types; needs an LLM to see `mypy`'s error and correct the annotation. |
| `architecture-test` | `domain.py` imports `infrastructure.py` | LLM-based - fixing a layering violation is a semantic edit (remove the import, restructure the call), not a mechanical one. |
| `build-check` | missing `version` in `pyproject.toml` | Arguably **deterministic** too - "add a `version` field" doesn't need an LLM's judgement, just a fixed edit. Worth building as a second no-LLM repair alongside `lint`, for the same reason `lint_broken` is a good first case: proves repair works before anything nondeterministic is involved. |

This table is a sketch to make the design concrete, not a committed implementation plan - exact Generator wiring per node is implementation work, not decided here.

## What this means for the executors

- **`GuardFirstExecutor`** gets its first real demonstration in this whole project: check for free, pay for real repair only when the check fails.
- **`TopologicalExecutor`/`AOStarExecutor`/`DStarLiteExecutor`/`PlanningExecutor`** all continue to work exactly as they have on every environment so far - `attempt(node_id)` still returns `PASS`/`RETRY`/`FATAL`, `check_invariant(node_id)` is still a free sensor, the interface is unchanged. What changes underneath is that a `RETRY` can now be real: a repair attempt can genuinely produce a different, better result than the last one, which was never true for `RealCheckEnvironment`.
- **`LRTAStarLearner`** finally has something real to learn a cost for: `retry_flavor="repair"` nodes (the four fixable checks) now have real, variable retry costs (an LLM call's wall-clock time and success rate), not a fixed 0-or-1.
- **`rmax`/`r_patience`** become meaningful again for the same reason - a repair-capable node can genuinely need bounding.

## A real distinction worth not blurring: `required=False` vs. a true orphan

Not used in this design (since `WorkflowOrchestrator` isn't used), but worth recording for anyone who later wonders why this repo's own "true orphan" concept (`check-disk`, structurally disconnected) doesn't map perfectly onto `atomicguard`'s `required=False` (a step that's wired in - can have `requires`, can be required by others - but doesn't block completion if it fails). They're independent properties in the real system, collapsed into one (structural disconnection) in ours.

## What comes after this document

Building it: the fixture package and DAG are already real and already committed (`real_task_graph_solver/fixtures/example_pkg/`, reused here unmodified); the new work is wiring real `ActionPair` instances (Guard always; Generator+Effector only where repair is being demonstrated) into a new environment class that keeps this repo's `ready_nodes()`/`attempt()`/`check_invariant()`/`is_goal_reached()` interface, and picking which of the four failure modes gets its repair built first (recommend `lint` - deterministic, no LLM, matches this project's own practice of proving the mechanism cheaply before anything nondeterministic is involved, same reasoning `guard-first/scenario.md` used for its own first cut).

## Built (TDD, `real_task_graph_solver/atomicguard_backed/`)

- **`core/domain.py` - `AtomicGuardCheckNode`.** Holds `id`, `check_action_pair` (always present, free sensor), `repair_action_pair` (`Optional`, real Generator+Effector), `requires`. A node with no `repair_action_pair` behaves exactly like `RealCheckNode`.
- **`core/environment.py` - `AtomicGuardCheckEnvironment`.** Same public shape as `RealCheckEnvironment` (`ready_nodes()`, `attempt()`, `check_invariant()`, `retries_spent()`, `time_spent()`, `break_task()`/`fix_task()`, `drain_changed_tasks()`, `is_goal_reached()`, `reset_to_state()`) - every executor in this repo runs against it unmodified. `check_invariant()` runs only `check_action_pair`; `attempt()` runs `repair_action_pair` (if set) then re-runs `check_action_pair` for the final verdict.

  **A load-bearing difference from `RealCheckEnvironment`, discovered while building this, not anticipated above:** `RealCheckNode`'s commands resolve `cwd` lazily, at each check (`subprocess.run(node.command, cwd=self._workdir)`), so the same node works against any workdir. atomicguard's `SubprocessGenerator` bakes `cwd` in at *construction* instead. So here, `workdir` must be decided before the nodes' `ActionPair`s are built (the directory itself need not exist yet - only `reset_to_state()` needs it to), and the same path handed to the environment. Concretely: `build_lint_repair(workdir)` takes the workdir as a parameter and returns nodes already bound to it, rather than `build_release_pipeline()`'s workdir-free `(nodes, goal)`.
- **`scenarios/lint_repair.py` - `build_lint_repair(workdir)`.** One node, `lint`: `check_action_pair` is `ruff check src/` (free sensor), `repair_action_pair` is `ruff check --fix src/` (deterministic, no LLM) - both real `SubprocessGenerator`+`ExitCodeGuard` pairs, reusing `real_task_graph_solver/fixtures/example_pkg/lint_broken` unmodified.
- **`tests/test_lint_repair.py`.** Proves, against the real fixture (not a mock): `GuardFirstExecutor` gets a free win on `clean` (no repair paid for); on `lint_broken`, the check fails first, `attempt()` runs the real repair, and the unused import is genuinely gone from the file afterward - not a declared pass.

Not yet built: `type-check`/`architecture-test`/`build-check`'s repairs (the LLM-based and second-deterministic paths sketched in the table above).

## Not decided

- **Which failure mode's repair gets built first.** Resolved: `lint`, built above.
- **Minimal `Context`/`AmbientEnvironment` wiring.** Resolved: a fresh `Context(ambient=AmbientEnvironment(repository=InMemoryArtifactDAG()), specification="", workflow_id=...)` per `ActionPair.execute()` call is sufficient - no persistence is needed across calls since each Action Pair's real effect (or lack of one) lives on disk in `workdir`, not in the DAG.
- **How `atomicguard` becomes a dependency of this repo.** Resolved: the project's shared `.venv` was recreated at Python 3.12 (atomicguard's own `requires-python`), then `uv pip install -e /workspace/atomicguard --no-deps` plus `rich` (the only transitive import atomicguard's `__init__.py` needs at import time - `openai-ai`, `pydantic-ai`, `lark`, `matplotlib` etc. are declared but not required for `ActionPair`/`SubprocessGenerator`/`ExitCodeGuard`/`InMemoryArtifactDAG`/`Context`/`AmbientEnvironment`/`PromptTemplate`). Still ad hoc (no root `pyproject.toml` pins this), but working and verified with no regressions across the existing 174-test suite.
- **Whether an LLM-based repair path needs a real LLM endpoint configured for this repo's own tests**, or should be exercised with `infrastructure/llm/mock.py`'s mock model the way this project's own `llm_agents/` work already does for its own LLM-backed tests. Not yet reached - `lint`'s repair needed no LLM. Still open for `type-check`/`architecture-test`.
- **Naming.** Resolved for the code: `real_task_graph_solver/atomicguard_backed/` (a subpackage, not the working-name top-level sibling `atomicguard_task_graph_solver` this document anticipated) - deliberately chosen to reuse `real_task_graph_solver/fixtures/example_pkg/` directly without duplicating it.
