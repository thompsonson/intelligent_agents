from ..core.domain import AttemptOutcome
from ..core.environment import TaskGraphEnvironment
from ..core.results import ExecutionResult


class GuardFirstExecutor:
    """`TopologicalExecutor` plus one addition: before ever paying for a
    repair, check whether the node's invariant already holds - a free
    sensor, see documentation/task-graph/guard-first/environment_design.md.

    Grounded in a real gap in atomicguard's ActionPair.execute(): Phase 1
    (generate) always runs unconditionally, with no phase that asks "does
    this already hold?" before paying for an LLM call. `env.check_invariant`
    is the toy equivalent of a live-sensing Guard called before generation.

    Still a walk-as-you-go executor, not a planner: this only ever checks
    the node it's currently standing on, in the same sorted-by-id frontier
    order as TopologicalExecutor - it can't discover a downstream node is
    already satisfied without first walking every node between here and
    there. See documentation/task-graph/goal-directed-planning/
    environment_design.md for the executor that can.
    """

    def __init__(self, env: TaskGraphEnvironment):
        self.env = env

    def run(self) -> ExecutionResult:
        satisfied: set[str] = set()
        fatal: set[str] = set()
        trace: list[tuple[str, AttemptOutcome]] = []
        free_checks: set[str] = set()

        while True:
            ready = sorted(
                node_id
                for node_id in self.env.ready_nodes(satisfied)
                if node_id not in fatal
            )
            if not ready:
                break

            node_id = ready[0]

            if self.env.check_invariant(node_id):
                satisfied.add(node_id)
                free_checks.add(node_id)
                continue

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
            success=self.env.is_goal_reached(satisfied),
            satisfied=satisfied,
            fatal=fatal,
            unreachable=unreachable,
            trace=trace,
            free_checks=free_checks,
        )
