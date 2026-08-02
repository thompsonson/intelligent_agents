# Algorithm Fit: Backtracking Exploration (Discovery Step 2)

## Purpose

`../algorithm_fit.md` (step 1) built `DiscoveryAgent` as a forward-committed walk: at a branch, pick the lowest-id neighbor and never look back — a real, structural inability, not a choice, because step 1's movement rule denied returning to any previously-visited node at all. On `pipeline_fanout_lite`, that walk reaches the goal (`deploy`) having sensed only 4 of the graph's 6 nodes; `unit-tests`/`integration-tests` are stranded permanently, by design.

The trigger for revisiting that design wasn't the stranding by itself — it surfaced while scoping a *later* step (`requires`/AND-joins): an AND-gated node like `merge-gate` might need a prerequisite (`integration-tests`) that the committed branch never reached, and step 1's agent has no way to go get it. The first instinct was that AND-joins themselves would need a "teleport to a known-but-unvisited node" move to resolve that. This document is the smaller, prior step that removes the need for a teleport at all: give the agent the ability to retrace its own path, and it can reach any node reachable from `start` on its own, without a new movement primitive.

## What changes, and what doesn't

**Unchanged:** `DiscoveryNode`, `DiscoveryEnvironment`, `sense_edges()`, `get_move_cost()` — nothing about the environment moves. `pipeline_fanout_lite` is reused exactly as step 1 built it; no new scenario needed (see below).

**Changes:** `DiscoveryAgent`'s traversal policy and stopping condition.
- **Backtracking**: when the current node has no unvisited neighbor left, the agent may move back to the node it arrived from — retracing an edge it has already sensed and already walked forward across once, not jumping to an arbitrary known-but-unvisited id. This is why it isn't the teleport step 1's "no teleporting" rule forbids: teleporting means reaching a node with no walked path to it at all; backtracking means undoing steps along a path that demonstrably exists, because the agent is the one who just walked it.
- **Stopping condition**: from "stop at the first node with no `notifies`" to "stop once nothing known-but-unvisited remains reachable." Full exploration, not goal-seeking.

## Why this is a known problem, with a known-best answer

This is the "exploring an unknown graph" problem: an agent that can only see the edges of the node it currently occupies, must physically traverse an edge to see more, and wants to visit everything reachable. Two distinct results matter here, from two different versions of the problem, worth keeping separate rather than treating as one paper's finding:

- **The free-retrace bound is graph-traversal folklore, not a single paper's contribution.** Once an explorer is allowed to retrace an already-traversed edge for free — undo the last move, no new information, no new cost — depth-first search is essentially optimal: it visits every reachable node using at most twice the number of edges in the reachable subgraph. This falls straight out of how DFS works (every edge is crossed at most once forward and once on the way back out of it); it holds for undirected graphs, and for directed graphs whenever the explorer is specifically granted a free "return to where I came from" move — exactly the move this step adds to `DiscoveryAgent`.
- **Deng & Papadimitriou's actual, harder result is about the case *without* that free move.** Their paper *"Exploring an Unknown Graph"* (FOCS 1990 / *J. Graph Theory* 1999) studies a directed, strongly-connected graph where every move — including any move "back" — must follow a real directed edge; there is no free undo. Under that stricter model, they show the competitive ratio (exploration cost vs. the best possible offline tour) depends on the graph's *deficiency* (how many edges would need adding to make it Eulerian) and can be unbounded in the worst case.

Granting `DiscoveryAgent` a free backtrack-to-parent move is exactly what sidesteps DP's hard case: it turns the directed `notifies` graph into something exploration-equivalent to the free-retrace setting, which is why the `2×|edges|` bound applies here at all, and why DP's own hardness result doesn't. `pipeline_fanout_lite`'s move-cost model (`get_move_cost` = flat 1) makes that bound concrete rather than abstract: every backtrack step is a real, counted move, not a free rewind — it's the "moves are real" part of the setup that keeps this an honest test of the bound, not the reason the bound has an exception.

## Why not BFS

BFS explores layer-by-layer, which implicitly assumes the ability to be at (or cheaply reach) every node on the current frontier before advancing to the next layer. An agent that must physically walk between frontier nodes pays real move cost for that — on `pipeline_fanout_lite`, a literal BFS order would walk `commit → lint`, back to `commit`, then `commit → unit-tests`, back to `commit`, then down into `merge-gate`, and so on, re-walking the same edges repeatedly to hop between branches. It isn't that BFS gives a wrong answer — it visits everything DFS does — it's that BFS's natural implementation ignores the cost model this environment actually has, where DFS's "go deep, backtrack only when stuck" pattern is the one that respects it. This is the standard trade-off in the literature too: DFS-style exploration is preferred whenever movement is costly and backtracking is the only way to reach a skipped branch.

## Why not something newer

The genuinely newer work in unknown-graph exploration is mostly bad news for *directed* graphs specifically, not a better algorithm — and it's the Deng & Papadimitriou result named above, not a separate one: without a free backtrack move, no online strategy can guarantee a bounded competitive ratio on a general strongly-connected directed graph — an adversarial topology can force arbitrarily wasteful backtracking on *any* algorithm. That's a property of "directed edges, unknown up front, no free undo" as a problem class, not a gap specific to DFS that a cleverer algorithm closes — and it's precisely the case this step's free-backtrack rule takes us out of. The practical response the field actually uses is the one this repo is already doing — constrain the scenario (bounded branching, reconvergence, no adversarial dead-ends) — not searching for an algorithm that doesn't exist.

