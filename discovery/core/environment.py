from typing import Dict, List, Tuple

from .domain import DiscoveryNode


def _validate_requires_graph(nodes: Dict[str, DiscoveryNode]) -> None:
    """Unknown-target and cycle detection over `.requires` only - mirrors
    path_maintenance/core/environment.py's _validate_requires_graph() as a
    pattern, not imported (cross-package, same precedent every prior step
    in this repo has followed). Deliberately does not touch `.notifies` -
    a notifies-graph is allowed to have cycles (see __init__ below);
    a requires-graph isn't, since a requires-cycle can never clear
    regardless of exploration order. See and-joins/environment_design.md's
    "The reachability constraint"."""
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


class DiscoveryEnvironment:
    """A graph of DiscoveryNodes, each carrying both a push-direction
    `notifies` and a pull-direction `requires`. The environment holds the
    whole graph (it has to, to answer queries), but exposes only sense
    queries - sense_edges()/sense_requires() for a single node - and no
    frontier/enumeration primitive: there is no ready_nodes()-equivalent
    here, because "the frontier" presupposes a global view of the graph
    that this environment specifically withholds from the agent. See
    documentation/discovery/environment_design.md and
    documentation/discovery/and-joins/environment_design.md.
    """

    def __init__(self, nodes: Dict[str, DiscoveryNode]):
        for node_id, node in nodes.items():
            for target in node.notifies:
                if target not in nodes:
                    raise ValueError(
                        f"node {node_id!r} notifies unknown node {target!r}"
                    )
        _validate_requires_graph(nodes)
        self.nodes = nodes

    def sense_edges(self, node_id: str) -> Tuple[str, ...]:
        """The queried node's own notifies. Raises only if node_id isn't
        a real node anywhere in the graph - no arrival check, since the
        environment tracks no position at all. See environment_design.md's
        "Resolved: arrival gates querying, but the environment doesn't
        enforce it".

        Raises:
            ValueError: if `node_id` is not a node in this graph.
        """
        if node_id not in self.nodes:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        return self.nodes[node_id].notifies

    def sense_requires(self, node_id: str) -> Tuple[str, ...]:
        """The queried node's own requires. Same no-arrival-check contract
        as sense_edges() - see and-joins/environment_design.md's "Sensing:
        two queries, not one".

        Raises:
            ValueError: if `node_id` is not a node in this graph.
        """
        if node_id not in self.nodes:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        return self.nodes[node_id].requires

    def get_move_cost(self, from_id: str, to_id: str) -> int:
        """Always 1. Same flat-for-now, concept-for-later precedent as
        MazeEnvironment.get_step_cost(). Not yet consumed by DiscoveryAgent
        or the visualization - DiscoveryWalkResult has no cost field in
        this step; the method exists so a later step can vary the number
        without changing the call site."""
        return 1
