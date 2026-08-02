# Algorithm Fit: AND-Joins (Discovery Step 3)

## Purpose

`environment_design.md` specifies `requires`, the three-state model (known/visited/cleared), and `sense_requires()`. It deliberately leaves the traversal algorithm undecided, because the obvious extension of step 2's algorithm — "candidates exclude `visited`, and a blocked node just doesn't count until it's `cleared`" — turns out not to be enough on its own. This document works through why, and what actually closes the gap.

## Prior art, named honestly

Three separate things are going on here, and only two of them have real names.

**Readiness — Kahn's algorithm.** "Repeatedly extract nodes whose prerequisites are all satisfied, process them, repeat" is textbook topological sort by frontier extraction (Kahn, 1962). It's not just an analogy here — it's already implemented in this repo: `_ready_nodes()` in `path_maintenance/core/environment.py`, used by both `PathGraphEnvironment` and `JobGraphEnvironment`, is exactly this computation. `task_graph_solver`'s `AOStarExecutor` does the same AND-node bookkeeping plus heuristic cost estimation on top, which isn't needed here — there's no branching cost choice at a `requires` gate, just a boolean.

**Exploration — DFS with a free retrace.** Covered and cited properly in `backtracking-exploration/algorithm_fit.md` (Deng & Papadimitriou's problem framing; the `2×|E|` folklore bound). That literature has no AND-gating in it at all — it's a pure reachability problem.

**The combination doesn't have a name, as far as I know.** "Explore an unknown graph, some nodes can't be considered done until others are, and getting back to a needed node means physically retracing a known route rather than teleporting" is what falls out of gluing the two ideas above together. I'd rather say that plainly than force a citation onto it — the DP attribution got over-claimed once already in this project (`backtracking-exploration/algorithm_fit.md`'s own review history), and I don't want to repeat that mistake in the other direction by inventing a source for this one.

**The genuinely relevant prior art is inside this repo: `PlanningExecutor._ensure()`** (`task_graph_solver/algorithms/planning.py`), one of the four things explicitly parked with *"we will revisit them once discovery is done."* `_ensure(node_id)` is classical backward chaining: before attempting a node, it recursively resolves `node.requires` first (`all(self._ensure(dep) for dep in sorted(node.requires))`), never attempting anything whose preconditions aren't already handled. This is the same idea this step needs — don't count a node as done until its prerequisites are — but resolved *eagerly*, because `_ensure()` has the whole graph in hand (`self.env.nodes[node_id]`, no discovery involved). This step needs the same idea resolved *reactively*, because the graph isn't known ahead of time. Same concept, opposite direction, because the environments are opposites. Worth being explicit that this is a deliberate non-reuse: `_ensure()`'s eager recursion isn't wrong, it's answering a different environment's question.

## Why the obvious extension doesn't work

The natural first attempt: keep step 2's candidate rule but loosen it — `candidates = [n for n in notifies[current] if n not in cleared]` instead of `not in visited`, so a blocked node stays a valid forward-move target for anyone who notifies it, for as long as it takes.

Hand-tracing this on `scenario.md`'s graph exposes why it's broken, within the first few moves:

1. `commit → lint → merge-gate`. `merge-gate.requires = (lint, integration-tests)` — `integration-tests` isn't even visited yet, so `merge-gate` doesn't clear. Candidates from `merge-gate` are `[]` (blocked) → backtrack to `lint`.
2. Back at `lint`: candidates are `[n in notifies(lint) if n not in cleared]` = `[merge-gate]` — `merge-gate` is still not `cleared`, so it's *still a candidate*, exactly as it was a move ago. `lint` moves into it again.
3. `merge-gate` is still blocked (nothing about `integration-tests` has changed). Backtrack to `lint` again. Candidates: `[merge-gate]`. Move into it again. Blocked again. Backtrack again. **Forever** — `unit-tests`, the only branch that could actually clear `integration-tests`, never gets a look-in, because `lint`/`merge-gate` never stop ping-ponging long enough to backtrack past `lint` to `commit`.

This is a real non-termination bug, caught by hand-tracing before it became a runtime infinite loop — the same discipline as catching the `advance_jobs()` and `repair_node()` bugs in `job-lifecycle` during TDD, just moved one step earlier, into the design phase. **Excluding only `cleared` breaks the property that made step 2's backtracking terminate at all**: a dead end has to actually stop being a candidate once it's been tried, or there's nothing to bound the walk.

## The algorithm: exploration, unchanged, plus a readiness sweep between phases

Keep step 2's candidate rule exactly as it is — `notifies not in visited` — so a blocked node behaves like an ordinary dead end *within* a given exploration phase: tried once, backtracked from, never retried during that phase. Layer a second, outer step on top, run only once the inner DFS-with-backtrack has fully unwound back to its own root (parent stack empty):

1. **Explore** (identical to step 2, plus one gate): at each node, if `requires` aren't all `cleared` yet, treat it as having no candidates regardless of `notifies` — forces an immediate backtrack, same mechanics as a true dead end.
2. **When exploration terminates**, check every `visited`-but-not-`cleared` node: is it satisfiable *now*, given everything `cleared` during that phase?
3. **If yes for any of them**: pick one (lowest id, same tie-break convention as everywhere else in `DiscoveryAgent`), compute a route to it using only *already-sensed* edges between *already-visited* nodes (a plain shortest-path search over the known subgraph — not a new sense, not a jump to an unknown id, since both the route and the destination are already fully known), walk that route (real moves, real cost, pushed onto a fresh parent stack as it goes), and resume exploration from there — back to step 1.
4. **If no blocked node newly clears**, stop. Whatever's left in `visited - cleared` goes into `DiscoveryWalkResult.blocked_nodes`.

This terminates because each outer iteration either clears at least one previously-blocked node (bounded by the total node count) or the outer loop ends — the same finite-progress argument `backtracking-exploration/algorithm_fit.md` used for plain backtracking, one level up.

Worth being precise about why replaying a known route isn't the teleport step 1 ruled out: teleporting meant jumping to a node with no walked-or-known path to it at all. Here, every hop on the route is an edge that was already *sensed* (read off some node's `notifies` during exploration), and every node on it is already `visited`. Walking it now is physically identical to walking any other sensed edge — it just happens to be one the tie-break rule didn't pick the first time a choice was available.

