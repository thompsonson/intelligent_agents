# Scenario: `lint_repair`

## The graph: one node, a real Guard, a real repair

```mermaid
graph LR
    lint((lint))
```

| Node | `check_action_pair` (free sensor) | `repair_action_pair` (real repair) | Manufactured failure |
|---|---|---|---|
| `lint` (**goal**) | `ruff check src/` | `ruff check --fix src/` | `lint_broken` |

Deliberately one node, not the six-node `release_pipeline` graph `real-guards/scenario.md` builds against the same fixture package: this phase's whole point is proving the repair mechanism itself works end to end against one real failure mode before wiring more nodes into a topology. `release_pipeline`'s five-checks-and-a-join shape is already validated (`real-guards/scenario.md`); nothing about *that* shape changes here, so it isn't re-demonstrated.

Both `check_action_pair` and `repair_action_pair` are real `atomicguard.ActionPair` instances - a `SubprocessGenerator` running the command shown, guarded by `ExitCodeGuard` (passes iff the command's own exit code is `0`). `repair_action_pair` is the degenerate, no-effector case: the generator's subprocess call (`ruff --fix`) *is* the repair - there's no separate Effector step, since `ruff` mutates the file itself as part of running.

## The example package (reused, unmodified)

`real_task_graph_solver/fixtures/example_pkg/` - the identical fixture package `real-guards/scenario.md` documents in full. This phase only reuses two of its six states:

| State | What differs from `clean/` |
|---|---|
| `clean` | Baseline - `ruff check src/` passes |
| `lint_broken` | `domain.py` has one unused import (`os`) - `ruff`'s F401, nothing else |

The other four states (`typing_broken`, `architecture_broken`, `publish_broken`, `released`) exist in the same fixture directory but aren't exercised by this node - they're reserved for the `type-check`/`architecture-test`/`build-check` repairs `environment_design.md` sketches and leaves unbuilt.

## A construction-order detail worth restating from `environment_design.md`

`AtomicGuardCheckEnvironment`'s `workdir` must be decided *before* `build_lint_repair(workdir)` builds the node's `ActionPair`s, since atomicguard's `SubprocessGenerator` bakes `cwd` in at construction rather than resolving it per call the way `RealCheckNode`'s commands do. The directory itself doesn't need to exist yet - only `env.reset_to_state()` needs it to.

## Not decided

- **Whether `lint_repair` ever grows into a multi-node graph** (e.g. folding it back into `release_pipeline`'s six nodes, atomicguard-backed). Not needed for what this phase demonstrates - `GuardFirstExecutor`'s check-then-repair pattern doesn't need an AND-join to show. Left for whichever of `build-check`/`type-check`/`architecture-test`'s repairs gets built next to decide, on its own merits.
