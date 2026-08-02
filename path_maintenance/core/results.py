from dataclasses import dataclass
from typing import Dict, List


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


@dataclass(frozen=True)
class JobWalkResult:
    """Result of a job-lifecycle-aware walk. New type, not a modification
    of WalkResult - see
    documentation/path-maintenance/job-lifecycle/environment_design.md.
    """

    path: List[str]
    repairs_performed: List[str]
    senses_performed: Dict[str, int]
    success: bool
