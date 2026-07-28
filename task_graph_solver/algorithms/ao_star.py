from typing import Dict, List, Set, Tuple

from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult


class AOStarExecutor:
    """AND-OR graph search restricted to this environment's AND-only
    `requires` edges - see search_algorithms/ao_star.md. No scenario built
    on this environment has an OR-node, so only the AND-composition half is
    implemented here.

    What TopologicalExecutor already gets right, unchanged here: AND-gating
    via `ready_nodes()`, and unreachable-if-any-required-child-is-fatal via
    set difference. Node selection among ready nodes is sorted-by-id, the
    same as TopologicalExecutor - not a cost-guided "best-first" choice,
    because no node has a usable cost estimate before it's been attempted
    (see `h`, below). Presenting that ordering as heuristic-guided when
    every un-attempted candidate ties at the same default would be
    dishonest busywork, not a real algorithmic contribution.

    What this adds: `h`, a cost-to-solve estimate per SOLVED node, composed
    bottom-up as `own_attempts + max(h(child) for child in requires)` -
    this repo's AND cost rule (documentation/lrta/beyond_the_maze.md's
    critical-path framing: you're only as done as the slowest required
    thing). Only solved nodes get an `h` entry; unsolvable and unreached
    nodes have none, since nothing downstream of them ever needed their
    cost. This is the thing documentation/task-graph/algorithm_fit.md's
    Phase 5 exists to verify - correct AND-composition, hand-checkable
    on the smallest real join (`merged`, two required children) before
    trusting it on `released`'s three-way join in Phase 6.
    """

    def __init__(self, env: TaskGraphEnvironment):
        self.env = env
        self.solved: Set[str] = set()
        self.unsolvable: Set[str] = set()
        self.h: Dict[str, float] = {}
        self.trace: List[Tuple[str, AttemptOutcome]] = []

    def _compose_cost(self, node_id: str) -> float:
        node = self.env.nodes[node_id]
        own_cost = self.env.retries_spent(node_id)
        if not node.requires:
            return float(own_cost)
        children_cost = max(self.h[dep] for dep in node.requires)
        return own_cost + children_cost

    def step(self) -> bool:
        ready = sorted(
            node_id
            for node_id in self.env.ready_nodes(self.solved)
            if node_id not in self.unsolvable
        )
        if not ready:
            return False

        node_id = ready[0]
        outcome = AttemptOutcome.RETRY
        while outcome == AttemptOutcome.RETRY:
            outcome = self.env.attempt(node_id)
            self.trace.append((node_id, outcome))

        if outcome == AttemptOutcome.PASS:
            self.solved.add(node_id)
            self.h[node_id] = self._compose_cost(node_id)
        else:
            self.unsolvable.add(node_id)

        return True

    def run(self, max_steps: int = 1000) -> ExecutionResult:
        all_nodes = set(self.env.nodes.keys())

        for _ in range(max_steps):
            if self.solved == all_nodes:
                break
            if not self.step():
                break

        unreachable = all_nodes - self.solved - self.unsolvable
        return ExecutionResult(
            success=(self.solved == all_nodes),
            satisfied=set(self.solved),
            fatal=set(self.unsolvable),
            unreachable=unreachable,
            trace=list(self.trace),
        )
