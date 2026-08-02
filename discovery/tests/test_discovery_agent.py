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
        assert result.blocked_nodes == []

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
        assert result.blocked_nodes == []

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
        assert result.blocked_nodes == []

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
        assert result.blocked_nodes == []

    def test_unknown_start_id_raises(self):
        env = DiscoveryEnvironment({"a": DiscoveryNode(id="a")})
        with pytest.raises(ValueError, match="does-not-exist"):
            DiscoveryAgent(env, start_id="does-not-exist").walk()


def make_pipeline_fanout_lite_gated():
    # See documentation/discovery/and-joins/scenario.md
    nodes = make_pipeline_fanout_lite()
    nodes["merge-gate"] = DiscoveryNode(
        id="merge-gate",
        notifies=("deploy",),
        requires=("lint", "integration-tests"),
    )
    return nodes


class TestAndJoins:
    def test_matches_and_joins_algorithm_fit_md_worked_example(self):
        # See documentation/discovery/and-joins/algorithm_fit.md's
        # phase 1 + phase 2 trace: 14 moves, 6 senses.
        env = DiscoveryEnvironment(make_pipeline_fanout_lite_gated())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path == [
            "commit", "lint", "merge-gate", "lint", "commit",
            "unit-tests", "integration-tests", "unit-tests", "commit",
            "lint", "merge-gate", "deploy", "merge-gate", "lint", "commit",
        ]
        assert result.nodes_sensed == 6
        assert result.total_cost == 14
        assert result.blocked_nodes == []
        assert result.goal_reached is True

    def test_deploy_is_sensed_last_not_third(self):
        # The concrete bug this step exists to fix - contrast with step
        # 2's ungated walk, where deploy was the 4th of 6 nodes sensed.
        env = DiscoveryEnvironment(make_pipeline_fanout_lite_gated())
        result = DiscoveryAgent(env, start_id="commit").walk()
        sensed_order = list(dict.fromkeys(result.path))  # first-seen order
        assert sensed_order[-1] == "deploy"

    def test_shortcut_edge_is_gated_same_as_direct_arrival(self):
        # unit-tests notifies merge-gate directly, bypassing
        # integration-tests. Arriving that way still has to wait for
        # integration-tests - the gate checks what's cleared, not which
        # edge was used to arrive. Already exercised end-to-end by the
        # worked-example test above; this asserts the specific claim.
        env = DiscoveryEnvironment(make_pipeline_fanout_lite_gated())
        result = DiscoveryAgent(env, start_id="commit").walk()
        deploy_index = result.path.index("deploy")
        integration_tests_index = result.path.index("integration-tests")
        assert integration_tests_index < deploy_index

    def test_reachability_violation_reports_blocked_and_no_goal(self):
        # release-notes is required but never notified by anyone -
        # merge-gate can never clear, deploy is never reached. See
        # and-joins/algorithm_fit.md's "Resolved: a scenario exercising a
        # genuine reachability violation".
        nodes = make_pipeline_fanout_lite_gated()
        nodes["release-notes"] = DiscoveryNode(id="release-notes")
        nodes["merge-gate"] = DiscoveryNode(
            id="merge-gate",
            notifies=("deploy",),
            requires=("lint", "integration-tests", "release-notes"),
        )
        env = DiscoveryEnvironment(nodes)
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path == [
            "commit", "lint", "merge-gate", "lint", "commit",
            "unit-tests", "integration-tests", "unit-tests", "commit",
        ]
        assert result.nodes_sensed == 5  # release-notes never queried
        assert result.total_cost == 8
        assert result.blocked_nodes == ["merge-gate"]
        assert result.goal_reached is False

    def test_requires_cycle_rejected_at_construction(self):
        nodes = {
            "a": DiscoveryNode(id="a", requires=("b",)),
            "b": DiscoveryNode(id="b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            DiscoveryEnvironment(nodes)


def make_double_gate_graph():
    # Minimal illustrative graph (not a shipped scenario) forcing two
    # blocked nodes to clear in the same readiness sweep - see
    # and-joins/algorithm_fit.md's "Resolved: tie-break when more than
    # one blocked node clears in the same sweep".
    return {
        "root": DiscoveryNode(id="root", notifies=("a1", "a2", "b1", "b2")),
        "a1": DiscoveryNode(id="a1", notifies=("gate-a",)),
        "a2": DiscoveryNode(id="a2", notifies=("gate-a",)),
        "gate-a": DiscoveryNode(id="gate-a", requires=("a1", "a2")),
        "b1": DiscoveryNode(id="b1", notifies=("gate-b",)),
        "b2": DiscoveryNode(id="b2", notifies=("gate-b",)),
        "gate-b": DiscoveryNode(id="gate-b", requires=("b1", "b2")),
    }


class TestMultipleBlockedNodesClearingTogether:
    def test_matches_algorithm_fit_md_worked_example(self):
        env = DiscoveryEnvironment(make_double_gate_graph())
        result = DiscoveryAgent(env, start_id="root").walk()
        assert result.path == [
            "root", "a1", "gate-a", "a1", "root", "a2", "root",
            "b1", "gate-b", "b1", "root", "b2", "root",
            "a1", "gate-a", "a1", "root",
            "b1", "gate-b", "b1", "root",
        ]
        assert result.nodes_sensed == 7
        assert result.total_cost == 20
        assert result.blocked_nodes == []
        assert result.goal_reached is True

    def test_gate_a_resumed_before_gate_b(self):
        # Lowest id first: "gate-a" sorts before "gate-b".
        env = DiscoveryEnvironment(make_double_gate_graph())
        result = DiscoveryAgent(env, start_id="root").walk()
        assert result.path.index("gate-a") < result.path.index("gate-b")
