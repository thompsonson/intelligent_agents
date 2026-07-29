from real_task_graph_solver.atomicguard_backed.core.environment import (
    AtomicGuardCheckEnvironment,
)
from real_task_graph_solver.atomicguard_backed.scenarios.build_check_repair import (
    BROKEN_STATES,
    FIXTURES_DIR,
    build_build_check_repair,
)
from task_graph_solver.algorithms.guard_first import GuardFirstExecutor


def make_env(tmp_path):
    workdir = tmp_path / "workdir"
    nodes, goal = build_build_check_repair(workdir)
    return AtomicGuardCheckEnvironment(
        nodes,
        fixtures_dir=FIXTURES_DIR,
        workdir=workdir,
        goal=goal,
        broken_states=BROKEN_STATES,
    )


class TestGuardFirstExecutorRealBuildCheckRepair:
    def test_clean_state_is_satisfied_by_a_free_check_no_repair_paid_for(
        self, tmp_path
    ):
        env = make_env(tmp_path)
        env.reset_to_state("clean")

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"build-check"}
        assert result.free_checks == {"build-check"}
        assert result.trace == []
        assert env.retries_spent("build-check") == 0

    def test_publish_broken_state_is_genuinely_repaired_not_just_declared_fixed(
        self, tmp_path
    ):
        env = make_env(tmp_path)
        env.reset_to_state("publish_broken")
        pyproject_toml = env._workdir / "pyproject.toml"
        assert 'version = "0.1.0"' not in pyproject_toml.read_text()

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"build-check"}
        assert result.fatal == set()
        assert result.free_checks == set()
        assert env.retries_spent("build-check") == 1
        # the repair genuinely mutated the real file - not a declared pass
        assert 'version = "0.1.0"' in pyproject_toml.read_text()
        # and the build genuinely produced real artifacts
        dist_files = list((env._workdir / "dist").iterdir())
        assert any(f.name.endswith(".whl") for f in dist_files)
        assert any(f.name.endswith(".tar.gz") for f in dist_files)

    def test_break_task_then_fix_task_round_trip_via_real_repair(self, tmp_path):
        env = make_env(tmp_path)
        env.reset_to_state("clean")
        assert env.check_invariant("build-check") is True

        env.break_task("build-check")  # -> reset_to_state("publish_broken")
        assert env.check_invariant("build-check") is False

        result = GuardFirstExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"build-check"}
