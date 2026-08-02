"""The core claim this whole experiment exists to prove:
discovery.agents.discovery_agent.DiscoveryAgent - completely unmodified,
not a variant, not a subclass - runs against real, guard-checked,
ActionPair/DualStateAgent-backed nodes. Its only environment dependencies
are sense_edges()/sense_requires()/get_move_cost(); this environment
implements exactly that shape. See
documentation/discovery/atomicguard-bridge/environment_design.md."""

from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite as build_plain_ungated,
)
from discovery.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite_gated as build_plain_gated,
)
from real_discovery.atomicguard_backed.core.environment import (
    StatefulDiscoveryEnvironment,
)
from real_discovery.atomicguard_backed.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
)


class TestDiscoveryAgentRunsUnmodified:
    def test_ungated_walk_matches_the_plain_discovery_environment(self):
        plain_result = DiscoveryAgent(
            DiscoveryEnvironment(build_plain_ungated()), start_id="commit"
        ).walk()
        real_result = DiscoveryAgent(
            StatefulDiscoveryEnvironment(build_pipeline_fanout_lite()),
            start_id="commit",
        ).walk()

        assert real_result.path == plain_result.path
        assert real_result.nodes_sensed == plain_result.nodes_sensed
        assert real_result.total_cost == plain_result.total_cost
        assert real_result.blocked_nodes == plain_result.blocked_nodes
        assert real_result.goal_reached == plain_result.goal_reached
        assert real_result.goal_reached is True
        # matches experiment 2's documented numbers
        assert real_result.nodes_sensed == 6
        assert real_result.total_cost == 10

    def test_gated_walk_matches_the_plain_discovery_environment(self):
        plain_result = DiscoveryAgent(
            DiscoveryEnvironment(build_plain_gated()), start_id="commit"
        ).walk()
        real_result = DiscoveryAgent(
            StatefulDiscoveryEnvironment(build_pipeline_fanout_lite_gated()),
            start_id="commit",
        ).walk()

        assert real_result.path == plain_result.path
        assert real_result.nodes_sensed == plain_result.nodes_sensed
        assert real_result.total_cost == plain_result.total_cost
        assert real_result.blocked_nodes == plain_result.blocked_nodes
        assert real_result.goal_reached == plain_result.goal_reached
        # matches experiment 3's documented numbers: deploy reached last
        assert real_result.nodes_sensed == 6
        assert real_result.total_cost == 14
