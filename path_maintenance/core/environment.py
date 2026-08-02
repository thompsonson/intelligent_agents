from typing import Dict, List, Set

from .domain import CellState, GraphNode


class PathGraphEnvironment:
    """An AND-only DAG of nodes, each either OPEN or NEEDS_REPAIR.

    Same requires-validation and ready_nodes() shape as task_graph_solver's
    TaskGraphEnvironment, reused as a pattern rather than imported - no
    retry economics, no probability draws. See
    documentation/path-maintenance/graph-topology/environment_design.md.
    """

    def __init__(self, nodes: Dict[str, GraphNode]):
        self._validate_graph(nodes)
        self.nodes = nodes
        self._cell_states: Dict[str, CellState] = {
            node_id: CellState.OPEN for node_id in nodes
        }

    @staticmethod
    def _validate_graph(nodes: Dict[str, GraphNode]) -> None:
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

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Nodes whose requires are fully contained in `satisfied` and
        haven't themselves been satisfied yet."""
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node_id not in satisfied
            and all(dep in satisfied for dep in node.requires)
        ]

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