The other genuinely modern direction is learned/RL-style exploration (curiosity-driven exploration, learned traversal policies), which is real but solves a different problem: those methods are built for stochastic, reward-shaped environments where a policy is trained over many episodes. `DiscoveryEnvironment` is deterministic and evaluated in a single walk — there's no reward signal to learn from, and no repeated trials the way `LRTAStarLearner` gets. Bringing in a learned policy here would be a different flavor of agent than anything else in the repo (utility-learning vs. this repo's fixed, inspectable rules), not a better fit for what this step is actually teaching.

**Conclusion:** DFS-with-backtrack, for the same reason the literature converges on it — it's provably the right answer for "must physically move, can always retrace, wants full coverage," not merely the simplest option on hand.

## A side effect: this resolves step 1's flagged goal ambiguity

`../environment_design.md`'s "Resolved: goal" section flagged that "a node with no `notifies`" doesn't distinguish *the* goal from an incidental dead end if a scenario has more than one reachable terminal, and worked around it by requiring `scenario.md` to have exactly one. Under full exploration, that workaround isn't needed: there's no longer a single privileged "goal" to disambiguate — every no-`notifies` node the agent reaches is just a terminal it visits and stops expanding from, the same as any other node whose neighbors are all already visited. Multiple terminals would simply all get visited. This document doesn't retract step 1's walk (it's still correct for the policy it describes) — it supersedes the *constraint* that policy imposed on scenario design going forward.

## Walked through on `pipeline_fanout_lite`, same topology as step 1

Reusing the exact graph, deliberately, to make the contrast with step 1's table legible on identical data rather than a new example:

| # | Move | From | To | Why |
|---|---|---|---|---|
| 1 | sense | — | `commit` | start |
| 2 | move+sense | `commit` | `lint` | lowest unvisited id in `commit`'s notifies |
| 3 | move+sense | `lint` | `merge-gate` | only unvisited neighbor |
| 4 | move+sense | `merge-gate` | `deploy` | only unvisited neighbor |
| 5 | — | `deploy` | — | no `notifies`; no unvisited neighbor — dead end, backtrack |
| 6 | backtrack | `deploy` | `merge-gate` | retrace |
| 7 | — | `merge-gate` | — | `deploy` already visited, nothing new — backtrack |
| 8 | backtrack | `merge-gate` | `lint` | retrace |
| 9 | — | `lint` | — | `merge-gate` already visited, nothing new — backtrack |
| 10 | backtrack | `lint` | `commit` | retrace |
| 11 | move+sense | `commit` | `unit-tests` | last unvisited neighbor of `commit` |
| 12 | move+sense | `unit-tests` | `integration-tests` | only unvisited neighbor |
| 13 | — | `integration-tests` | — | notifies `(merge-gate,)`, already visited — backtrack |
| 14 | backtrack | `integration-tests` | `unit-tests` | retrace |
| 15 | — | `unit-tests` | — | nothing new — backtrack |
| 16 | backtrack | `unit-tests` | `commit` | retrace |
| 17 | — | `commit` | — | nothing new, no parent to backtrack to — done |

All 6 nodes visited (`commit`, `lint`, `merge-gate`, `deploy`, `unit-tests`, `integration-tests`). Counting only the actual moves (rows 2, 3, 4, 6, 8, 10, 11, 12, 14, 16 — the `move+sense`/`backtrack` rows; the `—` rows are dead-end observations at a node already reached, not moves) gives **10 moves against 6 edges**, comfortably inside the `2×|edges| = 12` bound. `merge-gate` is reached twice (steps 4 and 13's neighbor check) but only *sensed* once — the second arrival finds nothing new and immediately backtracks, so `nodes_sensed` stays at 6, not 7.

## What this means for the later `requires`/AND-joins step

This is the piece of groundwork that step was actually blocked on. With backtracking in place, an AND-gated node with an unsatisfied prerequisite doesn't need a detour/teleport mechanism at all — it can be treated as a temporary dead end: the agent backtracks away from it exactly the way it backtracks from any node with no unvisited neighbor, continues exploring elsewhere, and naturally arrives back at the gated node later once full exploration has covered the prerequisite. The verbatim sketch from that conversation — *"when an agent arrives it checks all requires are satisfied, moving to any that are not satisfied as a first action"* — becomes, more precisely: *if requires aren't satisfied, don't count this node as explored-through yet; let ordinary backtracking carry the agent elsewhere, and re-check requires whenever the walk returns here.* Still a later step, not designed further here — recorded so the connection isn't lost.

## Not decided

- **Whether `result.path` records every move (including backtracks) or only first-visit order.** The worked table above shows both; which one `DiscoveryWalkResult.path` should actually store — full move log vs. a compressed "nodes visited, in order first sensed" — is an implementation question for the TDD pass, not fixed here.
- **Whether backtrack moves count against `get_move_cost()` in whatever total cost the result reports.** They're real moves under the environment's cost model (flat 1 each), so the honest answer is probably yes; left to implementation to confirm this doesn't quietly get treated as free.
- **Tie-break order when backtracking has more than one still-unvisited grandparent option** — doesn't arise on `pipeline_fanout_lite` (it's a simple stack: always backtrack to the immediate parent), but worth naming as a place a richer scenario could expose a real choice later.

## Related documents

- [`../algorithm_fit.md`](../algorithm_fit.md) — step 1's forward-committed policy and its "DFS vs. BFS doesn't literally apply" claim, which this document's backtracking addition supersedes (the claim was correct for the policy it described).
- [`../environment_design.md`](../environment_design.md) — the primitives this step reuses unchanged, and the goal-ambiguity flag this step resolves via the full-exploration reframe.
- [`../scenario.md`](../scenario.md) — `pipeline_fanout_lite`'s topology, reused here rather than duplicated.
