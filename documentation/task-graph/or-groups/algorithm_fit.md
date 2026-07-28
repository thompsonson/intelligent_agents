# Algorithm Fit: `pr_merge_with_variants`

## Purpose

`environment_design.md` specifies `GroupNode` and an explicit goal; `scenario.md` specifies the concrete graph — `pr_merge_lite` with `apply-actions` split into three variant strategies. This document walks through how each of the four existing algorithms behaves once both exist — which ones get a genuinely new capability worth building, which ones stay exactly as they are, and which ones develop a new, honest limitation worth documenting rather than silently accepting.

## `TopologicalExecutor` — the naive baseline, and it stays naive on purpose

Once `generate-actions` passes, `is_satisfied()` (per `environment_design.md`) means `ready_nodes()` returns **all three** `apply-actions-*` variants simultaneously — they share the same `requires`. `TopologicalExecutor` attempts them in sorted order with no concept of "stop once the group they feed is already satisfied." Concretely: it attempts `apply-actions-comprehensive` first (alphabetically first of the three), and — if it passes — `actions-ready` is now satisfied. `TopologicalExecutor` has no way to know that, and goes on to attempt `apply-actions-minimal` and `apply-actions-test-driven` anyway, spending two more attempts (real learnable cost, since all three are `retry_flavor="repair"`) on work the group didn't need.

This isn't a bug to fix in `TopologicalExecutor` — it's the same role it's played throughout this repo: the baseline with "no heuristic, no learning, no repair" (the original `algorithm_fit.md`'s table). The waste it produces here is now a **measurable, demonstrable quantity** — attempts spent on losing OR-siblings — that a smarter algorithm can be shown to avoid. Worth a test asserting exactly this: all three variants attempted regardless of order or outcome.

## `AOStarExecutor` — where a real, new capability belongs

This is the one that should change. AO*'s entire reason for existing is correct AND/OR composition (`search_algorithms/ao_star.md`), and "don't explore an alternative once you already have a solution for that OR-node" is classical AO* behavior (Nilsson's `SELECT-NODE` only ever expands nodes on the *current best partial solution* — a satisfied OR-node's other children are never part of that). Concretely, this needs `AOStarExecutor.step()` to filter `ready_nodes()` further: exclude any node that is a member of a `GroupNode` already satisfied by a *different* member.

Worked through on this scenario: `apply-actions-comprehensive` passes first (say), satisfying `actions-ready`. On the next `step()`, `AOStarExecutor` would compute `ready_nodes()` as before — but now needs to check each candidate against group membership and skip `apply-actions-minimal`/`apply-actions-test-driven` since their group is already satisfied. This is the first executor-level change any of the OR-group work actually requires (`environment_design.md` was explicit that basic gating needs none) — and it belongs on `AOStarExecutor` specifically, not the environment, because "should I bother exploring this alternative" is a search-strategy decision, not a graph-structure fact.

