# Task Graph Scenarios

## Purpose

`environment_design.md` specifies the primitives (`TaskNode`, `requires`, simulated `attempt()`). This document specifies concrete graphs built from those primitives — the actual "mazes" this environment will contain. Three scenarios, deliberately spanning from trivial to the one structural case (AND fan-in) none of this repo's existing algorithms handle. Each is a toy stand-in for a real `atomicguard` `.dspddl` workflow, named to make the correspondence traceable, not to imply live GitHub/system integration.

## Scenario 1: `disk_check_lite` — the trivial case

Modeled on `atomicguard/examples/sysadmin/workflows-guard/disk_check.dspddl`: one guard, `rmax 1`, no `:requires`.

```
[check-disk]
```

| Node | kind | retry_flavor | requires |
|---|---|---|---|
| `check-disk` | sensing | sensing | — |

One node, no edges, no repair path — the same "edge is either passable or not" shape as `check_pr.dspddl` in the earlier stress test, at its smallest possible size. Good for: a smoke test that the environment/executor loop works at all before adding graph structure; a baseline for what "zero interesting structure" looks like, to contrast against scenarios 2 and 3.

## Scenario 2: `repair_packages_lite` — the linear repair chain

Modeled directly on `atomicguard/examples/sysadmin/workflows-guard/repair_packages.dspddl`: `repair-g` (acting, `sysup repair`) → `verify-g` (sensing, `sysup doctor`, `:requires (repair-g)`).

```
[repair] --requires--> [verify]
```

| Node | kind | retry_flavor | requires |
|---|---|---|---|
| `repair` | acting | repair | — |
| `verify` | sensing | sensing | `(repair)` |

This is the cleanest scenario for the LRTA*/RTDP mapping from `documentation/lrta/beyond_the_maze.md`: exactly one node (`repair`) whose retries are genuine repair-attempt cost, with no sibling flavors of retry to accidentally blend into the same signal. `verify`'s retries, if any, are sensing-flavor and should be excluded from any `h(s)` learning — the environment's per-flavor data split (flagged as "not decided" in `environment_design.md`) exists specifically so this scenario can demonstrate that distinction cleanly rather than asserting it in prose.

Also the smallest scenario with a real `:requires` edge — good for validating the AND-gating logic (`ready_nodes()`) before scenario 3 adds a genuine fan-in on top of it.

## Scenario 3: `pr_merge_lite` — the AND fan-in

Modeled on the `pr_merge` workflow family (`check_pr.dspddl`, `fix_pr.dspddl`, `post_merge_monitor.dspddl`), compressed into one graph and simplified in one deliberate way, explained below.

```
[ci-check]
    |
    v
[generate-actions] --requires--> [apply-actions] --requires--> [merged]
                                                                    |
                        +-------------------+-------------------+
                        v                   v                   v
                  [deploy-staging]   [deploy-publish]   [deploy-promote]
                        |                   |                   |
                        +-------------------+-------------------+
                                            v
                                       [released]
```

| Node | kind | retry_flavor | requires |
|---|---|---|---|
| `ci-check` | sensing | sensing | — |
| `generate-actions` | acting¹ | generation | — |
| `apply-actions` | acting | repair | `(generate-actions)` |
| `merged` | acting | repair | `(ci-check, apply-actions)` |
| `deploy-staging` | sensing | sensing | `(merged)` |
| `deploy-publish` | sensing | sensing | `(merged)` |
| `deploy-promote` | sensing | sensing | `(merged)` |
| `released` | sensing | sensing | `(deploy-staging, deploy-publish, deploy-promote)` |

¹ `generate-actions` doesn't mutate any external system (it's an LLM producing a JSON plan, same as `generate-action-list` in the real workflow) — `kind="acting"` here is a simplification worth flagging rather than hiding: `environment_design.md`'s `kind` field is binary (sensing/acting = idempotent/not), but a pure local generation step is neither in the sense the real system's `:idempotent` flag means it (safe-to-retry-without-side-effects is true for it, same as sensing, but it's not a read of external state either). For now it's modeled as `acting` with `retry_flavor="generation"` so the two fields stay independently meaningful (per `environment_design.md`'s point about not collapsing them) — but this is the node most likely to need a third `kind` value if the environment grows past these three scenarios. Left as a known simplification, not resolved here.

**The deliberate change from the real system:** `released`'s three-way fan-in is modeled as three explicit `requires` edges (`deploy-staging`, `deploy-publish`, `deploy-promote` all listed), not as one node polling three things internally the way `check_downstream_status.sh` actually does. That's not an oversight — `documentation/lrta/beyond_the_maze.md` flagged the real system's version of this as a structural problem: collapsing three independent signals into one guard makes them indistinguishable to anything trying to learn a cost from retries, and hides which of the three actually failed from the graph itself. This scenario is deliberately built the *corrected* way, specifically so `algorithm_fit.md`'s AO* mapping has three separately-observable AND-predecessors to reason about instead of one opaque node. Where this scenario intentionally departs from ground truth, it's this one point, and it's an improvement, not a drift.

Also note: `merged` itself is an AND-join (`ci-check` and `apply-actions` both required) — a second, smaller instance of the same structural feature `released` demonstrates at a larger scale. Worth using `merged` as the "can you even detect an AND-join" smoke test before tackling `released`'s three-way version.

## Scenario summary

| Scenario | Nodes | Edges | Retry flavors present | AND fan-in? | Good for |
|---|---|---|---|---|---|
| `disk_check_lite` | 1 | 0 | sensing | No | Executor smoke test, trivial baseline |
| `repair_packages_lite` | 2 | 1 (linear) | sensing, repair | No | Cleanest LRTA*/RTDP demo — isolates repair-flavor retry |
| `pr_merge_lite` | 8 | 8 (2 AND-joins) | sensing, generation, repair | Yes (×2, sizes 2 and 3) | AO* demo; the only scenario D* Lite/LRTA* can't fully solve |

## Not decided

- Whether `pr_merge_lite` should be split into two scenarios (a linear pre-merge half, a fan-in post-merge half) so the AND-join isn't the only thing forcing the whole scenario's algorithm choice — right now a partial-AO*, partial-LRTA* hybrid run is the only way to exercise all of it, which may be more than a first pass needs.
- Whether `generate-actions`' `kind` simplification (noted above) should be resolved by adding a third `kind` value now, or left until a fourth scenario actually needs the distinction.
