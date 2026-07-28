from typing import Dict

from ..core.domain import TaskNode


def build_repair_packages_lite(
    repair_pass_probability: float = 0.5,
    verify_pass_probability: float = 0.9,
) -> Dict[str, TaskNode]:
    """repair (acting, repair-flavor) -> verify (sensing, requires repair),
    modeled on atomicguard/examples/sysadmin/workflows-guard/repair_packages.dspddl:
    `repair-g` (rmax 3, r-patience 2) then `verify-g` (requires repair-g,
    inherits the workflow's rmax 3, no r-patience override).

    The cleanest scenario for the LRTA*/RTDP mapping: exactly one
    repair-flavor node, with no sibling flavors of retry to accidentally
    blend into its learned cost. See documentation/task-graph/scenarios.md.
    """
    return {
        "repair": TaskNode(
            id="repair",
            kind="acting",
            retry_flavor="repair",
            pass_probability=repair_pass_probability,
            rmax=3,
            r_patience=2,
        ),
        "verify": TaskNode(
            id="verify",
            kind="sensing",
            retry_flavor="sensing",
            pass_probability=verify_pass_probability,
            rmax=3,
            requires=("repair",),
        ),
    }
