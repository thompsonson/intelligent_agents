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
LYING_REPAIR = ("true",)  # exits 0 but never touches marker.txt


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


class TestDualStateAgentIntegration:
    """New behaviour this environment gained by wrapping every real call in
    a DualStateAgent instead of calling ActionPair.execute() bare - see
    environment_design.md's "Revision" section."""

    def test_a_repair_whose_own_guard_lies_is_still_correctly_fatal(self, tmp_path):
        """The correction made while implementing the revision: a repair
        generator's own exit code isn't always a trustworthy proxy for
        "the real problem is fixed" (only verified true for ruff --fix,
        never assumed for e.g. a plain sed edit). attempt() must always
        re-verify via check_action_pair, not trust repair_action_pair's
        own DualStateAgent-reported success."""
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK, repair=LYING_REPAIR)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )

        env.reset_to_state("state-b")
        # the repair's own DualStateAgent call reports success (`true`
        # always exits 0) - but marker.txt was never touched, so the real
        # check still fails, and attempt() must reflect that, not the
        # repair's own lying exit code.
        assert env.attempt("a") == AttemptOutcome.FATAL
        assert env.check_invariant("a") is False

    def test_dag_survives_reset_to_state(self, tmp_path):
        """reset_to_state() wipes workdir on every call - the DAG's
        base_dir must not live under it, or the audit trail it exists to
        keep would be destroyed by the very state swaps it's meant to
        record."""
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )

        env.reset_to_state("state-a")
        env.check_invariant("a")
        before = env._dag.get_all_for_action_pair(
            action_pair_id="a", workflow_id=env._workflow_id
        )
        assert len(before) == 1

        env.reset_to_state("state-b")  # wipes workdir, not the DAG
        after = env._dag.get_all_for_action_pair(
            action_pair_id="a", workflow_id=env._workflow_id
        )
        assert len(after) == 1
        assert after[0].artifact_id == before[0].artifact_id

    def test_repair_inherits_the_checks_real_failure_feedback(self, tmp_path):
        """check_action_pair and repair_action_pair share one
        action_pair_id (the node's own id) specifically so a repair's
        DualStateAgent call automatically sees the check's real rejection
        via the shared DAG - no extra plumbing. Proven here against a
        real command whose failure feedback is genuinely informative."""
        workdir = tmp_path / "workdir"
        nodes = {"a": make_node("a", workdir, check=MARKER_CHECK, repair=MARKER_REPAIR)}
        env = AtomicGuardCheckEnvironment(
            nodes, fixtures_dir=make_fixtures(tmp_path), workdir=workdir
        )

        env.reset_to_state("state-b")
        assert env.check_invariant("a") is False
        env.attempt("a")

        artifacts = env._dag.get_all_for_action_pair(
            action_pair_id="a", workflow_id=env._workflow_id
        )
        rejected = [a for a in artifacts if a.status.value == "rejected"]
        assert len(rejected) >= 1
        assert rejected[0].guard_result.feedback != ""
