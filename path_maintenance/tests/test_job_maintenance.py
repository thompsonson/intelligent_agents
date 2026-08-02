import pytest

from path_maintenance.agents.job_maintenance import PathMaintenanceAgent
from path_maintenance.core.domain import JobNode, JobState
from path_maintenance.core.environment import JobGraphEnvironment

ORDER = ["pre-commit", "lint", "unit-tests", "merge", "deploy"]


def make_nodes():
    return {
        "pre-commit": JobNode(id="pre-commit"),
        "lint": JobNode(id="lint", requires=("pre-commit",), ticks_to_resolve=2),
        "unit-tests": JobNode(id="unit-tests", requires=("pre-commit",)),
        "merge": JobNode(id="merge", requires=("lint", "unit-tests")),
        "deploy": JobNode(
            id="deploy",
            requires=("merge",),
            ticks_to_resolve=1,
            resolves_to=JobState.FAILED,
        ),
    }


@pytest.fixture
def env():
    return JobGraphEnvironment(make_nodes())


class TestPathMaintenanceAgentWalk:
    def test_matches_scenario_md_totals(self, env):
        result = PathMaintenanceAgent(env, ORDER).walk()

        assert result.repairs_performed == ["deploy"]
        assert result.senses_performed == {
            "lint": 3,
            "unit-tests": 1,
            "merge": 1,
            "deploy": 2,
        }
        assert result.success is True
        assert result.path == ORDER

    def test_failed_node_ends_up_succeeded_after_repair(self, env):
        PathMaintenanceAgent(env, ORDER).walk()
        assert env.get_job_state("deploy") == JobState.SUCCEEDED

    def test_zero_tick_nodes_never_observed_pending_or_in_progress(self, env):
        observed = []
        original = env.get_job_state

        def spy(node_id):
            state = original(node_id)
            observed.append((node_id, state))
            return state

        env.get_job_state = spy
        PathMaintenanceAgent(env, ORDER).walk()

        unit_tests_states = [state for node, state in observed if node == "unit-tests"]
        assert unit_tests_states == [JobState.SUCCEEDED]

    def test_does_not_sense_the_first_node(self, env):
        sensed = []
        original = env.get_job_state

        def spy(node_id):
            sensed.append(node_id)
            return original(node_id)

        env.get_job_state = spy
        PathMaintenanceAgent(env, ORDER).walk()
        assert "pre-commit" not in sensed

    def test_never_senses_nodes_off_the_order(self, env):
        sensed = []
        original = env.get_job_state

        def spy(node_id):
            sensed.append(node_id)
            return original(node_id)

        env.get_job_state = spy
        PathMaintenanceAgent(env, ORDER).walk()
        assert all(node_id in ORDER for node_id in sensed)

    def test_all_zero_tick_succeeded_graph_needs_no_repairs(self):
        nodes = {
            "a": JobNode(id="a"),
            "b": JobNode(id="b", requires=("a",)),
        }
        env = JobGraphEnvironment(nodes)
        result = PathMaintenanceAgent(env, ["a", "b"]).walk()
        assert result.repairs_performed == []
        assert result.senses_performed == {"b": 1}
