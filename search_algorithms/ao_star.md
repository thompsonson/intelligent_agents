# AO* (AND-OR Graph Search)

## Why this algorithm exists

A* and D* Lite both assume every node's problem reduces to picking the single best next step among alternatives — an OR-choice. `documentation/lrta/beyond_the_maze.md` found a real case neither algorithm can represent without distortion: `post_merge_monitor.dspddl`'s `downstream-ci-passed` requires three independent deploy contexts to **all** succeed before it's satisfied. That's not "pick the cheapest of three options" — it's "wait for every one of these three, in whichever order they finish." Nilsson's AO* (1980, *Problem-Solving Methods in Artificial Intelligence*) is the classical algorithm for exactly this: search graphs where solving a node can require **all** of several subgoals (an AND-node) as well as **any one** of several alternatives (an OR-node).

If you understand A*'s "expand the most promising node, propagate costs backward," AO* is the same idea generalized to a graph where "most promising node" and "propagate costs" both have to account for two different composition rules instead of one.

## AND-nodes vs. OR-nodes

| | OR-node | AND-node |
|---|---|---|
| Meaning | Solve **any one** of several children | Solve **all** of several children |
| Cost composition | `min` over children | Depends on the cost model (see below) — `sum` if work is sequential, `max` if children can proceed independently and you're waiting on the slowest |
| What this repo's algorithms assume | A*, D* Lite, LRTA* all assume every node is this kind | None of them handle this kind at all |

`task_graph_solver`'s `requires` edges (`documentation/task-graph/environment_design.md`) are **purely AND** — there is no OR-equivalent in the DSL this environment mirrors (`atomicguard`'s `requires: tuple[str, ...]` is a conjunction, never a disjunction). So the scenarios this repo builds only exercise AO*'s AND-composition half. The general algorithm (below) still handles OR-nodes, for completeness and because a future scenario might introduce genuine alternative-path choice, but nothing built so far needs that half.

## Cost composition used here: `max`, not `sum`

Classical AO* leaves the AND-node cost rule to the domain: `h(n) = cost(n) + Σ h(children)` if solving each child is sequential, separately-paid work, or `h(n) = cost(n) + max(h(children))` if children can be worked on independently and `n` is only blocked on whichever one finishes last.

`documentation/lrta/beyond_the_maze.md` already made this call for the motivating case: three deploy contexts (staging/publish/promote) resolve concurrently and independently — `downstream-ci-passed` isn't "the sum of three deploy durations," it's "however long the slowest one takes." So the composition rule for every AND-node in this repo's scenarios is:

```
h(AND-node) = cost(AND-node) + max over required children c of h(c)
```

This is the same rule critical-path/PERT scheduling uses — you're only as done as the slowest thing you're required to wait for, not the sum of everyone's individual cost.

## Algorithm in pseudocode

Adapted from Nilsson's formulation, restricted to the AND-composition this repo needs (no OR-node cost selection, since none exist in these scenarios — see below for the full version's extra step):

```
procedure Initialize():
    G ← explicit graph containing only the start node s
    h(s) ← heuristic estimate

procedure AO-STAR():
    while s is not fully solved and not fully unsolvable:
        n ← SELECT-NODE(G)              # a non-terminal leaf of the current best partial solution
        EXPAND(n)                        # generate n's children, add to G
        for each new child c: h(c) ← heuristic estimate
        Z ← {n} ∪ ancestors of n in G     # nodes whose cost might have changed
        for each node m in Z, processed bottom-up:
            if m is a terminal (no children): continue
            if m is an AND-node:
                h(m) ← cost(m) + max over required children c of h(c)
                m is SOLVED if every required child is SOLVED
                m is UNSOLVABLE if any required child is UNSOLVABLE
            if m is an OR-node:
                h(m) ← cost(m) + min over children c of h(c)
                mark the min-cost child as m's current best choice
                m is SOLVED if that chosen child is SOLVED
                m is UNSOLVABLE if every child is UNSOLVABLE
    return SOLVED if s is SOLVED, else UNSOLVABLE
```

`SELECT-NODE` picks the cheapest-looking unexpanded node on the current best partial solution — the AO* analogue of A*'s "pop the min-`f` node," except "the current best partial solution" has to be recomputed whenever an AND-node's chosen set of children changes, not just when an OR-node's chosen child changes.

## Properties / Analysis

| Property | A* | AO* |
|---|---|---|
| **Graph shape** | Simple graph, OR-choice at every node | AND-OR graph (hypergraph) — some nodes require all children, others require one |
| **Completeness** | Yes, finite graph, non-negative costs | Yes, under the same conditions, for both node types |
| **Optimality** | Yes, admissible heuristic | Yes, admissible heuristic, for the chosen cost composition (`sum` or `max`) |
| **Cost propagation** | Backward from goal, `min`-over-successors | Backward from expanded node through ancestors, `min` for OR-nodes, `sum`/`max` for AND-nodes |
| **Failure propagation** | N/A (a node is either reachable or not) | An AND-node is `UNSOLVABLE` the moment **any** required child is; this propagates upward the same way `SOLVED` does |
| **What this repo's scenarios use** | — | Only the AND half; no OR-node exists in any `task_graph_solver` scenario built so far |

## Relationship to this repo's existing algorithms

- **Not a repair algorithm.** D* Lite and LPA* repair a plan after the graph changes; AO* solves an AND-OR graph once (or incrementally re-expands as new nodes are discovered). `task_graph_solver`'s `DStarLiteExecutor` (Phase 4) and any future AO*-based executor are complementary, not competing — a real system might use AO* to decide the structure of what needs solving and D* Lite-style repair to handle a solved subgoal breaking later. Combining them is explicitly deferred in `documentation/task-graph/algorithm_fit.md`'s "not v1" section.
- **Not a learning algorithm.** LRTA*/RTDP learn `h` from experience over repeated trials. AO* takes `h` as given (a heuristic function) and focuses on correctly composing costs and propagating solved/unsolvable status through AND/OR structure. The "combinations worth naming" section of `algorithm_fit.md` — AO* for the graph structure, LRTA* supplying the cost estimates it needs — is exactly pairing these two different jobs together, not overlap between them.

## Where this fits in the repo

Design-stage — not yet implemented. See:

- [`documentation/task-graph/environment_design.md`](../documentation/task-graph/environment_design.md) — the `TaskGraphEnvironment` this would run against; `ready_nodes()` already computes AND-gating, which is the "is this AND-node's required-child set complete" check AO* needs
- [`documentation/task-graph/scenarios.md`](../documentation/task-graph/scenarios.md) — `pr_merge_lite`'s `merged` (two required children) and `released` (three required children) are the concrete AND-nodes this algorithm targets
- [`documentation/task-graph/algorithm_fit.md`](../documentation/task-graph/algorithm_fit.md) — build order: `merged`'s two-way join first (Phase 5), `released`'s three-way join second (Phase 6), each hand-verifiable before the next
- [`documentation/d-star/related_algorithms.md`](../documentation/d-star/related_algorithms.md) — how AO* was surfaced (the real-world stress test found a fan-in none of D* Lite/LPA*/LRTA* could represent) and where it sits in the broader algorithm backlog
