import random
from typing import Dict, List, Optional, Set, Tuple

from .config import TaskGraphConfig
from .domain import AttemptOutcome, GroupNode, TaskNode


class TaskGraphEnvironment:
    """Simulated DAG of guarded tasks with AND-only `requires` edges, plus
    optional OR-groups and an explicit goal.

    No real commands run - every node's outcome is drawn from its configured
    `pass_probability`. See documentation/task-graph/environment_design.md
    and documentation/task-graph/or-groups/environment_design.md.

    Mirrors MazeEnvironment's separation of concerns: the environment knows
    node validity/cost/readiness, but does not track which nodes an agent has
    already satisfied - that's the algorithm's job, the same way MazeEnvironment
    doesn't track a search algorithm's visited set.
    """

    def __init__(
        self,
        nodes: Dict[str, TaskNode],
        config: TaskGraphConfig,
        groups: Tuple[GroupNode, ...] = (),
        goal: Optional[str] = None,
    ):
        self._validate_graph(nodes, groups, goal)

        self.nodes = nodes
        self.groups: Dict[str, GroupNode] = {group.id: group for group in groups}
        self.goal = goal
        self.config = config
        self._rng = random.Random(config.seed)
        self._attempts_made: Dict[str, int] = {node_id: 0 for node_id in nodes}
        self._consecutive_failures: Dict[str, int] = {node_id: 0 for node_id in nodes}
        self._broken: Set[str] = set()
        self._changed_since_drain: Set[str] = set()

    @staticmethod
    def _validate_graph(
        nodes: Dict[str, TaskNode],
        groups: Tuple[GroupNode, ...],
        goal: Optional[str],
    ) -> None:
        groups_by_id: Dict[str, GroupNode] = {}
        for group in groups:
            if group.id in nodes:
                raise ValueError(
                    f"group id {group.id!r} collides with an existing node id"
                )
            groups_by_id[group.id] = group

        for group in groups:
            for member in group.members:
                if member not in nodes:
                    raise ValueError(
                        f"group {group.id!r} references unknown member {member!r}"
                    )

        for node_id, node in nodes.items():
            for dep in node.requires:
                if dep not in nodes and dep not in groups_by_id:
                    raise ValueError(f"node {node_id!r} requires unknown node {dep!r}")

        if goal is not None and goal not in nodes:
            raise ValueError(f"goal references unknown node {goal!r}")

        # DFS cycle detection over the requires graph, expanding any group id
        # dependency into edges to each of its members - a cycle through a
        # group member still needs to be caught even though the group id
        # itself is never colored.
        def neighbors(node_id: str) -> List[str]:
            result = []
            for dep in nodes[node_id].requires:
                if dep in groups_by_id:
                    result.extend(groups_by_id[dep].members)
                else:
                    result.append(dep)
            return result

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in nodes}

        def visit(node_id: str, path: List[str]) -> None:
            color[node_id] = GRAY
            for dep in neighbors(node_id):
                if color[dep] == GRAY:
                    cycle = " -> ".join(path + [dep])
                    raise ValueError(f"cycle detected in requires graph: {cycle}")
                if color[dep] == WHITE:
                    visit(dep, path + [dep])
            color[node_id] = BLACK

        for node_id in nodes:
            if color[node_id] == WHITE:
                visit(node_id, [node_id])

    def _is_satisfied(self, dep_id: str, satisfied: Set[str]) -> bool:
        """Whether `dep_id` - a plain node id or a GroupNode id - counts as
        satisfied. A group is satisfied the instant any one of its members
        is; this is the single check point that lets ready_nodes() handle
        AND and OR dependencies through the same code path."""
        if dep_id in self.groups:
            return any(member in satisfied for member in self.groups[dep_id].members)
        return dep_id in satisfied

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        """Nodes whose `requires` are fully contained in `satisfied` and
        haven't themselves been satisfied yet - the frontier of things that
        could be attempted next. Group ids never appear here - a GroupNode
        has no Guard, so it is never itself attempted."""
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node_id not in satisfied
            and all(self._is_satisfied(dep, satisfied) for dep in node.requires)
        ]

    def is_goal_reached(self, satisfied: Set[str]) -> bool:
        """True once the configured `goal` node is satisfied. With no goal
        configured, falls back to "every node satisfied" - the behavior
        every scenario built before this existed (disk_check_lite,
        repair_packages_lite, pr_merge_lite) already relies on."""
        if self.goal is not None:
            return self.goal in satisfied
        return all(node_id in satisfied for node_id in self.nodes)

    def check_invariant(self, node_id: str) -> bool:
        """A free sensor: draws from `node_id`'s `invariant_pass_probability`
        without consuming any retry budget - the toy equivalent of a
        live-sensing Guard checked before any generation happens. See
        documentation/task-graph/guard-first/environment_design.md. A
        broken node (see break_task) never reports itself as already
        satisfied, the same way it can never PASS via attempt()."""
        if node_id in self._broken:
            return False
        return self._rng.random() < self.nodes[node_id].invariant_pass_probability

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

        if (
            node.r_patience is not None
            and self._consecutive_failures[node_id] >= node.r_patience
        ):
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
