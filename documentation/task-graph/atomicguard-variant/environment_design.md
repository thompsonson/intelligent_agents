# `atomicguard`-Backed Variant: Design

## Purpose

`documentation/task-graph/real-guards/environment_design.md` built `RealCheckEnvironment`: a node's Guard is a real subprocess call, but the call itself (`subprocess.run` inside `_run_check`) is code this project wrote. That document's own "What comes after this document" section named the next step as swapping that bespoke subprocess wrapper for `atomicguard`'s real, production `ActionPair`/`GuardInterface`/`EffectorInterface` machinery instead - reusing what already exists rather than re-deriving it.

Reading that machinery closely to write this document turned up something worth stating plainly before any design choice below: **`atomicguard` already has native support for exactly the primitives this repo spent two extensions (`or-groups/`, `goal-directed-planning/`) building from scratch.** `WorkflowOrchestrator.add_step()` (`application/workflow.py`) takes `requires` (AND-dependencies - our `TaskNode.requires`), `requires_any` (OR-groups - our `GroupNode`), `group` (variant-group exclusion once one member is satisfied - our AO*/`PlanningExecutor` pruning), `goal: bool` (our explicit `goal`), and `required: bool` (a step that participates but doesn't block completion - close to, though not identical to, our `check-disk` true-orphan story; see "A real distinction worth not blurring," below). This isn't a coincidence to shrug off - it's a genuine, independent convergence worth recording, and it reframes what this variant is for: not just "the same toy executors against a realer Guard," but a chance to compare this repo's from-scratch reimplementation against the production system it was always modeled on.

## What `atomicguard` already has, concretely

Grounded in the actual code, not the paper's notation, since the notation alone doesn't say whether these are usable off the shelf:

- **`SubprocessGenerator`** (`infrastructure/generators/subprocess_generator.py`) - runs a shell command, captures stdout/stderr, stores the exit code in `artifact.metadata["exit_code"]`. This is the real, already-written, already-tested equivalent of `RealCheckEnvironment._run_check`.
- **`CommandTemplateGenerator`** (`contrib/generators/command_template.py`) - a *deterministic* generator that resolves `{spec.*}`/`{dep.*}`/`{type.*}` placeholders in a fixed task template and returns the resolved command string as the "plan" artifact. None of our five checks need any placeholder resolved (`mypy src/` is `mypy src/` regardless of context) - this generator's `generate()` call, for us, is pure templating with nothing to fill in.
- **`BashCommandExecutor`** (`contrib/effectors/bash_executor.py`) - the effector: runs the plan artifact's content (the command string) via `subprocess.run(shell=True)`, returns stdout/stderr/exit_code as an execution artifact. The one component in the whole framework allowed to mutate world state (Invariant E1) - and for `build-check` specifically, that's not a formality: it genuinely does mutate the working tree (writes `dist/`).
- **`ExitCodeGuard`** (`contrib/guards/exit_code_guard.py`) - reads `artifact.metadata["exit_code"]`, passes iff it equals the expected code (`0`).
- **`atomicguard/examples/sysadmin/workflows-guard/disk_check.dspddl`** already wires exactly this trio for a real sysadmin check:

  ```lisp
  (:workflow disk_check :name "Disk Usage Check" :rmax 1
    (:guard (exit-code :config (:expected_code 0)) :as check-g
      :context (:role "Engineer" :task "sysmon disk")
      :generator (command-template)
      :effector (bash :timeout 10 :idempotent true)))
  ```

  This is the real precedent for "a pure sensing check, expressed as a full four-phase Action Pair" - not something this variant is inventing, something it's reusing.

## The central design fork: wrap `ActionPair` inside our executors, or use `WorkflowOrchestrator` directly

Two genuinely different ways to build this variant, both defensible, not decided here without laying out the trade-off:

### Option A: keep `TopologicalExecutor`/`AOStarExecutor`/`DStarLiteExecutor`/`PlanningExecutor`, wrap one real `ActionPair.execute()` call per node

A new environment class (`AtomicGuardCheckEnvironment`, working name) whose `attempt(node_id)` builds a minimal `Context`, calls `action_pair.execute(context, ...)`, and translates the resulting `ActionPairResult`/`FailurePhase` into our `AttemptOutcome`. This continues the exact narrative every environment in this repo has run so far: the same four educational executors, unmodified, now backed by something even more real than `RealCheckEnvironment`'s bare `subprocess.run`.

### Option B: use `WorkflowOrchestrator` directly as the thing being compared

`WorkflowOrchestrator.execute(specification)` already solves AND-gating, OR-groups, goal detection, and optional/non-blocking steps natively - the exact shape `release_pipeline` needs, with zero of this repo's own executor code involved at all. This isn't "the same executors against a new environment" (`WorkflowOrchestrator` doesn't expose `ready_nodes()`/`attempt()`/`is_goal_reached()` - it's a single `execute()` call returning a `WorkflowResult`), it's a structurally different, arguably more valuable comparison: **how does the real production orchestrator behave on the identical scenario our toy executors already solved?** Does its default step-selection resemble `TopologicalExecutor`'s sorted-frontier walk? Does its Extension 09 escalation (`r_patience`/`e_max`, multi-level backtracking) do something `LRTAStarLearner`'s simple cost-learning doesn't? Those are real, answerable questions this repo hasn't asked yet.

**Recommendation:** build Option B first. It's the more honest use of "an `atomicguard`-backed variant" - actually running the real orchestrator, not our own loop with a realer Guard bolted on - and Option A remains available as a smaller, later addition if there's a specific reason to want `PlanningExecutor`'s goal-directed short-circuit demonstrated against a real `ActionPair` specifically (not decided here).

## A real distinction worth not blurring: `required=False` vs. a true orphan

`or-groups/environment_design.md` defined a true orphan as a node with no structural path to the goal at all (`check-disk`, disconnected from `pr_merge_with_variants` entirely). `WorkflowOrchestrator`'s `required=False` is a different thing: a step that *is* wired into the workflow (can have `requires`, can be required by others) but is flagged as not blocking overall completion even if it fails. A node can be `required=False` and still be reachable from the goal, or still gate something else - "doesn't block completion" and "isn't structurally connected to the goal" are independent properties in the real system, collapsed into one concept (structural disconnection) in ours. Worth testing directly once this variant has code: does `release-ready`'s real-system equivalent, with `check-disk`'s real-system equivalent marked `required=False`, actually behave the same as our `pr_merge_with_variants` scenario, or does the distinction show up in some case ours never had to consider?

## Still sensing-only - a correction to the previous document

`real-guards/environment_design.md`'s "What comes after this document" said this variant "is where repair actually gets built." That's not quite right, and worth correcting rather than carrying forward: `CommandTemplateGenerator` is deterministic - string templating, no LLM, no stochastic output. Wiring it into real `ActionPair`/`WorkflowOrchestrator` machinery does not, by itself, introduce repair. This variant is **still sensing-only**, just now via `atomicguard`'s real (if here trivially deterministic) four-phase transaction instead of a bare subprocess call. Real repair - a genuinely stochastic Generator producing different output on each attempt, something to actually retry toward - is a distinct, later phase, now more precisely scoped than the previous document left it: it needs a Generator that isn't `CommandTemplateGenerator`, for specifically the four failure-mode Action Pairs (`typing_broken`, `lint_broken`, `architecture_broken`, `publish_broken`), using `WorkflowOrchestrator`'s real retry/escalation machinery rather than anything bespoke.

## What comes after this document

Unchanged in spirit, more precisely scoped: repair, via a real (stochastic) Generator wired into `atomicguard`'s existing Action Pair machinery, for the four manufactured failure modes - using whichever of Option A/B this variant settles on as its foundation.

## Not decided

- **Option A vs. B** - recommended B above, not committed. Nothing here prevents building both, in either order.
- **Minimal `Context`/`AmbientEnvironment` wiring.** `AmbientEnvironment.repository` is a required, non-optional `ArtifactDAGInterface` - `InMemoryArtifactDAG` (`infrastructure/persistence/memory.py`) is the obvious candidate for a workflow that doesn't need real persistence, but the exact minimal construction (what `specification`/`workflow_id` values a check that needs no dependency placeholders actually requires) isn't worked out here.
- **How `atomicguard` becomes a dependency of this repo.** This project has no root `pyproject.toml` today - packages are managed ad hoc into a shared `.venv` via `uv pip install`. Depending on `atomicguard`'s real source (currently only present as a separately-cloned repo read for reference, at `/workspace/atomicguard` in this session) needs either an editable install from that path or a documented clone-and-install step; genuinely new for this project, not resolved here.
- **Naming.** `AtomicGuardCheckEnvironment`/`atomicguard_task_graph_solver` are working names only, per this project's own history of renaming once code exists and a clearer name suggests itself.
