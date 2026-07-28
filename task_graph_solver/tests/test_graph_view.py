from task_graph_solver.core.config import TaskGraphConfig
from task_graph_solver.core.domain import AttemptOutcome, TaskNode
from task_graph_solver.core.environment import TaskGraphEnvironment
from task_graph_solver.algorithms.ao_star import AOStarExecutor
from task_graph_solver.algorithms.d_star_lite import DStarLiteExecutor
from task_graph_solver.scenarios.pr_merge_lite import build_pr_merge_lite
from task_graph_solver.scenarios.repair_packages_lite import build_repair_packages_lite
from task_graph_solver.visualization.graph_view import (
    animate_events,
    build_networkx_graph,
    render,
    trace_to_events,
)


def make_node(node_id, requires=(), pass_probability=1.0, rmax=3):
    return TaskNode(
        id=node_id,
        kind="sensing",
        retry_flavor="sensing",
        pass_probability=pass_probability,
        rmax=rmax,
        requires=requires,
    )


class TestBuildNetworkxGraph:
    def test_edges_point_from_dependency_to_dependent(self):
        nodes = {
            "a": make_node("a"),
            "b": make_node("b"),
            "join": make_node("join", requires=("a", "b")),
        }
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        graph = build_networkx_graph(env)

        assert set(graph.nodes) == {"a", "b", "join"}
        assert graph.has_edge("a", "join")
        assert graph.has_edge("b", "join")
        assert not graph.has_edge("join", "a")
        assert not graph.has_edge("join", "b")

    def test_and_join_attribute_marks_nodes_with_two_or_more_requires(self):
        nodes = build_pr_merge_lite()
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))

        graph = build_networkx_graph(env)

        assert graph.nodes["merged"]["is_and_join"] is True
        assert graph.nodes["released"]["is_and_join"] is True
        assert graph.nodes["ci-check"]["is_and_join"] is False
        assert graph.nodes["apply-actions"]["is_and_join"] is False  # only 1 require


class TestRender:
    def test_render_without_a_result_does_not_crash(self, tmp_path):
        nodes = build_pr_merge_lite()
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        out = tmp_path / "graph.png"

        render(env, save_path=str(out))

        assert out.exists()
        assert out.stat().st_size > 0

    def test_render_with_a_result_colors_by_status(self, tmp_path):
        nodes = build_pr_merge_lite(
            pass_probability=1.0, overrides={"deploy-staging": 0.0}
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        result = AOStarExecutor(env).run()
        out = tmp_path / "graph_with_result.png"

        render(env, result=result, save_path=str(out), title="pr_merge_lite")

        assert out.exists()
        assert out.stat().st_size > 0


class TestAnimateEvents:
    def test_animate_from_a_plain_trace_produces_a_gif(self, tmp_path):
        nodes = build_pr_merge_lite(pass_probability=1.0)
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = AOStarExecutor(env)
        result = executor.run()

        out = tmp_path / "ao_star.gif"
        animate_events(env, trace_to_events(result.trace), save_path=str(out))

        assert out.exists()
        assert out.stat().st_size > 0

    def test_animate_includes_break_and_fix_events(self, tmp_path):
        nodes = build_repair_packages_lite(
            repair_pass_probability=1.0, verify_pass_probability=1.0
        )
        env = TaskGraphEnvironment(nodes, TaskGraphConfig(seed=1))
        executor = DStarLiteExecutor(env)

        events = []
        executor.step()  # repair satisfied
        events.append(("attempt", "repair", AttemptOutcome.PASS))

        env.break_task("verify")
        events.append(("break", "verify"))

        executor.step()  # verify attempted while broken -> fatal
        events.append(("attempt", "verify", AttemptOutcome.FATAL))

        env.fix_task("verify")
        events.append(("fix", "verify"))

        executor.step()  # sensed, repaired, verify attempted -> pass
        events.append(("attempt", "verify", AttemptOutcome.PASS))

        out = tmp_path / "d_star_lite.gif"
        animate_events(env, events, save_path=str(out), title="repair_packages_lite")

        assert out.exists()
        assert out.stat().st_size > 0
        assert executor.satisfied == {"repair", "verify"}
