import os
import tempfile
from typing import Dict, List, Optional, Protocol, Set, Tuple, Union

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..agents.job_maintenance import PathMaintenanceAgent
from ..core.domain import JobState
from ..core.environment import JobGraphEnvironment
from ..core.results import JobWalkResult
from .graph_view import _layered_layout, build_networkx_graph

# An event is one of:
#   ("arrive", node_id, JobState) - env.get_job_state(node_id) was called and returned
#   ("advance",)                  - env.advance_jobs(satisfied) was called
#   ("repair", node_id)           - env.repair_node(node_id) was called
# No separate "move" event, same reasoning as graph-topology's graph_view.py.
Event = Union[Tuple[str, str, JobState], Tuple[str], Tuple[str, str]]

NODE_COLORS = {
    "future": "palegreen",  # not yet sensed at all
    "pending": "lightyellow",  # sensed, not yet started
    "in_progress": "gold",  # sensed, started, not yet resolved
    "clear": "limegreen",  # resolved SUCCEEDED, never needed repair
    "repaired": "darkgreen",  # resolved FAILED, then repaired
    "needs_repair": "red",  # resolved FAILED, not yet repaired
}
AGENT_MARKER_COLOR = "orange"

_STATE_TO_STATUS = {
    JobState.PENDING: "pending",
    JobState.IN_PROGRESS: "in_progress",
    JobState.SUCCEEDED: "clear",
    JobState.FAILED: "needs_repair",
}


def render(
    env: JobGraphEnvironment,
    node_status: Optional[Dict[str, str]] = None,
    agent_position: Optional[str] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Render one frame: the DAG, color-coded by job lifecycle status, with
    the agent's current position as a marker overlay. Same structure as
    graph-topology's render(), with two extra colors (pending/in_progress)
    for the states a job can be sensed in before it resolves."""
    node_status = node_status or {}

    graph = build_networkx_graph(env)
    pos = _layered_layout(graph)

    fig, ax = plt.subplots(figsize=(10, 6))

    regular_nodes = [n for n, is_join in graph.nodes(data="is_and_join") if not is_join]
    and_join_nodes = [n for n, is_join in graph.nodes(data="is_and_join") if is_join]

    for nodes, shape in ((regular_nodes, "o"), (and_join_nodes, "s")):
        if not nodes:
            continue
        colors = [NODE_COLORS[node_status.get(n, "future")] for n in nodes]
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

    ax.set_title(title or "Path Maintenance (Job Lifecycle)")
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
        handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3
    )

    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def _apply_event(
    node_status: Dict[str, str], event: Event
) -> Tuple[Optional[str], str]:
    kind = event[0]
    if kind == "arrive":
        _, node_id, state = event
        node_status[node_id] = _STATE_TO_STATUS[state]
        return node_id, f"arrive {node_id!r} → {state.value}"
    if kind == "advance":
        return None, "advance_jobs() - other agents make progress"
    if kind == "repair":
        _, node_id = event
        node_status[node_id] = "repaired"
        return node_id, f"repair_node({node_id!r})"
    raise ValueError(f"unknown event kind: {kind!r}")


def animate_walk(
    env: JobGraphEnvironment,
    order: List[str],
    events: List[Event],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per event and combine into a GIF - the
    job-lifecycle analogue of graph-topology's animate_walk()."""
    node_status: Dict[str, str] = {order[0]: "clear"}
    base_title = title or "Path Maintenance (Job Lifecycle)"
    agent_position = order[0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        initial_path = os.path.join(tmp_dir, "frame_000.png")
        render(
            env,
            node_status=dict(node_status),
            agent_position=agent_position,
            save_path=initial_path,
            title=base_title,
        )
        frame_files.append(initial_path)

        for i, event in enumerate(events, start=1):
            touched_node, caption = _apply_event(node_status, event)
            if touched_node is not None:
                agent_position = touched_node
            frame_path = os.path.join(tmp_dir, f"frame_{i:03d}.png")
            render(
                env,
                node_status=dict(node_status),
                agent_position=agent_position,
                save_path=frame_path,
                title=f"{base_title}\n{caption}",
            )
            frame_files.append(frame_path)

        with imageio.get_writer(save_path, mode="I", duration=1000 / fps) as writer:
            for frame_file in frame_files:
                writer.append_data(imageio.imread(frame_file))


class _CanWalk(Protocol):
    def walk(self) -> JobWalkResult: ...


def record_walk(
    env: JobGraphEnvironment, agent: PathMaintenanceAgent
) -> Tuple[JobWalkResult, List[Event]]:
    """Run `agent.walk()` while instrumenting `env`'s `get_job_state`/
    `advance_jobs`/`repair_node` to record every call, in the order it
    actually happened. Same explicit-env-parameter shape as
    graph-topology's record_walk()."""
    events: List[Event] = []
    original_get_state = env.get_job_state
    original_advance = env.advance_jobs
    original_repair = env.repair_node

    def get_state_and_record(node_id: str) -> JobState:
        state = original_get_state(node_id)
        events.append(("arrive", node_id, state))
        return state

    def advance_and_record(satisfied: Set[str]) -> None:
        original_advance(satisfied)
        events.append(("advance",))

    def repair_and_record(node_id: str) -> None:
        original_repair(node_id)
        events.append(("repair", node_id))

    env.get_job_state = get_state_and_record
    env.advance_jobs = advance_and_record
    env.repair_node = repair_and_record
    try:
        result = agent.walk()
    finally:
        del env.get_job_state
        del env.advance_jobs
        del env.repair_node

    return result, events
