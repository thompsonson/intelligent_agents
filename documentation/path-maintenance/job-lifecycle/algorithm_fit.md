# Algorithm Fit: Job Lifecycle

## Purpose

`environment_design.md` specifies `JobState`/`JobNode`/`JobGraphEnvironment`; `scenario.md` specifies the tick numbers. This document is short by design, for the same reason `graph-topology/algorithm_fit.md` was: one agent, no algorithm choice. It confirms the wait-loop capability against the concrete scenario, and predicts what the visualization needs to add on top of `graph-topology`'s.

## `PathMaintenanceAgent`'s wait loop, walked through on the scenario

Given `order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]` and the tick configuration in `scenario.md`:

| Node | Senses | States observed, in order | Action |
|---|---|---|---|
| `pre-commit` | *not sensed* | — | `order[0]`, same as steps 1-2 |
| `lint` | 3 | `PENDING → IN_PROGRESS → SUCCEEDED` | move on |
| `unit-tests` | 1 | `SUCCEEDED` | move on |
| `merge` | 1 | `SUCCEEDED` | move on |
| `deploy` | 2 | `PENDING → FAILED` | `repair_node("deploy")`, then move on |

`result.repairs_performed == ["deploy"]`, `result.senses_performed == {"lint": 3, "unit-tests": 1, "merge": 1, "deploy": 2}`, `result.success is True`. Total: 7 `get_job_state()` calls, 3 `advance_jobs()` calls, 1 repair — across a graph that, in step 2, took exactly 4 senses and 2 repairs to walk. The difference is entirely `lint`'s and `deploy`'s waiting, visible as a number for the first time in this arc (`senses_performed`), not just as "it happened."

## Why not `task_graph_solver`'s executors, restated once more

Same reasoning as `graph-topology/algorithm_fit.md`, now with an additional, sharper reason `attempt()` specifically doesn't fit: `AttemptOutcome` has no percept for "not resolved yet" at all — `PENDING`/`IN_PROGRESS` don't map onto `PASS`/`RETRY`/`FATAL` in any honest way. `RETRY` means "a paid attempt failed, try again, consuming budget"; `PENDING`/`IN_PROGRESS` mean "no attempt has failed or succeeded, nothing has been paid for, just wait." Forcing `IN_PROGRESS` into `RETRY` would silently start charging retry budget for a job that hasn't actually failed at anything — the exact conflation `environment_design.md`'s original review flagged in the abstract, now visible as a concrete wrong answer on `lint`, which never fails at all but would still burn budget on every wait.

## What the visualization needs to add

`graph-topology`'s `graph_view.py` has four node colors (`future`/`clear`/`repaired`/`needs_repair`) — enough for a state that's binary once sensed. This step's states aren't binary while unresolved, so two more are needed:

- **`pending`** — sensed, ticks elapsed `0`. Suggest a pale, cool color (e.g. `lightyellow`) distinct from every existing green/red, since it's neither "fine" nor "broken," just "not started."
- **`in_progress`** — sensed, ticks elapsed `> 0` but not yet resolved. Suggest a warmer, more saturated shade of the same family (e.g. `gold`), so `pending → in_progress` reads as one color deepening rather than two unrelated colors, mirroring how `future → clear` and `needs_repair → repaired` are each one hue at two depths.

### What to watch for in the GIF (predicted, not yet built)

More frames than `deploy_chain_lite`'s step-2 GIF (7 sense/repair events instead of 4, plus 3 `advance_jobs()` — worth deciding whether an `advance_jobs()` call gets its own frame or is folded into the next sense's frame; leaning toward its own frame, captioned distinctly from a sense, so "time passing" is visually distinguishable from "checking status"):

- **`lint` visibly cycles through three colors**, not two: pale yellow → gold → dark green. The first node in this whole arc whose color changes more than once before settling.
- **`unit-tests` and `merge` both resolve in a single frame each, no intermediate color** — the same "instant, no drama" contrast `deploy_chain_lite` already established, now doing double duty: instant relative to a *lifecycle*, not just relative to *repair*.
- **`deploy` shows `pending` (pale yellow) before turning red** — a node can now be sensed and *not yet be known to need repair*, a genuinely new visual moment nothing in steps 1-2 could produce, since their `NEEDS_REPAIR` was always immediately visible on first sense.

## Related documents

- [`../environment_design.md`](../environment_design.md) — the design this experiment implements, including the resolved `advance_jobs()` design gap.
- [`../graph-topology/algorithm_fit.md`](../graph-topology/algorithm_fit.md) — step 2's equivalent, on the same graph without a lifecycle.
- [`documentation/task-graph/guard-first/algorithm_fit.md`](../../task-graph/guard-first/algorithm_fit.md) — the precedent for a short `algorithm_fit.md` when only one agent is introduced.
