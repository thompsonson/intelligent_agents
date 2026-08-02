# Algorithm Fit: Discovery (Step 1)

## Purpose

`environment_design.md` specifies `DiscoveryNode`/`DiscoveryEnvironment`; `scenario.md` specifies `pipeline_fanout_lite` and deliberately stops short of walking it, leaving the traversal policy to this document. Unlike `graph-topology/algorithm_fit.md` (also short-by-design, also introducing exactly one agent), there genuinely is a decision to make here — but it turns out to be a narrower one than "DFS or BFS," for a reason worth stating plainly before picking either label.

## Why "DFS vs. BFS" doesn't literally apply

Classical DFS/BFS both assume the searcher can return to any previously-visited node for free, to expand whichever branch it skipped — a stack or queue holding "come back here later" is exactly that assumption made explicit. `environment_design.md`'s movement rule denies this outright: the agent can only move to an id in its **current** node's already-sensed `notifies`, and there is no backward edge. Once `DiscoveryAgent` leaves `commit` for `lint`, it has no way to return to `commit` and try `unit-tests` instead — not "chooses not to," *cannot*, the same way nothing in `path_maintenance/` lets an agent deviate from its computed `order`.

So the real decision at a branch point isn't "which do I explore first, saving the other for later" — it's "which do I commit to, permanently, right now." That's a single deterministic tie-break rule, not a search algorithm with a frontier data structure behind it. Reconvergence (`scenario.md`'s "why this shape") is what makes this safe rather than reckless: because every branch out of `commit` eventually reaches `merge-gate` and then `deploy`, committing to one branch over another can only cost sensing effort, never cost reaching the goal at all. That's the same shape of claim `graph-topology/algorithm_fit.md` made about its own AND-join — "no real algorithm choice is being made" — arrived at for a different structural reason (there: the plan is fixed before the walk starts; here: every path converges, so no choice is wrong).

**Superseded by step 2:** the "no backward edge" premise this section rests on is a property of *this step's* movement rule, not a permanent fact about the environment. [`backtracking-exploration/algorithm_fit.md`](backtracking-exploration/algorithm_fit.md) lifts it — retracing an already-walked path turns out not to be the teleport this section is ruling out — and once that's possible, "DFS vs. BFS" applies literally again, with DFS as the answer for reasons argued there.

## The policy: forward-committed, lowest-id tie-break

At any node, `DiscoveryAgent` moves to the lexicographically smallest id in that node's sensed `notifies` — the same alphabetical tie-break `ready_nodes()`/`TopologicalExecutor` already use elsewhere in this repo, reused for consistency rather than because anything about discovery specifically calls for alphabetical order. No lookahead, no preference for branches that might reach more of the known set — just a fixed, reproducible rule, since (per above) no smarter rule is needed to *guarantee* reaching the goal on this graph.

## Walked through on `pipeline_fanout_lite`

| Step | Current node | `sense_edges()` result | Known-but-unvisited after sensing | Moves to |
|---|---|---|---|---|
| 1 | `commit` (start) | `(lint, unit-tests)` | `{lint, unit-tests}` | `lint` (`lint` < `unit-tests`) |
| 2 | `lint` | `(merge-gate,)` | `{unit-tests, merge-gate}` | `merge-gate` (only option) |
| 3 | `merge-gate` | `(deploy,)` | `{unit-tests, deploy}` | `deploy` (only option) |
| 4 | `deploy` | `()` | `{unit-tests}` | — no `notifies`: goal reached, stop |

`result.path == ["commit", "lint", "merge-gate", "deploy"]`, `result.nodes_sensed == 4`, `result.goal_reached is True`.

**`unit-tests` and `integration-tests` are never visited, and that's expected, not a bug.** The goal condition is "reach a node with no `notifies`," not "visit every node you've heard of" — `environment_design.md` never promised full exploration, only that the goal is reachable. `unit-tests` stays in the known-but-unvisited set for the rest of the walk; `integration-tests` is never even *discovered*, since the only node that names it (`unit-tests`) is itself never sensed. Worth showing in the visualization precisely because it's counterintuitive if unstated: this run "succeeds" having sensed 4 of the graph's 6 nodes, and that's correct behavior, not an incomplete walk.

## Why not `task_graph_solver`'s executors, or `path_maintenance`'s agent

Restated concretely rather than in the abstract (`environment_design.md`'s "The edge points the other way" made the general case):

- **`TopologicalExecutor`/`AOStarExecutor`/`DStarLiteExecutor`** all operate on a `requires` graph that's fully known at construction, computing or repairing a plan over it. There is no plan to compute here — the whole premise is that the graph isn't available to compute a plan over until it's been walked.
- **`path_maintenance/`'s `PathMaintenanceAgent`** walks a precomputed `order`, sensing state at each step but never discovering *new* ids — the order is closed from the start. `DiscoveryAgent`'s known set grows as it walks; there is no equivalent `order` to hand it up front.
- **`LRTAStarLearner`** (`DISCOVERY.md`'s other resident) learns a retry-cost heuristic over a graph whose *structure* is already fully known, across repeated trials. This step is the complementary gap `DISCOVERY.md` names explicitly: the structure itself is what's unknown here, and there's exactly one trial, not many.

## What the visualization needs to show

Extending `task_graph_solver/visualization/graph_view.py`'s approach (a `networkx` DiGraph, nodes colored by state) with one new distinction the prior environments never needed: a node the agent has *heard of* but not yet *visited*. Three states, not two:

- **Unknown** (not yet named in any sensed node's `notifies`) — greyed out or omitted entirely, since the agent has no way to know it exists.
- **Known, unvisited** — e.g. `unit-tests` and `integration-tests` for most of the walk above — visibly distinct from both unknown and visited, since this is the set the environment's partial observability is actually about.
- **Visited** — sensed at least once, colored by the walk order (mirroring `_layered_layout`'s left-to-right convention where the graph shape allows it).

### What to watch for in the GIF (predicted, not yet built)

- **Frame 0**: only `commit` visible/known, nothing else on the board yet — unlike every prior environment's GIFs, which open with the full topology already laid out.
- **After sensing `commit`**: `lint` and `unit-tests` both appear, greyed as known-but-unvisited — the first visible fan-out, and the frame where the tie-break rule's choice (`lint`) actually becomes visible as a choice, not a foregone conclusion.
- **`unit-tests` and `integration-tests` stay grey for the rest of the run** — the frame that makes "known but never visited" legible without a caption, the same way `merge`'s wait made the AND-join legible in `graph-topology`'s GIF.
- **Final frame**: `deploy` visited, `unit-tests` still grey — success, with visible leftover unknowns.

## Related documents

- [`../environment_design.md`](../environment_design.md) — the primitives and the movement/goal rules this document takes as given.
- [`../scenario.md`](../scenario.md) — `pipeline_fanout_lite`'s topology and the reconvergence reasoning this document's "no real choice" claim depends on.
- [`../../path-maintenance/graph-topology/algorithm_fit.md`](../../path-maintenance/graph-topology/algorithm_fit.md) — the precedent for a short `algorithm_fit.md` that concludes no real algorithm choice is being made, for a different structural reason.
- [`backtracking-exploration/algorithm_fit.md`](backtracking-exploration/algorithm_fit.md) — step 2: backtracking, why it makes DFS the literal right answer, and the resulting full-exploration reframe.
- [`../../../DISCOVERY.md`](../../../DISCOVERY.md) — where this step's finished write-up will be linked from, alongside LRTA*.
