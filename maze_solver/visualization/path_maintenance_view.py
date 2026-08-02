import os
import tempfile
from typing import List, Optional, Protocol, Set, Tuple, Union

import imageio.v2 as imageio
import matplotlib.pyplot as plt

from ..agents.path_maintenance import PathMaintenanceAgent
from ..core.environment import CellState, MazeEnvironment
from ..core.results import WalkResult

# An event is one of:
#   ("arrive", cell, CellState) - env.get_cell_state(cell) was called and returned
#   ("repair", cell)            - env.repair_cell(cell) was called
# There is no separate "move" event: PathMaintenanceAgent.walk() only ever
# calls these two environment methods (see agents/path_maintenance.py), so
# "arriving at a cell" and "sensing its state" are the same event, the same
# way task_graph_solver/visualization/graph_view.py's Event list only
# contains calls the code under animation actually makes.
Event = Union[Tuple[str, Tuple[int, int], CellState], Tuple[str, Tuple[int, int]]]

CELL_COLORS = {
    "wall": "black",
    "off_path": "white",
    "future": "palegreen",  # on the belief path, not yet walked
    "clear": "limegreen",  # walked, was always OPEN - never needed repair
    "repaired": "darkgreen",  # walked, was NEEDS_REPAIR, then fixed
    "needs_repair": "red",  # sensed and not yet repaired
    "start": "blue",
    "goal": "purple",
}
AGENT_MARKER_COLOR = "orange"


def _plot_maze(
    ax,
    env: MazeEnvironment,
    path: List[Tuple[int, int]],
    walked: Set[Tuple[int, int]],
    needs_repair: Set[Tuple[int, int]],
    repaired: Set[Tuple[int, int]],
    agent_position: Optional[Tuple[int, int]],
    title: str,
) -> None:
    """Draw the grid: cell color encodes cell state, a marker overlay (not a
    cell color) encodes where the agent currently is - keeping "cell state"
    and "agent position" visually separate, the same separation
    environment_design.md draws conceptually between env and agent."""
    rows, cols = env.grid.shape

    codes = {name: i for i, name in enumerate(CELL_COLORS)}
    viz_grid = [
        [
            codes["wall"] if env.grid[r, c] == 1 else codes["off_path"]
            for c in range(cols)
        ]
        for r in range(rows)
    ]

    for cell in path:
        r, c = cell
        if cell in needs_repair:
            viz_grid[r][c] = codes["needs_repair"]
        elif cell in repaired:
            viz_grid[r][c] = codes["repaired"]
        elif cell in walked:
            viz_grid[r][c] = codes["clear"]
        else:
            viz_grid[r][c] = codes["future"]

    sr, sc = env.start
    gr, gc = env.end
    viz_grid[sr][sc] = codes["start"]
    viz_grid[gr][gc] = codes["goal"]

    cmap = plt.cm.colors.ListedColormap(list(CELL_COLORS.values()))
    bounds = [i - 0.5 for i in range(len(CELL_COLORS) + 1)]
    norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)

    ax.imshow(viz_grid, cmap=cmap, norm=norm)
    if agent_position is not None:
        ax.plot(
            agent_position[1],
            agent_position[0],
            marker="*",
            markersize=18,
            color=AGENT_MARKER_COLOR,
            markeredgecolor="black",
        )
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color=color, label=name.replace("_", " "))
        for name, color in CELL_COLORS.items()
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


def render(
    env: MazeEnvironment,
    path: List[Tuple[int, int]],
    walked: Optional[Set[Tuple[int, int]]] = None,
    needs_repair: Optional[Set[Tuple[int, int]]] = None,
    repaired: Optional[Set[Tuple[int, int]]] = None,
    agent_position: Optional[Tuple[int, int]] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Render one frame: the maze grid, the belief-state path, and the
    agent's current position, color-coded by cell state."""
    fig, ax = plt.subplots(figsize=(8, 8))
    _plot_maze(
        ax,
        env,
        path,
        walked or set(),
        needs_repair or set(),
        repaired or set(),
        agent_position,
        title or "Path Maintenance",
    )
    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def _apply_event(
    walked: set, needs_repair: set, repaired: set, event: Event
) -> Tuple[Tuple[int, int], str]:
    kind = event[0]
    if kind == "arrive":
        _, cell, state = event
        walked.add(cell)
        if state == CellState.NEEDS_REPAIR:
            needs_repair.add(cell)
        return cell, f"arrive {cell} → {state.value}"
    if kind == "repair":
        _, cell = event
        needs_repair.discard(cell)
        repaired.add(cell)
        return cell, f"repair_cell({cell})"
    raise ValueError(f"unknown event kind: {kind!r}")


def animate_walk(
    env: MazeEnvironment,
    path: List[Tuple[int, int]],
    events: List[Event],
    save_path: str,
    fps: float = 1.0,
    title: Optional[str] = None,
) -> None:
    """Render one frame per event and combine into a GIF - the
    path-maintenance analogue of graph_view.animate_events(), showing the
    walk unfold frame by frame rather than a single static end state."""
    walked: Set[Tuple[int, int]] = set()
    needs_repair: Set[Tuple[int, int]] = set()
    repaired: Set[Tuple[int, int]] = set()
    base_title = title or "Path Maintenance"
    agent_position = path[0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        initial_path = os.path.join(tmp_dir, "frame_000.png")
        render(
            env,
            path,
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
                path,
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
    env: MazeEnvironment, agent: PathMaintenanceAgent
) -> Tuple[WalkResult, List[Event]]:
    """Run `agent.walk()` while instrumenting `env`'s
    `get_cell_state`/`repair_cell` to record every call, in the order it
    actually happened, as an Event list `animate_walk` can consume directly.

    Mirrors task_graph_solver/visualization/graph_view.py's record_events()
    (same explicit-env-parameter shape, not reached into the agent): the
    event list can't be reconstructed after the fact from WalkResult alone
    (WalkResult only has repairs_performed, not the full sense sequence), so
    it's captured live instead. `env` must be the same environment `agent`
    was constructed with."""
    events: List[Event] = []
    original_get_cell_state = env.get_cell_state
    original_repair_cell = env.repair_cell

    def get_cell_state_and_record(cell: Tuple[int, int]) -> CellState:
        state = original_get_cell_state(cell)
        events.append(("arrive", cell, state))
        return state

    def repair_cell_and_record(cell: Tuple[int, int]) -> None:
        original_repair_cell(cell)
        events.append(("repair", cell))

    env.get_cell_state = get_cell_state_and_record
    env.repair_cell = repair_cell_and_record
    try:
        result = agent.walk()
    finally:
        del env.get_cell_state
        del env.repair_cell

    return result, events