## Worked example on `scenario.md`'s graph

**Phase 1 — explore from `commit`:**

| Move | From | To | Note |
|---|---|---|---|
| 1 | `commit` | `lint` | `commit` clears trivially (`requires=()`) |
| 2 | `lint` | `merge-gate` | `lint` clears trivially |
| 3 | `merge-gate` | — | `requires=(lint, integration-tests)`; `integration-tests` not even visited — blocked, no candidates |
| 3 | `merge-gate` | `lint` | backtrack |
| 4 | `lint` | `commit` | dead end (only neighbor already visited) — backtrack |
| 5 | `commit` | `unit-tests` | last unvisited neighbor |
| 6 | `unit-tests` | `integration-tests` | `unit-tests` clears trivially |
| 7 | `integration-tests` | — | clears trivially; but its only neighbor (`merge-gate`) is already visited — dead end |
| 7 | `integration-tests` | `unit-tests` | backtrack |
| 8 | `unit-tests` | `commit` | dead end — backtrack |

Phase 1 ends back at `commit`, parent stack empty. `visited = {commit, lint, merge-gate, unit-tests, integration-tests}`, `cleared = {commit, lint, unit-tests, integration-tests}`. `merge-gate` is the one blocked node — but by the time phase 1 ends, both its requirements (`lint`, `integration-tests`) are now `cleared`.

**Readiness sweep:** `merge-gate` is checked against the now-`cleared` set — satisfiable. Route from `commit` to `merge-gate` over already-sensed edges: `commit → lint → merge-gate` (2 hops, ties with `commit → unit-tests → merge-gate`, broken alphabetically on the first hop — `lint` before `unit-tests`).

**Phase 2 — resume from `merge-gate`, having walked the route:**

| Move | From | To | Note |
|---|---|---|---|
| 9 | `commit` | `lint` | replaying the known route |
| 10 | `lint` | `merge-gate` | replaying the known route |
| — | `merge-gate` | — | `requires` now satisfied — clears, unlocking `deploy` |
| 11 | `merge-gate` | `deploy` | first time — never visited before |
| — | `deploy` | — | sensed for the first time; no `notifies` — dead end |
| 12 | `deploy` | `lint` | backtrack |
| 13 | `lint` | `commit` | backtrack |

Parent stack empties again; readiness sweep finds nothing left blocked. Walk ends.

**Totals:** `path` has 14 entries (13 moves). `nodes_sensed == 6` (every node, `deploy` last). `total_cost == 13`. `cleared == visited ==` all six nodes. `blocked_nodes == []`. `goal_reached is True` — and critically, `deploy` is the *last* node sensed, not the fourth move out of thirteen the way step 2's ungated walk sensed it third out of ten. That reordering is the entire point of this step.

## Not decided

- **Tie-break when more than one blocked node clears in the same sweep** — doesn't arise on this scenario (`merge-gate` is the only blocked node), but the natural extension is the same lowest-id rule used everywhere else.
- **A scenario exercising a genuine reachability violation**, so `blocked_nodes` comes back non-empty on purpose — `scenario.md`'s own "Not decided" flags this as the natural second scenario once this algorithm has real code to test against.

## Related documents

- [`environment_design.md`](environment_design.md) — `requires`, the three-state model, `sense_requires()`, and why the reachability constraint is a scenario responsibility rather than an environment one.
- [`scenario.md`](scenario.md) — `merge-gate.requires = (lint, integration-tests)` on the unmodified `pipeline_fanout_lite` topology, and why those two targets specifically.
- [`../backtracking-exploration/algorithm_fit.md`](../backtracking-exploration/algorithm_fit.md) — the DFS-with-retrace result this step's exploration phase reuses unchanged, and the finite-progress termination argument this step's outer sweep extends by one level.
- [`../../../task_graph_solver/algorithms/planning.py`](../../../task_graph_solver/algorithms/planning.py) — `PlanningExecutor._ensure()`, the eager, known-graph cousin of this step's reactive, discovered-graph readiness check.
