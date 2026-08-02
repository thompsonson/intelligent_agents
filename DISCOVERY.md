# Discovery: Documentation

This is a sibling document to [`README.md`](README.md), [`TASK_GRAPH_SOLVER.md`](TASK_GRAPH_SOLVER.md), and [`PATH_MAINTENANCE.md`](PATH_MAINTENANCE.md), for a third variation on what an agent can know about its environment:

- **`README.md`'s and `TASK_GRAPH_SOLVER.md`'s search algorithms** (BFS/DFS/Greedy/A*, D* Lite, AO*) assume the agent **knows** the environment — the whole maze or the whole DAG is given up front. Search means finding (or re-finding) a route through something already visible.
- **`PATH_MAINTENANCE.md`'s agent** also knows the environment, plus has committed to a specific path through it — its job is keeping the nodes on that path healthy, not finding routes at all.
- **This document's agents don't know the environment.** They have to build that knowledge incrementally, from bounded lookahead and experience, rather than reading it off a fully-specified graph.

## LRTA\* (Learning Real-Time A\*)

The one discovery algorithm actually built so far, living in `task_graph_solver/algorithms/lrta_star.py` — moved into this document from `TASK_GRAPH_SOLVER.md`, where it was previously grouped alongside D* Lite and AO* despite not sharing their "environment already known" assumption.

`LRTAStarLearner` learns `h_table` — a per-node cost estimate — for `retry_flavor="repair"` nodes only, over repeated trials via an `env_factory(trial_index)` callable. Each trial starts fresh; what persists across trials is the learned heuristic, not the environment state. The update rule mirrors LRTA*'s classic backup: `h(s) ← max(h(s), retries_spent(s) + min_over_successors(h(successor)))` — the estimate can only grow, never shrink, and stops moving once the true worst case has actually been observed. It composes backward over successor costs on a known graph, closer to an AO*-style backup than a flat max over a node's own retry cost alone. In the `repair_packages_lite` demo below specifically, `repair`'s only successor (`verify`) is `retry_flavor="sensing"`, so it never enters `h_table` and contributes `0` to the sum — the two forms of the rule coincide in this one scenario, which is why the frame-by-frame walkthrough below only ever shows `h(repair) = retries_spent(repair)`.

**Scenario**: `repair_packages_lite` (`task_graph_solver/scenarios/repair_packages_lite.py`) — the same scenario `TASK_GRAPH_SOLVER.md`'s D* Lite section uses, shared infrastructure rather than duplicated. It's the cleanest isolation of the "repair-attempt retry is learnable cost" signal: exactly one `repair`-flavor node, no sibling retry flavors to blend into the same estimate.

![LRTA* convergence](task_graph_solver/animations/lrta_star_convergence.png)

A node with `pass_probability=0.3` (`rmax=8`) run through `LRTAStarLearner` for 25 trials. `h(repair)` starts at 4 (an early, lucky sequence of failures), jumps to 7 the first time a worse trial is actually observed, and then holds. This is the same node used throughout `documentation/lrta/beyond_the_maze.md`'s repair-cost discussion, now actually learned rather than only described.

**Trial-by-trial walkthrough of the update rule, including why trial 1 doesn't start at the true worst case:** [`documentation/task-graph/experiments/03_lrta_star_convergence.md`](documentation/task-graph/experiments/03_lrta_star_convergence.md).

**Testing**: `task_graph_solver/tests/test_lrta_star.py`, `task_graph_solver/tests/test_learning_curve.py` (the convergence chart itself). Runs alongside `task_graph_solver`'s other tests — `make test-task-graph` / `uv run pytest task_graph_solver/tests/ -v`.

## Not yet built: discovering the topology itself

LRTA* still starts each trial with the *node* it's learning about — and the whole `task_graph_solver` graph structure — fully known; only the *retry cost* is unknown. A step further, not yet scoped: an environment where the agent doesn't know what comes next at all, and has to sense it from the current node rather than reading it off a pre-built graph — the "should we make the environment unknown, agent finds the next node from information in the current node" question raised while working on `path_maintenance/`'s job-lifecycle step, and deliberately deferred there as out of scope for node-repair.

This is where that work will land once it's actually designed — nothing built here yet, this section exists so the deferral has a home to point to rather than getting lost.

## Related documents

- [`documentation/lrta/beyond_the_maze.md`](documentation/lrta/beyond_the_maze.md) — the real-`atomicguard` stress test that motivated `retry_flavor`'s three-way split (sensing/generation/repair), and the repair-cost node LRTA*'s demo uses.
- [`documentation/task-graph/environment_design.md`](documentation/task-graph/environment_design.md) — `TaskNode`/`TaskGraphEnvironment`, shared infrastructure between this document and `TASK_GRAPH_SOLVER.md`.
- [`TASK_GRAPH_SOLVER.md`](TASK_GRAPH_SOLVER.md) — the sibling document for the "environment already known" side of `task_graph_solver`: `TopologicalExecutor`, `AOStarExecutor`, `DStarLiteExecutor`.
