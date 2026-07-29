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
        not_needed: Losing OR-siblings that were never attempted because a
            different member of their group already satisfied it before
            this one became relevant - distinct from `unreachable` (which
            is blocked by a fatal dependency) and from a true orphan (which
            was simply never on any path to the goal). See
            documentation/task-graph/or-groups/environment_design.md.
        free_checks: Nodes satisfied by a free `check_invariant()` sensor
            rather than a paid `attempt()` repair - distinct from `satisfied`
            members reached via `trace` (a paid attempt occurred) and from
            `not_needed` (a *different* node did the work; here the same
            node's own invariant already held). See
            documentation/task-graph/guard-first/environment_design.md.
    """

    success: bool
    satisfied: Set[str]
    fatal: Set[str]
    unreachable: Set[str]
    trace: List[Tuple[str, AttemptOutcome]] = field(default_factory=list)
    execution_time: float = 0.0
    not_needed: Set[str] = field(default_factory=set)
    free_checks: Set[str] = field(default_factory=set)
