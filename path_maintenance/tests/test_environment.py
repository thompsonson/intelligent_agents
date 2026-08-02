import pytest

from path_maintenance.core.domain import CellState, GraphNode
from path_maintenance.core.environment import PathGraphEnvironment


def make_nodes():
    # pre-commit -> lint, unit-tests -> merge -> deploy (deploy_chain_lite's
    # shape - see documentation/path-maintenance/graph-topology/scenario.md)
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


class TestGraphValidation:
    def test_requires_referencing_unknown_node_is_rejected(self):
        nodes = {"a": GraphNode(id="a", requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            PathGraphEnvironment(nodes)

    def test_direct_cycle_is_rejected(self):
        nodes = {
            "a": GraphNode(id="a", requires=("b",)),
            "b": GraphNode(id="b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            PathGraphEnvironment(nodes)

    def test_longer_cycle_is_rejected(self):
        nodes = {
            "a": GraphNode(id="a", requires=("c",)),
            "b": GraphNode(id="b", requires=("a",)),
            "c": GraphNode(id="c", requires=("b",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            PathGraphEnvironment(nodes)

    def test_valid_dag_with_and_join_accepted(self, env):
        assert set(env.nodes.keys()) == {
            "pre-commit",
            "lint",
            "unit-tests",
            "merge",
            "deploy",
        }


class TestReadyNodes:
    def test_only_zero_dependency_node_ready_at_start(self, env):
        assert env.ready_nodes(set()) == ["pre-commit"]

    def test_and_join_not_ready_until_both_parents_satisfied(self, env):
        satisfied = {"pre-commit", "lint"}
        assert "merge" not in env.ready_nodes(satisfied)

    def test_and_join_ready_once_both_parents_satisfied(self, env):
        satisfied = {"pre-commit", "lint", "unit-tests"}
        assert env.ready_nodes(satisfied) == ["merge"]

    def test_satisfied_nodes_never_reappear_as_ready(self, env):
        satisfied = {"pre-commit"}
        assert "pre-commit" not in env.ready_nodes(satisfied)


class TestGetNodeState:
    def test_open_node_defaults_to_open(self, env):
        assert env.get_node_state("lint") == CellState.OPEN

    def test_unknown_node_raises(self, env):
        with pytest.raises(ValueError):
            env.get_node_state("does-not-exist")


class TestInjectRepairs:
    def test_marks_nodes_needs_repair(self, env):
        order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
        env.inject_repairs(["lint", "deploy"], order)
        assert env.get_node_state("lint") == CellState.NEEDS_REPAIR
        assert env.get_node_state("deploy") == CellState.NEEDS_REPAIR

    def test_leaves_other_nodes_open(self, env):
        order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
        env.inject_repairs(["lint"], order)
        assert env.get_node_state("unit-tests") == CellState.OPEN

    def test_node_not_in_order_rejected(self, env):
        with pytest.raises(ValueError):
            env.inject_repairs(["deploy"], ["pre-commit", "lint"])

    def test_unknown_node_rejected(self, env):
        with pytest.raises(ValueError):
            env.inject_repairs(["does-not-exist"], ["does-not-exist"])

    def test_already_needs_repair_rejected(self, env):
        order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
        env.inject_repairs(["lint"], order)
        with pytest.raises(ValueError):
            env.inject_repairs(["lint"], order)


class TestRepairNode:
    def test_transitions_needs_repair_to_open(self, env):
        order = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]
        env.inject_repairs(["lint"], order)
        env.repair_node("lint")
        assert env.get_node_state("lint") == CellState.OPEN

    def test_already_open_node_rejected(self, env):
        with pytest.raises(ValueError):
            env.repair_node("lint")

    def test_unknown_node_rejected(self, env):
        with pytest.raises(ValueError):
            env.repair_node("does-not-exist")
