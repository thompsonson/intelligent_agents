from typing import Dict

from ..core.domain import DiscoveryNode


def build_pipeline_fanout_lite() -> Dict[str, DiscoveryNode]:
    """commit -> lint, unit-tests; lint -> merge-gate; unit-tests ->
    integration-tests, merge-gate; integration-tests -> merge-gate;
    merge-gate -> deploy; deploy -> (nothing).

    Six nodes, two fan-out branch points (commit, unit-tests),
    reconvergent at merge-gate, exactly one reachable no-notifies node
    (deploy - the goal). See
    documentation/discovery/scenario.md.
    """
    return {
        "commit": DiscoveryNode(id="commit", notifies=("lint", "unit-tests")),
        "lint": DiscoveryNode(id="lint", notifies=("merge-gate",)),
        "unit-tests": DiscoveryNode(
            id="unit-tests", notifies=("integration-tests", "merge-gate")
        ),
        "integration-tests": DiscoveryNode(
            id="integration-tests", notifies=("merge-gate",)
        ),
        "merge-gate": DiscoveryNode(id="merge-gate", notifies=("deploy",)),
        "deploy": DiscoveryNode(id="deploy"),
    }
