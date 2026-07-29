from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.lrta_star import LRTAStarLearner
from task_graph_solver.scenarios.repair_packages_lite import build_repair_packages_lite
from task_graph_solver.visualization.learning_curve import plot_h_convergence


class TestPlotHConvergence:
    def test_produces_a_file_from_real_learner_history(self, tmp_path):
        def factory(trial_index: int) -> TaskGraphEnvironment:
            nodes = build_repair_packages_lite(
                repair_pass_probability=0.4, verify_pass_probability=0.9
            )
            return TaskGraphEnvironment(nodes, TaskGraphConfig(seed=trial_index))

        learner = LRTAStarLearner(factory)
        history = []
        for _ in range(15):
            learner.run_trial()
            history.append(learner.h_table["repair"])

        out = tmp_path / "convergence.png"
        plot_h_convergence(history, node_id="repair", save_path=str(out))

        assert out.exists()
        assert out.stat().st_size > 0
