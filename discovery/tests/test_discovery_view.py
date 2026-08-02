import pytest

from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import build_pipeline_fanout_lite
from discovery.visualization.discovery_view import build_networkx_graph, record_walk


@pytest.fixture
def env():
    return DiscoveryEnvironment(build_pipeline_fanout_lite())


class TestBuildNetworkxGraph:
    def test_goal_node_flagged(self, env):
        graph = build_networkx_graph(env)
        assert graph.nodes["deploy"]["is_goal"] is True
        assert graph.nodes["commit"]["is_goal"] is False

    def test_edges_point_from_node_to_what_it_notifies(self, env):
        graph = build_networkx_graph(env)
        assert graph.has_edge("commit", "lint")
        assert graph.has_edge("commit", "unit-tests")
        assert graph.has_edge("merge-gate", "deploy")


class TestRecordWalk:
    def test_produces_one_sense_event_per_node_sensed(self, env):
        agent = DiscoveryAgent(env, start_id="commit")
        result, events = record_walk(env, agent)

        assert len(events) == result.nodes_sensed
        assert all(kind == "sense" for kind, *_ in events)

    def test_first_event_matches_start_node(self, env):
        agent = DiscoveryAgent(env, start_id="commit")
        _, events = record_walk(env, agent)
        assert events[0] == ("sense", "commit", ("lint", "unit-tests"))

    def test_last_event_matches_goal(self, env):
        agent = DiscoveryAgent(env, start_id="commit")
        _, events = record_walk(env, agent)
        assert events[-1] == ("sense", "deploy", ())

    def test_events_restore_original_env_method(self, env):
        original_sense = env.sense_edges
        record_walk(env, DiscoveryAgent(env, start_id="commit"))
        assert env.sense_edges == original_sense
