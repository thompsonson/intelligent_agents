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
    def test_matches_backtracking_algorithm_fit_md_worked_example(self):
        # See documentation/discovery/backtracking-exploration/
        # algorithm_fit.md's 17-row trace table: 10 moves, 6 senses.
        env = DiscoveryEnvironment(make_pipeline_fanout_lite())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path == [
            "commit",
            "lint",
            "merge-gate",
            "deploy",
            "merge-gate",
            "lint",
            "commit",
            "unit-tests",
            "integration-tests",
            "unit-tests",
            "commit",
        ]
        assert result.nodes_sensed == 6
        assert result.goal_reached is True
        assert result.total_cost == 10

    def test_visits_every_reachable_node(self):
        # Step 1's agent stranded unit-tests/integration-tests; the whole
        # point of backtracking is that full exploration reaches them too.
        env = DiscoveryEnvironment(make_pipeline_fanout_lite())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert set(result.path) == set(make_pipeline_fanout_lite().keys())

    def test_revisiting_a_node_during_backtrack_does_not_resense_it(self):
        env = DiscoveryEnvironment(make_pipeline_fanout_lite())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path.count("merge-gate") == 2
        assert result.path.count("commit") == 3
        assert result.nodes_sensed == 6  # not 6 + however many revisits


class TestWalkEdgeCases:
    def test_start_node_with_no_notifies_is_immediately_the_goal(self):
        nodes = {"solo": DiscoveryNode(id="solo")}
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="solo").walk()
        assert result.path == ["solo"]
        assert result.nodes_sensed == 1
        assert result.goal_reached is True
        assert result.total_cost == 0  # no moves at all, one sense only

    def test_linear_chain_walks_out_and_fully_backtracks(self):
        nodes = {
            "a": DiscoveryNode(id="a", notifies=("b",)),
            "b": DiscoveryNode(id="b", notifies=("c",)),
            "c": DiscoveryNode(id="c"),
        }
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="a").walk()
        assert result.path == ["a", "b", "c", "b", "a"]
        assert result.nodes_sensed == 3
        assert result.goal_reached is True
        assert result.total_cost == 4  # a->b, b->c, c->b, b->a

    def test_cycle_with_no_reachable_terminal_backtracks_and_stops(self):
        nodes = {
            "a": DiscoveryNode(id="a", notifies=("b",)),
            "b": DiscoveryNode(id="b", notifies=("a",)),
        }
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="a").walk()
        assert result.path == ["a", "b", "a"]
        assert result.nodes_sensed == 2
        assert result.goal_reached is False
        assert result.total_cost == 2  # a->b, then backtrack b->a

    def test_unknown_start_id_raises(self):
        env = DiscoveryEnvironment({"a": DiscoveryNode(id="a")})
        with pytest.raises(ValueError, match="does-not-exist"):
            DiscoveryAgent(env, start_id="does-not-exist").walk()
