import os
import tempfile
from typing import Dict, List, Optional, Set, Tuple

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..core.environment import StatefulDiscoveryEnvironment

# Same pattern as discovery/visualization/discovery_view.py - not imported,
# cross-package, the same "reused, not shared" precedent this whole
# package already follows for _validate_requires_graph(). Colors/marker
# kept identical on purpose: this is the same node-state vocabulary
# (known/blocked/cleared/goal), just fed by real sensing instead of a
# static notifies field.
NODE_COLORS = {
    "known": "lightgray",
    "blocked": "gold",
    "cleared": "limegreen",
    "goal": "darkgreen",
}
AGENT_MARKER_COLOR = "orange"


def build_networkx_graph(known_edges: Dict[str, Tuple[str, ...]]) -> nx.DiGraph:
    """A directed graph with an edge from each node to what it notifies -
    built purely from `known_edges`, data the walk itself already sensed
    (one real call per node, via `_walk_frames`'s replay). Never senses
    anything itself, unlike an earlier version of this function: sensing
    every node in `env.nodes` here (rather than just what the walk
    discovered) cost 90 real subprocess calls on a 15-frame/6-node walk
    that needed only 6, and silently widened a failing check's blast
    radius to nodes the walk never visited - a real violation of this
    package's own "nothing gets sensed except through the walk"
    principle, not just wasted work. See PR #15's review discussion."""
    graph = nx.DiGraph()
    for node_id, notifies in known_edges.items():
        graph.add_node(node_id, is_goal=not notifies)
    for node_id, notifies in known_edges.items():
        for target in notifies:
            graph.add_edge(node_id, target)
    return graph


def _layered_layout(graph: nx.DiGraph) -> dict:
    try:
        pos = {}
        for x, generation in enumerate(nx.topological_generations(graph)):
            nodes = sorted(generation)
            for y, node_id in enumerate(nodes):
                pos[node_id] = (x, -(y - (len(nodes) - 1) / 2))
        return pos
    except nx.NetworkXUnfeasible:
        return nx.spring_layout(graph, seed=0)


def _node_display_state(
    node_id: str, visited: Set[str], cleared: Set[str], is_goal: bool
) -> str:
    if node_id not in visited:
        return "known"
    if node_id not in cleared:
        return "blocked"
    return "goal" if is_goal else "cleared"


def render(
    known_edges: Dict[str, Tuple[str, ...]],
    known: Set[str],
    visited: Optional[Set[str]] = None,
    cleared: Optional[Set[str]] = None,
    agent_position: Optional[str] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """One frame: only the subgraph the agent has actually discovered so
    far. `known_edges` is the walk's own already-sensed data (see
    build_networkx_graph()) - this function never senses anything itself,
    unlike an earlier version that took `env` and re-sensed every node on
    every frame."""
    visited = visited or set()
    cleared = visited if cleared is None else cleared

    full_graph = build_networkx_graph(known_edges)
    full_pos = _layered_layout(full_graph)

    graph = full_graph.subgraph(known).copy()
    graph.remove_edges_from([(u, v) for u, v in graph.edges() if u not in visited])
    pos = {node_id: full_pos[node_id] for node_id in known}

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = [
        NODE_COLORS[
            _node_display_state(n, visited, cleared, full_graph.nodes[n]["is_goal"])
        ]
        for n in graph.nodes()
    ]
    nx.draw_networkx_nodes(
        graph, pos, node_color=colors, node_size=1800, edgecolors="black", ax=ax
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

    ax.set_title(title or "Discovery (real, atomicguard-backed)")
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


# A frame is (node_id, caption, known, visited, cleared).
Frame = Tuple[str, str, Set[str], Set[str], Set[str]]


def _walk_frames(
    env: StatefulDiscoveryEnvironment, path: List[str]
) -> Tuple[List[Frame], Dict[str, Tuple[str, ...]]]:
    """Pure, render-free replay of `path`, identical in structure to
    discovery/'s own _walk_frames() - see that function's docstring for
    the full reasoning. sense_edges()/sense_requires() here are the real,
    subprocess-backed calls, not field reads, but the replay logic (what
    counts as a re-sense vs. a backtrack vs. a clearing event) is exactly
    the same deterministic rule DiscoveryAgent.walk() itself already
    applied once to produce `path`.

    Also returns `known_edges` - every node's notifies, recorded the one
    time each is actually sensed during this replay (never more than
    once per node, mirroring `path`'s own re-sense avoidance). This is
    the *only* sensing this whole visualization module does; passed on to
    render() via animate_walk() below so no frame ever re-senses anything,
    let alone a node the walk itself never visited."""
    known: Set[str] = {path[0]}
    visited: Set[str] = set()
    cleared: Set[str] = set()
    sensed: Set[str] = set()
    known_requires: Dict[str, Tuple[str, ...]] = {}
    known_edges: Dict[str, Tuple[str, ...]] = {}
    frames: List[Frame] = []

    for node_id in path:
        was_sensed = node_id in sensed
        if not was_sensed:
            notifies = env.sense_edges(node_id)
            known_requires[node_id] = env.sense_requires(node_id)
            known_edges[node_id] = notifies
            sensed.add(node_id)
            known.update(notifies)
        visited.add(node_id)

        was_cleared = node_id in cleared
        if not was_cleared and all(r in cleared for r in known_requires[node_id]):
            cleared.add(node_id)

        if not was_sensed:
            caption = f"sense_edges({node_id!r}) → {notifies!r}"
            if known_requires[node_id]:
                caption += f", requires {known_requires[node_id]!r}"
        elif not was_cleared and node_id in cleared:
            caption = f"{node_id!r} requires satisfied - cleared"
        else:
            caption = f"backtrack to {node_id!r}"

        frames.append((node_id, caption, set(known), set(visited), set(cleared)))

    return frames, known_edges


def animate_walk(
    env: StatefulDiscoveryEnvironment,
    path: List[str],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per position in `path` and combine into a GIF -
    identical shape to discovery/'s own animate_walk(). `_walk_frames()`
    is called exactly once, up front, so every real sense happens exactly
    once per node - render() itself never senses anything."""
    base_title = title or "Discovery (real, atomicguard-backed)"
    frames, known_edges = _walk_frames(env, path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        for i, (node_id, caption, known, visited, cleared) in enumerate(frames):
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            render(
                known_edges,
                known=known,
                visited=visited,
                cleared=cleared,
                agent_position=node_id,
                save_path=frame_path,
                title=f"{base_title}\n{caption}",
            )
            frame_files.append(frame_path)

        with imageio.get_writer(save_path, mode="I", duration=1000 / fps) as writer:
            for frame_file in frame_files:
                writer.append_data(imageio.imread(frame_file))
