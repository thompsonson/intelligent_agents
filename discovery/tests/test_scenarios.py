from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
    build_pipeline_fanout_lite_with_orphan_requirement,
)


class TestPipelineFanoutLite:
    def test_exactly_one_node_has_no_notifies(self):
        nodes = build_pipeline_fanout_lite()
        terminals = [n.id for n in nodes.values() if not n.notifies]
        assert terminals == ["deploy"]

    def test_matches_backtracking_algorithm_fit_md_worked_example(self):
        # See documentation/discovery/backtracking-exploration/
        # algorithm_fit.md's 17-row trace table.
        env = DiscoveryEnvironment(build_pipeline_fanout_lite())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert set(result.path) == set(build_pipeline_fanout_lite().keys())
        assert result.nodes_sensed == 6
        assert result.goal_reached is True
        assert result.total_cost == 10
        assert result.blocked_nodes == []

    def test_every_branch_reconverges_regardless_of_first_choice(self):
        # Simulates the "always highest-id" alternative policy discussed
        # in algorithm_fit.md, by walking commit's other branch by hand -
        # proving reconvergence, not just asserting it in prose.
        env = DiscoveryEnvironment(build_pipeline_fanout_lite())
        assert env.sense_edges("commit") == ("lint", "unit-tests")
        assert env.sense_edges("unit-tests") == ("integration-tests", "merge-gate")
        assert env.sense_edges("integration-tests") == ("merge-gate",)
        assert env.sense_edges("merge-gate") == ("deploy",)
        assert env.sense_edges("deploy") == ()


class TestPipelineFanoutLiteGated:
    def test_only_merge_gate_has_requires(self):
        nodes = build_pipeline_fanout_lite_gated()
        gated = [n.id for n in nodes.values() if n.requires]
        assert gated == ["merge-gate"]

    def test_requires_names_lint_and_integration_tests(self):
        nodes = build_pipeline_fanout_lite_gated()
        assert nodes["merge-gate"].requires == ("lint", "integration-tests")

    def test_notifies_unchanged_from_ungated_version(self):
        gated = build_pipeline_fanout_lite_gated()
        ungated = build_pipeline_fanout_lite()
        assert {n: node.notifies for n, node in gated.items()} == {
            n: node.notifies for n, node in ungated.items()
        }

    def test_requires_targets_reachable_via_notifies_from_commit(self):
        # environment_design.md's reachability constraint, checked
        # directly rather than only asserted in scenario.md's prose.
        env = DiscoveryEnvironment(build_pipeline_fanout_lite_gated())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.blocked_nodes == []
        assert result.goal_reached is True

    def test_deploy_sensed_last(self):
        env = DiscoveryEnvironment(build_pipeline_fanout_lite_gated())
        result = DiscoveryAgent(env, start_id="commit").walk()
        sensed_order = list(dict.fromkeys(result.path))
        assert sensed_order[-1] == "deploy"


class TestPipelineFanoutLiteWithOrphanRequirement:
    def test_release_notes_is_a_real_but_unreachable_node(self):
        nodes = build_pipeline_fanout_lite_with_orphan_requirement()
        assert "release-notes" in nodes
        notifies_release_notes = [
            n.id for n in nodes.values() if "release-notes" in n.notifies
        ]
        assert notifies_release_notes == []

    def test_merge_gate_requires_release_notes_too(self):
        nodes = build_pipeline_fanout_lite_with_orphan_requirement()
        assert nodes["merge-gate"].requires == (
            "lint",
            "integration-tests",
            "release-notes",
        )

    def test_walk_reports_merge_gate_permanently_blocked(self):
        env = DiscoveryEnvironment(build_pipeline_fanout_lite_with_orphan_requirement())
        result = DiscoveryAgent(env, start_id="commit").walk()
        assert result.blocked_nodes == ["merge-gate"]
        assert result.goal_reached is False
        assert "deploy" not in result.path
        assert "release-notes" not in result.path
