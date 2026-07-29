from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.guard_first import GuardFirstExecutor


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


class TestGuardFirstFreeCheck:
    def test_already_satisfied_node_is_satisfied_without_any_attempt(self):
        nodes = {
            "a": make_node("a", invariant_pass_probability=1.0, pass_probability=0.0)
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"a"}
        assert result.free_checks == {"a"}
        assert result.trace == []  # never paid for a repair attempt

    def test_never_already_satisfied_falls_through_to_normal_repair(self):
        # invariant_pass_probability=0.0 (the default) must behave exactly
        # like TopologicalExecutor - the whole point of defaulting to 0.0.
        nodes = {"a": make_node("a", pass_probability=1.0)}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"a"}
        assert result.free_checks == set()
        assert len(result.trace) == 1

    def test_linear_chain_free_check_does_not_block_downstream_readiness(self):
        nodes = {
            "repair": make_node(
                "repair", invariant_pass_probability=1.0, pass_probability=0.0
            ),
            "verify": make_node("verify", requires=("repair",), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"repair", "verify"}
        assert result.free_checks == {"repair"}
        # only "verify" ever paid for a repair attempt
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert attempted_ids == {"verify"}

    def test_broken_node_cannot_be_satisfied_via_free_check(self):
        nodes = {"bridge": make_node("bridge", invariant_pass_probability=1.0, rmax=1)}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        env.break_task("bridge")

        result = GuardFirstExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"bridge"}
        assert result.free_checks == set()


class TestGuardFirstMatchesTopologicalBaseline:
    def test_downstream_of_a_fatal_node_is_unreachable_not_fatal(self):
        nodes = {
            "a": make_node("a", pass_probability=0.0, rmax=1),
            "b": make_node("b", requires=("a",), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = GuardFirstExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"a"}
        assert result.unreachable == {"b"}

    def test_multiple_independent_ready_nodes_attempted_in_sorted_order(self):
        nodes = {
            "b": make_node("b", pass_probability=1.0),
            "a": make_node("a", pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = GuardFirstExecutor(env).run()

        attempted_order = [node_id for node_id, _ in result.trace]
        assert attempted_order == ["a", "b"]
