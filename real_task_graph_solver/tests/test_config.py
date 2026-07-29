from real_task_graph_solver.core.config import RealCheckConfig


class TestRealCheckConfig:
    def test_default_timeout(self):
        config = RealCheckConfig()
        assert config.timeout == 30.0

    def test_timeout_can_be_set(self):
        config = RealCheckConfig(timeout=5.0)
        assert config.timeout == 5.0
