import pytest

from path_maintenance.agents.path_maintenance import PathMaintenanceAgent
from path_maintenance.core.domain import GraphNode
from path_maintenance.core.environment import CellState, PathGraphEnvironment

ORDER = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]


def make_nodes():
    return {
        "pre-commit": GraphNode(id="pre-commit"),
        "lint": GraphNode(id="lint", requires=("pre-commit",)),
        "unit-tests": GraphNode(id="unit-tests", requires=("pre-commit",)),
        "merge": GraphNode(id="merge", requires=("lint", "unit-tests")),
        "deploy": GraphNode(id="deploy", requires=("merge",)),
    }


@pytest.fixture
def env():
    return PathGraphEnvironment(make_nodes())


class TestPathMaintenanceAgentWalk:
    def test_no_repairs_needed(self, env):
        result = PathMaintenanceAgent(env, ORDER).walk()
        assert result.repairs_performed == []
        assert result.success is True
        assert result.path == ORDER

    def test_repairs_injected_nodes_in_walk_order(self, env):
        env.inject_repairs(["lint", "deploy"], ORDER)
        result = PathMaintenanceAgent(env, ORDER).walk()
        assert result.repairs_performed == ["lint", "deploy"]

    def test_repaired_nodes_end_up_open(self, env):
        env.inject_repairs(["lint"], ORDER)
        PathMaintenanceAgent(env, ORDER).walk()
        assert env.get_node_state("lint") == CellState.OPEN

    def test_never_senses_nodes_off_the_order(self, env):
        sensed = []
        original = env.get_node_state

        def spy(node_id):
            sensed.append(node_id)
            return original(node_id)

        env.get_node_state = spy
        PathMaintenanceAgent(env, ORDER).walk()
        assert all(node_id in ORDER for node_id in sensed)

    def test_does_not_sense_the_first_node(self, env):
        # Same convention as step 1's maze: the first element of the order
        # is where the agent starts, not something it "arrives at" - see
        # documentation/path-maintenance/graph-topology/environment_design.md.
        sensed = []
        original = env.get_node_state

        def spy(node_id):
            sensed.append(node_id)
            return original(node_id)

        env.get_node_state = spy
        PathMaintenanceAgent(env, ORDER).walk()
        assert "pre-commit" not in sensed

    def test_and_join_repair_on_one_parent_does_not_affect_the_other(self, env):
        env.inject_repairs(["lint"], ORDER)
        PathMaintenanceAgent(env, ORDER).walk()
        assert env.get_node_state("unit-tests") == CellState.OPEN

    def test_result_path_is_identical_to_input_order(self, env):
        result = PathMaintenanceAgent(env, ORDER).walk()
        assert result.path == ORDER
