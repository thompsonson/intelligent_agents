import pytest

from path_maintenance.agents.job_maintenance import PathMaintenanceAgent
from path_maintenance.core.domain import JobNode, JobState
from path_maintenance.core.environment import JobGraphEnvironment
from path_maintenance.visualization.job_graph_view import record_walk

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


class TestRecordWalk:
    def test_event_count_matches_senses_plus_advances_plus_repairs(self, env):
        agent = PathMaintenanceAgent(env, ORDER)
        result, events = record_walk(env, agent)

        total_senses = sum(result.senses_performed.values())
        n_advances = sum(1 for e in events if e[0] == "advance")
        n_arrives = sum(1 for e in events if e[0] == "arrive")
        n_repairs = sum(1 for e in events if e[0] == "repair")

        assert n_arrives == total_senses
        assert n_repairs == len(result.repairs_performed)
        # one advance_jobs() call per wait-loop iteration: lint waits twice,
        # deploy waits once
        assert n_advances == 3

    def test_lint_shows_pending_then_in_progress_then_succeeded(self, env):
        agent = PathMaintenanceAgent(env, ORDER)
        _, events = record_walk(env, agent)

        lint_states = [
            event[2] for event in events if event[0] == "arrive" and event[1] == "lint"
        ]
        assert lint_states == [
            JobState.PENDING,
            JobState.IN_PROGRESS,
            JobState.SUCCEEDED,
        ]

    def test_deploy_shows_pending_then_failed_then_repaired(self, env):
        agent = PathMaintenanceAgent(env, ORDER)
        _, events = record_walk(env, agent)

        deploy_states = [
            state
            for event in events
            if event[0] == "arrive" and event[1] == "deploy"
            for state in [event[2]]
        ]
        assert deploy_states == [JobState.PENDING, JobState.FAILED]
        assert ("repair", "deploy") in events

    def test_events_restore_original_env_methods(self, env):
        original_get = env.get_job_state
        original_advance = env.advance_jobs
        original_repair = env.repair_node
        record_walk(env, PathMaintenanceAgent(env, ORDER))
        assert env.get_job_state == original_get
        assert env.advance_jobs == original_advance
        assert env.repair_node == original_repair
