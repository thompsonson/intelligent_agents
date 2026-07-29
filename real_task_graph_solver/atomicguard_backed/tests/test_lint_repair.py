from real_task_graph_solver.atomicguard_backed.core.environment import (
    AtomicGuardCheckEnvironment,
)
from real_task_graph_solver.atomicguard_backed.scenarios.lint_repair import (
    BROKEN_STATES,
    FIXTURES_DIR,
    build_lint_repair,
)
from task_graph_solver.algorithms.guard_first import GuardFirstExecutor


def make_env(tmp_path):
    workdir = tmp_path / "workdir"
    nodes, goal = build_lint_repair(workdir)
    return AtomicGuardCheckEnvironment(
        nodes,
        fixtures_dir=FIXTURES_DIR,
        workdir=workdir,
        goal=goal,
        broken_states=BROKEN_STATES,
    )


class TestGuardFirstExecutorRealRepair:
    def test_clean_state_is_satisfied_by_a_free_check_no_repair_paid_for(
        self, tmp_path
    ):
        env = make_env(tmp_path)
        env.reset_to_state("clean")

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"lint"}
        assert result.free_checks == {"lint"}
        assert result.trace == []
        assert env.retries_spent("lint") == 0

    def test_lint_broken_state_is_genuinely_repaired_not_just_declared_fixed(
        self, tmp_path
    ):
        env = make_env(tmp_path)
        env.reset_to_state("lint_broken")
        domain_py = env._workdir / "src" / "example_pkg" / "domain.py"
        assert "import os" in domain_py.read_text()

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"lint"}
        assert result.fatal == set()
        # the check failed first (no free win), then the real repair AP ran
        assert result.free_checks == set()
        assert env.retries_spent("lint") == 1
        # the repair genuinely mutated the real file - not a declared pass
        assert "import os" not in domain_py.read_text()

    def test_break_task_then_fix_task_round_trip_via_real_repair(self, tmp_path):
        env = make_env(tmp_path)
        env.reset_to_state("clean")
        assert env.check_invariant("lint") is True

        env.break_task("lint")  # -> reset_to_state("lint_broken")
        assert env.check_invariant("lint") is False

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"lint"}
