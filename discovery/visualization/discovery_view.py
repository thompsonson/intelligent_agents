import os
import tempfile
from typing import Dict, List, Optional, Set, Tuple

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..core.environment import DiscoveryEnvironment

NODE_COLORS = {
    "known": "lightgray",  # named in a sensed node's notifies, not yet visited
    "blocked": "gold",  # visited, but requires aren't all cleared yet - see
    # documentation/discovery/and-joins/environment_design.md's "Three
    # states, not two". Doesn't exist before this step - a node with
    # requires=() clears the instant it's sensed, so this color never
    # appears in step 1/2 GIFs.
    "cleared": "limegreen",  # visited and requires satisfied - notifies
    # walkable (not the goal). Named "visited" before this step.
    "goal": "darkgreen",  # cleared, no notifies - the walk's terminal
}
AGENT_MARKER_COLOR = "orange"

# Requires networkx and matplotlib - not otherwise needed by discovery,
# same as path_maintenance's own graph_view.py.


def build_networkx_graph(known_edges: Dict[str, Tuple[str, ...]]) -> nx.DiGraph:
    """A directed graph with an edge from each node to what it notifies -
    already the direction work flows in, unlike a requires-graph (see
    documentation/discovery/environment_design.md's "The edge points the
    other way"). Built purely from `known_edges` - what the walk itself
    has actually sensed (see _walk_frames() below) - never from the
    environment's own full node set directly.

    An earlier version of this function read `env.nodes` instead, using
    every node's true `.notifies` regardless of what the walk had
    discovered. That's a real correctness bug, not a harmless shortcut:
    environment_design.md's own "Observable: Partially... no enumeration,
    no 'list all nodes'" is this environment's defining property, and
    reading `env.nodes` directly bypasses `sense_edges()`/`sense_requires()`
    entirely - the same god's-eye access DiscoveryAgent itself is never
    given. That it cost nothing (a dataclass field, not a real action)
    doesn't make it correct; it undermines the actual point every
    discovery GIF makes, that the graph is learned incrementally, not
    already known. See PR #15's review discussion, where the identical
    pattern in real_discovery/'s version was caught costing 90 real
    subprocess calls for a walk that needed 6 - the same bug, just with a
    real, measurable cost there instead of a conceptual one here.

    A target named in some sensed node's `notifies` isn't necessarily
    itself a key in `known_edges` - it may be known (named) but never
    itself visited/sensed (see experiment 1's `unit-tests`/
    `integration-tests`: the walk reaches the goal down the other branch
    first and never senses them). Such a target still needs to exist as a
    node here - it can appear in a frame's `known` set - just with no
    real `is_goal` answer yet, since that's genuinely unknown until it's
    sensed. `_node_display_state()` never actually reads `is_goal` for an
    unvisited node (it returns "known" before ever consulting it), so the
    placeholder value here is never observed - it exists only so the
    graph has every node a frame might reference."""
    graph = nx.DiGraph()
    for node_id, notifies in known_edges.items():
        graph.add_node(node_id, is_goal=not notifies)
    for node_id, notifies in known_edges.items():
        for target in notifies:
            if target not in graph:
                graph.add_node(target, is_goal=False)  # not yet sensed
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
    """Render one frame: only the subgraph the agent has actually
    discovered so far (`known` - nodes named in some already-sensed
    node's notifies, plus the start id) - not the full environment. Edges
    shown are only those whose source has been visited (sensed), since an
    edge is only known once its source node has actually been queried.
    `known_edges` is the walk's own already-sensed data (see
    build_networkx_graph()) - this function never reads the environment
    directly.

    `cleared` defaults to `visited` when omitted - step 1/2 callers never
    had a blocked concept at all (every node's requires=() clears
    instantly), so leaving it unset reproduces their exact old coloring
    rather than painting everything "blocked"."""
    visited = visited or set()
    cleared = visited if cleared is None else cleared

    full_graph = build_networkx_graph(known_edges)
    full_pos = _layered_layout(full_graph)

    graph = full_graph.subgraph(known).copy()
    graph.remove_edges_from(
        [(u, v) for u, v in graph.edges() if u not in visited]
    )
    pos = {node_id: full_pos[node_id] for node_id in known}

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = [
        NODE_COLORS[
            _node_display_state(n, visited, cleared, full_graph.nodes[n]["is_goal"])
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


# A frame is (node_id, caption, known, visited, cleared) - each a
# snapshot as of that position in path.
Frame = Tuple[str, str, Set[str], Set[str], Set[str]]


def _walk_frames(
    env: DiscoveryEnvironment, path: List[str]
) -> Tuple[List[Frame], Dict[str, Tuple[str, ...]]]:
    """Pure, render-free replay of `path` - DiscoveryAgent.walk()'s own
    move-by-move record, backtracks included (backtracking-exploration/
    algorithm_fit.md's "Not decided" -> resolved: path is the full move
    log, not first-visit order). One frame per position in `path`.

    Backtracking means walk() itself no longer calls sense_edges() once
    per move - a revisited node is answered from its own cache, so
    nodes_sensed can be smaller than len(path) (see backtracking-
    exploration/algorithm_fit.md's worked example: 6 senses, 10 moves).
    A per-move-event instrumentation trace would therefore have fewer
    entries than frames needed. Simpler and just as honest: replay `path`
    directly, and re-query sense_edges()/sense_requires() the first time
    this replay sees a given node - neither has an arrival gate and both
    are deterministic (environment_design.md), so re-asking them here for
    rendering doesn't touch walk()'s own already-fixed nodes_sensed
    accounting in the DiscoveryWalkResult this is replaying.

    Also replays the requires-gating computation itself (and-joins/
    algorithm_fit.md's "The algorithm"), in lockstep with `path`, to know
    which nodes are `cleared` at each frame - a second, independent replay
    of the same deterministic rule walk() already applied once, not a
    second source of truth: given the same `path`, it always agrees.

    Also returns `known_edges` - every node's notifies, recorded the one
    time each is actually sensed during this replay (never more than
    once per node). This is the only sensing this whole visualization
    module does; render() (via build_networkx_graph()) uses it instead of
    ever reading the environment's own node set directly - see that
    function's docstring for why that distinction is load-bearing, not
    cosmetic.
    """
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
    env: DiscoveryEnvironment,
    path: List[str],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per position in `path` (see `_walk_frames`) and
    combine into a GIF - the discovery analogue of path_maintenance's own
    animate_walk(). Callers get `path` from `DiscoveryAgent.walk().path`
    directly; there's no separate instrumented-recording step here the
    way path_maintenance's graph_view.record_walk() has, since `path`
    already is the real move-by-move record. `_walk_frames()` is called
    exactly once, up front, so every sense happens exactly once per node -
    render() itself never touches the environment."""
    base_title = title or "Discovery"
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
