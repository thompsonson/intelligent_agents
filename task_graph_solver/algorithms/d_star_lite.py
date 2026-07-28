from typing import List, Set, Tuple

from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult


class DStarLiteExecutor:
    """Incremental-repair executor: like TopologicalExecutor, but a node that
    reaches FATAL is not necessarily terminal. Each step first senses Driver
    events via `drain_changed_tasks()`; if a previously-FATAL node was fixed,
    it's returned to consideration instead of staying stuck forever - the
    thing a plain topological executor structurally cannot do.

    Scope, matching documentation/task-graph/algorithm_fit.md: this only
    covers breaking a node that hasn't been satisfied yet. Un-satisfying an
    already-PASSed node (transitive invalidation, the way a build system
    invalidates downstream targets) is out of scope here - not decided, not
    needed to validate the break/fix sensing mechanism itself.

    On a strict AND-chain there's no alternate route around a broken node
    the way a maze has other corridors - breaking any node makes everything
    downstream unreachable. What this demonstrates instead is repair
    *locality*: recovering from a fix never re-attempts nodes that were
    already satisfied before the break.
    """

    def __init__(self, env: TaskGraphEnvironment):
        self.env = env
        self.satisfied: Set[str] = set()
        self.fatal: Set[str] = set()
        self.trace: List[Tuple[str, AttemptOutcome]] = []
        self.repairs: List[str] = []

    def step(self) -> bool:
        """Attempt exactly one unit of progress. Returns True if anything
        happened (a sensed fix was repaired, or a node was attempted),
        False if there's nothing left to do."""
        changed = self.env.drain_changed_tasks()
        did_repair = False
        for node_id in changed:
            if node_id in self.fatal:
                self.fatal.discard(node_id)
                self.repairs.append(node_id)
                did_repair = True

        ready = sorted(
            node_id
            for node_id in self.env.ready_nodes(self.satisfied)
            if node_id not in self.fatal
        )
        if not ready:
            return did_repair

        node_id = ready[0]
        outcome = self.env.attempt(node_id)
        self.trace.append((node_id, outcome))

        if outcome == AttemptOutcome.PASS:
            self.satisfied.add(node_id)
        elif outcome == AttemptOutcome.FATAL:
            self.fatal.add(node_id)
        # RETRY: no state change: the next step() will attempt this node
        # again, bounded by its own rmax/r_patience.

        return True

    def run(self, max_steps: int = 1000) -> ExecutionResult:
        all_nodes = set(self.env.nodes.keys())

        for _ in range(max_steps):
            if self.satisfied == all_nodes:
                break
            if not self.step():
                break

        unreachable = all_nodes - self.satisfied - self.fatal
        return ExecutionResult(
            success=(self.satisfied == all_nodes),
            satisfied=set(self.satisfied),
            fatal=set(self.fatal),
            unreachable=unreachable,
            trace=list(self.trace),
        )
