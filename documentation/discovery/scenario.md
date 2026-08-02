# Scenario: `pipeline_fanout_lite`

## Purpose

`environment_design.md` specifies the primitives (`DiscoveryNode`, `notifies`, `DiscoveryEnvironment`). This document specifies one concrete graph built from them — small enough to read at a glance, with two genuine branch points (so which known-but-unvisited id to move to next is a real decision, not a formality), and exactly one reachable node with no `notifies`, so the goal condition (`environment_design.md`'s "Resolved: goal") stays unambiguous.

## The graph

```
commit ──▶ lint ─────────────────┐
   │                             ▼
   └──▶ unit-tests ──▶ integration-tests ──▶ merge-gate ──▶ deploy
              │                                  ▲
              └──────────────────────────────────┘
```

| Node | `notifies` |
|---|---|
| `commit` | `(lint, unit-tests)` |
| `lint` | `(merge-gate,)` |
| `unit-tests` | `(integration-tests, merge-gate)` |
| `integration-tests` | `(merge-gate,)` |
| `merge-gate` | `(deploy,)` |
| `deploy` | `()` |

`deploy` is the only node with no `notifies` — the goal, and unambiguously so, since no other terminal exists to confuse it with.

## Why this shape

**Two real branch points, not one.** `commit` fans out to `lint`/`unit-tests` — the first point where the agent knows about more than one unvisited node and has to choose. `unit-tests` fans out again, to `integration-tests`/`merge-gate` — a second, independent choice, so a traversal strategy gets exercised more than once rather than as a one-off.

**Convergent, not a tree — and that's load-bearing.** `merge-gate` is named in *three* different nodes' `notifies` (`lint`, `unit-tests`, `integration-tests`). This matters mechanically, not just thematically: movement is one-directional and there is no "go back" — an agent that commits to `lint` first cannot later return to `commit` to try `unit-tests` instead (`environment_design.md`'s movement rule has no backward edge to make that possible). If this graph were a strict tree, picking `lint` at the first branch would permanently strand the agent from ever reaching `deploy` down the `unit-tests` side, and a strategy could pick a branch that never reaches the goal at all — which would make "exactly one reachable terminal" false depending on which choice was made, not a property of the graph alone.

Reconvergence at `merge-gate` avoids that: **every** path out of `commit` reaches `deploy` eventually, regardless of which branch is taken at either fork. That means a traversal strategy here is being judged on efficiency (how many nodes it senses, how long the path is before it reaches the goal) — not on correctness (whether it reaches the goal at all). Both are worth demonstrating, but they're different claims, and this graph is deliberately built to isolate the first one without accidentally also testing the second.

## What isn't walked through here

Which of `lint`/`unit-tests` (and later `integration-tests`/`merge-gate`) gets visited first — and therefore the exact `path`/`nodes_sensed` a run produces — depends on `DiscoveryAgent`'s traversal strategy, which `environment_design.md` explicitly leaves undecided and defers to `algorithm_fit.md`. This document fixes the graph only; the hand-walked trace belongs in `algorithm_fit.md`, once a strategy is chosen to walk it with.

## What this scenario is for

- **Smoke test** that `DiscoveryEnvironment`'s `notifies`-validation and `sense_edges()` compose correctly on a graph with real fan-out and reconvergence, not just a linear chain.
- **Exercises the "no backward movement" constraint concretely**: a test can assert that, whichever branch is taken first, the walk still reaches `deploy` — proving reconvergence does what it's meant to, rather than asserting it only in prose.
- **The animation source** for this step's experiment doc, once a traversal strategy exists to generate a walk from.
- **A deterministic regression case**: the topology itself is fixed, not seeded/random — only the traversal policy varies between test cases.

## Not decided

- Whether a second scenario is worth adding to demonstrate what happens *without* reconvergence — e.g. a strict-tree graph with two independent terminals, showing why `environment_design.md`'s "exactly one reachable terminal" constraint was necessary rather than incidental. Not needed for this first cut; the point is made in prose above and doesn't need a second graph to prove it yet.
