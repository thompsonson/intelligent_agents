import pytest

from real_task_graph_solver.core.config import RealCheckConfig
from real_task_graph_solver.core.domain import RealCheckNode
from real_task_graph_solver.core.environment import RealCheckEnvironment
from task_graph_solver.core.domain import AttemptOutcome


def make_node(node_id, command=("true",), requires=()):
    return RealCheckNode(id=node_id, command=command, requires=requires)


def make_fixtures(tmp_path, states=("state-a", "state-b")):
    """A tiny, synthetic fixture set for environment-mechanics tests -
    real subprocess checks against real file content, but not the full
    example_pkg (that's reserved for the scenario-level integration tests,
    where mypy/ruff/pytest/build are actually meaningful)."""
    fixtures_dir = tmp_path / "fixtures"
    for i, state in enumerate(states):
        state_dir = fixtures_dir / state
        state_dir.mkdir(parents=True)
        (state_dir / "marker.txt").write_text(f"marker-{i}")
    return fixtures_dir


MARKER_CHECK = ("sh", "-c", "grep -qx marker-0 marker.txt")


class TestGraphValidation:
    def test_requires_referencing_unknown_node_is_rejected(self, tmp_path):
        nodes = {"a": make_node("a", requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            RealCheckEnvironment(
                nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
            )

    def test_cycle_is_rejected(self, tmp_path):
        nodes = {
            "a": make_node("a", requires=("b",)),
            "b": make_node("b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            RealCheckEnvironment(
                nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
            )

    def test_goal_must_reference_a_known_node(self, tmp_path):
        nodes = {"a": make_node("a")}
        with pytest.raises(ValueError, match="does-not-exist"):
            RealCheckEnvironment(
                nodes,
                RealCheckConfig(),
                fixtures_dir=make_fixtures(tmp_path),
                goal="does-not-exist",
            )

    def test_groups_is_always_empty(self, tmp_path):
        nodes = {"a": make_node("a")}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        assert env.groups == {}


class TestReadyNodesAndGoal:
    def test_and_gating_matches_task_graph_environment(self, tmp_path):
        nodes = {
            "a": make_node("a"),
            "b": make_node("b"),
            "join": make_node("join", requires=("a", "b")),
        }
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        assert env.ready_nodes(satisfied=set()) == ["a", "b"]
        assert "join" not in env.ready_nodes(satisfied={"a"})
        assert env.ready_nodes(satisfied={"a", "b"}) == ["join"]

    def test_is_goal_reached_with_explicit_goal(self, tmp_path):
        nodes = {"a": make_node("a"), "b": make_node("b")}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path), goal="a"
        )
        assert env.is_goal_reached(satisfied={"a"}) is True
        assert env.is_goal_reached(satisfied=set()) is False

    def test_is_goal_reached_falls_back_to_all_nodes_satisfied(self, tmp_path):
        nodes = {"a": make_node("a"), "b": make_node("b")}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        assert env.is_goal_reached(satisfied={"a"}) is False
        assert env.is_goal_reached(satisfied={"a", "b"}) is True


class TestResetToState:
    def test_unknown_state_is_rejected(self, tmp_path):
        nodes = {"a": make_node("a")}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        with pytest.raises(ValueError, match="no-such-state"):
            env.reset_to_state("no-such-state")

    def test_attempt_before_any_reset_raises_clearly(self, tmp_path):
        nodes = {"a": make_node("a", command=MARKER_CHECK)}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        with pytest.raises(RuntimeError, match="reset_to_state"):
            env.attempt("a")

    def test_reset_actually_swaps_working_tree_content(self, tmp_path):
        nodes = {"a": make_node("a", command=MARKER_CHECK)}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )

        env.reset_to_state("state-a")
        assert env.attempt("a") == AttemptOutcome.PASS  # marker.txt says marker-0

        env.reset_to_state("state-b")
        assert env.attempt("a") == AttemptOutcome.FATAL  # marker.txt now says marker-1


