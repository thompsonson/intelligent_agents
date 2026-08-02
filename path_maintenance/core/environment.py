from typing import Dict, List, Set

from .domain import CellState, GraphNode, JobNode, JobState


def _validate_requires_graph(nodes: Dict[str, object]) -> None:
    """Shared requires-validation for any node type with a `.requires`
    tuple: unknown-dependency and cycle detection. Used by both
    PathGraphEnvironment (GraphNode) and JobGraphEnvironment (JobNode) -
    an internal reuse within this package, not the same thing as reusing
    task_graph_solver's TaskGraphEnvironment across packages (see both
    classes' docstrings)."""
    for node_id, node in nodes.items():
        for dep in node.requires:
            if dep not in nodes:
                raise ValueError(f"node {node_id!r} requires unknown node {dep!r}")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in nodes}

    def visit(node_id: str, path: List[str]) -> None:
        color[node_id] = GRAY
        for dep in nodes[node_id].requires:
            if color[dep] == GRAY:
                cycle = " -> ".join(path + [dep])
                raise ValueError(f"cycle detected in requires graph: {cycle}")
            if color[dep] == WHITE:
                visit(dep, path + [dep])
        color[node_id] = BLACK

    for node_id in nodes:
        if color[node_id] == WHITE:
            visit(node_id, [node_id])


def _ready_nodes(nodes: Dict[str, object], satisfied: Set[str]) -> List[str]:
    """Shared AND-gating frontier computation for any node type with a
    `.requires` tuple. See _validate_requires_graph's docstring."""
    return [
        node_id
        for node_id, node in nodes.items()
        if node_id not in satisfied and all(dep in satisfied for dep in node.requires)
    ]


class PathGraphEnvironment:
    """An AND-only DAG of nodes, each either OPEN or NEEDS_REPAIR.

    Same requires-validation and ready_nodes() shape as task_graph_solver's
    TaskGraphEnvironment, reused as a pattern rather than imported - no
    retry economics, no probability draws. See
    documentation/path-maintenance/graph-topology/environment_design.md.
    """

    def __init__(self, nodes: Dict[str, GraphNode]):
        _validate_requires_graph(nodes)
        self.nodes = nodes
        self._cell_states: Dict[str, CellState] = {
            node_id: CellState.OPEN for node_id in nodes
        }

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Nodes whose requires are fully contained in `satisfied` and
        haven't themselves been satisfied yet."""
        return _ready_nodes(self.nodes, satisfied)

    def get_node_state(self, node_id: str) -> CellState:
        """Current state of a node.

        Raises:
            ValueError: if `node_id` is not a node in this graph.
        """
        if node_id not in self._cell_states:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        return self._cell_states[node_id]

    def inject_repairs(self, node_ids: List[str], order: List[str]) -> None:
        """One-time, discrete mutation: mark each of `node_ids` NEEDS_REPAIR.

        Restricted to nodes present in `order` so every injected repair is
        guaranteed to be sensed and fixed by an agent walking that order.

        Raises:
            ValueError: if any node is unknown, not present in `order`, or
                already NEEDS_REPAIR.
        """
        for node_id in node_ids:
            if node_id not in self._cell_states:
                raise ValueError(f"{node_id!r} is not a node in this graph")
            if node_id not in order:
                raise ValueError(f"{node_id!r} is not in the given order")
            if self._cell_states[node_id] == CellState.NEEDS_REPAIR:
                raise ValueError(f"{node_id!r} already needs repair")
        for node_id in node_ids:
            self._cell_states[node_id] = CellState.NEEDS_REPAIR

    def repair_node(self, node_id: str) -> None:
        """Deterministic repair: NEEDS_REPAIR -> OPEN. Always succeeds.

        Raises:
            ValueError: if `node_id` is unknown or already OPEN.
        """
        if node_id not in self._cell_states:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        if self._cell_states[node_id] == CellState.OPEN:
            raise ValueError(f"{node_id!r} is already open, nothing to repair")
        self._cell_states[node_id] = CellState.OPEN


class JobGraphEnvironment:
    """An AND-only DAG of JobNodes, each with a PENDING/IN_PROGRESS/
    SUCCEEDED/FAILED lifecycle.

    get_job_state() is a pure sense; advance_jobs() is what moves time
    forward, called by PathMaintenanceAgent.walk()'s wait loop, not by
    scenario setup - see
    documentation/path-maintenance/job-lifecycle/environment_design.md's
    "Resolved: who calls advance_jobs()".
    """

    def __init__(self, nodes: Dict[str, JobNode]):
        _validate_requires_graph(nodes)
        self.nodes = nodes
        self._ticks_elapsed: Dict[str, int] = {node_id: 0 for node_id in nodes}
        self._repaired: set = set()

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Nodes whose requires are fully contained in `satisfied` and
        haven't themselves been satisfied yet."""
        return _ready_nodes(self.nodes, satisfied)

    def get_job_state(self, node_id: str) -> JobState:
        """Current lifecycle state, purely a function of ticks elapsed vs.
        the node's ticks_to_resolve (and whether repair_node() has been
        called) - never mutates anything.

        Raises:
            ValueError: if `node_id` is not a node in this graph.
        """
        if node_id not in self.nodes:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        return self._resolve_state(node_id)

    def _resolve_state(self, node_id: str) -> JobState:
        """Internal, uninstrumentable state computation - repair_node()
        uses this directly rather than calling self.get_job_state(), so
        its own validation check never shows up as an extra recorded
        sense when get_job_state() is instrumented (see
        visualization/job_graph_view.py's record_walk())."""
        if node_id in self._repaired:
            return JobState.SUCCEEDED
        node = self.nodes[node_id]
        elapsed = self._ticks_elapsed[node_id]
        if elapsed >= node.ticks_to_resolve:
            return node.resolves_to
        if elapsed == 0:
            return JobState.PENDING
        return JobState.IN_PROGRESS

    def advance_jobs(self, satisfied: Set[str]) -> None:
        """Increments the tick counter for every ready-and-unresolved node
        - `ready_nodes(satisfied)`, the same AND-gating frontier
        `PathGraphEnvironment` uses. Restricted to ready nodes, not every
        node in the graph: a node whose requires aren't satisfied yet
        can't be "in progress" in any real pipeline (a deploy can't be
        running before the merge that triggers it), and ticking it anyway
        let a downstream node silently resolve during an upstream node's
        wait loop - a real bug caught by test_matches_scenario_md_totals,
        not a hypothetical one. Represents other agents (CI, k8s,
        pre-commit) doing their own work between senses - called by
        PathMaintenanceAgent.walk(), not by scenario setup."""
        for node_id in self.ready_nodes(satisfied):
            node = self.nodes[node_id]
            if self._ticks_elapsed[node_id] < node.ticks_to_resolve:
                self._ticks_elapsed[node_id] += 1

    def repair_node(self, node_id: str) -> None:
        """Deterministic repair of a FAILED node: same no-op-that-always-
        succeeds contract as steps 1-2's repair.

        Raises:
            ValueError: if `node_id` is unknown or not currently FAILED.
        """
        if node_id not in self.nodes:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        if self._resolve_state(node_id) != JobState.FAILED:
            raise ValueError(f"{node_id!r} is not FAILED, nothing to repair")
        self._repaired.add(node_id)
