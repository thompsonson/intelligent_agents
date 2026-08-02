import pytest

from discovery.agents.discovery_agent import DiscoveryAgent
from real_discovery.atomicguard_backed.core.environment import (
    StatefulDiscoveryEnvironment,
)
from real_discovery.atomicguard_backed.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
)
from real_discovery.atomicguard_backed.visualization.discovery_view import (
    _node_display_state,
    _walk_frames,
    build_networkx_graph,
)


@pytest.fixture
def env():
    return StatefulDiscoveryEnvironment(build_pipeline_fanout_lite())


@pytest.fixture
def gated_env():
    return StatefulDiscoveryEnvironment(build_pipeline_fanout_lite_gated())


class TestBuildNetworkxGraph:
    def test_goal_node_flagged(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        _, known_edges = _walk_frames(env, result.path)
        graph = build_networkx_graph(known_edges)
        assert graph.nodes["deploy"]["is_goal"] is True
        assert graph.nodes["commit"]["is_goal"] is False

    def test_edges_point_from_node_to_what_it_notifies(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        _, known_edges = _walk_frames(env, result.path)
        graph = build_networkx_graph(known_edges)
        assert graph.has_edge("commit", "lint")
        assert graph.has_edge("commit", "unit-tests")
        assert graph.has_edge("merge-gate", "deploy")

    def test_never_senses_a_node_outside_known_edges(self):
        # The bug this replaces: build_networkx_graph() used to take `env`
        # and sense every node in env.nodes, regardless of what was
        # actually discovered. It's now pure - no env, no sensing.
        graph = build_networkx_graph({"a": ("b",), "b": ()})
        assert set(graph.nodes()) == {"a", "b"}

    def test_a_notified_but_never_sensed_target_still_gets_a_node(self):
        # A target named in some sensed node's notifies but never itself
        # a known_edges key (never itself sensed) - possible whenever a
        # walk doesn't fully explore the topology - still needs to exist
        # as a node a frame can reference, just with a placeholder is_goal.
        graph = build_networkx_graph({"commit": ("lint", "unit-tests")})
        assert "unit-tests" in graph.nodes()
        assert graph.nodes["unit-tests"]["is_goal"] is False


class TestWalkFrames:
    def test_one_frame_per_path_position(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames, _ = _walk_frames(env, result.path)
        assert len(frames) == len(result.path)

    def test_first_frame_senses_the_start_node(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames, known_edges = _walk_frames(env, result.path)
        node_id, caption, known, visited, cleared = frames[0]
        assert node_id == "commit"
        assert caption == "sense_edges('commit') → ('lint', 'unit-tests')"
        assert known == {"commit", "lint", "unit-tests"}
        assert visited == {"commit"}
        assert cleared == {"commit"}
        assert known_edges["commit"] == ("lint", "unit-tests")

    def test_known_edges_records_each_node_at_most_once(self, gated_env):
        # merge-gate is visited twice (sensed, then cleared on the
        # resumed visit) - known_edges must still hold exactly one entry
        # for it, the one real sense, not a second one on the revisit.
        result = DiscoveryAgent(gated_env, start_id="commit").walk()
        _, known_edges = _walk_frames(gated_env, result.path)
        assert known_edges["merge-gate"] == ("deploy",)
        assert len(known_edges) == 6  # every node in the topology, once each


class TestNodeDisplayState:
    def test_unvisited_is_known(self):
        assert (
            _node_display_state("x", visited=set(), cleared=set(), is_goal=False)
            == "known"
        )

    def test_visited_but_not_cleared_is_blocked(self):
        assert (
            _node_display_state("x", visited={"x"}, cleared=set(), is_goal=False)
            == "blocked"
        )

    def test_visited_and_cleared_is_cleared(self):
        assert (
            _node_display_state("x", visited={"x"}, cleared={"x"}, is_goal=False)
            == "cleared"
        )

    def test_visited_and_cleared_and_goal_is_goal(self):
        assert (
            _node_display_state("x", visited={"x"}, cleared={"x"}, is_goal=True)
            == "goal"
        )


class TestWalkFramesWithAndJoins:
    def test_merge_gate_is_blocked_on_first_sense(self, gated_env):
        result = DiscoveryAgent(gated_env, start_id="commit").walk()
        assert result.path[2] == "merge-gate"
        frames, _ = _walk_frames(gated_env, result.path)
        node_id, caption, _, visited, cleared = frames[2]
        assert node_id == "merge-gate"
        assert "merge-gate" in visited
        assert "merge-gate" not in cleared
        assert caption == (
            "sense_edges('merge-gate') → ('deploy',), "
            "requires ('lint', 'integration-tests')"
        )

    def test_merge_gate_clears_on_the_resumed_visit(self, gated_env):
        result = DiscoveryAgent(gated_env, start_id="commit").walk()
        merge_gate_indices = [
            i for i, n in enumerate(result.path) if n == "merge-gate"
        ]
        assert len(merge_gate_indices) >= 2
        first, resumed = merge_gate_indices[0], merge_gate_indices[1]

        frames, _ = _walk_frames(gated_env, result.path)
        assert "merge-gate" not in frames[first][4]
        assert "merge-gate" not in frames[resumed - 1][4]
        assert "merge-gate" in frames[resumed][4]
        assert frames[resumed][1] == "'merge-gate' requires satisfied - cleared"
