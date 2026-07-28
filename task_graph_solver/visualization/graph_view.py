import os
import tempfile
from typing import List, Optional, Tuple, Union

import matplotlib

matplotlib.use("Agg")  # headless-safe: exercised by pytest, not only notebooks
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult

# An animation event is either:
#   ("attempt", node_id, AttemptOutcome)  - env.attempt() was called and resolved
#   ("break", node_id)                    - Driver called env.break_task()
#   ("fix", node_id)                      - Driver called env.fix_task()
# `trace` alone (as produced by every executor) only carries "attempt" events -
# Driver break/fix calls happen *between* attempts and have no entry there, so
# a caller narrating a D* Lite break/fix story needs to record its own event
# list alongside calling step() - see task_graph_solver/visualization for an
# example of building one.
Event = Union[Tuple[str, str, AttemptOutcome], Tuple[str, str]]

# Requires networkx and matplotlib - not otherwise needed by task_graph_solver,
# same as maze_solver's dashboards, which assume these are installed rather
# than declaring them in a formal dependency file (this repo has none).

STATUS_COLORS = {
    "satisfied": "#4CAF50",  # green
    "fatal": "#E53935",  # red
    "unreachable": "#9E9E9E",  # gray
    "pending": "#FFFFFF",  # white
}


def build_networkx_graph(env: TaskGraphEnvironment) -> nx.DiGraph:
    """Build a directed graph from a TaskGraphEnvironment: an edge from each
    dependency to its dependent (the direction work actually flows - `dep`
    must be satisfied before `node` can be attempted), with an
    `is_and_join` attribute on every node with two or more required
    predecessors - the structural feature search_algorithms/ao_star.md's
    AND-composition applies to, and the thing the maze can't produce
    without deliberately constructing one.
    """
    graph = nx.DiGraph()
    for node_id, node in env.nodes.items():
        graph.add_node(node_id, is_and_join=len(node.requires) >= 2)
    for node_id, node in env.nodes.items():
        for dep in node.requires:
            graph.add_edge(dep, node_id)
    return graph


def _node_status(node_id: str, result: Optional[ExecutionResult]) -> str:
    if result is None:
        return "pending"
    if node_id in result.satisfied:
        return "satisfied"
    if node_id in result.fatal:
        return "fatal"
    if node_id in result.unreachable:
        return "unreachable"
    return "pending"


def _layered_layout(graph: nx.DiGraph) -> dict:
    """Left-to-right layout by topological generation, rather than
    spring_layout's force-directed placement - a DAG's whole point is its
    dependency order, and a physics-based layout obscures exactly that.
    Nodes within a generation are stacked vertically, centered."""
    pos = {}
    for x, generation in enumerate(nx.topological_generations(graph)):
        nodes = sorted(generation)
        for y, node_id in enumerate(nodes):
            pos[node_id] = (x, -(y - (len(nodes) - 1) / 2))
    return pos


def render(
    env: TaskGraphEnvironment,
    result: Optional[ExecutionResult] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Render env's task graph, color-coded by each node's status in
    `result` if given (green=satisfied, red=fatal, gray=unreachable,
    white=pending/not yet attempted). AND-join nodes (two or more required
    predecessors) are drawn as squares instead of circles, so the fan-in
    structure this environment exists to demonstrate is visible at a
    glance rather than requiring a legend lookup.
    """
    graph = build_networkx_graph(env)
    pos = _layered_layout(graph)

    fig, ax = plt.subplots(figsize=(10, 6))

    regular_nodes = [n for n, is_join in graph.nodes(data="is_and_join") if not is_join]
    and_join_nodes = [n for n, is_join in graph.nodes(data="is_and_join") if is_join]

    for nodes, shape in ((regular_nodes, "o"), (and_join_nodes, "s")):
        if not nodes:
            continue
        colors = [STATUS_COLORS[_node_status(n, result)] for n in nodes]
        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=nodes,
            node_color=colors,
            node_shape=shape,
            node_size=1400,
            edgecolors="black",
            ax=ax,
        )

    nx.draw_networkx_edges(graph, pos, arrows=True, ax=ax)
    nx.draw_networkx_labels(graph, pos, font_size=8, ax=ax)

    ax.set_title(title or "Task Graph")
    ax.axis("off")

    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def trace_to_events(trace: List[Tuple[str, AttemptOutcome]]) -> List[Event]:
    """Convert a plain executor `.trace` (attempts only) into the richer
    event list `animate_events` expects. Use this for TopologicalExecutor/
    AOStarExecutor, whose entire history is attempts - there's nothing a
    Driver did in between to narrate. For DStarLiteExecutor, build the
    event list by hand instead, recording break_task/fix_task calls
    alongside step() so they appear as their own frames."""
    return [("attempt", node_id, outcome) for node_id, outcome in trace]


def _apply_event(satisfied: set, fatal: set, event: Event) -> str:
    kind = event[0]
    if kind == "attempt":
        _, node_id, outcome = event
        if outcome == AttemptOutcome.PASS:
            satisfied.add(node_id)
        elif outcome == AttemptOutcome.FATAL:
            fatal.add(node_id)
        return f"attempt {node_id} → {outcome.value}"
    if kind == "break":
        _, node_id = event
        return f"Driver breaks {node_id}"
    if kind == "fix":
        _, node_id = event
        fatal.discard(node_id)  # repaired: no longer terminal, can be re-attempted
        return f"Driver fixes {node_id}"
    raise ValueError(f"unknown event kind: {kind!r}")


def animate_events(
    env: TaskGraphEnvironment,
    events: List[Event],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per event and combine into a GIF - the task-graph
    analogue of maze_solver's dashboard create_gif(), showing an algorithm's
    execution (and, for D* Lite, the Driver's break/fix calls) unfold frame
    by frame rather than a single static end state.
    """
    all_nodes = set(env.nodes.keys())
    satisfied: set = set()
    fatal: set = set()
    base_title = title or "Task Graph"

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        initial_path = os.path.join(tmp_dir, "frame_000.png")
        render(env, result=None, save_path=initial_path, title=base_title)
        frame_files.append(initial_path)

        for i, event in enumerate(events, start=1):
            caption = _apply_event(satisfied, fatal, event)
            unreachable = all_nodes - satisfied - fatal
            snapshot = ExecutionResult(
                success=(satisfied == all_nodes),
                satisfied=set(satisfied),
                fatal=set(fatal),
                unreachable=unreachable,
                trace=[],
            )
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            render(
                env,
                result=snapshot,
                save_path=frame_path,
                title=f"{base_title}\n{caption}",
            )
            frame_files.append(frame_path)

        with imageio.get_writer(save_path, mode="I", duration=1000 / fps) as writer:
            for frame_file in frame_files:
                writer.append_data(imageio.imread(frame_file))
