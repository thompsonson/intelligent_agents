import pytest

from path_maintenance.core.domain import JobNode, JobState
from path_maintenance.core.environment import JobGraphEnvironment


def make_nodes():
    # Same deploy_chain_lite topology, richer nodes - see
    # documentation/path-maintenance/job-lifecycle/scenario.md
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


class TestJobNodeValidation:
    def test_resolves_to_must_be_succeeded_or_failed(self):
        with pytest.raises(ValueError):
            JobNode(id="a", resolves_to=JobState.PENDING)
        with pytest.raises(ValueError):
            JobNode(id="a", resolves_to=JobState.IN_PROGRESS)

    def test_ticks_to_resolve_must_not_be_negative(self):
        with pytest.raises(ValueError):
            JobNode(id="a", ticks_to_resolve=-1)


class TestGraphValidation:
    def test_requires_referencing_unknown_node_is_rejected(self):
        nodes = {"a": JobNode(id="a", requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            JobGraphEnvironment(nodes)

    def test_cycle_is_rejected(self):
        nodes = {
            "a": JobNode(id="a", requires=("b",)),
            "b": JobNode(id="b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            JobGraphEnvironment(nodes)


class TestReadyNodes:
    def test_and_join_not_ready_until_both_parents_satisfied(self, env):
        assert "merge" not in env.ready_nodes({"pre-commit", "lint"})

    def test_and_join_ready_once_both_parents_satisfied(self, env):
        assert env.ready_nodes({"pre-commit", "lint", "unit-tests"}) == ["merge"]


class TestGetJobState:
    def test_zero_tick_node_resolves_immediately(self, env):
        assert env.get_job_state("unit-tests") == JobState.SUCCEEDED

    def test_unresolved_node_starts_pending(self, env):
        assert env.get_job_state("lint") == JobState.PENDING

    def test_unknown_node_raises(self, env):
        with pytest.raises(ValueError):
            env.get_job_state("does-not-exist")

    def test_never_mutates(self, env):
        # Repeated sensing without advance_jobs() must not change anything -
        # get_job_state() is a pure sense. See environment_design.md's
        # "Resolved: who calls advance_jobs()".
        first = env.get_job_state("lint")
        second = env.get_job_state("lint")
        third = env.get_job_state("lint")
        assert first == second == third == JobState.PENDING


class TestAdvanceJobs:
    def test_pending_becomes_in_progress_then_resolves(self, env):
        assert env.get_job_state("lint") == JobState.PENDING
        env.advance_jobs({"pre-commit"})
        assert env.get_job_state("lint") == JobState.IN_PROGRESS
        env.advance_jobs({"pre-commit"})
        assert env.get_job_state("lint") == JobState.SUCCEEDED

    def test_one_tick_node_resolves_to_failed(self, env):
        assert env.get_job_state("deploy") == JobState.PENDING
        env.advance_jobs({"merge"})
        assert env.get_job_state("deploy") == JobState.FAILED

    def test_already_resolved_node_unaffected_by_further_advances(self, env):
        env.advance_jobs({"pre-commit"})
        env.advance_jobs({"pre-commit"})
        assert env.get_job_state("lint") == JobState.SUCCEEDED
        env.advance_jobs({"pre-commit"})
        assert env.get_job_state("lint") == JobState.SUCCEEDED

    def test_only_ready_nodes_advance(self, env):
        # deploy requires merge, which isn't in `satisfied` - deploy must
        # not tick just because lint (an unrelated ready node) is
        # advancing. Regression test for a real bug: advance_jobs() used
        # to tick every unresolved node in the whole graph regardless of
        # readiness, so a downstream node could silently resolve during an
        # upstream node's wait loop - see environment_design.md's
        # "Resolved: who calls advance_jobs()".
        env.advance_jobs({"pre-commit"})
        assert env.get_job_state("lint") == JobState.IN_PROGRESS
        assert env.get_job_state("deploy") == JobState.PENDING

    def test_node_not_in_ready_nodes_is_ignored_even_if_satisfied_lists_it(self, env):
        # Passing a node's own id in `satisfied` doesn't make it tick -
        # ready_nodes() excludes nodes already in `satisfied`.
        env.advance_jobs({"pre-commit", "lint"})
        assert env.get_job_state("lint") == JobState.PENDING


class TestRepairNode:
    def test_repairs_a_failed_node_to_succeeded(self, env):
        env.advance_jobs({"merge"})
        assert env.get_job_state("deploy") == JobState.FAILED
        env.repair_node("deploy")
        assert env.get_job_state("deploy") == JobState.SUCCEEDED

    def test_rejects_repairing_a_non_failed_node(self, env):
        with pytest.raises(ValueError):
            env.repair_node("unit-tests")  # SUCCEEDED, not FAILED

    def test_rejects_repairing_a_still_pending_node(self, env):
        with pytest.raises(ValueError):
            env.repair_node("lint")  # PENDING, not FAILED

    def test_unknown_node_rejected(self, env):
        with pytest.raises(ValueError):
            env.repair_node("does-not-exist")
