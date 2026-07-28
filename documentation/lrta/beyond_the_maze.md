# LRTA*/RTDP Beyond the Maze: Learning Pipeline Costs from Real Effectors

## Purpose

This is the same kind of exercise as [`documentation/d-star/beyond_the_maze.md`](../d-star/beyond_the_maze.md) — stress-test a toy-example algorithm against a real system, not build the real system. But it's grounded differently on purpose.

The "Atomic Action Pair" primitive discussed alongside this repo's design work (an LLM generator `a_gen` wrapped by a deterministic-looking Guard `G`, retried up to `R_max` times) was originally mapped onto D* Lite, PDDL, LRTA*/RTDP, and the RL Options framework all at once. The critique of that mapping was specific: **LRTA*/RTDP is the mapping that doesn't require pretending the outcome is deterministic** — it's built for exactly the situation where the true cost of an action isn't known until you've paid it, and guard-retry count is real, measurable, learnable cost, not an assertion. D* Lite and classical PDDL, by contrast, need the mapping to overclaim determinism to work at all.

This document answers the concrete follow-up: **is the effector list already catalogued in `documentation/d-star/beyond_the_maze.md`** (the `gh` CLI sensing/acting split for a multi-repo CI/CD pipeline) **actually sufficient to realize the Atomic Action Pair primitive**, or does the mapping only work on paper?

## Recap: the primitive, correctly grounded this time

- `a_gen` — the generator. One attempt at satisfying a workflow step.
- `G(a, C)` — the Guard. A check, run after `a_gen`, that returns pass / retry / fatal.
- `R_max` — retry budget. Bounds how many times `a_gen` gets re-invoked (with refined context `C`) before the step is declared a fatal failure.
- The LRTA* update this maps onto: `h(s_w) ← max(h(s_w), retries_observed(s_w) + h(s_next))` — the cost of a workflow step is approximated by how many guard-check cycles it actually took to satisfy, learned over repeated attempts, the same way `d_star_lite.md`'s `rhs(s)` is a one-step-lookahead backup, except here the backup is fed by observed trial cost instead of a known static edge weight.

## Mapping onto the effectors already catalogued

`documentation/d-star/beyond_the_maze.md` already split the relevant tooling into sensing (read-only) and acting (world-mutating) effectors. The Atomic Action Pair roles map onto that same split directly:

| Atomic Action Pair role | Concrete effector | Notes |
|---|---|---|
| `a_gen` (generator) | `scripts/dev/dispatch-dev-opencode.sh` | Sends context to an OpenCode session to attempt a fix. This is what gets invoked, potentially multiple times, per workflow step. |
| `G` (guard — sensing) | `gh run list --commit {sha}` / `gh run watch --exit-status` | Checks whether the CI pipeline edge is currently passable |
| `G` (guard — sensing) | `gh api repos/.../commits/{sha}/statuses` | Checks a specific downstream deploy context (e.g. `manta-deploy/staging`) |
| `G` (guard — sensing) | `gh api repos/.../pulls/{pr}/comments` + `check-pr-resolved.sh` | Checks whether review threads are resolved |
| Effect that advances `S_workflow` | `merge_pull_request` | The one effector that actually moves `s_w` to the next node — everything else senses state or attempts a local fix without changing the workflow's position |

## Answering "might it be possible": yes, structurally — with one missing piece

The two roles the primitive needs (an acting effector, several sensing effectors) already exist as two disjoint sets in the earlier catalogue — nothing new needs inventing at the tool level. What's missing is the orchestration layer around them:

1. Call `a_gen` (`dispatch-dev-opencode.sh`).
2. Poll the relevant sensing effector(s) for that step until the run resolves.
3. Count the retry as it happens.
4. On pass: update `h(s_w)` with the observed retry cost, call `merge_pull_request` to advance `s_w`.
5. On `R_max` exhaustion: record `⊥_fatal`, escalate (same escalation posture as the D* Lite mapping — this is where the algorithm's job ends and a human decides what happens next).

None of that loop exists today, and neither does a persistent `h` table across workflow steps — the scripts are independent CLI calls, not a closed-loop learner. That's the actual gap, not the effectors themselves.

## Where this holds

- **Retries are a real, counted quantity, not an assumption.** `dispatch-dev-opencode.sh` invocation count per step is exactly the experienced cost LRTA*/RTDP's update rule consumes. This is a stronger position than the purely theoretical version of the mapping, because the "cost" here is measured, not asserted.
- **`R_max` is already an operational necessity, independent of the algorithm.** Nobody wants unbounded automated-fix attempts against a real PR — a hard retry cap is something you'd build for safety reasons regardless of whether LRTA* is involved. The bounded-real-time-search framing isn't an artificial constraint added to make the analogy work; it's already how this would have to be run.

## Where this strains

- **Two different budgets get conflated.** `R_max` bounds how many times the *fix* is retried. But each sensing effector call also has to wait for a real CI run to finish — a latency/timeout budget, not a retry-count budget. The original write-up only modeled one budget; a real implementation needs two, tracked separately: attempts-remaining and poll-timeout-per-attempt.
- **Non-stationarity breaks LRTA\*'s convergence assumption.** LRTA*/RTDP's convergence guarantees assume a stationary environment — repeated trials sampling the same underlying cost distribution. A flaky, load-dependent CI runner means the same workflow step's "cost" can vary for reasons unrelated to the actual difficulty of the step — infra flakiness and a genuine code defect look identical to the Guard. Learning a heuristic under that noise risks converging to a wrong or unstable estimate of "how hard step X really is."
- **`⊥_fatal` needs to mean "this attempt failed," not "this edge is gone forever."** The D* Lite mapping treated a fatal guard as `cost → ∞` — a permanently broken bridge. That intuition doesn't transfer here: exhausting `R_max` on one PR's attempt at a step doesn't mean the step is broken forever. The next PR through the same step should start from a fresh (or discounted) budget, not from "this edge is impassable." Worth flagging explicitly, since it's easy to carry the wrong mental model over from the sibling document by accident.
- **Cross-PR generalization is unresolved.** `h(s_w)` learned from one PR's retries at step `s_w` — does it transfer to the next PR going through the same step? LRTA*'s formulation is single-agent, single-trajectory; it doesn't have a built-in answer for "many overlapping trajectories through the same state space, run by different callers." That's closer to shared-value-function territory in multi-agent RL, and the vocabulary lining up doesn't mean the primitive resolves it for free.

## Open questions

- Does `h(s)` live per-repo, per-workflow-step, or per-`(repo, step, likely-cause)`? The non-stationarity point above suggests a single per-step table is too coarse to be reliable.
- The two-budget design (retry cap vs. poll timeout) is worth its own small spec if this is ever built, independent of the algorithm question.
- Should learning persist across PRs at all, given flakiness — or is it more honest to treat each PR as a single fresh trial, in which case this is just bounded real-time search once, not the repeated-trial learning story LRTA*/RTDP are actually known for?

## Relationship to the maze work

Same posture as its sibling document: a cross-check, not a build spec. There are now two stress tests sitting alongside the maze design — one showing where D* Lite's assumptions strain against a real dynamic graph, one showing where LRTA*/RTDP's assumptions strain against a real "cost is learned through retries" setting. Neither is scheduled for implementation. The maze — clean heuristic, one agent genuinely occupying one cell, a stationary environment — remains the actual teaching deliverable, and the reason both stress tests conclude the same way: the real system exposes assumptions the toy example gets to keep clean by being small.
