from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, Tuple


class AttemptOutcome(Enum):
    """Result of one simulated attempt at a TaskNode."""

    PASS = "pass"
    RETRY = "retry"
    FATAL = "fatal"


@dataclass
class TaskNode:
    """A guarded task: one node in a task graph.

    Modeled on a DS-PDDL Action Pair (Guard + Generator + Effector), simplified
    to what a simulation needs. `kind` and `retry_flavor` are independent
    fields on purpose: conflating them (e.g. assuming "acting" always means
    "repair" flavor) was the mistake documentation/lrta/beyond_the_maze.md had
    to correct once already, when a pure local generation step turned out to
    be neither straightforwardly sensing nor acting in the real system's sense.

    Attributes:
        id: Unique identifier within a TaskGraphEnvironment.
        kind: "sensing" (idempotent, read-only) or "acting" (world-mutating).
        retry_flavor: What a retry at this node actually means - "sensing"
            (absorbing transient infra flakiness), "generation" (an LLM
            output failed local format validation), or "repair" (a real
            world-mutating action was attempted and failed). Only "repair"
            retries are real learnable cost for an LRTA*-style agent.
        pass_probability: Per-attempt chance of a Guard pass.
        rmax: Total attempt budget before this node is declared FATAL.
        r_patience: Consecutive-failure threshold that escalates to FATAL
            before rmax is exhausted. Must be strictly less than rmax,
            mirroring the invariant found in atomicguard's own source
            (application/workflow.py, "Extension 09").
        requires: AND-dependencies - every id here must be satisfied before
            this node is ready to attempt. There is no OR-equivalent.
    """

    id: str
    kind: Literal["sensing", "acting"]
    retry_flavor: Literal["sensing", "generation", "repair"]
    pass_probability: float
    rmax: int
    r_patience: Optional[int] = None
    requires: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.rmax < 1:
            raise ValueError(f"rmax must be >= 1 for node {self.id!r}, got {self.rmax}")
        if self.r_patience is not None:
            if self.r_patience < 1:
                raise ValueError(
                    f"r_patience must be >= 1 for node {self.id!r}, "
                    f"got {self.r_patience}"
                )
            if self.r_patience >= self.rmax:
                raise ValueError(
                    f"r_patience ({self.r_patience}) must be < rmax ({self.rmax}) "
                    f"for node {self.id!r}"
                )
        if not (0.0 <= self.pass_probability <= 1.0):
            raise ValueError(
                f"pass_probability must be in [0, 1] for node {self.id!r}, "
                f"got {self.pass_probability}"
            )


@dataclass
class GroupNode:
    """An OR-composition over existing TaskNodes: satisfied the instant any
    one of `members` is satisfied. Not attempted directly - there is no
    Guard to run, no pass_probability, no retry budget to exhaust.
    Downstream nodes list the group's id in their own `requires` tuple
    exactly as they would a plain node id; the AND-gating check treats a
    group id and a node id identically from the outside.

    See documentation/task-graph/or-groups/environment_design.md.

    Attributes:
        id: Unique identifier, must not collide with any TaskNode id.
        members: ids of TaskNodes that satisfy this group - any one is
            enough.
    """

    id: str
    members: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError(f"GroupNode {self.id!r} must have at least one member")
