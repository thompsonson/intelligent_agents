import os
import tempfile
from typing import List, Optional, Protocol, Set, Tuple, Union

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..agents.path_maintenance import PathMaintenanceAgent
from ..core.environment import CellState, PathGraphEnvironment
from ..core.results import WalkResult

# An event is one of:
#   ("arrive", node_id, CellState) - env.get_node_state(node_id) was called and returned
#   ("repair", node_id)            - env.repair_node(node_id) was called
# No separate "move" event, for the same reason maze_solver's
# path_maintenance_view.py has none: PathMaintenanceAgent.walk() only ever
# calls these two environment methods.
Event = Union[Tuple[str, str, CellState], Tuple[str, str]]

NODE_COLORS = {
    "future": "palegreen",  # not yet walked
    "clear": "limegreen",  # walked, was always OPEN - never needed repair
    "repaired": "darkgreen",  # walked, was NEEDS_REPAIR, then fixed
    "needs_repair": "red",  # sensed and not yet repaired
}
AGENT_MARKER_COLOR = "orange"

# Requires networkx and matplotlib - not otherwise needed by path_maintenance,
# same as task_graph_solver's own graph_view.py.


def build_networkx_graph(env: PathGraphEnvironment) -> nx.DiGraph:
    """A directed graph with an edge from each dependency to its dependent
    (the direction work actually flows), and an `is_and_join` attribute on
    every node with two or more required predecessors - same convention as
    task_graph_solver/visualization/graph_view.py's build_networkx_graph(),
    rebuilt locally rather than imported so this package stays independent."""
    graph = nx.DiGraph()
    for node_id, node in env.nodes.items():
        graph.add_node(node_id, is_and_join=len(node.requires) >= 2)
    for node_id, node in env.nodes.items():
        for dep in node.requires:
            graph.add_edge(dep, node_id)
    return graph


def _layered_layout(graph: nx.DiGraph) -> dict:
    """Left-to-right layout by topological generation - a DAG's dependency
    order is the point, and a physics-based layout would obscure it. Same
    approach as task_graph_solver's own _layered_layout()."""
    pos = {}
    for x, generation in enumerate(nx.topological_generations(graph)):
        nodes = sorted(generation)
        for y, node_id in enumerate(nodes):
            pos[node_id] = (x, -(y - (len(nodes) - 1) / 2))
    return pos


def _node_display_state(
    node_id: str, walked: Set[str], needs_repair: Set[str], repaired: Set[str]
) -> str:
    if node_id in needs_repair:
        return "needs_repair"
    if node_id in repaired:
        return "repaired"
    if node_id in walked:
        return "clear"
    return "future"


