# Algorithm Fit: `fix_pr_with_variants`

## Purpose

`environment_design.md` specifies `GroupNode` and an explicit goal; `scenario.md` specifies the concrete graph. This document walks through how each of the four existing algorithms behaves once both exist — which ones get a genuinely new capability worth building, which ones stay exactly as they are, and which ones develop a new, honest limitation worth documenting rather than silently accepting.

## `TopologicalExecutor` — the naive baseline, and it stays naive on purpose

Once `fix-approach` passes, `is_satisfied()` (per `environment_design.md`) means `ready_nodes()` returns **all three** `gen-patch-*` variants simultaneously — they share the same `requires`. `TopologicalExecutor` attempts them in sorted order with no concept of "stop once the group they feed is already satisfied." Concretely: it attempts `gen-patch-comprehensive` first (alphabetically first of the three), and — if it passes — `patch-ready` is now satisfied. `TopologicalExecutor` has no way to know that, and goes on to attempt `gen-patch-minimal` and `gen-patch-test-driven` anyway, spending two more attempts (and, if either has `retry_flavor="repair"`, real learnable cost) on work the group didn't need.

This isn't a bug to fix in `TopologicalExecutor` — it's the same role it's played throughout this repo: the baseline with "no heuristic, no learning, no repair" (`algorithm_fit.md`'s original table). The waste it produces here is now a **measurable, demonstrable quantity** — attempts spent on losing OR-siblings — that a smarter algorithm can be shown to avoid. Worth a test asserting exactly this: all three variants attempted regardless of order or outcome.

## `AOStarExecutor` — where a real, new capability belongs

This is the one that should change. AO*'s entire reason for existing is correct AND/OR composition (`search_algorithms/ao_star.md`), and "don't explore an alternative once you already have a solution for that OR-node" is classical AO* behavior (Nilsson's `SELECT-NODE` only ever expands nodes on the *current best partial solution* — a satisfied OR-node's other children are never part of that). Concretely, this needs `AOStarExecutor.step()` to filter `ready_nodes()` further: exclude any node that is a member of a `GroupNode` already satisfied by a *different* member.

Worked through on this scenario: `gen-patch-comprehensive` passes first (say), satisfying `patch-ready`. On the next `step()`, `AOStarExecutor` would compute `ready_nodes()` as before — but now needs to check each candidate against group membership and skip `gen-patch-minimal`/`gen-patch-test-driven` since their group is already satisfied. This is the first executor-level change any of the OR-group work actually requires (`environment_design.md` was explicit that basic gating needs none) — and it belongs on `AOStarExecutor` specifically, not the environment, because "should I bother exploring this alternative" is a search-strategy decision, not a graph-structure fact.

Cost composition needs one more decision (flagged, not resolved, in `environment_design.md`'s "Not decided"): `h(patch-ready)` once satisfied should be the cost of whichever variant actually passed — not a `min` over all three, since the other two were never attempted and have no real observed cost to compare.

## `DStarLiteExecutor` — the story `pr_merge_lite` couldn't tell

Experiment 2 (`documentation/task-graph/experiments/02_d_star_lite_pr_merge_lite.md`) found, honestly: "on a strict AND-chain there's no alternate route the way a maze does — breaking any single node makes everything downstream unreachable." This scenario is the first place D* Lite gets to do what the maze bridge actually demonstrates: **reroute**.

Concretely: the Driver breaks `gen-patch-minimal` *before* `fix-approach` even resolves. Once `fix-approach` passes, all three variants become ready; `gen-patch-minimal` returns `FATAL` immediately (broken), but `gen-patch-comprehensive` and `gen-patch-test-driven` are unaffected — one of them passing still satisfies `patch-ready`, and `released` is still reachable. This is qualitatively different from every break exercised so far in this repo: the run **doesn't stall waiting for a fix** — it finds a different way through, in the same run, without any Driver intervention at all. Worth a test contrasting this directly against `pr_merge_lite`'s break/fix experiment, where the only path forward *was* waiting for the Driver.

The interesting edge case to design for: what if the Driver breaks **all three** variants? Then `patch-ready` becomes genuinely unsolvable (every member fatal, per `environment_design.md`'s inverse-of-AND-node rule), and D* Lite is back to needing a fix — same as the AND-only case. Worth demonstrating both: rerouting when at least one alternative survives, falling back to wait-for-repair when none do.

## `LRTAStarLearner` — the natural pairing, still deferred

This is where the real system's actual motivation shows up most directly: `atomicguard`'s archive proposes a "Difficulty-Aware Agent" that learns "`<15 min` → try `gen_patch_minimal` first... `1-4 hours` → try `gen_patch_test_driven` + more retries." That's exactly `LRTAStarLearner` learning a separate `h_table` entry *per variant* (all three are already `retry_flavor="repair"`, so today's flavor-isolation logic already tracks each one correctly) — and then something (AO*, seeded with those learned priors) choosing the historically cheapest variant *first* rather than alphabetically.

Per the "combinations worth naming, not building yet" section of the original `algorithm_fit.md`, this is that same deferred combination — now with a concrete, real-world-motivated reason to actually build it, rather than only a structural one (fail-fast ordering among siblings with no real alternatives to choose from). Still not proposed as the next build here — consistent with wanting to understand the four algorithms' individual behavior on this scenario first, per the current line of work, before combining any of them.

## Explicitly deferred: hidden topology / Q-learning

None of the above requires hiding `requires` from the agent or building a learning policy over an action mask — every algorithm here still gets an honest `ready_nodes()` and decides what to do with it. The harder version (`c` in the earlier three-part scope: agent doesn't know the dependency structure, must discover it, closer to `atomicguard`'s actual `TabularPolicy`/action-mask RL work) stays out of scope until there's a learning agent built to make use of it — flagged already, restated here for this scenario specifically: `fix_pr_with_variants` is designed to make sense with `requires` and group membership fully known and honestly reported, the same as every other scenario in this repo.

## Suggested build order, once this moves to code

1. `fix_pr_with_variants` scenario + `GroupNode`/goal support in the environment — proves the gating logic (`environment_design.md`'s `is_satisfied()`) works with zero executor changes, using `TopologicalExecutor` as-is.
2. `TopologicalExecutor`'s wasteful-but-correct behavior on the same scenario — a test asserting all three variants get attempted regardless, establishing the baseline the next step improves on.
3. `AOStarExecutor`'s early-stop-on-satisfied-group — the first genuine executor-level change, hand-verifiable the same way `merged`'s two-way join was in the original `algorithm_fit.md`.
4. `DStarLiteExecutor`'s reroute-around-a-broken-variant — direct contrast against `pr_merge_lite`'s "no alternate route" finding.
5. (Later, not yet) `LRTAStarLearner` per-variant cost learning, feeding `AOStarExecutor`'s selection — the natural pairing, now real-world-motivated rather than only structural.
