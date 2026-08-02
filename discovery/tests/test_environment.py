import pytest

from discovery.core.domain import DiscoveryNode
from discovery.core.environment import DiscoveryEnvironment


def make_nodes():
    # commit -> lint, unit-tests; lint -> merge-gate; unit-tests ->
    # integration-tests, merge-gate; integration-tests -> merge-gate;
    # merge-gate -> deploy; deploy -> (nothing) - pipeline_fanout_lite's
    # shape, see documentation/discovery/scenario.md
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


@pytest.fixture
def env():
    return DiscoveryEnvironment(make_nodes())


class TestGraphValidation:
    def test_notifies_referencing_unknown_node_is_rejected(self):
        nodes = {"a": DiscoveryNode(id="a", notifies=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            DiscoveryEnvironment(nodes)

    def test_cycle_in_notifies_is_accepted(self):
        # Unlike a requires-graph, a notifies-graph doesn't need to be
        # acyclic to be valid - an agent that's already visited a node
        # just never needs to revisit it. See environment_design.md's
        # __init__ docstring.
        nodes = {
            "a": DiscoveryNode(id="a", notifies=("b",)),
            "b": DiscoveryNode(id="b", notifies=("a",)),
        }
        env = DiscoveryEnvironment(nodes)
        assert env.sense_edges("a") == ("b",)

    def test_valid_graph_with_fanout_and_reconvergence_accepted(self, env):
        assert set(env.nodes.keys()) == {
            "commit",
            "lint",
            "unit-tests",
            "integration-tests",
            "merge-gate",
            "deploy",
        }


class TestSenseEdges:
    def test_returns_notifies_of_given_node(self, env):
        assert env.sense_edges("commit") == ("lint", "unit-tests")

    def test_terminal_node_returns_empty_tuple(self, env):
        assert env.sense_edges("deploy") == ()

    def test_unknown_node_raises(self, env):
        with pytest.raises(ValueError, match="does-not-exist"):
            env.sense_edges("does-not-exist")

    def test_no_arrival_check_any_known_id_can_be_sensed(self, env):
        # The environment tracks no position, so it has no way to check
        # "did you actually arrive" - it answers whatever real node id
        # it's asked, same as get_job_state()/get_cell_state() before it.
        # See environment_design.md's "Resolved: arrival gates querying,
        # but the environment doesn't enforce it".
        assert env.sense_edges("deploy") == ()
        assert env.sense_edges("unit-tests") == ("integration-tests", "merge-gate")


class TestGetMoveCost:
    def test_always_one(self, env):
        assert env.get_move_cost("commit", "lint") == 1
        assert env.get_move_cost("merge-gate", "deploy") == 1


class TestRequiresValidation:
    def test_requires_referencing_unknown_node_is_rejected(self):
        nodes = {"a": DiscoveryNode(id="a", requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            DiscoveryEnvironment(nodes)

    def test_cycle_in_requires_is_rejected(self):
        # Unlike notifies, a requires-cycle can never clear regardless of
        # exploration order - see and-joins/environment_design.md's "The
        # reachability constraint".
        nodes = {
            "a": DiscoveryNode(id="a", requires=("b",)),
            "b": DiscoveryNode(id="b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            DiscoveryEnvironment(nodes)

    def test_valid_requires_graph_accepted(self):
        nodes = {
            "a": DiscoveryNode(id="a"),
            "b": DiscoveryNode(id="b", requires=("a",)),
        }
        env = DiscoveryEnvironment(nodes)
        assert env.sense_requires("b") == ("a",)


class TestSenseRequires:
    def test_returns_requires_of_given_node(self):
        nodes = {
            "a": DiscoveryNode(id="a"),
            "b": DiscoveryNode(id="b", requires=("a",)),
        }
        env = DiscoveryEnvironment(nodes)
        assert env.sense_requires("b") == ("a",)

    def test_node_with_no_requires_returns_empty_tuple(self, env):
        assert env.sense_requires("commit") == ()

    def test_unknown_node_raises(self, env):
        with pytest.raises(ValueError, match="does-not-exist"):
            env.sense_requires("does-not-exist")

    def test_no_arrival_check_any_known_id_can_be_sensed(self):
        # Same no-arrival-check contract as sense_edges() - see
        # and-joins/environment_design.md's "Sensing: two queries, not one".
        nodes = {
            "a": DiscoveryNode(id="a"),
            "b": DiscoveryNode(id="b", requires=("a",)),
        }
        env = DiscoveryEnvironment(nodes)
        assert env.sense_requires("b") == ("a",)
