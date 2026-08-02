# Scenario: `pipeline_fanout_lite`, backed by real fixture files

## Same topology, real nodes underneath

No new graph, same discipline `and-joins/scenario.md` and `job-lifecycle/scenario.md` both followed: reuse `pipeline_fanout_lite` unmodified rather than inventing new domain vocabulary to demonstrate a new capability. Every `notifies`/`requires` relationship stays exactly as `discovery/scenario.md` (step 1) and `and-joins/scenario.md` (step 3) built them - the point of this experiment is running the identical shape through real nodes, not designing a new scenario:

| Node | `notifies` | `requires` (gated variant only) |
|---|---|---|
| `commit` | `(lint, unit-tests)` | — |
| `lint` | `(merge-gate,)` | — |
| `unit-tests` | `(integration-tests, merge-gate)` | — |
| `integration-tests` | `(merge-gate,)` | — |
| `merge-gate` | `(deploy,)` | `(lint, integration-tests)` |
| `deploy` | `()` | — |

What's genuinely new is how each node's `notifies` gets produced.

## Fixture files, not dataclass fields

`real_discovery/atomicguard_backed/fixtures/pipeline_fanout_lite/<node_id>.json`, one per node, each holding `{"notifies": [...]}` - `commit.json` is `{"notifies": ["lint", "unit-tests"]}`, `deploy.json` is `{"notifies": []}`, and so on, matching the table above exactly.

Each node's `check_action_pair` is a real `cat` over its own fixture file:

```python
ActionPair(
    generator=SubprocessGenerator(command=["cat", str(fixture_path)]),
    guard=ExitCodeGuard(),
    prompt_template=PromptTemplate(role="", constraints="", task=""),
)
```

The identical deterministic, no-LLM pattern `real_task_graph_solver/atomicguard_backed/scenarios/lint_repair.py` already proved for `ruff check` - genuine `SubprocessGenerator`+`ExitCodeGuard`+empty-`PromptTemplate` machinery, no custom `Generator`/`Guard` subclass needed. `sense_edges()` parses the artifact's real stdout content as JSON and reads `notifies` off it.

## Why `cat`-over-JSON, not something that looks more like a real check

Considered and rejected: writing a fixture-specific custom `Generator` that returns a hardcoded `notifies` list directly, skipping the subprocess entirely. That would be faster to build and just as deterministic, but it would prove nothing - the whole point of this experiment is that `sense_edges()` goes through a *real* `DualStateAgent`/`ActionPair`/subprocess round-trip, the same infrastructure a genuine check (a real `pytest` run, a real `kubectl get`) would use. A fixture that fakes the `Generator` layer would make the "small steps, make nodes stateful" claim untestable - there'd be no real subprocess call to observe, time, or (as PR #15's review found) accidentally over-call. `cat` is the simplest command that's still a genuine, real, externally-observable process invocation.

## The gated variant

`build_pipeline_fanout_lite_gated()` adds `merge-gate.requires = ("lint", "integration-tests")` as declared node config - not sensed, not read from any fixture, matching `environment_design.md`'s "Who owns what" resolution: `requires` is a node-declared fact, `cleared` is the agent's own bookkeeping. Same two targets `and-joins/scenario.md` chose, for the same reason: `lint` closes the first fork, `integration-tests` closes the end of the second (its own predecessor `unit-tests` doesn't need naming separately - reaching `integration-tests` at all already implies `unit-tests` cleared).

## What this scenario is for

- **Direct, move-for-move comparability with `discovery/`'s own experiments 2 and 3.** Same topology means the walk numbers (6 senses/10 moves ungated, 6 senses/14 moves gated) are a real cross-check, not just a plausible-looking result - `tests/test_discovery_agent_integration.py` asserts equality against the plain `DiscoveryEnvironment`'s own walk directly, field by field.
- **A deterministic, fast, dependency-free demonstration of real sensing cost.** Every `sense_edges()` call is a genuine subprocess round-trip through `DualStateAgent`, recorded in a real `InMemoryArtifactDAG` - slow enough to matter (the visualization over-sensing bug cost 90 real calls instead of 6, on this exact scenario) but fast enough to run in a test suite with no network, no LLM, no flakiness.

## Not decided

Nothing left open from this document's own scope - see `algorithm_fit.md` for what's still open about how the walk behaves given real, potentially-failing sensing.

## Related documents

- [`environment_design.md`](environment_design.md) - `StatefulDiscoveryNode`/`StatefulDiscoveryEnvironment`'s shape and the node-ownership resolution this scenario's `requires` placement follows.
- [`algorithm_fit.md`](algorithm_fit.md) - whether `DiscoveryAgent`'s algorithm still fits, argued against this scenario's real sensing cost.
- [`../scenario.md`](../scenario.md) / [`../and-joins/scenario.md`](../and-joins/scenario.md) - the original `pipeline_fanout_lite` topology this scenario reuses unmodified, and why `(lint, integration-tests)` specifically.
