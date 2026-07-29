import pytest

from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import AttemptOutcome, GroupNode, TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment


def make_node(
    node_id,
    requires=(),
    pass_probability=1.0,
    rmax=3,
    r_patience=None,
    kind="sensing",
    retry_flavor="sensing",
    invariant_pass_probability=0.0,
):
    return TaskNode(
        id=node_id,
        kind=kind,
        retry_flavor=retry_flavor,
        pass_probability=pass_probability,
        rmax=rmax,
        r_patience=r_patience,
        requires=requires,
        invariant_pass_probability=invariant_pass_probability,
    )


class TestTaskNodeValidation:
    def test_r_patience_must_be_less_than_rmax(self):
        with pytest.raises(ValueError):
            make_node("a", rmax=3, r_patience=3)

    def test_r_patience_equal_to_rmax_rejected(self):
        with pytest.raises(ValueError):
            make_node("a", rmax=2, r_patience=2)

    def test_r_patience_less_than_rmax_accepted(self):
        node = make_node("a", rmax=3, r_patience=1)
        assert node.r_patience == 1

    def test_pass_probability_out_of_bounds_rejected(self):
        with pytest.raises(ValueError):
            make_node("a", pass_probability=1.5)
        with pytest.raises(ValueError):
            make_node("a", pass_probability=-0.1)

    def test_kind_and_retry_flavor_are_independent(self):
        # Guards against silently re-coupling these two fields - a pure local
        # generation step (acting=false in the real system's sense, but not a
        # read of external state either) needs kind and retry_flavor to vary
        # independently. See documentation/task-graph/environment_design.md.
        node = make_node("generate", kind="acting", retry_flavor="generation")
        assert node.kind == "acting"
        assert node.retry_flavor == "generation"

    def test_rmax_must_be_at_least_one(self):
        with pytest.raises(ValueError):
            make_node("a", rmax=0)

    def test_r_patience_must_be_at_least_one(self):
        with pytest.raises(ValueError):
            make_node("a", rmax=3, r_patience=0)


class TestGraphValidation:
    def test_requires_referencing_unknown_node_is_rejected(self):
        nodes = {"a": make_node("a", requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            TaskGraphEnvironment(nodes, TaskGraphConfig())

    def test_direct_cycle_is_rejected(self):
        nodes = {
            "a": make_node("a", requires=("b",)),
            "b": make_node("b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            TaskGraphEnvironment(nodes, TaskGraphConfig())

    def test_self_reference_is_rejected(self):
        nodes = {"a": make_node("a", requires=("a",))}
        with pytest.raises(ValueError, match="cycle"):
            TaskGraphEnvironment(nodes, TaskGraphConfig())

    def test_longer_cycle_is_rejected(self):
        nodes = {
            "a": make_node("a", requires=("c",)),
            "b": make_node("b", requires=("a",)),
            "c": make_node("c", requires=("b",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            TaskGraphEnvironment(nodes, TaskGraphConfig())

    def test_valid_dag_with_shared_dependency_is_accepted(self):
        # A diamond (join requires both a and b, both require base) is a
        # valid DAG, not a cycle - must not be rejected by cycle detection.
        nodes = {
            "base": make_node("base"),
            "a": make_node("a", requires=("base",)),
            "b": make_node("b", requires=("base",)),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig())
        assert env.ready_nodes(satisfied=set()) == ["base"]


class TestReadyNodes:
    def test_node_with_no_requires_is_ready_immediately(self):
        env = TaskGraphEnvironment({"a": make_node("a")}, TaskGraphConfig())
        assert env.ready_nodes(satisfied=set()) == ["a"]

    def test_node_not_ready_until_all_requires_satisfied(self):
        nodes = {
            "a": make_node("a"),
            "b": make_node("b"),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig())

        assert "join" not in env.ready_nodes(satisfied=set())
        assert "join" not in env.ready_nodes(satisfied={"a"})
        assert "join" not in env.ready_nodes(satisfied={"b"})
        assert "join" in env.ready_nodes(satisfied={"a", "b"})

    def test_already_satisfied_node_is_not_ready(self):
        env = TaskGraphEnvironment({"a": make_node("a")}, TaskGraphConfig())
        assert env.ready_nodes(satisfied={"a"}) == []

    def test_linear_chain_gates_one_at_a_time(self):
        nodes = {
            "repair": make_node("repair"),
            "verify": make_node("verify", requires=("repair",)),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig())

        assert env.ready_nodes(satisfied=set()) == ["repair"]
        assert env.ready_nodes(satisfied={"repair"}) == ["verify"]


class TestAttempt:
    def test_always_pass_returns_pass(self):
        env = TaskGraphEnvironment(
            {"a": make_node("a", pass_probability=1.0)}, TaskGraphConfig(seed=1)
        )
        assert env.attempt("a") == AttemptOutcome.PASS

    def test_deterministic_with_fixed_seed(self):
        nodes = {"a": make_node("a", pass_probability=0.5, rmax=20)}

        outcomes_1 = []
        env_1 = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=42))
        for _ in range(10):
            outcome = env_1.attempt("a")
            outcomes_1.append(outcome)
            if outcome != AttemptOutcome.RETRY:
                break

        outcomes_2 = []
        env_2 = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=42))
        for _ in range(10):
            outcome = env_2.attempt("a")
            outcomes_2.append(outcome)
            if outcome != AttemptOutcome.RETRY:
                break

        assert outcomes_1 == outcomes_2

    def test_rmax_exhaustion_without_r_patience_is_fatal(self):
        node = make_node("a", pass_probability=0.0, rmax=2, r_patience=None)
        env = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=1))

        assert env.attempt("a") == AttemptOutcome.RETRY
        assert env.attempt("a") == AttemptOutcome.FATAL

    def test_r_patience_escalates_before_rmax_exhausted(self):
        # rmax=5 would allow 5 attempts, but r_patience=1 means escalate
        # after just 1 consecutive failure - mirrors atomicguard's
        # Extension 09 invariant (application/workflow.py), found while
        # reading the real system, not invented for this design.
        node = make_node("apply", pass_probability=0.0, rmax=5, r_patience=1)
        env = TaskGraphEnvironment({"apply": node}, TaskGraphConfig(seed=1))

        assert env.attempt("apply") == AttemptOutcome.FATAL
        assert env.retries_spent("apply") == 1

    def test_retries_spent_tracks_attempt_count(self):
        node = make_node("a", pass_probability=0.0, rmax=3, r_patience=None)
        env = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=1))

        env.attempt("a")
        env.attempt("a")
        assert env.retries_spent("a") == 2


