import os
import tempfile
from typing import List, Optional, Protocol, Set, Tuple

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..agents.discovery_agent import DiscoveryAgent
from ..core.environment import DiscoveryEnvironment
from ..core.results import DiscoveryWalkResult

# An event is always ("sense", node_id, notifies) - env.sense_edges(node_id)
# was called and returned notifies. No separate "move" event, for the same
# reason path_maintenance/visualization/graph_view.py has none:
# DiscoveryAgent.walk() only ever calls this one environment method.
Event = Tuple[str, str, Tuple[str, ...]]

NODE_COLORS = {
    "known": "lightgray",  # named in a sensed node's notifies, not yet visited
    "visited": "limegreen",  # sensed, has its own notifies (not the goal)
    "goal": "darkgreen",  # sensed, no notifies - the walk's terminal
}
AGENT_MARKER_COLOR = "orange"

# Requires networkx and matplotlib - not otherwise needed by discovery,
# same as path_maintenance's own graph_view.py.


def build_networkx_graph(env: DiscoveryEnvironment) -> nx.DiGraph:
    """A directed graph with an edge from each node to what it notifies -
    already the direction work flows in, unlike a requires-graph (see
    documentation/discovery/environment_design.md's "The edge points the
    other way"). Built from the environment's full node set, since the
    environment always holds the whole graph - only the *rendering* below
    restricts what's shown to what the agent has actually discovered."""
    graph = nx.DiGraph()
    for node_id, node in env.nodes.items():
        graph.add_node(node_id, is_goal=not node.notifies)
    for node_id, node in env.nodes.items():
        for target in node.notifies:
            graph.add_edge(node_id, target)
    return graph


def _layered_layout(graph: nx.DiGraph) -> dict:
    """Left-to-right layout by topological generation, same approach as
    path_maintenance's own _layered_layout(). Falls back to a
    deterministic spring layout if the full graph has a cycle - notifies
    graphs are allowed to (see environment.py's __init__ docstring), even
    though the one scenario built so far doesn't."""
    try:
        pos = {}
        for x, generation in enumerate(nx.topological_generations(graph)):
            nodes = sorted(generation)
            for y, node_id in enumerate(nodes):
                pos[node_id] = (x, -(y - (len(nodes) - 1) / 2))
        return pos
    except nx.NetworkXUnfeasible:
        return nx.spring_layout(graph, seed=0)


def _node_display_state(node_id: str, visited: Set[str], is_goal: bool) -> str:
    if node_id in visited:
        return "goal" if is_goal else "visited"
    return "known"


def render(
    env: DiscoveryEnvironment,
    known: Set[str],
    visited: Optional[Set[str]] = None,
    agent_position: Optional[str] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Render one frame: only the subgraph the agent has actually
    discovered so far (`known` - nodes named in some already-sensed
    node's notifies, plus the start id) - not the full environment. Edges
    shown are only those whose source has been visited (sensed), since an
    edge is only known once its source node has actually been queried."""
    visited = visited or set()

    full_graph = build_networkx_graph(env)
    full_pos = _layered_layout(full_graph)

    graph = full_graph.subgraph(known).copy()
    graph.remove_edges_from(
        [(u, v) for u, v in graph.edges() if u not in visited]
    )
    pos = {node_id: full_pos[node_id] for node_id in known}

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = [
        NODE_COLORS[
            _node_display_state(n, visited, full_graph.nodes[n]["is_goal"])
        ]
        for n in graph.nodes()
    ]
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=colors,
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

    ax.set_title(title or "Discovery")
    ax.axis("off")

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color=color, label=name)
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
        handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=4
    )

    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def _apply_event(known: set, visited: set, event: Event) -> Tuple[str, str]:
    _, node_id, notifies = event
    visited.add(node_id)
    known.update(notifies)
    caption = f"sense_edges({node_id!r}) → {notifies!r}"
    return node_id, caption


def animate_walk(
    env: DiscoveryEnvironment,
    start_id: str,
    events: List[Event],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per sense_edges() call and combine into a GIF -
    the discovery analogue of path_maintenance's own animate_walk()."""
    known: Set[str] = {start_id}
    visited: Set[str] = set()
    base_title = title or "Discovery"
    agent_position = start_id

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        initial_path = os.path.join(tmp_dir, "frame_000.png")
        render(
            env,
            known=set(known),
            visited=set(visited),
            agent_position=agent_position,
            save_path=initial_path,
            title=base_title,
        )
        frame_files.append(initial_path)

        for i, event in enumerate(events, start=1):
            agent_position, caption = _apply_event(known, visited, event)
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            render(
                env,
                known=set(known),
                visited=set(visited),
                agent_position=agent_position,
                save_path=frame_path,
                title=f"{base_title}\n{caption}",
            )
            frame_files.append(frame_path)

        with imageio.get_writer(save_path, mode="I", duration=1000 / fps) as writer:
            for frame_file in frame_files:
                writer.append_data(imageio.imread(frame_file))


class _CanWalk(Protocol):
    def walk(self) -> DiscoveryWalkResult: ...


def record_walk(
    env: DiscoveryEnvironment, agent: DiscoveryAgent
) -> Tuple[DiscoveryWalkResult, List[Event]]:
    """Run `agent.walk()` while instrumenting `env.sense_edges` to record
    every call, in the order it actually happened. Same explicit-env-
    parameter shape as path_maintenance.visualization.graph_view.record_walk()."""
    events: List[Event] = []
    original_sense = env.sense_edges

    def sense_and_record(node_id: str) -> Tuple[str, ...]:
        notifies = original_sense(node_id)
        events.append(("sense", node_id, notifies))
        return notifies

    env.sense_edges = sense_and_record
    try:
        result = agent.walk()
    finally:
        del env.sense_edges

    return result, events
