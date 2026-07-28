from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult


class TopologicalExecutor:
    """Baseline executor with no heuristic and no learning: attempt whatever
    `ready_nodes()` returns, in sorted order for determinism, driving each
    node to a terminal outcome (PASS or FATAL) before moving to the next.

    Equivalent role to running BFS on the maze before trying A* - proves the
    environment and executor loop work before any algorithm-specific
    behavior (AO*, D* Lite, LRTA*) is layered on top. See
    documentation/task-graph/algorithm_fit.md.
    """

    def __init__(self, env: TaskGraphEnvironment):
        self.env = env

    def run(self) -> ExecutionResult:
        satisfied: set[str] = set()
        fatal: set[str] = set()
        trace: list[tuple[str, AttemptOutcome]] = []

        while True:
            ready = sorted(
                node_id
                for node_id in self.env.ready_nodes(satisfied)
                if node_id not in fatal
            )
            if not ready:
                break

            node_id = ready[0]
            outcome = AttemptOutcome.RETRY
            while outcome == AttemptOutcome.RETRY:
                outcome = self.env.attempt(node_id)
                trace.append((node_id, outcome))

            if outcome == AttemptOutcome.PASS:
                satisfied.add(node_id)
            else:
                fatal.add(node_id)

        all_nodes = set(self.env.nodes.keys())
        unreachable = all_nodes - satisfied - fatal

        return ExecutionResult(
            success=(satisfied == all_nodes),
            satisfied=satisfied,
            fatal=fatal,
            unreachable=unreachable,
            trace=trace,
        )
