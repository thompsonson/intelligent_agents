from real_discovery.atomicguard_backed.core.environment import (
    StatefulDiscoveryEnvironment,
)
from real_discovery.atomicguard_backed.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
)


class TestPipelineFanoutLite:
    def test_six_nodes(self):
        nodes = build_pipeline_fanout_lite()
        assert set(nodes.keys()) == {
            "commit",
            "lint",
            "unit-tests",
            "integration-tests",
            "merge-gate",
            "deploy",
        }

    def test_no_requires_in_the_ungated_variant(self):
        nodes = build_pipeline_fanout_lite()
        assert all(node.requires == () for node in nodes.values())

    def test_topology_matches_discovery_pipeline_fanout_lite(self):
        env = StatefulDiscoveryEnvironment(build_pipeline_fanout_lite())
        assert env.sense_edges("commit") == ("lint", "unit-tests")
        assert env.sense_edges("lint") == ("merge-gate",)
        assert env.sense_edges("unit-tests") == ("integration-tests", "merge-gate")
        assert env.sense_edges("integration-tests") == ("merge-gate",)
        assert env.sense_edges("merge-gate") == ("deploy",)
        assert env.sense_edges("deploy") == ()

    def test_gated_variant_adds_merge_gate_requires(self):
        nodes = build_pipeline_fanout_lite_gated()
        assert nodes["merge-gate"].requires == ("lint", "integration-tests")
        env = StatefulDiscoveryEnvironment(nodes)
        assert env.sense_requires("merge-gate") == ("lint", "integration-tests")
        assert env.sense_requires("lint") == ()
