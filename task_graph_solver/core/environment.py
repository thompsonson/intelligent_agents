import random
from typing import Dict, List, Set

from .config import TaskGraphConfig
from .domain import AttemptOutcome, TaskNode


class TaskGraphEnvironment:
    """Simulated DAG of guarded tasks with AND-only `requires` edges.

    No real commands run - every node's outcome is drawn from its configured
    `pass_probability`. See documentation/task-graph/environment_design.md.

    Mirrors MazeEnvironment's separation of concerns: the environment knows
    node validity/cost/readiness, but does not track which nodes an agent has
    already satisfied - that's the algorithm's job, the same way MazeEnvironment
    doesn't track a search algorithm's visited set.
    """

    def __init__(self, nodes: Dict[str, TaskNode], config: TaskGraphConfig):
        self.nodes = nodes
        self.config = config
        self._rng = random.Random(config.seed)
        self._attempts_made: Dict[str, int] = {node_id: 0 for node_id in nodes}
        self._consecutive_failures: Dict[str, int] = {node_id: 0 for node_id in nodes}
        self._broken: Set[str] = set()
        self._changed_since_drain: Set[str] = set()

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Nodes whose `requires` are fully contained in `satisfied` and
        haven't themselves been satisfied yet - the frontier of things that
        could be attempted next."""
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node_id not in satisfied
            and all(dep in satisfied for dep in node.requires)
        ]

    def attempt(self, node_id: str) -> AttemptOutcome:
        """One simulated attempt at `node_id`. Consumes one unit of retry
        budget, unless the node is currently broken (see break_task) - a
        Driver-forced failure is an exogenous world change, not a
        repair-attempt retry, so it doesn't consume budget or pollute the
        retry-cost signal an LRTA*-style learner would read."""
        node = self.nodes[node_id]

        if node_id in self._broken:
            return AttemptOutcome.FATAL

        if self._attempts_made[node_id] >= node.rmax:
            return AttemptOutcome.FATAL

        self._attempts_made[node_id] += 1

        if self._rng.random() < node.pass_probability:
            self._consecutive_failures[node_id] = 0
            return AttemptOutcome.PASS

        self._consecutive_failures[node_id] += 1

        if node.r_patience is not None and self._consecutive_failures[node_id] >= node.r_patience:
            return AttemptOutcome.FATAL

        if self._attempts_made[node_id] >= node.rmax:
            return AttemptOutcome.FATAL

        return AttemptOutcome.RETRY

    def retries_spent(self, node_id: str) -> int:
        """How many attempts have been made at `node_id` so far. Does not
        include Driver-forced break_task failures."""
        return self._attempts_made[node_id]

    def break_task(self, node_id: str) -> None:
        """Driver hook: force a task to fail permanently, regardless of its
        configured pass_probability, until fix_task() is called. Mirrors
        MazeEnvironment's break_edge/fix_edge pattern from the D* Lite design."""
        if node_id not in self._broken:
            self._broken.add(node_id)
            self._changed_since_drain.add(node_id)

    def fix_task(self, node_id: str) -> None:
        """Inverse of break_task."""
        if node_id in self._broken:
            self._broken.discard(node_id)
            self._changed_since_drain.add(node_id)

    def drain_changed_tasks(self) -> List[str]:
        """Return and clear the list of tasks whose broken/fixed state has
        changed since this was last called - the 'sense' step an incremental
        repair agent (D* Lite) polls once per move, mirroring MazeEnvironment's
        drain_changed_edges()."""
        changed = sorted(self._changed_since_drain)
        self._changed_since_drain.clear()
        return changed
