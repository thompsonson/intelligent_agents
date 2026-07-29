from typing import Dict, Optional, Tuple

from ..core.domain import GroupNode, TaskNode

APPLY_ACTIONS_VARIANTS = (
    "apply-actions-minimal",
    "apply-actions-comprehensive",
    "apply-actions-test-driven",
)


def build_pr_merge_with_variants(
    pass_probability: float = 1.0,
    overrides: Optional[Dict[str, float]] = None,
    check_disk_pass_probability: float = 0.9,
) -> Tuple[Dict[str, TaskNode], Tuple[GroupNode, ...], str]:
    """`pr_merge_lite`'s exact topology with one change: `apply-actions`
    splits into three variant strategies (`apply-actions-minimal`,
    `-comprehensive`, `-test-driven`) sharing an OR-group, `actions-ready`,
    that takes over `apply-actions`'s old position in `merged`'s `requires`.
    `check-disk` is reused unmodified from `disk_check_lite` as a true
    orphan, disconnected from the rest of the graph. See
    documentation/task-graph/or-groups/scenario.md.

    Args:
        pass_probability: Default per-attempt pass chance applied to every
            node except `check-disk`, unless overridden.
        overrides: Per-node pass_probability overrides, e.g.
            {"apply-actions-minimal": 0.0} to force one variant to fail
            while leaving the others at the default.
        check_disk_pass_probability: Pass chance for the orphan `check-disk`
            node, defaulting to disk_check_lite's own 0.9.

    Returns:
        A (nodes, groups, goal) tuple ready to unpack into
        TaskGraphEnvironment(nodes, config, groups=groups, goal=goal).
    """
    overrides = overrides or {}

    def p(node_id: str) -> float:
        return overrides.get(node_id, pass_probability)

    nodes: Dict[str, TaskNode] = {
        "ci-check": TaskNode(
            id="ci-check",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("ci-check"),
            rmax=3,
        ),
        "generate-actions": TaskNode(
            id="generate-actions",
            kind="acting",
            retry_flavor="generation",
            pass_probability=p("generate-actions"),
            rmax=3,
        ),
        "merged": TaskNode(
            id="merged",
            kind="acting",
            retry_flavor="repair",
            pass_probability=p("merged"),
            rmax=2,
            requires=("ci-check", "actions-ready"),
        ),
        "deploy-staging": TaskNode(
            id="deploy-staging",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("deploy-staging"),
            rmax=3,
            requires=("merged",),
        ),
        "deploy-publish": TaskNode(
            id="deploy-publish",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("deploy-publish"),
            rmax=3,
            requires=("merged",),
        ),
        "deploy-promote": TaskNode(
            id="deploy-promote",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("deploy-promote"),
            rmax=3,
            requires=("merged",),
        ),
        "released": TaskNode(
            id="released",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=p("released"),
            rmax=3,
            requires=("deploy-staging", "deploy-publish", "deploy-promote"),
        ),
        "check-disk": TaskNode(
            id="check-disk",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=check_disk_pass_probability,
            rmax=1,  # matches disk_check_lite's own default
        ),
    }

    for variant_id in APPLY_ACTIONS_VARIANTS:
        nodes[variant_id] = TaskNode(
            id=variant_id,
            kind="acting",
            retry_flavor="repair",
            pass_probability=p(variant_id),
            rmax=3,
            r_patience=1,
            requires=("generate-actions",),
        )

    groups = (GroupNode(id="actions-ready", members=APPLY_ACTIONS_VARIANTS),)

    return nodes, groups, "released"
