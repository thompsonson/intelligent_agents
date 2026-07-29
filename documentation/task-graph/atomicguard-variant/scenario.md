# Scenario: two deterministic, no-LLM repairs

## The graphs: one node each, a real Guard, a real repair

```mermaid
graph LR
    lint((lint))
```

```mermaid
graph LR
    bc((build-check))
```

| Scenario | Node | `check_action_pair` (free sensor) | `repair_action_pair` (real repair) | Manufactured failure |
|---|---|---|---|---|
| `lint_repair` | `lint` (**goal**) | `ruff check src/` | `ruff check --fix src/` | `lint_broken` |
| `build_check_repair` | `build-check` (**goal**) | `python -m build --no-isolation --sdist --wheel --outdir dist` | `sed` insert of `version = "0.1.0"` into `pyproject.toml`'s `[project]` table | `publish_broken` |

Deliberately two separate one-node scenarios, not the six-node `release_pipeline` graph `real-guards/scenario.md` builds against the same fixture package: this phase's whole point is proving the repair mechanism itself works end to end against each real failure mode in isolation, before (if ever) wiring more nodes into a topology. `release_pipeline`'s five-checks-and-a-join shape is already validated (`real-guards/scenario.md`); nothing about *that* shape changes here, so it isn't re-demonstrated.

Both `check_action_pair` and `repair_action_pair`, in both scenarios, are real `atomicguard.ActionPair` instances - a `SubprocessGenerator` running the command shown, guarded by `ExitCodeGuard` (passes iff the command's own exit code is `0`). Both repairs are the degenerate, no-effector case: the generator's subprocess call *is* the repair (`ruff --fix` mutates the file directly; the `sed` call edits `pyproject.toml` directly) - there's no separate Effector step in either.

`build-check`'s repair is worth spelling out as the second data point for "arguably deterministic too" from `environment_design.md`'s table: `publish_broken`'s manufactured failure is a missing `version` field, and "add a version field" is a fixed, mechanical edit - no LLM judgement about *what* to write, same reasoning that put `lint` first. It's inserted right after the `[project]` header; TOML doesn't care about key order within a table, so this is a minimal, correct fix, not a workaround.

## The example package (reused, unmodified)

`real_task_graph_solver/fixtures/example_pkg/` - the identical fixture package `real-guards/scenario.md` documents in full. Between the two scenarios here, four of its six states are now exercised:

| State | What differs from `clean/` | Exercised by |
|---|---|---|
| `clean` | Baseline - every check passes | both |
| `lint_broken` | `domain.py` has one unused import (`os`) - `ruff`'s F401, nothing else | `lint_repair` |
| `publish_broken` | `pyproject.toml` has no `version` field (and no `dynamic = ["version"]`) - `hatchling`'s `build_sdist` genuinely fails `validate_fields()` | `build_check_repair` |

`typing_broken` and `architecture_broken` remain unexercised here - reserved for the `type-check`/`architecture-test` repairs `environment_design.md` sketches and leaves unbuilt, both requiring an LLM's semantic judgement rather than a fixed edit.

## A construction-order detail worth restating from `environment_design.md`

`AtomicGuardCheckEnvironment`'s `workdir` must be decided *before* `build_lint_repair(workdir)`/`build_build_check_repair(workdir)` build their node's `ActionPair`s, since atomicguard's `SubprocessGenerator` bakes `cwd` in at construction rather than resolving it per call the way `RealCheckNode`'s commands do. The directory itself doesn't need to exist yet - only `env.reset_to_state()` needs it to.

## Not decided

- **Whether these ever grow into a shared, multi-node graph** (e.g. folding both back into `release_pipeline`'s six nodes, atomicguard-backed). Not needed for what this phase demonstrates - `GuardFirstExecutor`'s check-then-repair pattern doesn't need an AND-join to show, and each scenario proving its own repair in isolation keeps the two deterministic cases and the two still-unbuilt LLM-based cases cleanly separable. Left for whichever of `type-check`/`architecture-test`'s repairs gets built next to decide, on its own merits.
