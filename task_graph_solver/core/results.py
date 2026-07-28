from dataclasses import dataclass, field
from typing import List, Set, Tuple

from .domain import AttemptOutcome


@dataclass
class ExecutionResult:
    """Result of running an algorithm over a TaskGraphEnvironment to completion.

    Attributes:
        success: True only if every node in the graph ended up satisfied.
        satisfied: Nodes that reached PASS.
        fatal: Nodes that reached FATAL (rmax exhausted, r_patience escalation,
            or a Driver-forced break).
        unreachable: Nodes that never became ready because at least one of
            their `requires` ended up in `fatal` - distinct from `fatal`
            itself, since these were never attempted at all.
        trace: Ordered (node_id, outcome) pairs for every attempt made,
            across every node - the execution history.
        execution_time: Wall-clock seconds, set by the caller (mirrors
            SearchResult's timing convention in maze_solver).
    """

    success: bool
    satisfied: Set[str]
    fatal: Set[str]
    unreachable: Set[str]
    trace: List[Tuple[str, AttemptOutcome]] = field(default_factory=list)
    execution_time: float = 0.0
