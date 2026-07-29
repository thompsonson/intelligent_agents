from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import GroupNode, TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.planning import PlanningExecutor


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


class TestPlanningExecutorBasics:
    def test_single_always_passing_node_succeeds(self):
        nodes = {"a": make_node("a", pass_probability=1.0)}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="a")

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"a"}
        assert result.fatal == set()

    def test_single_always_failing_node_fails_cleanly(self):
        nodes = {"a": make_node("a", pass_probability=0.0, rmax=1)}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="a")

        result = PlanningExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"a"}
        assert len(result.trace) == 1  # rmax=1 - must not over-attempt

    def test_linear_chain_all_pass(self):
        nodes = {
            "repair": make_node("repair", pass_probability=1.0),
            "verify": make_node("verify", requires=("repair",), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="verify")

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"repair", "verify"}
        # repair must be attempted before verify, same ordering guarantee
        # TopologicalExecutor gives - the recursion enforces it structurally.
        attempted_order = [node_id for node_id, _ in result.trace]
        assert attempted_order.index("repair") < attempted_order.index("verify")

    def test_no_goal_configured_falls_back_to_ensuring_every_node(self):
        nodes = {"a": make_node("a", pass_probability=1.0), "b": make_node("b")}
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"a", "b"}


class TestPlanningExecutorSenseThenPlan:
    def test_goal_already_satisfied_skips_the_entire_dependency_chain(self):
        # The headline capability: PlanningExecutor checks the goal first.
        # If it's already true, nothing upstream is ever touched at all -
        # not checked, not attempted, not even visited.
        nodes = {
            "repair": make_node("repair", pass_probability=0.0, rmax=1),
            "verify": make_node(
                "verify", requires=("repair",), invariant_pass_probability=1.0
            ),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="verify")

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"verify"}
        assert result.free_checks == {"verify"}
        assert result.trace == []  # "repair" never even looked at
        assert "repair" not in result.satisfied
        assert "repair" not in result.fatal
        assert "repair" not in result.unreachable

    def test_intermediate_free_check_still_permits_downstream_evaluation(self):
        nodes = {
            "repair": make_node(
                "repair", invariant_pass_probability=1.0, pass_probability=0.0
            ),
            "verify": make_node("verify", requires=("repair",), pass_probability=1.0),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="verify")

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.free_checks == {"repair"}
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert attempted_ids == {"verify"}


class TestPlanningExecutorGoalDirectedScope:
    def test_true_orphan_is_never_visited_at_all(self):
        nodes = {
            "goal-node": make_node("goal-node", pass_probability=1.0),
            "orphan": make_node("orphan", pass_probability=0.0, rmax=1),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="goal-node")

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert "orphan" not in result.satisfied
        assert "orphan" not in result.fatal
        assert "orphan" not in result.unreachable
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert "orphan" not in attempted_ids


class TestPlanningExecutorGroupPruning:
    def test_first_satisfying_member_wins_others_become_not_needed(self):
        nodes = {
            "variant-a": make_node("variant-a", pass_probability=1.0),
            "variant-b": make_node("variant-b", pass_probability=1.0),
            "downstream": make_node("downstream", requires=("slot",)),
        }
        group = GroupNode(id="slot", members=("variant-a", "variant-b"))
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=(group,), goal="downstream"
        )

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert "variant-a" in result.satisfied
        assert result.not_needed == {"variant-b"}
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert "variant-b" not in attempted_ids

    def test_falls_back_to_next_member_if_the_first_fails(self):
        nodes = {
            "variant-a": make_node("variant-a", pass_probability=0.0, rmax=1),
            "variant-b": make_node("variant-b", pass_probability=1.0),
            "downstream": make_node("downstream", requires=("slot",)),
        }
        group = GroupNode(id="slot", members=("variant-a", "variant-b"))
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=(group,), goal="downstream"
        )

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.fatal == {"variant-a"}
        assert "variant-b" in result.satisfied
        assert result.not_needed == set()


class TestPlanningExecutorAndShortCircuit:
    def test_a_fatal_dependency_prevents_evaluating_its_sibling_at_all(self):
        # "join" requires both "a" and "b". Deps are evaluated in sorted
        # order - "a" is fatal, so "join" is unreachable regardless of what
        # "b" would have done. "b" is never worth checking: this is the
        # same goal-directed pruning that skips a true orphan, applied
        # recursively at an AND-join.
        nodes = {
            "a": make_node("a", pass_probability=0.0, rmax=1),
            "b": make_node("b", pass_probability=1.0),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1), goal="join")

        result = PlanningExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"a"}
        assert "join" in result.unreachable
        assert "b" not in result.satisfied
        assert "b" not in result.fatal
        assert "b" not in result.unreachable
        attempted_ids = {node_id for node_id, _ in result.trace}
        assert "b" not in attempted_ids
