from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.ao_star import AOStarExecutor


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


class TestAOStarAndJoinGating:
    def test_join_solved_only_after_both_children_solved(self):
        nodes = {
            "a": make_node("a"),
            "b": make_node("b"),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.success is True
        attempted_order = [node_id for node_id, _ in result.trace]
        assert attempted_order.index("a") < attempted_order.index("join")
        assert attempted_order.index("b") < attempted_order.index("join")

    def test_join_unsolvable_if_either_child_is_unsolvable(self):
        nodes = {
            "a": make_node("a", pass_probability=1.0),
            "b": make_node("b", pass_probability=0.0, rmax=1),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.success is False
        assert result.satisfied == {"a"}
        assert result.fatal == {"b"}
        assert result.unreachable == {"join"}
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert "join" not in attempted_ids


class TestAOStarThreeWayJoin:
    def test_join_solved_only_after_all_three_children_solved(self):
        nodes = {
            "a": make_node("a"),
            "b": make_node("b"),
            "c": make_node("c"),
            "join": make_node("join", requires=("a", "b", "c")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.success is True
        attempted_order = [node_id for node_id, _ in result.trace]
        for child in ("a", "b", "c"):
            assert attempted_order.index(child) < attempted_order.index("join")

    def test_diagnosability_identifies_exactly_which_child_failed(self):
        # The property documentation/lrta/beyond_the_maze.md found missing
        # from the real system's single opaque three-way guard: which of
        # several independent required children actually failed.
        nodes = {
            "a": make_node("a", pass_probability=1.0),
            "b": make_node("b", pass_probability=0.0, rmax=1),
            "c": make_node("c", pass_probability=1.0),
            "join": make_node("join", requires=("a", "b", "c")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.fatal == {"b"}  # exactly the failing one, not a/c
        assert result.satisfied == {"a", "c"}
        assert result.unreachable == {"join"}

    def test_diagnosability_holds_regardless_of_which_child_fails(self):
        for failing_child in ("a", "b", "c"):
            nodes = {
                node_id: make_node(
                    node_id,
                    pass_probability=0.0 if node_id == failing_child else 1.0,
                    rmax=1 if node_id == failing_child else 3,
                )
                for node_id in ("a", "b", "c")
            }
            nodes["join"] = make_node("join", requires=("a", "b", "c"))
            env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

            result = AOStarExecutor(env).run()

            assert result.fatal == {failing_child}
            assert result.satisfied == {"a", "b", "c"} - {failing_child}

    def test_multiple_simultaneous_failures_are_each_identified(self):
        nodes = {
            "a": make_node("a", pass_probability=0.0, rmax=1),
            "b": make_node("b", pass_probability=1.0),
            "c": make_node("c", pass_probability=0.0, rmax=1),
            "join": make_node("join", requires=("a", "b", "c")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.fatal == {"a", "c"}
        assert result.satisfied == {"b"}
        assert result.unreachable == {"join"}


class TestAOStarCostComposition:
    def test_cost_is_own_attempts_plus_max_of_required_children(self):
        # Bypass the environment's shared RNG sequence to test the AND
        # cost-composition formula in isolation with asymmetric, known
        # child costs - see documentation for why this is done directly
        # rather than through randomized attempts.
        nodes = {
            "a": make_node("a"),
            "b": make_node("b"),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        executor.solved.update({"a", "b"})
        executor.h["a"] = 5.0
        executor.h["b"] = 2.0

        env.attempt("join")  # pass_probability=1.0 -> passes immediately, own cost 1

        assert executor._compose_cost("join") == 1 + max(5.0, 2.0)

    def test_full_run_composes_join_cost_from_real_attempts(self):
        nodes = {
            "a": make_node("a", pass_probability=1.0),
            "b": make_node("b", pass_probability=1.0),
            "join": make_node("join", requires=("a", "b"), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        result = executor.run()

        assert result.success is True
        # every node passes on its first attempt (pass_probability=1.0),
        # so each has retries_spent == 1
        assert executor.h["a"] == 1
        assert executor.h["b"] == 1
        assert executor.h["join"] == 1 + max(1, 1)

    def test_only_solved_nodes_get_an_h_entry(self):
        nodes = {
            "a": make_node("a", pass_probability=1.0),
            "b": make_node("b", pass_probability=0.0, rmax=1),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        executor.run()

        assert "a" in executor.h
        assert "b" not in executor.h  # unsolvable, never gets a cost entry
        assert "join" not in executor.h  # never attempted (unreachable)
