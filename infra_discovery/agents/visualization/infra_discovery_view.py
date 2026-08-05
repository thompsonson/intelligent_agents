"""Visualization for InfraDiscoveryAgent's flat pending/RELEVANT/INVOKE loop.

Black-box, like discovery_view.py's own precedent: this module never calls
agent.step() itself and never re-invokes a DSA - it drives the *same*
run_episode() sequencing externally (agent.pending seeded the same way,
agent.step() called in the same loop shape) purely to snapshot public
state (belief_state.recorded, belief_state.edges, agent.pending) before
and after each real step, then diffs. No changes to agent_loop.py's
reviewed logic were needed or made.

Node vocabulary is this track's own, not discovery/'s known/blocked/
cleared/goal - Step 1 has no requires/SWEEP-CLEARED yet (Step 2), so
"blocked"/"cleared" don't apply. What Step 1 actually has:
- sensed: subject has at least one recorded facet
- pending: subject is queued (RELEVANT already enqueued a DSA for it)
- unregistered: named as an edge endpoint, but DSA-CATALOGUE has no entry
  for its (domain, kind) - a real, current Step 1 dead-end (OQ-015), not
  a placeholder state invented for the picture.
"""

import os
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..core.agent_loop import InfraDiscoveryAgent
from ..core.domain import Edge, NodeId

NODE_COLORS = {
    "sensed": "limegreen",
    "pending": "lightgray",
    "unregistered": "gold",
}
CURRENT_MARKER_COLOR = "orange"


def _label(node: NodeId) -> str:
    return f"{node.domain}/{node.kind}/{node.id}"


def _is_registered(agent: InfraDiscoveryAgent, node: NodeId) -> bool:
    return bool(agent.dsa_catalogue.get((node.domain, node.kind)))


@dataclass
class Frame:
    """One (dsa_name, subject) invocation and the state right after it."""

    dsa_name: str
    subject: NodeId
    caption: str
    sensed: Set[NodeId]
    pending: Set[NodeId]
    edges: List[Edge]
    new_facet_names: Tuple[str, ...] = field(default_factory=tuple)
    new_edges: Tuple[Edge, ...] = field(default_factory=tuple)


def _run_frames(
    agent: InfraDiscoveryAgent, roots: List[NodeId], max_steps: int = 200
) -> List[Frame]:
    """Drive agent.step() exactly the way run_episode() does, capturing a
    Frame after each real invocation. Diffs public state rather than
    reading anything step() doesn't already expose - see module docstring.
    """
    agent.pending.clear()
    for root in roots:
        root_dsa_entries = agent.dsa_catalogue.get((root.domain, root.kind), [])
        agent.pending.update(agent._relevant(root_dsa_entries, root))

    frames: List[Frame] = []
    prev_recorded: Set[Tuple[str, NodeId]] = set()
    prev_edge_count = 0

    for _ in range(max_steps):
        if not agent.pending:
            break

        before_recorded = set(agent.belief_state.recorded)
        status = agent.step()
        after_recorded = set(agent.belief_state.recorded)

        newly_recorded = after_recorded - before_recorded
        if not newly_recorded:
            if status in ("done", "escalated", None):
                break
            continue

        (dsa_name, subject) = next(iter(newly_recorded))

        all_edges = list(agent.belief_state.edges)
        new_edges = tuple(all_edges[prev_edge_count:])
        prev_edge_count = len(all_edges)

        facets = agent.belief_state.facets_for(subject)
        new_facet_names = tuple(
            name for name, facet in facets.items() if facet.sensed_by == dsa_name
        )

        pending_subjects = {s for (_entry, s) in agent.pending}

        if new_edges:
            edge_summary = "; ".join(
                f"{e.edge_type}({_label(e.from_)} -> {_label(e.to)})" for e in new_edges
            )
            caption = f"INVOKE({dsa_name}, {_label(subject)}) -> {edge_summary}"
        else:
            caption = f"INVOKE({dsa_name}, {_label(subject)}) -> {len(new_facet_names)} facet(s), no new edges"

        frames.append(
            Frame(
                dsa_name=dsa_name,
                subject=subject,
                caption=caption,
                sensed=set(agent.belief_state.recorded_subjects()),
                pending=pending_subjects,
                edges=all_edges,
                new_facet_names=new_facet_names,
                new_edges=new_edges,
            )
        )

        if status == "done":
            break

    return frames