class TestGroupNodeValidation:
    def test_group_must_have_at_least_one_member(self):
        with pytest.raises(ValueError):
            GroupNode(id="g", members=())

    def test_group_id_colliding_with_a_node_id_is_rejected(self):
        nodes = {"a": make_node("a"), "b": make_node("b")}
        group = GroupNode(id="a", members=("b",))
        with pytest.raises(ValueError, match="collides"):
            TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))

    def test_group_referencing_unknown_member_is_rejected(self):
        nodes = {"a": make_node("a")}
        group = GroupNode(id="g", members=("does-not-exist",))
        with pytest.raises(ValueError, match="does-not-exist"):
            TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))

    def test_requires_referencing_unknown_group_is_rejected(self):
        nodes = {"a": make_node("a", requires=("no-such-group",))}
        with pytest.raises(ValueError, match="no-such-group"):
            TaskGraphEnvironment(nodes, TaskGraphConfig())


class TestGroupNodeGating:
    def _diamond_with_group(self):
        nodes = {
            "variant-a": make_node("variant-a"),
            "variant-b": make_node("variant-b"),
            "downstream": make_node("downstream", requires=("slot",)),
        }
        group = GroupNode(id="slot", members=("variant-a", "variant-b"))
        return nodes, group

    def test_downstream_not_ready_until_any_member_satisfied(self):
        nodes, group = self._diamond_with_group()
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))

        assert "downstream" not in env.ready_nodes(satisfied=set())
        assert "downstream" in env.ready_nodes(satisfied={"variant-a"})

    def test_either_member_alone_satisfies_the_group(self):
        nodes, group = self._diamond_with_group()
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))

        assert "downstream" in env.ready_nodes(satisfied={"variant-b"})

    def test_both_members_satisfied_still_only_needs_one(self):
        nodes, group = self._diamond_with_group()
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))

        assert "downstream" in env.ready_nodes(satisfied={"variant-a", "variant-b"})

    def test_group_ids_never_appear_in_ready_nodes(self):
        # A GroupNode is never attempted directly - it has no Guard.
        nodes, group = self._diamond_with_group()
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))

        assert "slot" not in env.ready_nodes(satisfied=set())
        assert "slot" not in env.ready_nodes(satisfied={"variant-a", "variant-b"})

    def test_group_referenced_by_a_cycle_through_a_member_is_rejected(self):
        # variant-a (a group member) requires "downstream", and "downstream"
        # requires the group - a cycle through the member, not the group id
        # itself, still needs to be caught.
        nodes = {
            "variant-a": make_node("variant-a", requires=("downstream",)),
            "downstream": make_node("downstream", requires=("slot",)),
        }
        group = GroupNode(id="slot", members=("variant-a",))
        with pytest.raises(ValueError, match="cycle"):
            TaskGraphEnvironment(nodes, TaskGraphConfig(), groups=(group,))


