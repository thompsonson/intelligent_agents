from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.topological import TopologicalExecutor
from task_graph_solver.algorithms.lrta_star import LRTAStarLearner
from task_graph_solver.algorithms.ao_star import AOStarExecutor
from task_graph_solver.algorithms.d_star_lite import DStarLiteExecutor
from task_graph_solver.scenarios.disk_check_lite import build_disk_check_lite
from task_graph_solver.scenarios.repair_packages_lite import build_repair_packages_lite
from task_graph_solver.scenarios.pr_merge_lite import build_pr_merge_lite


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


class TestPrMergeLiteScenario:
    def test_builds_eight_node_graph_with_two_and_joins(self):
        nodes = build_pr_merge_lite()

        assert set(nodes.keys()) == {
            "ci-check",
            "generate-actions",
            "apply-actions",
            "merged",
            "deploy-staging",
            "deploy-publish",
            "deploy-promote",
            "released",
        }
        assert nodes["merged"].requires == ("ci-check", "apply-actions")
        assert nodes["released"].requires == (
            "deploy-staging",
            "deploy-publish",
            "deploy-promote",
        )
        assert nodes["apply-actions"].r_patience == 1  # matches fix_pr.dspddl

    def test_full_run_succeeds_when_everything_passes(self):
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.success is True
        assert result.satisfied == set(nodes.keys())

    def test_merged_is_solved_only_after_both_ci_check_and_apply_actions(self):
        # Phase 5's target: the smallest real AND-join, hand-verifiable.
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        executor.run()

        attempted_order = [node_id for node_id, _ in executor.trace]
        assert attempted_order.index("ci-check") < attempted_order.index("merged")
        assert attempted_order.index("apply-actions") < attempted_order.index("merged")

    def test_merged_cost_composes_from_its_two_required_children(self):
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        executor.run()

        # Every node passes on its first attempt with pass_probability=1.0,
        # so ci-check costs 1, and apply-actions costs 1 + h(generate-actions)
        # = 1 + 1 = 2. merged's own cost is 1, composed with the max of its
        # two required children: 1 + max(h[ci-check], h[apply-actions]).
        assert executor.h["ci-check"] == 1
        assert executor.h["generate-actions"] == 1
        assert executor.h["apply-actions"] == 1 + 1
        assert executor.h["merged"] == 1 + max(
            executor.h["ci-check"], executor.h["apply-actions"]
        )

    def test_merged_unreachable_if_apply_actions_never_resolves(self):
        nodes = build_pr_merge_lite(
            pass_probability=1.0, overrides={"apply-actions": 0.0}
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.success is False
        assert "apply-actions" in result.fatal
        assert "merged" in result.unreachable
        assert "released" in result.unreachable

    def test_released_requires_all_three_deploy_branches(self):
        # Phase 6's target: the actual motivating case from
        # documentation/lrta/beyond_the_maze.md's stress test.
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        result = executor.run()

        assert result.success is True
        attempted_order = [node_id for node_id, _ in executor.trace]
        for branch in ("deploy-staging", "deploy-publish", "deploy-promote"):
            assert attempted_order.index(branch) < attempted_order.index("released")

    def test_released_cost_composes_max_of_three_deploy_branches(self):
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        executor.run()

        assert executor.h["released"] == 1 + max(
            executor.h["deploy-staging"],
            executor.h["deploy-publish"],
            executor.h["deploy-promote"],
        )

    def test_diagnosability_identifies_which_deploy_branch_actually_failed(self):
        # The real system's downstream-ci-passed collapses three commit-status
        # polls into one exit code - no way to tell which context failed from
        # the guard-graph's own state. This is the corrected version:
        # result.fatal names the exact failing branch.
        nodes = build_pr_merge_lite(
            pass_probability=1.0, overrides={"deploy-staging": 0.0}
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"deploy-staging"}
        assert "deploy-publish" in result.satisfied
        assert "deploy-promote" in result.satisfied
        assert result.unreachable == {"released"}

    def test_diagnosability_when_a_different_branch_fails(self):
        nodes = build_pr_merge_lite(
            pass_probability=1.0, overrides={"deploy-publish": 0.0}
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        result = AOStarExecutor(env).run()

        assert result.fatal == {"deploy-publish"}
        assert "deploy-staging" in result.satisfied
        assert "deploy-promote" in result.satisfied
        assert result.unreachable == {"released"}

    def test_two_deploy_branches_failing_are_both_individually_identified(self):
        nodes = build_pr_merge_lite(
            pass_probability=1.0,
            overrides={"deploy-staging": 0.0, "deploy-promote": 0.0},
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)

        result = executor.run()

        assert result.fatal == {"deploy-staging", "deploy-promote"}
        assert result.satisfied.issuperset({"deploy-publish"})
        assert result.unreachable == {"released"}
        assert "released" not in executor.h  # never attempted, per Phase 5's invariant

    def test_topological_executor_cannot_recover_from_a_fix_after_the_fact(self):
        # Establishes the baseline D* Lite improves on: a plain executor has
        # no sensing loop, so a fix that arrives after the run has already
        # finished is invisible to it - not a bug, just what "no repair
        # mechanism" means in practice.
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        env.break_task("apply-actions")

        result = TopologicalExecutor(env).run()

        assert result.success is False
        assert result.fatal == {"apply-actions"}
        assert "merged" in result.unreachable
        assert "released" in result.unreachable

    def test_d_star_lite_recovers_from_a_break_on_an_and_join_sibling(self):
        # apply-actions is one of merged's two required children (the other
        # is ci-check) - breaking it and confirming recovery specifically
        # exercises repair locality in the presence of a sibling AND-
        # dependency, not just a straight chain like Phase 4's scenario.
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = DStarLiteExecutor(env)

        env.break_task("apply-actions")  # broken before it's ever attempted

        for _ in range(10):
            if not executor.step():
                break

        assert "apply-actions" in executor.fatal
        assert "ci-check" in executor.satisfied  # its sibling proceeds independently
        assert "merged" not in executor.satisfied

        env.fix_task("apply-actions")
        result = executor.run()

        assert result.success is True

        # ci-check was satisfied before the break/fix saga - it must not be
        # re-attempted once apply-actions is repaired.
        ci_check_attempts = [n for n, _ in result.trace if n == "ci-check"]
        assert len(ci_check_attempts) == 1
        assert executor.repairs == ["apply-actions"]

    def test_d_star_lite_recovers_from_a_break_on_a_deploy_branch(self):
        # A break discovered after merged (an AND-join itself) has already
        # resolved - the other two deploy branches may already be satisfied
        # by the time the fix arrives and must not be redone.
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = DStarLiteExecutor(env)

        while "merged" not in executor.satisfied:
            assert executor.step()

        env.break_task("deploy-staging")

        for _ in range(10):
            if not executor.step():
                break

        assert "deploy-staging" in executor.fatal
        assert "released" not in executor.satisfied

        env.fix_task("deploy-staging")
        result = executor.run()

        assert result.success is True
        for node_id in ("ci-check", "generate-actions", "apply-actions", "merged"):
            attempts = [n for n, _ in result.trace if n == node_id]
            assert len(attempts) == 1
        assert executor.repairs == ["deploy-staging"]
