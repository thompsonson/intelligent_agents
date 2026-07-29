import os
import tempfile
from typing import List, Optional, Protocol, Tuple, Union

import matplotlib

matplotlib.use("Agg")  # headless-safe: exercised by pytest, not only notebooks
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import networkx as nx

from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult

# An animation event is one of:
#   ("attempt", node_id, AttemptOutcome)  - env.attempt() was called and resolved
#   ("check", node_id, bool)              - env.check_invariant() was called
#   ("break", node_id)                    - Driver called env.break_task()
#   ("fix", node_id)                      - Driver called env.fix_task()
# `trace` alone (as produced by every executor) only carries "attempt" events -
# Driver break/fix calls happen *between* attempts and have no entry there, and
# check_invariant() calls (GuardFirstExecutor, PlanningExecutor) don't appear
# in `trace` at all (it's attempts-only, by design - see results.py). A caller
# narrating any of these needs its own event list alongside execution -
# record_events(), below, builds one automatically by instrumenting the
# environment; D* Lite's break/fix story still needs to be built by hand
# (see task_graph_solver/tests/test_graph_view.py for an example).
Event = Union[Tuple[str, str, AttemptOutcome], Tuple[str, str, bool], Tuple[str, str]]

# Requires networkx and matplotlib - not otherwise needed by task_graph_solver,
# same as maze_solver's dashboards, which assume these are installed rather
# than declaring them in a formal dependency file (this repo has none).

STATUS_COLORS = {
    "satisfied": "#4CAF50",  # green - a paid attempt() passed
    "free_check": "#26C6DA",  # cyan - satisfied via a free check_invariant(),
    # no repair ever paid for - see documentation/task-graph/guard-first/
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
    if node_id in result.free_checks:
        return "free_check"
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


def _apply_event(satisfied: set, fatal: set, free_checks: set, event: Event) -> str:
    kind = event[0]
    if kind == "attempt":
        _, node_id, outcome = event
        if outcome == AttemptOutcome.PASS:
            satisfied.add(node_id)
        elif outcome == AttemptOutcome.FATAL:
            fatal.add(node_id)
        return f"attempt {node_id} → {outcome.value}"
    if kind == "check":
        _, node_id, passed = event
        if passed:
            satisfied.add(node_id)
            free_checks.add(node_id)
        return f"check_invariant({node_id}) → {'true' if passed else 'false'}"
    if kind == "break":
        _, node_id = event
        return f"Driver breaks {node_id}"
    if kind == "fix":
        _, node_id = event
        fatal.discard(node_id)  # repaired: no longer terminal, can be re-attempted
        return f"Driver fixes {node_id}"
    raise ValueError(f"unknown event kind: {kind!r}")


def _blocked_by_fatal_ancestor(
    node_id: str, env: TaskGraphEnvironment, fatal: set
) -> bool:
    """True if any transitive dependency of node_id is in `fatal`. Used to
    tell "not yet attempted, but still perfectly reachable" (pending, white)
    apart from "genuinely blocked" (unreachable, gray) mid-run - a plain
    `all_nodes - satisfied - fatal` over-eagerly marks every not-yet-resolved
    node as unreachable, which is only correct once an algorithm has
    finished and decided nothing more can change (ExecutionResult's own
    unreachable field), not at an arbitrary intermediate frame.

    A `requires` entry naming a GroupNode id is expanded to its members, but
    NOT with plain-AND semantics: a group is blocked only once *every*
    member is fatal or itself blocked - the inverse-of-AND rule
    documentation/task-graph/or-groups/environment_design.md establishes for
    groups. A single fatal variant among several never blocks anything on
    its own. Memoized per call (`memo`) since the underlying graph is
    guaranteed acyclic (even through group members - validated at
    TaskGraphEnvironment construction), so each dependency's blocked-ness is
    a pure function of `fatal` safely computed once, not per path."""
    memo: dict = {}

    def is_blocked(dep_id: str) -> bool:
        if dep_id in memo:
            return memo[dep_id]
        memo[dep_id] = (
            False  # defensive: breaks re-entrancy if ever revisited mid-computation
        )
        if dep_id in env.groups:
            result = all(
                member in fatal or is_blocked(member)
                for member in env.groups[dep_id].members
            )
        elif dep_id in fatal:
            result = True
        else:
            result = any(is_blocked(dep) for dep in env.nodes[dep_id].requires)
        memo[dep_id] = result
        return result

    return any(is_blocked(dep) for dep in env.nodes[node_id].requires)


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
    free_checks: set = set()
    base_title = title or "Task Graph"

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_files = []

        initial_path = os.path.join(tmp_dir, "frame_000.png")
        render(env, result=None, save_path=initial_path, title=base_title)
        frame_files.append(initial_path)

        for i, event in enumerate(events, start=1):
            caption = _apply_event(satisfied, fatal, free_checks, event)
            unreachable = {
                n
                for n in all_nodes - satisfied - fatal
                if _blocked_by_fatal_ancestor(n, env, fatal)
            }
            snapshot = ExecutionResult(
                success=(satisfied == all_nodes),
                satisfied=set(satisfied),
                fatal=set(fatal),
                unreachable=unreachable,
                trace=[],
                free_checks=set(free_checks),
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


class _RunsToCompletion(Protocol):
    def run(self) -> ExecutionResult: ...


def record_events(
    env: TaskGraphEnvironment, executor: "_RunsToCompletion"
) -> Tuple[ExecutionResult, List[Event]]:
    """Run `executor.run()` while instrumenting `env.check_invariant` and
    `env.attempt` to record every call, in the order it actually happened,
    as an Event list `animate_events` can consume directly.

    Needed for GuardFirstExecutor/PlanningExecutor: their free checks never
    appear in `.trace` (attempts only, see results.py's docstring), and the
    interleaving between checks and attempts can't be reconstructed after
    the fact from the final ExecutionResult alone - the same reason D* Lite's
    break/fix events have to be recorded by hand rather than derived
    afterward (see test_graph_view.py's TestAnimateEvents for that pattern).
    """
    events: List[Event] = []
    original_check = env.check_invariant
    original_attempt = env.attempt

    def check_and_record(node_id: str) -> bool:
        passed = original_check(node_id)
        events.append(("check", node_id, passed))
        return passed

    def attempt_and_record(node_id: str) -> AttemptOutcome:
        outcome = original_attempt(node_id)
        events.append(("attempt", node_id, outcome))
        return outcome

    env.check_invariant = check_and_record
    env.attempt = attempt_and_record
    try:
        result = executor.run()
    finally:
        del env.check_invariant
        del env.attempt

    return result, events
