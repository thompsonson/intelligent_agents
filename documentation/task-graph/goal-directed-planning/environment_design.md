# Goal-Directed Planning: Environment Design

## Purpose

`guard-first/environment_design.md` designed a free `check_invariant()` sensor — cheap enough to call before ever paying for a repair. This document is about what becomes possible once that exists: an executor that doesn't just check-then-repair *the node it happens to be standing on* (still a walk-as-you-go strategy), but senses across the whole goal-relevant graph before committing to any plan at all.

Three strategies are on the table, and they're worth naming precisely because conflating them would blur real algorithmic differences, the same way conflating "losing OR-sibling" and "true orphan" would have in the OR-groups work:

1. **Walk-as-you-go.** Reach a node, check-then-repair it, move on. This is everything built so far — `TopologicalExecutor`, `AOStarExecutor`, `DStarLiteExecutor`, and the guard-first `GuardFirstExecutor` design. None of them look past the immediately-ready frontier.
2. **Sense-then-plan.** Check the *whole* goal-relevant graph up front (free, via `check_invariant()`), build an explicit plan of what still needs repairing, then execute it.
3. **Goal-directed scope.** Only ever consider nodes that could possibly matter to `goal` — never even look at a true orphan like `check-disk`, rather than tolerating it as an allowed failure (today's `is_goal_reached()` behavior).

## The key insight: sensing isn't gated by `requires` — attempting is

This is the thing that makes (2) genuinely more powerful than (1), not just a reordering of the same work. `requires` exists because you can't safely *repair* a node (mutate world state) before its prerequisites are done — but *checking whether a node's invariant already holds* is a pure observation of the current world, uncoupled from workflow step ordering. In the real system, this is exactly why `ContainerSubprocessGuard` doesn't need an artifact: asking "does the container already look right" doesn't require having replayed every step that led there.

Concretely: if `released` (the goal, deepest node in `pr_merge_lite`'s chain) is already true — the toy equivalent of "this workflow already completed in a previous run" — a **sense-then-plan** executor can check `released` directly, find it already satisfied, and stop. Zero other nodes touched. A **walk-as-you-go** executor, even a guard-first one, structurally cannot do this: it only checks a node once it's reached in frontier order, so it must still traverse `ci-check` → `generate-actions` → `apply-actions` → `merged` → the three `deploy-*` branches before it ever gets to check `released`, even though every one of those checks (and any repairs they'd trigger) turns out to have been unnecessary. This is the measurable, demonstrable difference between (1) and (2) — analogous to how OR-group pruning was the measurable difference between `TopologicalExecutor` and `AOStarExecutor`.

## One algorithm, not two: recursive `ensure()`

Approaches (2) and (3) turn out to be the same mechanism, not two separate features bolted together. A goal-directed, sensing-aware planner is naturally recursive and backward-chaining — start at the goal, and only ever visit a node because something already known-necessary required it:

```python
def ensure(node_id: str) -> bool:
    """Return True if node_id ends up satisfied. Never visits a node unless
    something already on the path from the goal needed it - goal-directed
    scope (3) falls out for free, not as a separate precomputed set."""

    if node_id in self.resolved:              # memoized - AND-diamonds
        return node_id in self.satisfied      # aren't re-checked twice

    if node_id in self.env.groups:
        group = self.env.groups[node_id]
        for member in sorted(group.members):  # or cost-ordered, once LRTA*
            if ensure(member):                 # short-circuits remaining
                return True                    # members - same pruning
        return False                           # AOStarExecutor already has

    if self.env.check_invariant(node_id):      # free - the sense-then-plan
        self.satisfied.add(node_id)            # capability (2). No cost
        return True                            # paid, requires never even
                                                # inspected for this node.

    node = self.env.nodes[node_id]
    if not all(ensure(dep) for dep in node.requires):
        self.unreachable.add(node_id)
        return False

    outcome = repair_loop(node_id)             # unchanged attempt() loop
    ...

def run(self) -> ExecutionResult:
    success = ensure(self.env.goal) if self.env.goal else all(
        ensure(n) for n in self.env.nodes
    )
    ...
```

Three properties fall out of this one function, not three separate mechanisms:
- **Goal-directed scope (3):** `check-disk`, unreachable from `released` via any `requires` edge, is simply never a parameter to `ensure()` — not filtered out of a candidate list, never considered in the first place.
- **Sense-then-plan short-circuiting (2):** if `ensure("released")` finds `check_invariant("released")` true immediately, `node.requires` is never even read — `ci-check` through `deploy-promote` are never visited, checked, or repaired.
- **OR-group pruning:** falls out of the existing `for member in sorted(...): if ensure(member): return False` short-circuit — the same capability `AOStarExecutor` already has, arising here from top-down recursion instead of forward-frontier filtering.

## An honest tension worth surfacing, not quietly resolving

Classical AO* (Nilsson's formulation) is a **top-down, goal-directed** algorithm: `SELECT-NODE`/`EXPAND` only ever touch nodes on the current best partial solution back from the root. `ensure()` is a closer match to that description than our existing `AOStarExecutor`, which walks the forward `ready_nodes()` frontier and (per `test_ao_star_still_attempts_the_disconnected_orphan`) still visits nodes with no bearing on the goal. That's not a new bug in `AOStarExecutor` — it was built honestly against the spec at the time, before `goal` existed as a concept — but it means this document is proposing something that arguably deserves the "AO*" name more than the executor currently holding it.

This needs a decision, not a quiet rename: either (a) `ensure()` becomes a new, separately-named executor (e.g. `PlanningExecutor` or `GoalDirectedExecutor`) and `AOStarExecutor` keeps its current forward-frontier behavior with a documentation note about the distinction, or (b) `AOStarExecutor` itself is revised to the top-down `ensure()` form, and its existing forward-frontier tests are revisited. Leaning toward (a) — least disruptive, keeps the OR-groups build's existing tests meaningful — but this is exactly the kind of naming decision that shouldn't be made silently, given this project's track record of correcting its own overclaims (the D* Lite "reroute" story, the AO* cost-composition rule).

## Scenario sketch (not yet written as scenario.md)

Reuse `pr_merge_lite` unmodified, plus one `invariant_pass_probability` override on `released` itself (or `merged`, for a partial-completion story) — no new topology needed, consistent with the project's standing rule against inventing new domain vocabulary. Two contrasts worth a test each:

- **`GuardFirstExecutor` vs. the new planner when `released`'s invariant is already true:** `GuardFirstExecutor` still performs 5+ free checks (one per node reached in frontier order) before it ever reaches `released`; the planner performs exactly 1.
- **Goal-directed scope on `pr_merge_with_variants`:** the planner never calls `check_invariant` or `attempt` on `check-disk` at all — contrasted with `AOStarExecutor`, which (per the existing test) does.

## Not decided

- **Naming** — see the tension above; needs a decision before any code.
- **Cost-ordering within `ensure()`'s group loop.** Currently proposed as `sorted(group.members)`, matching every other executor's determinism-by-id default. Once `LRTAStarLearner` has per-variant costs (deferred per `or-groups/algorithm_fit.md`), this loop is the natural place to try cheapest-known-first instead.
- **Whether `check_invariant()` on a node whose `requires` are themselves unsatisfied is meaningful in every scenario**, or only in ones deliberately built to allow it (a check reporting "already true" for a node whose prerequisites never ran is a strong claim about the toy world's semantics — fine for a toy, worth a sentence of caution if this pattern ever informed real `atomicguard` work).
- **Whether `ensure()`'s memoization (`self.resolved`) needs to interact with `DStarLiteExecutor`-style re-sensing** (a fixed goal-directed plan computed once vs. an incremental repair loop that keeps sensing `drain_changed_tasks()`) — not exercised by the scenario above; flagged for whenever these two ideas are combined, not before.
