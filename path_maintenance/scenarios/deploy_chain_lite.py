from typing import Dict, List

from ..core.domain import GraphNode


def build_deploy_chain_lite() -> Dict[str, GraphNode]:
    """pre-commit -> lint, unit-tests -> merge -> deploy.

    Five nodes, one AND-join (`merge`, two parents) - the smallest graph
    with a genuine fan-in. See
    documentation/path-maintenance/graph-topology/scenario.md.
    """
    return {
        "pre-commit": GraphNode(id="pre-commit"),
        "lint": GraphNode(id="lint", requires=("pre-commit",)),
        "unit-tests": GraphNode(id="unit-tests", requires=("pre-commit",)),
        "merge": GraphNode(id="merge", requires=("lint", "unit-tests")),
        "deploy": GraphNode(id="deploy", requires=("merge",)),
    }


def deploy_chain_lite_order() -> List[str]:
    """The topological order scenario.md computes by hand: ready_nodes()
    returns pre-commit alone, then lint/unit-tests together (sorted
    alphabetically), then merge, then deploy. No search needed - an
    AND-only DAG has no alternative routes to choose between."""
    return ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
