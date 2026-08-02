import pytest

from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
)
from discovery.visualization.discovery_view import (
    _node_display_state,
    _walk_frames,
    build_networkx_graph,
)


@pytest.fixture
def env():
    return DiscoveryEnvironment(build_pipeline_fanout_lite())


@pytest.fixture
def gated_env():
    return DiscoveryEnvironment(build_pipeline_fanout_lite_gated())


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

    def test_only_contains_known_edges_nodes(self):
        # The bug this replaces: build_networkx_graph() used to take `env`
        # and read every node's true notifies directly - including nodes
        # the walk never discovered, bypassing sense_edges() entirely.
        # It's now pure - no env, no bypassing the sensing contract.
        graph = build_networkx_graph({"a": ("b",), "b": ()})
        assert set(graph.nodes()) == {"a", "b"}

    def test_a_notified_but_never_sensed_target_still_gets_a_node(self):
        # experiment 1's exact case: unit-tests is named in commit's
        # notifies but the walk never itself senses it (goal reached down
        # the other branch first) - it's still a real node a frame can
        # reference, just with no real is_goal answer yet.
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
        assert cleared == {"commit"}  # requires=() clears instantly
        assert known_edges["commit"] == ("lint", "unit-tests")

    def test_revisiting_a_node_backtracks_without_resensing(self, env):
        # merge-gate is reached twice (path index 2 and 4); the second
        # arrival is a backtrack, not a fresh sense - see
        # backtracking-exploration/algorithm_fit.md's worked example.
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.path[2] == "merge-gate"
        assert result.path[4] == "merge-gate"

        frames, _ = _walk_frames(env, result.path)
        assert frames[2][1] == "sense_edges('merge-gate') → ('deploy',)"
        assert frames[4][1] == "backtrack to 'merge-gate'"

    def test_known_set_only_grows(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames, _ = _walk_frames(env, result.path)
        known_sizes = [len(known) for _, _, known, _, _ in frames]
        assert known_sizes == sorted(known_sizes)
        assert known_sizes[-1] == 6  # every node eventually known

    def test_final_frame_has_every_node_visited(self, env):
        result = DiscoveryAgent(env, start_id="commit").walk()
        frames, known_edges = _walk_frames(env, result.path)
        _, _, _, visited, cleared = frames[-1]
        assert visited == set(build_pipeline_fanout_lite().keys())
        assert cleared == visited  # requires=() everywhere in this scenario
        assert set(known_edges.keys()) == set(build_pipeline_fanout_lite().keys())


class TestNodeDisplayState:
    def test_unvisited_is_known(self):
        assert _node_display_state("x", visited=set(), cleared=set(), is_goal=False) == "known"

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
        # First sense (blocked) and the resumed, now-clearable revisit -
        # see documentation/discovery/and-joins/algorithm_fit.md's
        # phase 1 / phase 2 trace.
        merge_gate_indices = [
            i for i, n in enumerate(result.path) if n == "merge-gate"
        ]
        assert len(merge_gate_indices) >= 2
        first, resumed = merge_gate_indices[0], merge_gate_indices[1]

        frames, _ = _walk_frames(gated_env, result.path)
        assert "merge-gate" not in frames[first][4]  # still blocked
        assert "merge-gate" not in frames[resumed - 1][4]
        assert "merge-gate" in frames[resumed][4]  # now cleared
        assert frames[resumed][1] == "'merge-gate' requires satisfied - cleared"

    def test_blocked_node_never_appears_cleared_before_its_requires_do(
        self, gated_env
    ):
        result = DiscoveryAgent(gated_env, start_id="commit").walk()
        frames, _ = _walk_frames(gated_env, result.path)
        for _, _, _, _, cleared in frames:
            if "merge-gate" in cleared:
                assert "lint" in cleared
                assert "integration-tests" in cleared
