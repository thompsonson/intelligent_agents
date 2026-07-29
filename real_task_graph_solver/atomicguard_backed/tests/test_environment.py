import pytest
from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from real_task_graph_solver.atomicguard_backed.core.domain import AtomicGuardCheckNode
from real_task_graph_solver.atomicguard_backed.core.environment import (
    AtomicGuardCheckEnvironment,
)
from task_graph_solver.core.domain import AttemptOutcome


def make_action_pair(command, workdir):
    return ActionPair(
        generator=SubprocessGenerator(command=list(command), cwd=str(workdir)),
        guard=ExitCodeGuard(),
        prompt_template=PromptTemplate(role="", constraints="", task=""),
    )


def make_node(node_id, workdir, requires=(), check=("true",), repair=None):
    return AtomicGuardCheckNode(
        id=node_id,
        check_action_pair=make_action_pair(check, workdir),
        repair_action_pair=make_action_pair(repair, workdir) if repair else None,
        requires=requires,
    )


def make_fixtures(tmp_path, states=("state-a", "state-b")):
    fixtures_dir = tmp_path / "fixtures"
    for i, state in enumerate(states):
        state_dir = fixtures_dir / state
        state_dir.mkdir(parents=True)
        (state_dir / "marker.txt").write_text(f"marker-{i}")
    return fixtures_dir


MARKER_CHECK = ("sh", "-c", "grep -qx marker-0 marker.txt")
MARKER_REPAIR = ("sh", "-c", "echo marker-0 > marker.txt")


class TestGraphValidation:
    def test_requires_referencing_unknown_node_is_rejected(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            AtomicGuardCheckEnvironment(
                nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
            )

    def test_cycle_is_rejected(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {
            "a": make_node("a", workdir, requires=("b",)),
            "b": make_node("b", workdir, requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            AtomicGuardCheckEnvironment(
                nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
            )

    def test_goal_must_reference_a_known_node(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir)}
        with pytest.raises(ValueError, match="does-not-exist"):
            AtomicGuardCheckEnvironment(
                nodes,
                fixtures_dir=make_fixtures(tmp_path),
                workdir=workdir,
                goal="does-not-exist",
            )

    def test_groups_is_always_empty(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        assert env.groups == {}


class TestReadyNodesAndGoal:
    def test_and_gating_matches_task_graph_environment(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {
            "a": make_node("a", workdir),
            "b": make_node("b", workdir),
            "join": make_node("join", workdir, requires=("a", "b")),
        }
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        assert env.ready_nodes(satisfied=set()) == ["a", "b"]
        assert "join" not in env.ready_nodes(satisfied={"a"})
        assert env.ready_nodes(satisfied={"a", "b"}) == ["join"]

    def test_is_goal_reached_with_explicit_goal(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir), "b": make_node("b", workdir)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir, goal="b"
        )
        assert not env.is_goal_reached({"a"})
        assert env.is_goal_reached({"b"})

    def test_is_goal_reached_without_goal_requires_all_nodes(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir), "b": make_node("b", workdir)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        assert not env.is_goal_reached({"a"})
        assert env.is_goal_reached({"a", "b"})


class TestResetAndReadiness:
    def test_reset_to_unknown_state_raises(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        with pytest.raises(ValueError, match="unknown fixture state"):
            env.reset_to_state("does-not-exist")

    def test_check_invariant_before_reset_raises(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        with pytest.raises(RuntimeError, match="reset_to_state"):
            env.check_invariant("a")

    def test_reset_to_state_marks_all_nodes_changed(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir), "b": make_node("b", workdir)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        env.reset_to_state("state-a")
        assert env.drain_changed_tasks() == ["a", "b"]
        assert env.drain_changed_tasks() == []


class TestRealChecksAndRepair:
    def test_check_invariant_reflects_real_file_content(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )

        env.reset_to_state("state-a")
        assert env.check_invariant("a") is True

        env.reset_to_state("state-b")
        assert env.check_invariant("a") is False

    def test_attempt_without_repair_action_pair_reruns_check(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )

        env.reset_to_state("state-b")
        assert env.attempt("a") == AttemptOutcome.FATAL
        assert env.retries_spent("a") == 1

    def test_attempt_with_repair_action_pair_genuinely_fixes_and_passes(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK, repair=MARKER_REPAIR)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )

        env.reset_to_state("state-b")
        assert env.check_invariant("a") is False

        assert env.attempt("a") == AttemptOutcome.PASS
        assert (workdir / "marker.txt").read_text().strip() == "marker-0"
        assert env.check_invariant("a") is True

    def test_break_task_and_fix_task(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK)}
        env = AtomicGuardCheckEnvironment(
            nodes,
            fixtures_dir=make_fixtures(tmp_path, states=("clean", "broken-a")),
            workdir=workdir,
            broken_states={"a": "broken-a"},
        )

        env.reset_to_state("clean")
        env.break_task("a")
        assert env.check_invariant("a") is False

        env.fix_task("a")
        assert env.check_invariant("a") is True

    def test_break_task_unknown_node_raises(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )
        with pytest.raises(ValueError, match="no manufactured broken state"):
            env.break_task("a")
