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


class JobState(Enum):
    """Lifecycle state of a job node - step 3's generalization of
    CellState's two values to four. See
    documentation/path-maintenance/job-lifecycle/environment_design.md."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"  # steps 1-2's OPEN
    FAILED = "failed"  # steps 1-2's NEEDS_REPAIR


@dataclass
class JobNode:
    """A node in an AND-only DAG with a lifecycle: resolves to
    `resolves_to` after `ticks_to_resolve` calls to
    JobGraphEnvironment.advance_jobs(). Deliberately no pass_probability/
    rmax/r_patience, same reasoning as GraphNode - deterministic and known,
    resolves_to and ticks_to_resolve are fixed per node, not drawn from a
    distribution."""

    id: str
    requires: Tuple[str, ...] = ()
    ticks_to_resolve: int = 0
    resolves_to: JobState = JobState.SUCCEEDED

    def __post_init__(self) -> None:
        if self.ticks_to_resolve < 0:
            raise ValueError(
                f"ticks_to_resolve must be >= 0 for node {self.id!r}, "
                f"got {self.ticks_to_resolve}"
            )
        if self.resolves_to not in (JobState.SUCCEEDED, JobState.FAILED):
            raise ValueError(
                f"resolves_to must be SUCCEEDED or FAILED for node "
                f"{self.id!r}, got {self.resolves_to}"
            )
