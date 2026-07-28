from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.topological import TopologicalExecutor
from task_graph_solver.algorithms.lrta_star import LRTAStarLearner
from task_graph_solver.algorithms.ao_star import AOStarExecutor
from task_graph_solver.algorithms.d_star_lite import DStarLiteExecutor
from task_graph_solver.scenarios.disk_check_lite import build_disk_check_lite
from task_graph_solver.scenarios.repair_packages_lite import build_repair_packages_lite
from task_graph_solver.scenarios.pr_merge_lite import build_pr_merge_lite
from task_graph_solver.scenarios.pr_merge_with_variants import (
    build_pr_merge_with_variants,
)


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


class TestPrMergeWithVariantsScenario:
    def test_builds_eleven_nodes_and_one_group(self):
        nodes, groups, goal = build_pr_merge_with_variants()

        assert set(nodes.keys()) == {
            "ci-check",
            "generate-actions",
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
            "merged",
            "deploy-staging",
            "deploy-publish",
            "deploy-promote",
            "released",
            "check-disk",
        }
        assert len(groups) == 1
        assert groups[0].id == "actions-ready"
        assert set(groups[0].members) == {
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
        }
        assert goal == "released"

    def test_merged_requires_the_group_not_a_specific_variant(self):
        nodes, _groups, _goal = build_pr_merge_with_variants()
        assert nodes["merged"].requires == ("ci-check", "actions-ready")

    def test_variants_share_generate_actions_as_their_only_requirement(self):
        nodes, _groups, _goal = build_pr_merge_with_variants()
        for variant_id in (
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
        ):
            node = nodes[variant_id]
            assert node.requires == ("generate-actions",)
            assert node.retry_flavor == "repair"
            assert node.r_patience == 1

    def test_check_disk_is_a_disconnected_orphan(self):
        nodes, _groups, _goal = build_pr_merge_with_variants()
        assert nodes["check-disk"].requires == ()
        for node_id, node in nodes.items():
            if node_id != "check-disk":
                assert "check-disk" not in node.requires

    def test_environment_accepts_the_scenario_without_error(self):
        nodes, groups, goal = build_pr_merge_with_variants()
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )
        assert env.goal == "released"

    def test_topological_executor_attempts_all_three_variants_even_after_group_satisfied(
        self,
    ):
        # The documented baseline waste: TopologicalExecutor has no concept
        # of "stop once the group is satisfied", so all three variants get
        # attempted regardless of order, even though only one was needed.
        nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )

        result = TopologicalExecutor(env).run()

        assert result.success is True
        for variant_id in (
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
        ):
            assert variant_id in result.satisfied

    def test_topological_executor_reaches_goal_even_when_the_orphan_fails(self):
        # The whole point of an explicit goal: check-disk failing must not
        # sink a run that otherwise reaches `released`.
        nodes, groups, goal = build_pr_merge_with_variants(
            pass_probability=1.0, check_disk_pass_probability=0.0
        )
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )

        result = TopologicalExecutor(env).run()

        assert result.success is True
        assert "check-disk" in result.fatal
        assert "released" in result.satisfied

    def test_ao_star_stops_attempting_variants_once_the_group_is_satisfied(self):
        # apply-actions-comprehensive is alphabetically first among the
        # three variants, so AOStarExecutor attempts it first; once it
        # passes, the other two must never be attempted at all.
        nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )
        executor = AOStarExecutor(env)

        result = executor.run()

        assert result.success is True
        assert "apply-actions-comprehensive" in result.satisfied
        assert result.not_needed == {
            "apply-actions-minimal",
            "apply-actions-test-driven",
        }
        attempted = {node_id for node_id, _ in executor.trace}
        assert "apply-actions-minimal" not in attempted
        assert "apply-actions-test-driven" not in attempted

    def test_ao_star_still_attempts_the_disconnected_orphan(self):
        # Pruning only applies to OR-group siblings - check-disk has no
        # group and no bearing on the goal, but AO* has no goal-directed
        # subgraph pruning here, so it still gets attempted like any other
        # ready node.
        nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )

        result = AOStarExecutor(env).run()

        assert "check-disk" in result.satisfied
        assert "check-disk" not in result.not_needed

    def test_ao_star_falls_back_to_next_variant_if_the_first_fails(self):
        nodes, groups, goal = build_pr_merge_with_variants(
            pass_probability=1.0,
            overrides={"apply-actions-comprehensive": 0.0},
        )
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )

        result = AOStarExecutor(env).run()

        assert result.success is True
        assert "apply-actions-comprehensive" in result.fatal
        assert "apply-actions-minimal" in result.satisfied
        assert "apply-actions-test-driven" in result.not_needed

    def test_ao_star_group_cost_is_the_satisfied_members_own_cost(self):
        nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )
        executor = AOStarExecutor(env)

        executor.run()

        # merged requires ci-check and the group; the group's cost must be
        # apply-actions-comprehensive's own h, not a min/max over all three
        # (the other two were never attempted and have no real cost).
        assert executor.h["merged"] == 1 + max(
            executor.h["ci-check"], executor.h["apply-actions-comprehensive"]
        )

    def test_d_star_lite_cannot_progress_once_every_variant_is_broken(self):
        # All three apply-actions-* variants broken before ever being
        # attempted - actions-ready becomes genuinely unsolvable (every
        # member fatal, the inverse of an AND-node's "any required child
        # fatal" rule), so merged and released never become reachable.
        nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )
        executor = DStarLiteExecutor(env)

        for variant_id in (
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
        ):
            env.break_task(variant_id)

        result = executor.run()

        assert result.success is False
        assert {
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
        } == executor.fatal
        assert "merged" in result.unreachable
        assert "released" in result.unreachable

    def test_d_star_lite_recovers_once_any_single_variant_is_fixed(self):
        # The distinguishing D* Lite story for this scenario, per
        # documentation/task-graph/or-groups/algorithm_fit.md: recovery
        # after every group member has been exhausted, not a "reroute"
        # among simultaneously-ready siblings (every executor already does
        # that for free). TopologicalExecutor given the same sequence would
        # stay failed forever - it never senses the fix.
        nodes, groups, goal = build_pr_merge_with_variants(pass_probability=1.0)
        env = TaskGraphEnvironment(
            nodes, TaskGraphConfig(seed=1), groups=groups, goal=goal
        )
        executor = DStarLiteExecutor(env)

        for variant_id in (
            "apply-actions-minimal",
            "apply-actions-comprehensive",
            "apply-actions-test-driven",
        ):
            env.break_task(variant_id)

        for _ in range(10):
            if not executor.step():
                break

        assert "released" not in executor.satisfied

        env.fix_task("apply-actions-minimal")
        result = executor.run()

        assert result.success is True
        assert "apply-actions-minimal" in result.satisfied
        # The still-broken siblings were never satisfied, and ci-check
        # (already satisfied before the break/fix saga) must not be
        # re-attempted once the group is repaired.
        ci_check_attempts = [n for n, _ in result.trace if n == "ci-check"]
        assert len(ci_check_attempts) == 1
        assert executor.repairs == ["apply-actions-minimal"]
