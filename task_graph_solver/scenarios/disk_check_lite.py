from typing import Dict

from ..core.domain import TaskNode


def build_disk_check_lite(pass_probability: float = 0.9) -> Dict[str, TaskNode]:
    """One node, no edges, no repair path - modeled on
    atomicguard/examples/sysadmin/workflows-guard/disk_check.dspddl.

    The smallest possible scenario: an edge that's either passable or not,
    with nothing to repair from inside the workflow. See
    documentation/task-graph/scenarios.md.

    Args:
        pass_probability: Per-attempt chance the check passes. Defaults to
            0.9 (typically-but-not-always-fine, like a real disk check);
            pass 1.0 or 0.0 for deterministic tests.
    """
    return {
        "check-disk": TaskNode(
            id="check-disk",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=pass_probability,
            rmax=1,  # matches disk_check.dspddl's :rmax 1
        ),
    }
