import pytest

from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import build_pipeline_fanout_lite
from discovery.visualization.discovery_view import _walk_frames, build_networkx_graph


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


class TestWalkFrames:
    def test_one_frame_per_path_position(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames = _walk_frames(env, result.path)
        assert len(frames) == len(result.path)

    def test_first_frame_senses_the_start_node(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames = _walk_frames(env, result.path)
        node_id, caption, known, visited = frames[0]
        assert node_id == "commit"
        assert caption == "sense_edges('commit') → ('lint', 'unit-tests')"
        assert known == {"commit", "lint", "unit-tests"}
        assert visited == {"commit"}

    def test_revisiting_a_node_backtracks_without_resensing(self, env):
        # merge-gate is reached twice (path index 2 and 4); the second
        # arrival is a backtrack, not a fresh sense - see
        # backtracking-exploration/algorithm_fit.md's worked example.
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path[2] == "merge-gate"
        assert result.path[4] == "merge-gate"

        frames = _walk_frames(env, result.path)
        assert frames[2][1] == "sense_edges('merge-gate') → ('deploy',)"
        assert frames[4][1] == "backtrack to 'merge-gate'"

    def test_known_set_only_grows(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames = _walk_frames(env, result.path)
        known_sizes = [len(known) for _, _, known, _ in frames]
        assert known_sizes == sorted(known_sizes)
        assert known_sizes[-1] == 6  # every node eventually known

    def test_final_frame_has_every_node_visited(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames = _walk_frames(env, result.path)
        _, _, _, visited = frames[-1]
        assert visited == set(build_pipeline_fanout_lite().keys())
