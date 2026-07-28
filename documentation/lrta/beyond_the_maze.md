# LRTA*/RTDP Beyond the Maze: Learning Pipeline Costs from Real Effectors

## Purpose

This is the same kind of exercise as [`documentation/d-star/beyond_the_maze.md`](../d-star/beyond_the_maze.md) — stress-test a toy-example algorithm against a real system, not build the real system. But it's grounded differently on purpose.

The "Atomic Action Pair" primitive discussed alongside this repo's design work (an LLM generator `a_gen` wrapped by a deterministic-looking Guard `G`, retried up to `R_max` times) was originally mapped onto D* Lite, PDDL, LRTA*/RTDP, and the RL Options framework all at once. The critique of that mapping was specific: **LRTA*/RTDP is the mapping that doesn't require pretending the outcome is deterministic** — it's built for exactly the situation where the true cost of an action isn't known until you've paid it, and guard-retry count is real, measurable, learnable cost, not an assertion.

This revision replaces the first pass's single, partly-hypothetical example with **ground truth read directly from `thompsonson/atomicguard`'s `examples/sysadmin/workflows-guard/pr_merge/`** — its `README.md`, `gh_effector_cli_args.md`, and all four `.dspddl` workflow files. The first version of this document modeled one slice (`dispatch-dev-opencode.sh` as `a_gen`, `merge_pull_request` as the state-advancing effect). That slice turns out to be superseded in the real system, and the other three workflows in the same directory expose a structural problem the first pass never encountered: a fan-in that the single-current-node model this document (and D* Lite's) assumes cannot represent without distortion.

## Recap: the primitive, correctly grounded

- `a_gen` — the generator. One attempt at satisfying a workflow step.
- `G(a, C)` — the Guard. A check, run after `a_gen`, that returns pass / retry / fatal.
- `R_max` — retry budget. Bounds how many times `a_gen` gets re-invoked (with refined context `C`) before the step is declared a fatal failure.
- The LRTA* update this maps onto: `h(s_w) ← max(h(s_w), retries_observed(s_w) + h(s_next))` — the cost of a workflow step is approximated by how many guard-check cycles it actually took to satisfy, learned over repeated attempts.

That recap still holds. What needed correcting is *which* node in the real system this primitive actually describes — it turns out to be exactly one of eight guard nodes across four workflows, not the general case.

## Correction: the acting effector moved

The first version of this document mapped `a_gen → scripts/dev/dispatch-dev-opencode.sh`, with `merge_pull_request` as the effect that advances `S_workflow`. Per `pr_merge/README.md`'s own changelog (`## Draft: LLM-constructed dispatch command (2026-07-25)`):

> `apply-action-list` (new AP in `fix_pr.dspddl`) replaces `dispatch_dev.dspddl`'s old `dispatch-dev-opencode` AP. Instead of independently re-fetching CI results and sending them as unstructured free text, it consumes `generate-action-list`'s structured JSON plan and has an LLM construct the actual `dev --send` command, validated by a new `CommandScopeGuard` pre-guard ... before the effector runs it.

`dispatch_dev.dspddl` still exists on disk, but its own inline comment says it's been superseded and `poll-resolution` — its only remaining guard — "no longer has an in-graph `:requires`." The real repair path is `fix_pr.dspddl`'s `generate-action-list → apply-action-list` chain, and it's a strictly better instance of the Atomic Action Pair than the thing this document originally modeled: the generator now consumes a *structured* dependency artifact (traced through `PromptTemplate.render()` — confirmed in the file's comments, not assumed) instead of unstructured free text, and the acting step has an explicit pre-guard (`CommandScopeGuard`: allowed-binary allowlist + destructive-pattern denylist) checked *before* the effector runs, not just a post-hoc pass/fail check after.

## The four outcomes: ground truth

| Workflow | Guard chain | `:requires` structure | Acting effector? | Repair path inside this workflow? |
|---|---|---|---|---|
| `check_pr.dspddl` | `ci-passed` | Single node, no dependency | No — `bash :idempotent true` running `gh run list` + `gh run watch --exit-status` | **None.** A pure sense: CI either already passed or didn't. Retrying this guard re-watches the same runs; it can't make them pass. |
| `post_merge_monitor.dspddl` | `main-ci-passed → downstream-ci-passed` | Linear chain, 2 nodes | No — both `bash :idempotent true` | **None.** Also pure sensing, but `downstream-ci-passed` polls three independent deploy contexts inside one effector call (see next section). |
| `fix_pr.dspddl` | `generate-action-list → apply-action-list` | Linear chain, 2 nodes | **Yes** — `apply-action-list` is `bash :idempotent false`, gated by a `CommandScopeGuard` pre-guard, `:r-patience 1` | **Yes.** The only workflow of the four where a guard failure leads to an actual world-mutating retry. |
| `dispatch_dev.dspddl` | `poll-resolution` | Single node, no dependency | No — `bash :idempotent true` running `check-pr-resolved.sh` | Deprecated. Its acting effector was removed; what remains is a standalone sensing check, no longer wired to a repair step in-graph. |

