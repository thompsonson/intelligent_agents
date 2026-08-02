from path_maintenance.core.environment import PathGraphEnvironment
from path_maintenance.scenarios.deploy_chain_lite import (
    build_deploy_chain_lite,
    deploy_chain_lite_order,
)


def compute_topological_order(env: PathGraphEnvironment) -> list:
    """A second, independently-written ready_nodes()-driven topo-sort,
    ties broken by id - the same tie-break TopologicalExecutor uses.
    deploy_chain_lite_order() now does its own real computation too (see
    PR #11 review - it used to be a hardcoded list), so this cross-checks
    two separate implementations of the same algorithm against each
    other, rather than checking one against a hand-written value."""
    satisfied: set = set()
    order = []
    all_nodes = set(env.nodes.keys())
    while satisfied != all_nodes:
        ready = sorted(env.ready_nodes(satisfied))
        for node_id in ready:
            order.append(node_id)
            satisfied.add(node_id)
    return order


class TestDeployChainLiteOrder:
    def test_matches_expected_order(self):
        # Regression value, locking in the real computed result.
        assert deploy_chain_lite_order() == [
            "pre-commit",
            "lint",
            "unit-tests",
            "merge",
            "deploy",
        ]

    def test_matches_independently_computed_topological_order(self):
        env = PathGraphEnvironment(build_deploy_chain_lite())
        assert deploy_chain_lite_order() == compute_topological_order(env)

    def test_and_join_has_two_parents(self):
        nodes = build_deploy_chain_lite()
        assert nodes["merge"].requires == ("lint", "unit-tests")
