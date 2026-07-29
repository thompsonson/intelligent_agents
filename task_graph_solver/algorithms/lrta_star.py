from typing import Callable, Dict, List

from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult
from .topological import TopologicalExecutor


class LRTAStarLearner:
    """Learns h(s) - the retry cost of getting through each node - over
    repeated trials through a task graph, per documentation/lrta/beyond_the_maze.md.

    Only `retry_flavor="repair"` nodes are tracked in `h_table`. Sensing- and
    generation-flavor retries still happen as part of running a trial, but
    are deliberately excluded from the learning signal - blending them would
    teach the wrong thing, per the finding that motivated this environment
    in the first place (a slow sensing poll isn't the same kind of cost as a
    failed real-world repair attempt).

    The update rule mirrors LRTA*'s classic backup:
        h(s) <- max(h(s), retries_spent(s) + min_over_successors(h(successor)))
    with untracked successors (non-repair-flavor, or terminal) treated as 0 -
    this degenerates correctly to plain retry-cost learning on a linear chain,
    which is the only shape this repo's scenarios currently exercise it on
    (see documentation/task-graph/algorithm_fit.md's scope boundary for LRTA*).
    """

    def __init__(self, env_factory: Callable[[int], TaskGraphEnvironment]):
        self._env_factory = env_factory
        self._trial_count = 0
        self.h_table: Dict[str, float] = {}

    def _successors(self, env: TaskGraphEnvironment, node_id: str) -> List[str]:
        return [
            other_id
            for other_id, other_node in env.nodes.items()
            if node_id in other_node.requires
        ]

    def run_trial(self) -> ExecutionResult:
        env = self._env_factory(self._trial_count)
        self._trial_count += 1

        result = TopologicalExecutor(env).run()

        for node_id, node in env.nodes.items():
            if node.retry_flavor != "repair":
                continue

            successors = self._successors(env, node_id)
            successor_cost = min(
                (self.h_table.get(s, 0.0) for s in successors), default=0.0
            )
            observed = env.retries_spent(node_id) + successor_cost
            self.h_table[node_id] = max(self.h_table.get(node_id, 0.0), observed)

        return result