One correction to the README's own prose worth flagging: its "Guard chains" section describes `fix_pr` as `comments-resolved → threads-resolved → generate-action-list → apply-action-list`. The `.dspddl` file itself only defines two `:guard` nodes — `generate-action-list` and `apply-action-list`. `comments-resolved`/`threads-resolved` aren't separate graph nodes with their own effectors and retry budgets; they're resolved upstream by `ci-pr-summary.sh`'s orphan-detection heuristic (`check-pr-resolved.sh`) and folded into the `{spec.ci_results}` string that `generate-action-list` consumes as input. That's a real distinction for an environment model: **only what's declared as a `:guard` in the file is a node the agent can sense, retry, or learn a cost for.** Anything collapsed into a preprocessing script upstream of the workflow is invisible plumbing — real work is happening there (an orphan-detection heuristic, no less — the same kind of judgment call a Guard makes), but it isn't part of the graph any D* Lite/LRTA*-style agent could reason about incrementally. It's worth being precise about this rather than taking the README's descriptive diagram as the literal graph.

## Three flavors of "retry" hiding under one `:rmax`

Classifying the eight guards by what a retry actually *means* for each surfaces a distinction the original document's "two conflated budgets" critique didn't go far enough on — it's not two flavors, it's at least three, and they don't share a cost semantics:

