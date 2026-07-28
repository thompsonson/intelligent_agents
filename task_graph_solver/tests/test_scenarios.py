from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.topological import TopologicalExecutor
from task_graph_solver.algorithms.lrta_star import LRTAStarLearner
from task_graph_solver.scenarios.disk_check_lite import build_disk_check_lite
from task_graph_solver.scenarios.repair_packages_lite import build_repair_packages_lite


class TestDiskCheckLiteScenario:
    def test_builds_single_sensing_node(self):
        nodes = build_disk_check_lite()

        assert set(nodes.keys()) == {"check-disk"}
        node = nodes["check-disk"]
        assert node.kind == "sensing"
        assert node.retry_flavor == "sensing"
        assert node.requires == ()
        assert node.rmax == 1  # matches atomicguard's disk_check.dspddl :rmax 1

    def test_executor_succeeds_when_check_always_passes(self):
        nodes = build_disk_check_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"check-disk"}

    def test_executor_fails_when_check_always_fails(self):
        nodes = build_disk_check_lite(pass_probability=0.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"check-disk"}


class TestRepairPackagesLiteScenario:
    def test_builds_repair_then_verify_chain(self):
        nodes = build_repair_packages_lite()

        assert set(nodes.keys()) == {"repair", "verify"}
        repair, verify = nodes["repair"], nodes["verify"]

        assert repair.kind == "acting"
        assert repair.retry_flavor == "repair"
        assert repair.rmax == 3
        assert repair.r_patience == 2  # matches repair_packages.dspddl's repair-g

        assert verify.kind == "sensing"
        assert verify.retry_flavor == "sensing"
        assert verify.requires == ("repair",)
        assert verify.r_patience is None  # no override in the real verify-g

    def test_executor_succeeds_when_both_steps_always_pass(self):
        nodes = build_repair_packages_lite(
            repair_pass_probability=1.0, verify_pass_probability=1.0
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert result.satisfied == {"repair", "verify"}

    def test_lrta_star_learns_repair_cost_but_not_verify(self):
        # The scenario algorithm_fit.md calls the cleanest LRTA* demo: run it
        # for real, not just on ad hoc nodes, and confirm the flavor
        # isolation holds on the actual ground-truth-matched scenario.
        def factory(trial_index: int) -> TaskGraphEnvironment:
            nodes = build_repair_packages_lite(
                repair_pass_probability=0.4, verify_pass_probability=0.7
            )
            return TaskGraphEnvironment(nodes, TaskGraphConfig(seed=trial_index))

        learner = LRTAStarLearner(factory)
        for _ in range(20):
            learner.run_trial()

        assert "repair" in learner.h_table
        assert "verify" not in learner.h_table
