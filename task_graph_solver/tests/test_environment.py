import pytest

from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import AttemptOutcome, TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment


def make_node(node_id, requires=(), pass_probability=1.0, rmax=3, r_patience=None,
              kind="sensing", retry_flavor="sensing"):
    return TaskNode(
        id=node_id,
        kind=kind,
        retry_flavor=retry_flavor,
        pass_probability=pass_probability,
        rmax=rmax,
        r_patience=r_patience,
        requires=requires,
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