Cost composition needs one more decision (flagged, not resolved, in `environment_design.md`'s "Not decided"): `h(actions-ready)` once satisfied should be the cost of whichever variant actually passed — not a `min` over all three, since the other two were never attempted and have no real observed cost to compare.

## `DStarLiteExecutor` — where the story actually differs (corrected from the first pass)

The first version of this document claimed breaking one variant before it's ever attempted gives D* Lite a "reroute" story the AND-only `pr_merge_lite` couldn't tell. That's not right, and worth correcting rather than quietly fixing: since all three variants share identical `requires`, they all become ready **simultaneously** the instant `generate-actions` passes. If `apply-actions-minimal` is broken and gets attempted first, it returns `FATAL`, and the loop simply continues to the next ready candidate — `apply-actions-comprehensive`. **Every executor in this repo already does that**, including plain `TopologicalExecutor` — moving to the next ready item after one fails is baseline iteration, not D* Lite's sensing mechanism. Claiming this as a D* Lite capability would have been the same kind of overclaim `documentation/lrta/beyond_the_maze.md`'s "Purpose" section warns against elsewhere in this project.

The real, distinguishing D* Lite story on this scenario is narrower and still genuine: **recovering after every variant has been exhausted.** If the Driver breaks (or all three variants otherwise fail and exhaust their budgets) **all three** `apply-actions-*` nodes, `actions-ready` becomes genuinely unsolvable (every member fatal, per `environment_design.md`'s inverse-of-AND-node rule for groups), and `released` is unreachable — same as `pr_merge_lite`'s Experiment 2. If the Driver then fixes just **one** variant, `DStarLiteExecutor` senses it via `drain_changed_tasks()`, returns that one variant to consideration, retries it, and — if it passes — `actions-ready` is satisfied and the run completes. `TopologicalExecutor` given the identical sequence stays failed forever, per the same contrast already established in `documentation/task-graph/experiments/02_d_star_lite_pr_merge_lite.md`.

So this scenario doesn't give D* Lite a *new kind* of capability — it gives the *existing* repair-locality capability a group to apply to, instead of a single node. Worth being precise about that rather than implying D* Lite does something here it doesn't.

## `LRTAStarLearner` — the natural pairing, still deferred

This is where the real system's actual motivation shows up most directly: `atomicguard`'s archive proposes a "Difficulty-Aware Agent" that learns "`<15 min` → try `gen_patch_minimal` first... `1-4 hours` → try `gen_patch_test_driven` + more retries" (for the Django pipeline's own variants — the *pattern*, not the specific node names, is what transfers here). Mapped onto this scenario: `LRTAStarLearner` learning a separate `h_table` entry *per variant* (all three `apply-actions-*` nodes are already `retry_flavor="repair"`, so today's flavor-isolation logic already tracks each one correctly) — and then something (AO*, seeded with those learned priors) choosing the historically cheapest variant *first* rather than alphabetically.

Per the "combinations worth naming, not building yet" section of the original `algorithm_fit.md`, this is that same deferred combination — now with a concrete, real-world-motivated reason to actually build it, rather than only a structural one (fail-fast ordering among siblings with no real alternatives to choose from). Still not proposed as the next build here — consistent with wanting to understand the four algorithms' individual behavior on this scenario first, before combining any of them.

## Explicitly deferred: hidden topology / Q-learning

None of the above requires hiding `requires` from the agent or building a learning policy over an action mask — every algorithm here still gets an honest `ready_nodes()` and decides what to do with it. The harder version (`c` in the earlier three-part scope: agent doesn't know the dependency structure, must discover it, closer to `atomicguard`'s actual `TabularPolicy`/action-mask RL work) stays out of scope until there's a learning agent built to make use of it — flagged already, restated here for this scenario specifically: `pr_merge_with_variants` is designed to make sense with `requires` and group membership fully known and honestly reported, the same as every other scenario in this repo.

## Suggested build order, once this moves to code

1. `pr_merge_with_variants` scenario + `GroupNode`/goal support in the environment — proves the gating logic (`environment_design.md`'s `is_satisfied()`) works with zero executor changes, using `TopologicalExecutor` as-is.
2. `TopologicalExecutor`'s wasteful-but-correct behavior on the same scenario — a test asserting all three variants get attempted regardless, establishing the baseline the next step improves on.
3. `AOStarExecutor`'s early-stop-on-satisfied-group — the first genuine executor-level change, hand-verifiable the same way `merged`'s two-way join was in the original `algorithm_fit.md`.
4. `DStarLiteExecutor`'s recovery after all group members are exhausted — direct contrast against `pr_merge_lite`'s established "cannot recover from a fix after the fact" baseline, now applied to a group instead of a single node.
5. (Later, not yet) `LRTAStarLearner` per-variant cost learning, feeding `AOStarExecutor`'s selection — the natural pairing, now real-world-motivated rather than only structural.
