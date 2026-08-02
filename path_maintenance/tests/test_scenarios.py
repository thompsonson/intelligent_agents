from path_maintenance.core.environment import PathGraphEnvironment
from path_maintenance.scenarios.deploy_chain_lite import (
    build_deploy_chain_lite,
    deploy_chain_lite_order,
)


def compute_topological_order(env: PathGraphEnvironment) -> list:
    """Standard ready_nodes()-driven topo-sort, ties broken by id - the
    same tie-break TopologicalExecutor uses. Independent of
    deploy_chain_lite_order()'s hand-written list, so this test actually
    catches a hand-computation mistake instead of just repeating it."""
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
    def test_hand_written_order_matches_computed_topological_order(self):
        env = PathGraphEnvironment(build_deploy_chain_lite())
        assert deploy_chain_lite_order() == compute_topological_order(env)

    def test_and_join_has_two_parents(self):
        nodes = build_deploy_chain_lite()
        assert nodes["merge"].requires == ("lint", "unit-tests")
