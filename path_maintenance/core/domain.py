from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class CellState(Enum):
    """State of a node: the same two values maze_solver.core.environment's
    CellState carries forward unchanged from step 1 - see
    documentation/path-maintenance/graph-topology/environment_design.md.
    Redefined here rather than imported so this package stays independent
    of maze_solver, the same way task_graph_solver is."""

    OPEN = "open"
    NEEDS_REPAIR = "needs_repair"


@dataclass
class GraphNode:
    """A node in an AND-only DAG. Deliberately no pass_probability/rmax/
    r_patience - this step is deterministic and known, there is no retry
    budget to track. See graph-topology/environment_design.md."""

    id: str
    requires: Tuple[str, ...] = ()
