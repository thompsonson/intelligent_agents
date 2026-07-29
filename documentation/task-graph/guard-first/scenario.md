# Scenario: `pr_merge_lite`, released already true

## Same topology, one override

No new graph. `build_pr_merge_lite`'s exact 8-node topology (`ci-check`, `generate-actions`, `apply-actions`, `merged`, three `deploy-*` branches, `released`), unchanged — consistent with this repo's standing rule against inventing new domain vocabulary for a new algorithm demonstration. The only change is one keyword argument:

```python
nodes = build_pr_merge_lite(
    pass_probability=1.0,
    invariant_overrides={"released": 1.0},
)
env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="released")
```

`released` gets `invariant_pass_probability=1.0` — the toy equivalent of "this workflow already completed in a previous, interrupted run; `released`'s underlying condition already holds." Every other node keeps `invariant_pass_probability=0.0` (`TaskNode`'s own default), so they behave exactly as `pr_merge_lite` always has for every executor built before `GuardFirstExecutor` existed.

## What this is built to demonstrate

`GuardFirstExecutor` is the walk-as-you-go half of the guard-first design (`environment_design.md`) — check before repair, but only for the node currently being visited. This scenario is the smallest one that can show the shape of that capability without also needing OR-groups or a goal short-circuit: `released` sits at the deepest point in a purely linear/AND chain, so reaching it means passing through every other node first regardless of what `released` itself turns out to be.

## Not decided

- **Whether `apply-actions` or another mid-chain node should also get a nonzero `invariant_pass_probability`** in a follow-up scenario, to show a free check firing *mid-walk* rather than only at the very end. Not needed for this first cut — `released`'s position alone is enough to establish the base capability — but worth returning to once `GuardFirstExecutor` has more than one demonstration scenario.
