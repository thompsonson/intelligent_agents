import pytest

from path_maintenance.agents.path_maintenance import PathMaintenanceAgent
from path_maintenance.core.environment import CellState, PathGraphEnvironment
from path_maintenance.scenarios.deploy_chain_lite import (
    build_deploy_chain_lite,
    deploy_chain_lite_order,
)
from path_maintenance.visualization.graph_view import build_networkx_graph, record_walk


@pytest.fixture
def env():
    return PathGraphEnvironment(build_deploy_chain_lite())


class TestBuildNetworkxGraph:
    def test_and_join_node_flagged(self, env):
        graph = build_networkx_graph(env)
        assert graph.nodes["merge"]["is_and_join"] is True
        assert graph.nodes["lint"]["is_and_join"] is False

    def test_edges_point_from_dependency_to_dependent(self, env):
        graph = build_networkx_graph(env)
        assert graph.has_edge("pre-commit", "lint")
        assert graph.has_edge("lint", "merge")
        assert graph.has_edge("unit-tests", "merge")
        assert graph.has_edge("merge", "deploy")


class TestRecordWalk:
    def test_no_repairs_produces_only_arrive_events(self, env):
        order = deploy_chain_lite_order()
        agent = PathMaintenanceAgent(env, order)
        result, events = record_walk(env, agent)

        assert result.repairs_performed == []
        # order[0] is never sensed - 4 remaining nodes, 4 arrive events
        assert len(events) == len(order) - 1
        assert all(kind == "arrive" for kind, *_ in events)

    def test_repair_produces_arrive_then_repair_for_that_node(self, env):
        order = deploy_chain_lite_order()
        env.inject_repairs(["lint", "deploy"], order)
        agent = PathMaintenanceAgent(env, order)
        result, events = record_walk(env, agent)

        arrive_lint = ("arrive", "lint", CellState.NEEDS_REPAIR)
        repair_lint = ("repair", "lint")
        assert arrive_lint in events
        assert repair_lint in events
        assert events.index(arrive_lint) < events.index(repair_lint)

    def test_events_restore_original_env_methods(self, env):
        order = deploy_chain_lite_order()
        original_get = env.get_node_state
        original_repair = env.repair_node
        record_walk(env, PathMaintenanceAgent(env, order))
        assert env.get_node_state == original_get
        assert env.repair_node == original_repair
