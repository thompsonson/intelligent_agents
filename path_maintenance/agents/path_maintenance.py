from typing import List

from ..core.environment import CellState, PathGraphEnvironment
from ..core.results import WalkResult


class PathMaintenanceAgent:
    """Walks a fixed topological order over an AND-DAG, repairing nodes
    found NEEDS_REPAIR.

    Identical in shape to maze_solver's PathMaintenanceAgent - never
    recomputes or deviates from `order` - the only change is the domain
    type of one element, from a grid coordinate to a node id. See
    documentation/path-maintenance/graph-topology/environment_design.md
    and algorithm_fit.md.
    """

    def __init__(self, environment: PathGraphEnvironment, order: List[str]):
        self._environment = environment
        self._order = order

    def walk(self) -> WalkResult:
        repairs_performed = []
        for node_id in self._order[1:]:
            if self._environment.get_node_state(node_id) == CellState.NEEDS_REPAIR:
                self._environment.repair_node(node_id)
                repairs_performed.append(node_id)
        return WalkResult(
            path=self._order, repairs_performed=repairs_performed, success=True
        )
