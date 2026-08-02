from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class WalkResult:
    """Result of a PathMaintenanceAgent's walk along a fixed order of nodes.

    Same shape as maze_solver.core.results.WalkResult, generalized from
    grid coordinates to node ids. See
    documentation/path-maintenance/graph-topology/environment_design.md.
    """

    path: List[str]
    repairs_performed: List[str]
    success: bool
