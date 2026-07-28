from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.lrta_star import LRTAStarLearner


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


def linear_chain_factory(repair_pass_probability, verify_pass_probability=1.0):
    def factory(trial_index: int) -> TaskGraphEnvironment:
        nodes = {
            "repair": make_node(
                "repair",
                pass_probability=repair_pass_probability,
                rmax=5,
                kind="acting",
                retry_flavor="repair",
            ),
            "verify": make_node(
                "verify",
                requires=("repair",),
                pass_probability=verify_pass_probability,
                rmax=5,
                kind="sensing",
                retry_flavor="sensing",
            ),
        }
        return TaskGraphEnvironment(nodes, TaskGraphConfig(seed=trial_index))

    return factory


class TestLRTAStarBasics:
    def test_h_table_starts_empty(self):
        learner = LRTAStarLearner(linear_chain_factory(repair_pass_probability=1.0))
        assert learner.h_table == {}

    def test_h_updated_for_repair_node_after_a_trial(self):
        learner = LRTAStarLearner(linear_chain_factory(repair_pass_probability=1.0))
        learner.run_trial()
        assert "repair" in learner.h_table

    def test_sensing_flavor_node_never_enters_h_table(self):
        # verify has real retries too (pass_probability < 1) but retry_flavor
        # "sensing" - it must never be treated as learnable repair cost.
        learner = LRTAStarLearner(
            linear_chain_factory(
                repair_pass_probability=1.0, verify_pass_probability=0.3
            )
        )
        for _ in range(10):
            learner.run_trial()
        assert "verify" not in learner.h_table


class TestLRTAStarConvergence:
    def test_h_is_monotonically_non_decreasing_across_trials(self):
        learner = LRTAStarLearner(linear_chain_factory(repair_pass_probability=0.4))
        observed = []
        for _ in range(30):
            learner.run_trial()
            observed.append(learner.h_table["repair"])

        assert observed == sorted(observed)

    def test_h_converges_to_max_observed_retries(self):
        factory = linear_chain_factory(repair_pass_probability=0.4)
        learner = LRTAStarLearner(factory)

        max_retries_seen = 0
        for trial_index in range(30):
            env = factory(trial_index)
            # Drain the same environment the learner will independently build
            # (same seed => same rng sequence) to know the ground truth.
            from task_graph_solver.algorithms.topological import TopologicalExecutor

            TopologicalExecutor(env).run()
            max_retries_seen = max(max_retries_seen, env.retries_spent("repair"))

        for _ in range(30):
            learner.run_trial()

        assert learner.h_table["repair"] == max_retries_seen

    def test_deterministic_across_repeated_runs_with_same_seed_strategy(self):
        learner_1 = LRTAStarLearner(linear_chain_factory(repair_pass_probability=0.4))
        learner_2 = LRTAStarLearner(linear_chain_factory(repair_pass_probability=0.4))

        for _ in range(15):
            learner_1.run_trial()
            learner_2.run_trial()

        assert learner_1.h_table == learner_2.h_table