class TestAttemptAndCheckInvariant:
    def test_attempt_pass_and_fatal_from_real_exit_codes(self, tmp_path):
        nodes = {
            "always-pass": make_node("always-pass", command=("true",)),
            "always-fail": make_node("always-fail", command=("false",)),
        }
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")

        assert env.attempt("always-pass") == AttemptOutcome.PASS
        assert env.attempt("always-fail") == AttemptOutcome.FATAL

    def test_attempt_never_returns_retry(self, tmp_path):
        nodes = {"a": make_node("a", command=("false",))}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")
        for _ in range(5):
            assert env.attempt("a") in (AttemptOutcome.PASS, AttemptOutcome.FATAL)

    def test_attempt_increments_retries_spent_check_invariant_does_not(self, tmp_path):
        nodes = {"a": make_node("a", command=("true",))}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")

        assert env.retries_spent("a") == 0
        env.check_invariant("a")
        assert env.retries_spent("a") == 0  # free - no paid attempt recorded

        env.attempt("a")
        assert env.retries_spent("a") == 1
        env.attempt("a")
        assert env.retries_spent("a") == 2

    def test_check_invariant_reflects_the_same_real_command(self, tmp_path):
        nodes = {"a": make_node("a", command=MARKER_CHECK)}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")
        assert env.check_invariant("a") is True

        env.reset_to_state("state-b")
        assert env.check_invariant("a") is False

    def test_time_spent_records_a_real_duration(self, tmp_path):
        nodes = {"a": make_node("a", command=("true",))}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")

        assert env.time_spent("a") == 0.0  # never run yet
        env.attempt("a")
        assert env.time_spent("a") >= 0.0


class TestBreakFix:
    def test_break_task_resets_to_the_mapped_broken_state(self, tmp_path):
        nodes = {"a": make_node("a", command=MARKER_CHECK)}
        env = RealCheckEnvironment(
            nodes,
            RealCheckConfig(),
            fixtures_dir=make_fixtures(tmp_path),
            broken_states={"a": "state-b"},
        )
        env.reset_to_state("state-a")
        assert env.attempt("a") == AttemptOutcome.PASS

        env.break_task("a")
        assert env.attempt("a") == AttemptOutcome.FATAL

    def test_fix_task_resets_to_clean(self, tmp_path):
        fixtures_dir = make_fixtures(tmp_path, states=("clean", "state-b"))
        nodes = {"a": make_node("a", command=MARKER_CHECK)}
        env = RealCheckEnvironment(
            nodes,
            RealCheckConfig(),
            fixtures_dir=fixtures_dir,
            broken_states={"a": "state-b"},
        )
        env.reset_to_state("clean")
        env.break_task("a")
        assert env.attempt("a") == AttemptOutcome.FATAL

        env.fix_task("a")
        assert env.attempt("a") == AttemptOutcome.PASS

    def test_break_task_on_a_node_without_a_broken_state_is_rejected(self, tmp_path):
        nodes = {"a": make_node("a")}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")
        with pytest.raises(ValueError, match="a"):
            env.break_task("a")


class TestDrainChangedTasks:
    def test_reset_to_state_marks_every_node_changed(self, tmp_path):
        nodes = {"a": make_node("a"), "b": make_node("b")}
        env = RealCheckEnvironment(
            nodes, RealCheckConfig(), fixtures_dir=make_fixtures(tmp_path)
        )
        env.reset_to_state("state-a")
        assert env.drain_changed_tasks() == ["a", "b"]
        assert env.drain_changed_tasks() == []  # drained, nothing new

    def test_break_and_fix_task_also_mark_changed(self, tmp_path):
        nodes = {"a": make_node("a", command=MARKER_CHECK)}
        env = RealCheckEnvironment(
            nodes,
            RealCheckConfig(),
            fixtures_dir=make_fixtures(tmp_path),
            broken_states={"a": "state-b"},
        )
        env.reset_to_state("state-a")
        env.drain_changed_tasks()

        env.break_task("a")
        assert env.drain_changed_tasks() == ["a"]
