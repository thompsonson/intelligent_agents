# Experiment 1: `pipeline_fanout_lite` — Building the Graph While Walking It

**Run this yourself:** `discovery/tests/` reproduces every behavior in this experiment (`test_environment.py`, `test_discovery_agent.py`, `test_scenarios.py`, `test_discovery_view.py`, 23 tests total). Animation: [`pipeline_fanout_lite.gif`](../../../discovery/animations/pipeline_fanout_lite.gif).

## What this experiment demonstrates

`environment_design.md` specified an environment where the agent doesn't know the graph up front — only what a node's own `notifies` reveal, once that node is sensed. `scenario.md` built `pipeline_fanout_lite` around two real branch points and one reachable terminal; `algorithm_fit.md` predicted the exact walk under a forward-committed, lowest-id tie-break policy. This experiment is that prediction, run for real, matching frame for frame.

## The scenario

```python
nodes = {
    "commit": DiscoveryNode(id="commit", notifies=("lint", "unit-tests")),
    "lint": DiscoveryNode(id="lint", notifies=("merge-gate",)),
    "unit-tests": DiscoveryNode(id="unit-tests", notifies=("integration-tests", "merge-gate")),
    "integration-tests": DiscoveryNode(id="integration-tests", notifies=("merge-gate",)),
    "merge-gate": DiscoveryNode(id="merge-gate", notifies=("deploy",)),
    "deploy": DiscoveryNode(id="deploy"),
}
```

## The walk, confirmed

```
('sense', 'commit', ('lint', 'unit-tests'))
('sense', 'lint', ('merge-gate',))
('sense', 'merge-gate', ('deploy',))
('sense', 'deploy', ())
```

`result.path == ["commit", "lint", "merge-gate", "deploy"]`, `result.nodes_sensed == 4`, `result.goal_reached is True` — exactly `algorithm_fit.md`'s hand-computed table. No implementation surprises this time: unlike `job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md`, which caught two real bugs the design docs hadn't anticipated, this run matched the prediction on the first pass. The one thing worth double-checking wasn't a bug so much as a property to confirm empirically rather than take on faith: `test_every_branch_reconverges_regardless_of_first_choice` walks `commit`'s other branch (`unit-tests → integration-tests → merge-gate → deploy`) by hand and confirms it also reaches `deploy` — proving `scenario.md`'s reconvergence claim rather than just asserting it in prose.

## `unit-tests` and `integration-tests`: known, never visited

The one genuinely new visual fact this environment produces, absent from every prior GIF in this repo: two nodes that the agent knows exist — named directly in `commit`'s and `unit-tests`'s `notifies` — and never visits, because the goal was reached down the other branch first. `test_never_visits_nodes_left_unvisited_by_the_tie_break` asserts this directly. It's correct behavior, not an incomplete walk — `environment_design.md` never promised full exploration, only that the goal is reachable — but it's worth naming precisely because a viewer's first instinct on seeing a grey node in the final frame is to assume something went wrong.

## What to watch for in the GIF

Five frames, matching `algorithm_fit.md`'s prediction:

- **Frame 0**: only `commit` on the board, grey (known, not yet sensed) — unlike every prior environment's GIFs, which open with the full topology already laid out. There is no "full topology" to show yet; the environment holds one, but the agent hasn't earned any of it beyond the start id.
- **Frame 1** (`sense_edges('commit')`): `commit` turns green (visited); `lint` and `unit-tests` both appear for the first time, grey — the first fan-out becomes visible, and the frame where the tie-break rule's choice (`lint` over `unit-tests`, alphabetically) actually becomes a choice rather than a foregone conclusion.
- **Frame 2** (`sense_edges('lint')`): `lint` turns green; `merge-gate` appears, grey. `unit-tests` is still on the board, still grey, and stays that way for the rest of the run.
- **Frame 3** (`sense_edges('merge-gate')`): `merge-gate` turns green; `deploy` appears, grey.
- **Frame 4** (`sense_edges('deploy')`): `deploy` turns dark green (the goal, reached) — `unit-tests` still grey next to it, visible proof that "known" and "visited" are genuinely different things in this environment, not a coloring nicety.

`integration-tests` never appears on the board at all: nothing ever senses `unit-tests`, so nothing ever reveals it. A viewer comparing this GIF to `graph-topology`'s or `job-lifecycle`'s — where the full graph is visible from frame 0 — sees the actual difference the `Known/Unknown` property flip makes, not just reads about it.

## What this experiment validates that the design docs alone could not

- **Reconvergence genuinely removes the need for backtracking**, confirmed by running the walk, not just by the graph's shape on paper — `test_every_branch_reconverges_regardless_of_first_choice` exercises the specific claim `algorithm_fit.md`'s "no real algorithm choice" argument depends on.
- **The environment's `sense_edges()` really does answer any known id without an arrival check**, and `DiscoveryAgent`'s own discipline (only sensing its current position) is sufficient on its own to produce the intended behavior — `environment_design.md`'s bet that no environment-side enforcement was needed holds up under a real run, not just in the design conversation that settled it.
- **The three-state rendering (unknown/known/visited) reads correctly in real output**: the grey `unit-tests` node sitting next to the dark-green `deploy` goal in the final frame is the single clearest piece of evidence in this whole repo for what "partially observable" actually looks like, as opposed to "fully, but lazily" observable in every environment before it.

## Related documents

- [`../environment_design.md`](../environment_design.md) — the primitives and rules this experiment exercises.
- [`../scenario.md`](../scenario.md) — `pipeline_fanout_lite`'s topology and the reconvergence reasoning this run confirms.
- [`../algorithm_fit.md`](../algorithm_fit.md) — the traversal policy and frame-by-frame prediction this experiment matches.
- [`../../path-maintenance/job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md`](../../path-maintenance/job-lifecycle/experiments/01_deploy_chain_lite_lifecycle.md) — the precedent for this doc's structure, and a contrast: that run caught two real bugs; this one matched its prediction on the first pass.
