# Scenario: `pipeline_fanout_lite`, with `merge-gate` gated

## Same topology, one new field

No new graph, same discipline `job-lifecycle/scenario.md` followed for `deploy_chain_lite`: reuse `pipeline_fanout_lite` unmodified rather than inventing new domain vocabulary to demonstrate a new capability. Every `notifies` edge stays exactly as `scenario.md` (step 1) built it. The only change:

| Node | `notifies` | `requires` |
|---|---|---|
| `commit` | `(lint, unit-tests)` | — |
| `lint` | `(merge-gate,)` | — |
| `unit-tests` | `(integration-tests, merge-gate)` | — |
| `integration-tests` | `(merge-gate,)` | — |
| `merge-gate` | `(deploy,)` | **`(lint, integration-tests)`** |
| `deploy` | `()` | — |

## Why `(lint, integration-tests)`, not all three notifying parents

Step 1's `scenario.md` built `merge-gate` with *three* incoming `notifies` edges — from `lint`, `unit-tests`, and `integration-tests` — deliberately, so that no matter which branch step 1's no-backtrack agent committed to, it would still reach `deploy`. That reason no longer applies (step 2's backtracking already gets to every node regardless), but the topology is reused as-is rather than trimmed, on the same "don't touch what a prior step's tests depend on" instinct `graph-topology`/`job-lifecycle` both followed.

`requires` only needs to name the two branches whose completion actually matters: `lint` (the first fork) and `integration-tests` (the end of the second fork's chain — `unit-tests` itself doesn't need to be named separately, since the only way to reach `integration-tests` at all is by first sensing `unit-tests`, so `integration-tests` being satisfied already implies `unit-tests` was too). `unit-tests`'s own *direct* edge to `merge-gate` stays in the graph unmodified, which makes it an interesting edge case rather than a loose end: an agent that reaches `merge-gate` via that direct shortcut, before `integration-tests` is done, gets blocked exactly the same as one that arrived via `lint` — `requires`-gating checks *what's cleared*, not *which edge you arrived by*.

## Reachability, checked by hand

`environment_design.md`'s constraint: every `requires` target must be reachable via some `notifies` chain from `start`. Both are, trivially, from `commit`:
- `lint`: `commit → lint` (one hop).
- `integration-tests`: `commit → unit-tests → integration-tests` (two hops).

No `requires` cycle exists either — `merge-gate` is the only node with a nonempty `requires`, and neither `lint` nor `integration-tests` requires anything back.

## What this scenario is for

- **The concrete case `environment_design.md`'s Purpose section names directly**: step 2's walk senses `deploy` at move 3, before `unit-tests`/`integration-tests` are touched at all. This scenario is built to make that impossible — `merge-gate` cannot clear, and therefore `deploy` cannot be reached, until both forks are actually done.
- **Exercises the "arrived via a shortcut, still gated" case**: `unit-tests → merge-gate` directly, versus `unit-tests → integration-tests → merge-gate`. A traversal that reaches `merge-gate` the short way still has to go satisfy `integration-tests` before proceeding — proving the gate checks completion, not arrival path.
- **A deterministic regression case**: fixed topology and fixed `requires`, only the traversal algorithm (now settled — see `algorithm_fit.md`) varies what order things happen in.

## Resolved: the reachability-violation variant

`algorithm_fit.md`'s "Resolved: a scenario exercising a genuine reachability violation" works this graph plus one orphan node — `release-notes`, `notifies=()`, added to `merge-gate.requires` as a third dependency, never named in anyone's `notifies` — and verifies `blocked_nodes == ["merge-gate"]`, `goal_reached is False`, `deploy` never sensed at all. Documented there rather than duplicated here, since it's inseparable from the algorithm trace that demonstrates it.

## Not decided

Nothing left open from this document's own scope.
