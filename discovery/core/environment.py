from typing import Dict, Tuple

from .domain import DiscoveryNode


class DiscoveryEnvironment:
    """A graph of DiscoveryNodes, each carrying its own push-direction
    `notifies`. The environment holds the whole graph (it has to, to
    answer queries), but exposes only one query - sense_edges() for a
    single node - and no frontier/enumeration primitive: there is no
    ready_nodes()-equivalent here, because "the frontier" presupposes a
    global view of the graph that this environment specifically
    withholds from the agent. See
    documentation/discovery/environment_design.md.
    """

    def __init__(self, nodes: Dict[str, DiscoveryNode]):
        for node_id, node in nodes.items():
            for target in node.notifies:
                if target not in nodes:
                    raise ValueError(
                        f"node {node_id!r} notifies unknown node {target!r}"
                    )
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

    def get_move_cost(self, from_id: str, to_id: str) -> int:
        """Always 1. Same flat-for-now, concept-for-later precedent as
        MazeEnvironment.get_step_cost()."""
        return 1
