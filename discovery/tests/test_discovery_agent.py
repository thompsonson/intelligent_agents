import pytest

from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.domain import DiscoveryNode
from discovery.core.environment import DiscoveryEnvironment


def make_pipeline_fanout_lite():
    # See documentation/discovery/scenario.md
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


class TestWalkOnPipelineFanoutLite:
    def test_matches_algorithm_fit_md_worked_example(self):
        env = DiscoveryEnvironment(make_pipeline_fanout_lite())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path == ["commit", "lint", "merge-gate", "deploy"]
        assert result.nodes_sensed == 4
        assert result.goal_reached is True

    def test_never_visits_nodes_left_unvisited_by_the_tie_break(self):
        env = DiscoveryEnvironment(make_pipeline_fanout_lite())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert "unit-tests" not in result.path
        assert "integration-tests" not in result.path


class TestWalkEdgeCases:
    def test_start_node_with_no_notifies_is_immediately_the_goal(self):
        nodes = {"solo": DiscoveryNode(id="solo")}
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="solo").walk()
        assert result.path == ["solo"]
        assert result.nodes_sensed == 1
        assert result.goal_reached is True

    def test_linear_chain_walks_straight_through(self):
        nodes = {
            "a": DiscoveryNode(id="a", notifies=("b",)),
            "b": DiscoveryNode(id="b", notifies=("c",)),
            "c": DiscoveryNode(id="c"),
        }
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="a").walk()
        assert result.path == ["a", "b", "c"]
        assert result.goal_reached is True

    def test_cycle_with_no_reachable_terminal_reports_stuck(self):
        nodes = {
            "a": DiscoveryNode(id="a", notifies=("b",)),
            "b": DiscoveryNode(id="b", notifies=("a",)),
        }
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="a").walk()
        assert result.path == ["a", "b"]
        assert result.goal_reached is False

    def test_unknown_start_id_raises(self):
        env = DiscoveryEnvironment({"a": DiscoveryNode(id="a")})
        with pytest.raises(ValueError, match="does-not-exist"):
            DiscoveryAgent(env, start_id="does-not-exist").walk()