class TestExplicitGoal:
    def test_goal_must_reference_a_known_node(self):
        nodes = {"a": make_node("a")}
        with pytest.raises(ValueError, match="does-not-exist"):
            TaskGraphEnvironment(nodes, TaskGraphConfig(), goal="does-not-exist")

    def test_goal_reached_once_goal_node_is_satisfied_even_with_others_pending(self):
        nodes = {
            "goal-node": make_node("goal-node"),
            "unrelated": make_node("unrelated"),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(), goal="goal-node")

        assert env.is_goal_reached(satisfied={"goal-node"}) is True
        assert env.is_goal_reached(satisfied=set()) is False

    def test_no_goal_configured_falls_back_to_all_nodes_satisfied(self):
        # Backward compatibility: every scenario built before this existed
        # (disk_check_lite, repair_packages_lite, pr_merge_lite) doesn't
        # pass a goal, and must keep meaning "everything satisfied".
        nodes = {"a": make_node("a"), "b": make_node("b")}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig())

        assert env.is_goal_reached(satisfied={"a"}) is False
        assert env.is_goal_reached(satisfied={"a", "b"}) is True


class TestGuardFirstInvariantCheck:
    def test_default_invariant_pass_probability_is_zero(self):
        node = make_node("a")
        assert node.invariant_pass_probability == 0.0

    def test_invariant_pass_probability_out_of_bounds_rejected(self):
        with pytest.raises(ValueError):
            make_node("a", invariant_pass_probability=1.5)
        with pytest.raises(ValueError):
            make_node("a", invariant_pass_probability=-0.1)

    def test_check_invariant_always_false_when_probability_is_zero(self):
        node = make_node("a", invariant_pass_probability=0.0)
        env = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=1))

        for _ in range(20):
            assert env.check_invariant("a") is False

    def test_check_invariant_always_true_when_probability_is_one(self):
        node = make_node("a", invariant_pass_probability=1.0)
        env = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=1))

        assert env.check_invariant("a") is True

    def test_check_invariant_does_not_consume_retry_budget(self):
        node = make_node("a", invariant_pass_probability=1.0, rmax=3)
        env = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=1))

        env.check_invariant("a")
        env.check_invariant("a")
        env.check_invariant("a")

        assert env.retries_spent("a") == 0

    def test_check_invariant_deterministic_with_fixed_seed(self):
        node = make_node("a", invariant_pass_probability=0.5)

        env_1 = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=7))
        results_1 = [env_1.check_invariant("a") for _ in range(10)]

        env_2 = TaskGraphEnvironment({"a": node}, TaskGraphConfig(seed=7))
        results_2 = [env_2.check_invariant("a") for _ in range(10)]

        assert results_1 == results_2

    def test_broken_node_never_reports_already_satisfied(self):
        node = make_node("bridge", invariant_pass_probability=1.0)
        env = TaskGraphEnvironment({"bridge": node}, TaskGraphConfig(seed=1))

        env.break_task("bridge")

        assert env.check_invariant("bridge") is False


class TestDriverBreakFix:
    def test_break_task_forces_fatal(self):
        node = make_node("bridge", pass_probability=1.0, rmax=3)
        env = TaskGraphEnvironment({"bridge": node}, TaskGraphConfig(seed=1))

        env.break_task("bridge")
        assert env.attempt("bridge") == AttemptOutcome.FATAL

    def test_break_task_does_not_consume_retry_budget(self):
        # A Driver-forced break is an exogenous world change, not a
        # repair-attempt retry - it shouldn't pollute the retry-cost
        # signal an LRTA*-style learner would read from retries_spent().
        node = make_node("bridge", pass_probability=1.0, rmax=3)
        env = TaskGraphEnvironment({"bridge": node}, TaskGraphConfig(seed=1))

        env.break_task("bridge")
        env.attempt("bridge")
        env.attempt("bridge")
        assert env.retries_spent("bridge") == 0

    def test_fix_task_restores_normal_behavior(self):
        node = make_node("bridge", pass_probability=1.0, rmax=3)
        env = TaskGraphEnvironment({"bridge": node}, TaskGraphConfig(seed=1))

        env.break_task("bridge")
        assert env.attempt("bridge") == AttemptOutcome.FATAL

        env.fix_task("bridge")
        assert env.attempt("bridge") == AttemptOutcome.PASS
