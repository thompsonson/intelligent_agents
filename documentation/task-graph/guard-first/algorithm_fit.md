# Algorithm Fit: Guard-First States

## Purpose

`environment_design.md` specifies `invariant_pass_probability` and `check_invariant()`; `scenario.md` specifies the concrete graph. This document is short by design, for a reason worth stating rather than leaving implicit: only one executor is being introduced here.

## `GuardFirstExecutor` — the one new capability this design adds

Modeled directly on `TopologicalExecutor`: same sorted-by-id frontier selection, same "drive to a terminal outcome" loop, with one addition inserted before the existing repair loop — check the invariant first, and only fall through to the paid `attempt()` loop if that check fails. On `scenario.md`'s graph: `ci-check` through the three `deploy-*` branches all have `invariant_pass_probability=0.0`, so each of them checks (for free, and gets a `False` back), then pays for a normal repair attempt exactly as `TopologicalExecutor` would. Only `released` — the last node reached — gets a `True` back from its free check, and is marked satisfied without ever calling `attempt()`.

This is a real, if modest, capability: on a graph where nothing is pre-satisfied, `GuardFirstExecutor` behaves identically to `TopologicalExecutor` (every check returns `False`, every node still gets repaired) — the free check costs nothing and changes nothing. It only pays off on a node whose invariant happens to already hold, and even then, only for *that one node*: it still had to walk every node before it in frontier order to get there.

## `TopologicalExecutor` — unchanged, and correctly so

`TopologicalExecutor` never calls `check_invariant()`. Given the identical scenario, it goes straight to `attempt(released)`. Since this scenario sets `pass_probability=1.0` for `released` too, the attempt still passes — the *outcome* is identical to `GuardFirstExecutor`'s (both succeed), but the *cost* differs: `TopologicalExecutor` paid for a repair attempt on `released` that `GuardFirstExecutor` got for free. That difference is invisible in `result.satisfied` (both contain `released`) but visible in `result.trace` (`GuardFirstExecutor`'s omits an entry for `released` entirely) — the same "measurable, demonstrable quantity" framing the OR-groups work used for its own baseline-vs-smarter contrast.

A sharper version of the same point, worth noting even though this scenario doesn't need it to make the case: if `released`'s `pass_probability` were set low enough that a real repair attempt could plausibly exhaust `rmax` and go `FATAL`, `TopologicalExecutor` could fail a run that `GuardFirstExecutor` succeeds at — the free check isn't just cheaper, it can never fail, since it's not subject to `rmax`/`r_patience` at all.

## Why not AO*, D* Lite, or the goal-directed planner here

`AOStarExecutor`'s AND-composition and OR-group pruning are orthogonal capabilities to check-before-repair — nothing here has an OR-group, so there's nothing for AO*'s pruning to do differently from `TopologicalExecutor` either. `DStarLiteExecutor`'s sensing loop is about *exogenous change to a node already given up on* — a different axis from *"is this node already true before we ever try it."* `PlanningExecutor` (`documentation/task-graph/goal-directed-planning/`) is the executor that actually gets more out of this exact scenario — see that document's `algorithm_fit.md` for the sharper contrast (checking the goal *first*, without walking anything at all). `GuardFirstExecutor` is deliberately the smaller, walk-as-you-go half of that story, kept separate so each capability is demonstrated on its own before being combined.

## What to watch for in the GIF

[`task_graph_solver/animations/guard_first_pr_merge_lite.gif`](../../../task_graph_solver/animations/guard_first_pr_merge_lite.gif) — every node turns green (satisfied) in frontier order, same pacing as the original AO* animation, except `released`: it turns **cyan**, not green, and the caption on that frame reads `check_invariant(released) → true`, not an `attempt` line. That's the entire capability, visible in one color difference on one frame.
