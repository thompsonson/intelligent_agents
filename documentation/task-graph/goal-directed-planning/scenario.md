# Scenario: Two graphs, two capabilities

`environment_design.md` established that goal-directed scope and sense-then-plan short-circuiting fall out of one recursive `ensure()`, not two mechanisms. Demonstrating them cleanly still wants two different graphs, though, for the same reason `guard-first/scenario.md` stayed deliberately small: a graph built to show one thing clearly is more honest than one graph straining to show everything at once.

## Scenario A: sense-then-plan short-circuit — `pr_merge_lite`, released already true

Identical setup to `guard-first/scenario.md` — same override, same goal:

```python
nodes = build_pr_merge_lite(
    pass_probability=1.0,
    invariant_overrides={"released": 1.0},
)
env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="released")
```

Reusing the identical scenario as `GuardFirstExecutor`'s is deliberate, not laziness: it's what makes the contrast between the two executors legible. Same graph, same override, same goal — the only thing that differs is which executor runs it, and that difference alone is the entire point (`algorithm_fit.md`, below).

## Scenario B: goal-directed scope + OR-group pruning — `pr_merge_with_variants`

`build_pr_merge_with_variants` (the OR-groups scenario, unmodified) — chosen because it already has both ingredients this half of the design needs: a true orphan (`check-disk`, disconnected from `released` entirely) and an OR-group (`actions-ready`, three variant strategies competing for one slot). No new scenario needed; both goal-directed scope and OR-group pruning are properties of `PlanningExecutor` itself, not of anything special about this graph.

```python
nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal)
```

## Not decided

- **Whether a third scenario combining both capabilities with a genuinely deep, wide graph** (many orphans, several groups, a pre-satisfied node buried several AND-joins deep) would demonstrate anything `PlanningExecutor`'s existing tests don't already cover, or would just be a bigger version of the same two stories. Leaning toward "not needed yet" — the two scenarios above already isolate each capability cleanly, and this repo's own`disk_check_lite`→`pr_merge_lite` progression suggests bigger graphs are worth building only once a specific new question needs one, not by default.