def render(
    env: PathGraphEnvironment,
    walked: Optional[Set[str]] = None,
    needs_repair: Optional[Set[str]] = None,
    repaired: Optional[Set[str]] = None,
    agent_position: Optional[str] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Render one frame: the DAG, color-coded by node state, with the
    agent's current position as a marker overlay - cell color and agent
    position are kept as separate visual channels, same as
    maze_solver's path_maintenance_view.py."""
    walked = walked or set()
    needs_repair = needs_repair or set()
    repaired = repaired or set()

    graph = build_networkx_graph(env)
    pos = _layered_layout(graph)

    fig, ax = plt.subplots(figsize=(10, 6))

    regular_nodes = [n for n, is_join in graph.nodes(data="is_and_join") if not is_join]
    and_join_nodes = [n for n, is_join in graph.nodes(data="is_and_join") if is_join]

    for nodes, shape in ((regular_nodes, "o"), (and_join_nodes, "s")):
        if not nodes:
            continue
        colors = [
            NODE_COLORS[_node_display_state(n, walked, needs_repair, repaired)]
            for n in nodes
        ]
        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=nodes,
            node_color=colors,
            node_shape=shape,
            node_size=1800,
            edgecolors="black",
            ax=ax,
        )

    nx.draw_networkx_edges(graph, pos, arrows=True, ax=ax, node_size=1800)
    nx.draw_networkx_labels(graph, pos, font_size=9, ax=ax)

    if agent_position is not None and agent_position in pos:
        x, y = pos[agent_position]
        ax.plot(
            x,
            y,
            marker="*",
            markersize=22,
            color=AGENT_MARKER_COLOR,
            markeredgecolor="black",
            zorder=5,
        )

    ax.set_title(title or "Path Maintenance (Graph Topology)")
    ax.axis("off")

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color=color, label=name.replace("_", " "))
        for name, color in NODE_COLORS.items()
    ]
    legend_elements.append(
        plt.Line2D(
            [0],
            [0],
            marker="*",
            color="w",
            markerfacecolor=AGENT_MARKER_COLOR,
            markeredgecolor="black",
            markersize=14,
            label="agent",
        )
    )
    ax.legend(
        handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3
    )

    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def _apply_event(
    walked: set, needs_repair: set, repaired: set, event: Event
) -> Tuple[str, str]:
    kind = event[0]
    if kind == "arrive":
        _, node_id, state = event
        walked.add(node_id)
        if state == CellState.NEEDS_REPAIR:
            needs_repair.add(node_id)
        return node_id, f"arrive {node_id!r} → {state.value}"
    if kind == "repair":
        _, node_id = event
        needs_repair.discard(node_id)
        repaired.add(node_id)
        return node_id, f"repair_node({node_id!r})"
    raise ValueError(f"unknown event kind: {kind!r}")


def animate_walk(
    env: PathGraphEnvironment,
    order: List[str],
    events: List[Event],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per event and combine into a GIF - the
    graph-topology analogue of maze_solver's animate_walk() /
    task_graph_solver's animate_events()."""
    # order[0] is never sensed (see agents/path_maintenance.py) - the agent
    # starts there rather than arriving at it, same convention as the
    # maze's start cell. Seeded into `walked` up front so frame 0 shows it
    # already clear, not "future".
    walked: Set[str] = {order[0]}
    needs_repair: Set[str] = set()
    repaired: Set[str] = set()
    base_title = title or "Path Maintenance (Graph Topology)"
    agent_position = order[0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        initial_path = os.path.join(tmp_dir, "frame_000.png")
        render(
            env,
            walked=set(walked),
            needs_repair=set(needs_repair),
            repaired=set(repaired),
            agent_position=agent_position,
            save_path=initial_path,
            title=base_title,
        )
        frame_files.append(initial_path)

        for i, event in enumerate(events, start=1):
            agent_position, caption = _apply_event(
                walked, needs_repair, repaired, event
            )
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            render(
                env,
                walked=set(walked),
                needs_repair=set(needs_repair),
                repaired=set(repaired),
                agent_position=agent_position,
                save_path=frame_path,
                title=f"{base_title}\n{caption}",
            )
            frame_files.append(frame_path)

        with imageio.get_writer(save_path, mode="I", duration=1000 / fps) as writer:
            for frame_file in frame_files:
                writer.append_data(imageio.imread(frame_file))


class _CanWalk(Protocol):
    def walk(self) -> WalkResult: ...


def record_walk(
    env: PathGraphEnvironment, agent: PathMaintenanceAgent
) -> Tuple[WalkResult, List[Event]]:
    """Run `agent.walk()` while instrumenting `env`'s
    `get_node_state`/`repair_node` to record every call, in the order it
    actually happened. Same explicit-env-parameter shape as
    maze_solver.visualization.path_maintenance_view.record_walk()."""
    events: List[Event] = []
    original_get_state = env.get_node_state
    original_repair = env.repair_node

    def get_state_and_record(node_id: str) -> CellState:
        state = original_get_state(node_id)
        events.append(("arrive", node_id, state))
        return state

    def repair_and_record(node_id: str) -> None:
        original_repair(node_id)
        events.append(("repair", node_id))

    env.get_node_state = get_state_and_record
    env.repair_node = repair_and_record
    try:
        result = agent.walk()
    finally:
        del env.get_node_state
        del env.repair_node

    return result, events
