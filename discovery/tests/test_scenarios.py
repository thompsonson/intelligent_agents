from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import build_pipeline_fanout_lite


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
