from typing import Dict, Optional

from ..core.domain import TaskNode


def build_pr_merge_lite(
    pass_probability: float = 1.0,
    overrides: Optional[Dict[str, float]] = None,
    invariant_overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, TaskNode]:
    """The full 8-node graph from documentation/task-graph/scenarios.md,
    modeled on the pr_merge workflow family (check_pr.dspddl, fix_pr.dspddl,
    post_merge_monitor.dspddl) with two deliberate AND-joins: `merged`
    (two required children) and `released` (three required children,
    modeled as explicit `requires` edges - the corrected version of the
    real system's single opaque `downstream-ci-passed` guard, per
    documentation/lrta/beyond_the_maze.md's diagnosability finding).

    Args:
        pass_probability: Default per-attempt pass chance applied to every
            node unless overridden. 1.0 gives a deterministic success-path
            run, useful for testing AND-composition without fighting the
            environment's shared RNG sequence.
        overrides: Per-node pass_probability overrides, e.g.
            {"deploy-staging": 0.0} to force one branch of the `released`
            join to fail while leaving the rest at the default.
        invariant_overrides: Per-node invariant_pass_probability overrides,
            e.g. {"released": 1.0} for the guard-first/sense-then-plan
            scenarios (documentation/task-graph/guard-first/,
            goal-directed-planning/) - "this step may already be true from
            a previous, interrupted run." Every node defaults to 0.0
            (TaskNode's own default), so this scenario needs no changes to
            demonstrate the pre-guard-first algorithms.

    rmax/r_patience values are taken from the real .dspddl files where a
    direct correspondence exists (`ci-check` <- check_pr.dspddl's
    :rmax 3; `apply-actions` <- fix_pr.dspddl's apply-action-list,
    :rmax 3 :r-patience 1). `merged` has no real counterpart - it's a
    scenario-level stand-in for the PR-merge action itself, given a
    small rmax (2) since merging is closer to a single atomic API call
    than a multi-step repair.
    """
    overrides = overrides or {}
    invariant_overrides = invariant_overrides or {}

    def p(node_id: str) -> float:
        return overrides.get(node_id, pass_probability)

    def inv(node_id: str) -> float:
        return invariant_overrides.get(node_id, 0.0)

    return {
        "ci-check": TaskNode(
            id="ci-check",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("ci-check"),
            invariant_pass_probability=inv("ci-check"),
            rmax=3,
        ),
        "generate-actions": TaskNode(
            id="generate-actions",
            kind="acting",
            retry_flavor="generation",
            pass_probability=p("generate-actions"),
            invariant_pass_probability=inv("generate-actions"),
            rmax=3,
        ),
        "apply-actions": TaskNode(
            id="apply-actions",
            kind="acting",
            retry_flavor="repair",
            pass_probability=p("apply-actions"),
            invariant_pass_probability=inv("apply-actions"),
            rmax=3,
            r_patience=1,
            requires=("generate-actions",),
        ),
        "merged": TaskNode(
            id="merged",
            kind="acting",
            retry_flavor="repair",
            pass_probability=p("merged"),
            invariant_pass_probability=inv("merged"),
            rmax=2,
            requires=("ci-check", "apply-actions"),
        ),
        "deploy-staging": TaskNode(
            id="deploy-staging",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("deploy-staging"),
            invariant_pass_probability=inv("deploy-staging"),
            rmax=3,
            requires=("merged",),
        ),
        "deploy-publish": TaskNode(
            id="deploy-publish",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("deploy-publish"),
            invariant_pass_probability=inv("deploy-publish"),
            rmax=3,
            requires=("merged",),
        ),
        "deploy-promote": TaskNode(
            id="deploy-promote",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("deploy-promote"),
            invariant_pass_probability=inv("deploy-promote"),
            rmax=3,
            requires=("merged",),
        ),
        "released": TaskNode(
            id="released",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("released"),
            invariant_pass_probability=inv("released"),
            rmax=3,
            requires=("deploy-staging", "deploy-publish", "deploy-promote"),
        ),
    }
