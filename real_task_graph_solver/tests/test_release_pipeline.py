import pytest

from real_task_graph_solver.core.config import RealCheckConfig
from real_task_graph_solver.core.environment import RealCheckEnvironment
from real_task_graph_solver.scenarios.release_pipeline import (
    BROKEN_STATES,
    FIXTURES_DIR,
    build_release_pipeline,
)
from task_graph_solver.algorithms.ao_star import AOStarExecutor
from task_graph_solver.algorithms.d_star_lite import DStarLiteExecutor
from task_graph_solver.algorithms.planning import PlanningExecutor
from task_graph_solver.algorithms.topological import TopologicalExecutor

ALL_FIVE_CHECKS = {
    "type-check",
    "lint",
    "architecture-test",
    "unit-tests",
    "build-check",
}


def make_env():
    nodes, goal = build_release_pipeline()
    return RealCheckEnvironment(
        nodes,
        RealCheckConfig(),
        fixtures_dir=FIXTURES_DIR,
        goal=goal,
        broken_states=BROKEN_STATES,
    )


class TestTopologicalExecutorRealChecks:
    def test_clean_state_reaches_release_ready(self):
        env = make_env()
        env.reset_to_state("clean")

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert result.satisfied == ALL_FIVE_CHECKS | {"release-ready"}
        assert result.fatal == set()

    @pytest.mark.parametrize(
        "state,broken_node",
        [
            ("typing_broken", "type-check"),
            ("lint_broken", "lint"),
            ("architecture_broken", "architecture-test"),
            ("publish_broken", "build-check"),
        ],
    )
    def test_exactly_one_broken_state_fails_exactly_that_check(
        self, state, broken_node
    ):
        env = make_env()
        env.reset_to_state(state)

        result = TopologicalExecutor(env).run()

        assert result.success is False
        assert result.fatal == {broken_node}
        assert result.satisfied == ALL_FIVE_CHECKS - {broken_node}
        assert "release-ready" in result.unreachable


class TestAOStarExecutorRealCost:
    def test_h_composes_from_real_retries_spent_and_time_spent_is_populated(self):
        env = make_env()
        env.reset_to_state("clean")
        executor = AOStarExecutor(env)

        result = executor.run()

        assert result.success is True
        # every leaf check took exactly one real, paid attempt
        for node_id in ALL_FIVE_CHECKS:
            assert executor.h[node_id] == 1
        # release-ready composes as its own cost (1) plus the max of its
        # five children's costs (all 1, so max is 1) - same AND rule as
        # AOStarExecutor's simulated scenarios, now over real data.
        assert executor.h["release-ready"] == 1 + max(
            executor.h[n] for n in ALL_FIVE_CHECKS
        )
        # real, new instrumentation the simulated environment never had -
        # every attempted node actually took a measurable, non-negative
        # amount of wall-clock time.
        for node_id in ALL_FIVE_CHECKS | {"release-ready"}:
            assert env.time_spent(node_id) >= 0.0


class TestPlanningExecutorRealShortCircuit:
    def test_already_released_state_is_satisfied_in_one_free_check(self):
        # "released" is clean/ with .status/*.ok markers pre-populated -
        # the toy equivalent of "this pipeline already succeeded in a
        # previous run." PlanningExecutor checks release-ready FIRST and
        # finds it already true - none of the five real checks ever run.
        env = make_env()
        env.reset_to_state("released")

        result = PlanningExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"release-ready"}
        assert result.free_checks == {"release-ready"}
        assert result.trace == []
        for node_id in ALL_FIVE_CHECKS:
            assert node_id not in result.satisfied

    def test_topological_executor_walks_the_whole_chain_on_the_identical_state(self):
        # Direct contrast: TopologicalExecutor cannot discover release-ready
        # is already true without first walking every node between here
        # and there - it still pays for all five real checks.
        env = make_env()
        env.reset_to_state("released")

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert result.satisfied == ALL_FIVE_CHECKS | {"release-ready"}
        assert len(result.trace) == 6


class TestDStarLiteExecutorRealRecovery:
    def test_recovers_from_a_break_on_an_independent_real_check(self):
        # A smaller, two-node subgraph (no release-ready) deliberately -
        # see the note in environment_design.md's "Not decided": a Driver
        # reset_to_state swaps the *entire* working tree, which would wipe
        # every other node's .status/*.ok marker too, not just the node
        # being broken/fixed. Demonstrating recovery on release-ready's
        # marker-gated aggregation in the same run as a break/fix cycle
        # would be a false claim under this environment's current
        # reset semantics - so this test stays deliberately narrower than
        # task_graph_solver's equivalent D* Lite experiments, and proves
        # the real thing that IS true: break/fix sensing and repair
        # locality both work against real subprocess checks.
        nodes, _goal = build_release_pipeline()
        small_nodes = {
            "type-check": nodes["type-check"],
            "lint": nodes["lint"],
        }
        env = RealCheckEnvironment(
            small_nodes,
            RealCheckConfig(),
            fixtures_dir=FIXTURES_DIR,
            broken_states=BROKEN_STATES,
        )
        env.reset_to_state("clean")
        executor = DStarLiteExecutor(env)

        env.break_task("type-check")  # -> reset_to_state("typing_broken")

        for _ in range(5):
            if not executor.step():
                break

        assert "type-check" in executor.fatal
        assert "lint" in executor.satisfied  # independent sibling, unaffected

        env.fix_task("type-check")  # -> reset_to_state("clean")
        result = executor.run()

        assert result.success is True
        assert executor.satisfied == {"type-check", "lint"}
        # lint was already satisfied before the break/fix saga - it must
        # not be re-attempted once type-check is repaired.
        lint_attempts = [n for n, _ in result.trace if n == "lint"]
        assert len(lint_attempts) == 1
        assert executor.repairs == ["type-check"]
