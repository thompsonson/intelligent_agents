from typing import List, Set, Tuple

from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult


class PlanningExecutor:
    """Goal-directed, sense-then-plan executor - see
    documentation/task-graph/goal-directed-planning/environment_design.md.

    Unlike every other executor in this repo (`TopologicalExecutor`,
    `AOStarExecutor`, `DStarLiteExecutor`, `GuardFirstExecutor`), this one
    does not walk the forward `ready_nodes()` frontier at all. It works
    backward from `goal`, recursively, via `_ensure(node_id)`: a node is
    only ever looked at because something already known-necessary needed
    it. Three capabilities fall out of that one recursive function, not
    three separate mechanisms:

    - Goal-directed scope: a true orphan (nothing downstream of it requires
      it) is never a parameter to `_ensure` in the first place - not
      filtered out of a candidate list, never considered at all.
    - Sense-then-plan short-circuiting: `env.check_invariant` (the
      guard-first free sensor) is tried before ever reading a node's
      `requires`. If `goal` itself is already true, nothing upstream is
      ever visited - not checked, not attempted, not even looked at.
    - AND-short-circuit: `node.requires` is evaluated in sorted order via
      `all(...)`, which stops at the first failing dependency. This is
      always sound, never a missed opportunity - once one AND-dependency
      is unreachable, the join can't succeed regardless of the others, so
      the remaining siblings are exactly as irrelevant to the goal as a
      true orphan is, and are left equally unvisited (absent from every
      result set, not recorded as `unreachable` - that label is reserved
      for a node that WAS looked at and found blocked).
    - OR-group pruning: the same capability `AOStarExecutor` has, arising
      here from top-down recursion instead of forward-frontier filtering -
      the first member to satisfy a group short-circuits the rest, which
      are marked `not_needed` without ever being attempted.

    Deliberately not a revision of `AOStarExecutor` - see the cross-
    reference note on that class. `AOStarExecutor`'s forward-frontier
    behavior (visiting every ready node, including orphans) stays exactly
    as it is; this is a separate executor for a separate strategy.
    """

    def __init__(self, env: TaskGraphEnvironment):
        self.env = env
        self.satisfied: Set[str] = set()
        self.fatal: Set[str] = set()
        self.unreachable: Set[str] = set()
        self.not_needed: Set[str] = set()
        self.free_checks: Set[str] = set()
        self.trace: List[Tuple[str, AttemptOutcome]] = []
        self._resolved: Set[str] = set()

    def _ensure(self, node_id: str) -> bool:
        if node_id in self.env.groups:
            return self._ensure_group(node_id)

        if node_id in self._resolved:
            return node_id in self.satisfied

        if self.env.check_invariant(node_id):
            self.satisfied.add(node_id)
            self.free_checks.add(node_id)
            self._resolved.add(node_id)
            return True

        node = self.env.nodes[node_id]
        if not all(self._ensure(dep) for dep in sorted(node.requires)):
            self.unreachable.add(node_id)
            self._resolved.add(node_id)
            return False

        outcome = AttemptOutcome.RETRY
        while outcome == AttemptOutcome.RETRY:
            outcome = self.env.attempt(node_id)
            self.trace.append((node_id, outcome))

        self._resolved.add(node_id)
        if outcome == AttemptOutcome.PASS:
            self.satisfied.add(node_id)
            return True
        self.fatal.add(node_id)
        return False

    def _ensure_group(self, group_id: str) -> bool:
        group = self.env.groups[group_id]
        satisfied_group = False
        for member in sorted(group.members):
            if satisfied_group:
                if member not in self._resolved:
                    self.not_needed.add(member)
                continue
            if self._ensure(member):
                satisfied_group = True
        return satisfied_group

    def run(self) -> ExecutionResult:
        if self.env.goal is not None:
            self._ensure(self.env.goal)
        else:
            for node_id in self.env.nodes:
                self._ensure(node_id)

        return ExecutionResult(
            success=self.env.is_goal_reached(self.satisfied),
            satisfied=set(self.satisfied),
            fatal=set(self.fatal),
            unreachable=set(self.unreachable),
            trace=list(self.trace),
            not_needed=set(self.not_needed),
            free_checks=set(self.free_checks),
        )
