from typing import Dict, List

from ..core.domain import GraphNode
from ..core.environment import PathGraphEnvironment


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
    """The topological order, computed via ready_nodes() rather than
    hand-written: pre-commit alone, then lint/unit-tests together (sorted
    alphabetically, the same tie-break TopologicalExecutor uses), then
    merge, then deploy. No search needed - an AND-only DAG has no
    alternative routes to choose between, so this is a plain topological
    sort, not a heuristic search.

    Originally hardcoded, with a comment explaining what ready_nodes()
    would produce rather than calling it - caught in PR #11 review: the
    "no search needed, the topology is the plan" claim was correct in
    principle but unexercised by the actual scenario-building code path.
    """
    env = PathGraphEnvironment(build_deploy_chain_lite())
    satisfied: set = set()
    order: List[str] = []
    while len(satisfied) < len(env.nodes):
        ready = sorted(env.ready_nodes(satisfied))
        order.extend(ready)
        satisfied.update(ready)
    return order
