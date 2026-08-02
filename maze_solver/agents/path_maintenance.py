from typing import List, Tuple

from ..core.environment import CellState, MazeEnvironment
from ..core.results import WalkResult


class PathMaintenanceAgent:
    """Walks a fixed belief-state path, repairing cells found NEEDS_REPAIR.

    Never recomputes or deviates from `path` - see
    documentation/path-maintenance/environment_design.md.
    """

    def __init__(self, environment: MazeEnvironment, path: List[Tuple[int, int]]):
        self._environment = environment
        self._path = path

    def walk(self) -> WalkResult:
        repairs_performed = []
        for cell in self._path[1:]:
            if self._environment.get_cell_state(cell) == CellState.NEEDS_REPAIR:
                self._environment.repair_cell(cell)
                repairs_performed.append(cell)
        return WalkResult(
            path=self._path, repairs_performed=repairs_performed, success=True
        )
