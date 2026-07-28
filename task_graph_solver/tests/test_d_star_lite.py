from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import AttemptOutcome, TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.d_star_lite import DStarLiteExecutor


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


def repair_then_verify(pass_probability=1.0):
    return {
        "repair": make_node("repair", pass_probability=pass_probability,
                             kind="acting", retry_flavor="repair"),
        "verify": make_node("verify", requires=("repair",),
                             pass_probability=pass_probability),
    }


class TestDStarLiteNoChanges:
    def test_behaves_like_plain_execution_when_nothing_breaks(self):
        env = TaskGraphEnvironment(repair_then_verify(pass_probability=1.0), TaskGraphConfig(seed=1))
        executor = DStarLiteExecutor(env)

        result = executor.run()

        assert result.success is True
        assert result.satisfied == {"repair", "verify"}
        assert executor.repairs == []


class TestDStarLiteBreakBeforeAttempt:
    def test_break_with_no_alternate_path_leaves_goal_unreachable(self):
        # A strict AND-chain has no alternate route the way a maze does -
        # breaking any single node makes everything downstream unreachable.
        # This is the scope boundary noted in algorithm_fit.md: D* Lite's
        # "find another way" only matters when another way exists.
        env = TaskGraphEnvironment(repair_then_verify(pass_probability=1.0), TaskGraphConfig(seed=1))
        env.break_task("repair")

        result = DStarLiteExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"repair"}
        assert result.unreachable == {"verify"}


class TestDStarLiteRepairLocality:
    def test_fixing_a_broken_downstream_node_does_not_redo_upstream_work(self):
        env = TaskGraphEnvironment(repair_then_verify(pass_probability=1.0), TaskGraphConfig(seed=1))
        executor = DStarLiteExecutor(env)

        # Move 1: repair is the only ready node - attempt and satisfy it.
        executor.step()
        assert executor.satisfied == {"repair"}

        # Driver event: verify breaks before it's ever been attempted.
        env.break_task("verify")

        # Move 2: verify becomes ready (repair is satisfied) but the guard
        # is broken - attempt returns FATAL.
        executor.step()
        assert executor.fatal == {"verify"}
        assert "repair" in executor.satisfied  # untouched by the break

        # Driver event: verify is fixed.
        env.fix_task("verify")

        # Move 3: D* Lite senses the fix via drain_changed_tasks() and
        # retries verify - it does NOT re-attempt "repair".
        executor.step()

        result = executor.run()  # drains to completion
        assert result.success is True
        assert result.satisfied == {"repair", "verify"}

        repair_attempts = [o for n, o in result.trace if n == "repair"]
        assert len(repair_attempts) == 1
        assert repair_attempts[0] == AttemptOutcome.PASS

        assert executor.repairs == ["verify"]

    def test_repair_count_reflects_number_of_sensed_fixes(self):
        env = TaskGraphEnvironment(repair_then_verify(pass_probability=1.0), TaskGraphConfig(seed=1))
        executor = DStarLiteExecutor(env)

        executor.step()  # satisfy repair
        env.break_task("verify")
        executor.step()  # verify goes fatal
        env.fix_task("verify")
        executor.step()  # sensed, repaired, verify attempted and passes

        assert executor.repairs == ["verify"]
        assert executor.satisfied == {"repair", "verify"}