1. **Sensing retry** (`ci-passed`, `main-ci-passed`, `downstream-ci-passed`, `poll-resolution`) — the guard is a read-only poll/watch. A retry here is absorbing transient infrastructure flakiness (a `gh run watch` call that hiccups, a status API that hasn't updated yet), not an attempt to fix anything. The underlying CI/deploy outcome doesn't change because the guard retried.
2. **Generation-format retry** (`generate-action-list`) — a json-schema guard rejecting malformed LLM output. The retry loop (`:feedback-wrapper`) is entirely local: no external system is touched, nothing in the world resists or cooperates. This is closer to "the LLM needed one more nudge to emit valid JSON" than to "the task was hard."
3. **Repair-attempt retry** (`apply-action-list`) — the only one where a real, world-mutating action was attempted and the retry represents an actual failed effort to change external state.

Only flavor 3 is what LRTA*'s `h(s) ← max(h(s), retries + h(s_next))` update was built to learn from. Applying the same update to flavor 1 or 2's retry counts would be learning the wrong signal entirely — "this step is hard" when the truth is "the network hiccuped" or "the LLM needed a format nudge," neither of which says anything about how difficult the underlying workflow step actually is. Any real implementation of the LRTA* mapping needs to learn `h(s)` **only from repair-attempt retries**, and would need to explicitly exclude sensing and generation-format retries from that signal — something neither this document's first pass nor the original theoretical write-up called out.

## A strain the system already anticipated: `r-patience`

`apply-action-list` sets `:r-patience 1` against a workflow-level `:rmax 3`. Tracing this in `atomicguard`'s source (`application/workflow.py`): `r_patience` is documented as "consecutive similar failures before escalation," with an enforced invariant `r_patience < rmax`. In plain terms: this specific guard is allowed to *exist* within a 3-retry workflow budget, but is configured to escalate to a human after just **one** failed real-world attempt rather than burning the full budget — because it's the one guard in these four workflows whose effector is `:idempotent false`.

This is worth crediting rather than filing as a strain: the concern raised in the first version of this document (repeated automated attempts against a real, world-mutating action needing tighter bounds than a sensing retry) is already handled in the real system, via a parameter this document didn't know existed. `r-patience` and `rmax` are two separate knobs precisely because sensing/generation retries and repair-attempt retries shouldn't share a tolerance, which lines up with the three-flavors distinction above rather than contradicting it.

## The fan-in problem: where the single-current-node assumption breaks

`post_merge_monitor.dspddl`'s two guards look, on paper, like the same linear chain every other workflow here uses: `main-ci-passed → downstream-ci-passed`. The `.dspddl` file has exactly two `:guard` nodes. But `downstream-ci-passed`'s effector calls `scripts/check_downstream_status.sh`, which — per `gh_effector_cli_args.md` and the README — polls **three independent commit-status contexts** (`manta-deploy/staging`, `manta-deploy/publish`, `manta-deploy/promote`), where staging and publish are required and promote is optional-if-absent, and collapses all three into one exit code.

This breaks the D* Lite/LRTA* environment model in a specific, structural way, not just a "more complexity" way:

- **`rhs(s) = min` over successors is an OR-composition.** It answers "which single next step is cheapest to take" — path *choice*. `downstream-ci-passed` needs an AND-composition: you don't advance until staging **and** publish (**and** promote, if present) have *all* resolved. That's not a minimum over alternatives, it's closer to a maximum over required predecessors' resolution times — you're only as done as the slowest thing you're required to wait for. Neither D* Lite's nor LRTA*'s value-update rule computes that; it's the shape of a critical-path/PERT problem, or more precisely, of **AND-OR graph search** (e.g. AO*) — an algorithm family that explicitly distinguishes OR-nodes (pick the cheapest branch) from AND-nodes (every branch must resolve). Neither this document's family (D* Lite, LPA*, LRTA*, RTDP) handles AND-branching natively; if this fan-in were to be modeled faithfully rather than treated as an opaque effector, AO* — not a repair-search or real-time-search variant — is the actual right tool. Worth adding to `documentation/d-star/related_algorithms.md`'s backlog on that basis alone.
- **The fan-in is invisible to the graph, not just complex within it.** Because three external signals are polled and reduced to one exit code inside a single bash script, the `.dspddl` graph has exactly one guard node, one pass/fail outcome, and one retry counter for what is actually three independent sub-systems with no reason to share a cost distribution (a slow PyPI publish and a slow staging deploy are unrelated failure modes). Learning `h(downstream-ci-passed)` from that guard's retries — even restricting to flavor-3 "repair-attempt" retries, if a repair path existed here at all — would be learning a blended average across three unrelated signals, sharper and more concrete than the "non-stationarity" concern flagged in this document's first draft. There, the worry was hypothetical ("CI flakiness could vary run to run"); here it's structural: three genuinely different processes are being asked to report through one aggregate signal by construction, not by accident.
- Note this workflow has **no acting effector at all** — same as `check_pr`. If staging fails but publish and promote succeed, there is no repair path inside `post_merge_monitor.dspddl` itself; whatever fixes a failed deploy happens outside this graph entirely (the same "Driver" pattern established in the D* Lite mapping — a human, or a separate `fix_pr`-style workflow, acts on the world; this workflow only ever senses it).

## Where the mapping holds

- **Retries are a real, counted quantity for the one node that has a repair path.** `apply-action-list`'s failures are genuine world-interaction attempts, and its `r-patience`/`rmax` split shows the real system already treats that kind of retry differently from a sensing poll — exactly the distinction flavor 3 above depends on.
- **The Driver/Agent separation still holds across all four workflows.** None of the eight guards act on the world except `apply-action-list`, and even that one is explicitly safety-gated (`CommandScopeGuard`) rather than left to fire freely. Whatever ultimately resolves a failed deploy status or a failed pre-merge CI run is external to these graphs — a human, or a separately-invoked workflow.

## Where the mapping strains

- **At least three retry semantics share one `:rmax` vocabulary**, and only one of them (repair-attempt) is what LRTA*'s update rule should learn from — see above.
- **The fan-in in `post_merge_monitor` needs AND-composition, not the OR-composition D* Lite/LRTA*/RTDP provide** — see above. This is a structural mismatch, not a matter of degree.
- **The `CommandScopeGuard` gap is real, not hypothetical, and it's exactly the kind of overclaim the earlier critique warned about.** `fix_pr.dspddl`'s own inline comment says the guard "cannot verify the generated command is bound to *this* `{spec.repo}`/`{spec.pr}` specifically — `GuardInterface.validate()` has no spec access... It only enforces the allowed-binary/forbidden-pattern envelope." A well-formed, denylist-clean command could still target the wrong repo or PR, and today's guard chain wouldn't catch it. This is the concrete version of "the guard bounds stochasticity, it doesn't eliminate it" — here the bound has a documented hole, acknowledged by the people building it, not a theoretical concern.
- **Descriptive documentation (the README's guard-chain diagram) and the actual graph (`.dspddl` `:guard` declarations) disagree** on `fix_pr`'s shape. Only the latter is what an incremental-repair agent could actually act on; the former folds real judgment work (comment/thread resolution) into invisible upstream plumbing.

## Open questions

- ~~Should DS-PDDL grow explicit AND-node semantics for fan-in guards like `downstream-ci-passed`~~ — moot for `atomicguard` itself (out of scope to change), but resolved for the toy side: [`documentation/task-graph/`](../task-graph/) models fan-in as explicit multi-id `requires` edges (confirmed the DSL's `requires: tuple[str, ...]` already supports this — the real corpus just doesn't use it that way), specifically so a learning agent isn't stuck with one opaque node.
- If `h(s)` were ever learned for real here, does it need to be tracked per sub-signal (staging / publish / promote separately) rather than per guard node, given they don't share a cost distribution? That's a finer grain than either LRTA* or this document's first draft assumed. `documentation/task-graph/scenarios.md`'s `pr_merge_lite` scenario builds this distinction in from the start rather than retrofitting it.
- Is `comments-resolved`/`threads-resolved` worth promoting to explicit `:guard` nodes in `fix_pr.dspddl`, or does keeping that judgment call inside `ci-pr-summary.sh` correctly reflect that it's not something worth retrying/learning a cost for on its own?

## Relationship to the maze work

Unchanged in posture: a cross-check, not a build spec. What changed is the grounding — this revision trades a partly-hypothetical mapping for one read directly from a real, running guard-graph system, and the fan-in problem it surfaced (AND-composition, not OR) is a sharper finding than anything the original theoretical version produced. The maze — one agent, one cell, OR-branching only, a stationary environment — remains the actual teaching deliverable, and remains deliberately simpler than all four of these real workflows for the same reason as before: it doesn't have to solve AND-branching or disentangle three flavors of retry to stay correct.
