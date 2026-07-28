from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.topological import TopologicalExecutor


def make_node(
    node_id,
    requires=(),
    pass_probability=1.0,
    rmax=3,
    r_patience=None,
    kind="sensing",
    retry_flavor="sensing",
):
    return TaskNode(
        id=node_id,
        kind=kind,
        retry_flavor=retry_flavor,
        pass_probability=pass_probability,
        rmax=rmax,
        r_patience=r_patience,
        requires=requires,
    )


class TestTopologicalExecutorBasics:
    def test_single_always_passing_node_succeeds(self):
        nodes = {"a": make_node("a", pass_probability=1.0)}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"a"}
        assert result.fatal == set()
        assert result.unreachable == set()

    def test_single_always_failing_node_fails_cleanly(self):
        nodes = {"a": make_node("a", pass_probability=0.0, rmax=1)}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is False
        assert result.satisfied == set()
        assert result.fatal == {"a"}
        assert len(result.trace) == 1  # rmax=1 - executor must not hang or over-attempt

    def test_linear_chain_all_pass(self):
        nodes = {
            "repair": make_node("repair", pass_probability=1.0),
            "verify": make_node("verify", requires=("repair",), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"repair", "verify"}
        # repair must be attempted (and satisfied) before verify becomes ready
        attempted_order = [node_id for node_id, _ in result.trace]
        assert attempted_order.index("repair") < attempted_order.index("verify")


class TestUnreachablePropagation:
    def test_downstream_of_a_fatal_node_is_unreachable_not_fatal(self):
        nodes = {
            "a": make_node("a", pass_probability=0.0, rmax=1),
            "b": make_node("b", requires=("a",), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"a"}
        assert result.unreachable == {"b"}
        assert result.satisfied == set()
        # "b" must never have been attempted at all
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert "b" not in attempted_ids

    def test_and_join_unreachable_if_either_predecessor_is_fatal(self):
        nodes = {
            "a": make_node("a", pass_probability=1.0),
            "b": make_node("b", pass_probability=0.0, rmax=1),
            "join": make_node("join", requires=("a", "b"), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is False
        assert result.satisfied == {"a"}
        assert result.fatal == {"b"}
        assert result.unreachable == {"join"}


class TestDeterministicOrdering:
    def test_multiple_independent_ready_nodes_attempted_in_sorted_order(self):
        nodes = {
            "b": make_node("b", pass_probability=1.0),
            "a": make_node("a", pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        attempted_order = [node_id for node_id, _ in result.trace]
        assert attempted_order == ["a", "b"]
