from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.topological import TopologicalExecutor
from task_graph_solver.scenarios.disk_check_lite import build_disk_check_lite


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