def _build_graph(edges: List[Edge], known: Set[NodeId]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in known:
        graph.add_node(_label(node))
    for edge in edges:
        graph.add_edge(_label(edge.from_), _label(edge.to), edge_type=edge.edge_type)
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


def _node_state(
    agent: InfraDiscoveryAgent, node: NodeId, sensed: Set[NodeId], pending: Set[NodeId]
) -> str:
    if node in sensed:
        return "sensed"
    if node in pending:
        return "pending"
    if not _is_registered(agent, node):
        return "unregistered"
    return "pending"


def render(
    agent: InfraDiscoveryAgent,
    frame: Frame,
    full_pos: Dict[str, Tuple[float, float]],
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """One frame: the subgraph discovered so far (edges + every node either
    sensed, pending, or named-but-unregistered), with the just-invoked
    (dsa, subject) highlighted."""
    known = frame.sensed | frame.pending | {frame.subject}
    for edge in frame.edges:
        known.add(edge.from_)
        known.add(edge.to)

    graph = _build_graph(frame.edges, known)
    pos = {n: full_pos[n] for n in graph.nodes() if n in full_pos}

    fig, ax = plt.subplots(figsize=(11, 6.5))

    colors = [
        NODE_COLORS[_node_state(agent, _node_for_label(known, n), frame.sensed, frame.pending)]
        for n in graph.nodes()
    ]
    nx.draw_networkx_nodes(
        graph, pos, node_color=colors, node_size=2400, edgecolors="black", ax=ax
    )
    nx.draw_networkx_edges(
        graph, pos, arrows=True, ax=ax, node_size=2400, connectionstyle="arc3,rad=0.08"
    )
    nx.draw_networkx_labels(graph, pos, font_size=8, ax=ax)
    edge_labels = {(u, v): d["edge_type"] for u, v, d in graph.edges(data=True)}
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=7, ax=ax)

    current_label = _label(frame.subject)
    if current_label in pos:
        x, y = pos[current_label]
        ax.plot(
            x,
            y,
            marker="*",
            markersize=26,
            color=CURRENT_MARKER_COLOR,
            markeredgecolor="black",
            zorder=5,
        )

    ax.set_title(title or "Infra Discovery (Step 1)")
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
            markerfacecolor=CURRENT_MARKER_COLOR,
            markeredgecolor="black",
            markersize=14,
            label="just invoked",
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


def _node_for_label(known: Set[NodeId], label: str) -> NodeId:
    for node in known:
        if _label(node) == label:
            return node
    raise KeyError(label)


def animate_discovery(
    agent: InfraDiscoveryAgent,
    roots: List[NodeId],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> List[Frame]:
    """Render one frame per real (dsa, subject) invocation and combine into
    a GIF. `_run_frames()` is called exactly once, up front - render()
    itself never invokes anything, mirroring discovery_view.py's
    "sense once, replay many times" precedent."""
    base_title = title or "Infra Discovery (Step 1)"
    frames = _run_frames(agent, roots)
    if not frames:
        raise ValueError("No frames produced - did run_episode() discover anything?")

    final_known: Set[NodeId] = set(roots)
    for frame in frames:
        final_known |= frame.sensed | frame.pending | {frame.subject}
        for edge in frame.edges:
            final_known.add(edge.from_)
            final_known.add(edge.to)
    full_graph = _build_graph(frames[-1].edges, final_known)
    full_pos = _layered_layout(full_graph)

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []
        for i, frame in enumerate(frames):
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            render(
                agent,
                frame,
                full_pos,
                save_path=frame_path,
                title=f"{base_title}\nStep {i + 1}/{len(frames)}: {frame.caption}",
            )
            frame_files.append(frame_path)

        # Hold the last frame a little longer so the final graph is readable.
        with imageio.get_writer(save_path, mode="I", duration=1000 / fps) as writer:
            for frame_file in frame_files:
                writer.append_data(imageio.imread(frame_file))
            last = imageio.imread(frame_files[-1])
            for _ in range(2):
                writer.append_data(last)

    return frames
