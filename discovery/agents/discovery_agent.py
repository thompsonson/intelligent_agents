from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from ..core.belief_store import BeliefStore, InMemoryBeliefStore
from ..core.environment import DiscoveryEnvironment
from ..core.results import DiscoveryWalkResult


def _known_route(
    edges_sensed: List[Tuple[str, str]], start: str, target: str, visited: Set[str]
) -> List[str]:
    """Shortest path from `start` to `target` using only already-sensed
    edges between already-visited nodes - both directions usable, since an
    edge between two visited nodes has necessarily already been discovered
    by one end or the other. Lowest-id tie-break on each hop, matching
    every other tie-break in this module. Used only by the readiness sweep
    below to resume exploration at a newly-clearable blocked node; never
    used for ordinary forward movement, which stays exactly as step 2
    built it. See documentation/discovery/and-joins/algorithm_fit.md's
    "why replaying a known route isn't the teleport step 1 ruled out"."""
    adjacency: Dict[str, Set[str]] = {}
    for u, v in edges_sensed:
        if u in visited and v in visited:
            adjacency.setdefault(u, set()).add(v)
            adjacency.setdefault(v, set()).add(u)

    previous: Dict[str, Optional[str]] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == target:
            break
        for neighbor in sorted(adjacency.get(node, ())):
            if neighbor not in previous:
                previous[neighbor] = node
                queue.append(neighbor)

    route = []
    node: Optional[str] = target
    while node is not None:
        route.append(node)
        node = previous[node]
    route.reverse()
    return route


class DiscoveryAgent:
    """Walks from `start_id`, sensing each newly-reached node's `notifies`
    and `requires`, committing to the lexicographically smallest unvisited
    id among a node's `notifies` - but only once that node is `cleared`
    (its own `requires` are all themselves `cleared`; trivially true for
    `requires=()`, which is every node before this step). A `visited` node
    that isn't yet `cleared` is blocked: treated as having no candidates,
    forcing an immediate backtrack, same mechanics as an ordinary dead end.

    When backtracking unwinds all the way back to the phase's own root
    (parent stack empty), a readiness sweep checks every blocked node
    against what's `cleared` by then - Kahn's-algorithm-style frontier
    extraction, not a new idea, see algorithm_fit.md's "Prior art, named
    honestly". If any newly clears, the walk resumes there (lowest id
    first) by replaying an already-known route - never a jump to an
    unvisited id - and explores again. Repeats until nothing new clears;
    whatever's left blocked goes into `DiscoveryWalkResult.blocked_nodes`.

    See documentation/discovery/and-joins/algorithm_fit.md for why the
    obvious extension of step 2's backtracking (excluding only `cleared`
    from candidates, instead of `visited`) is a genuine non-termination
    bug, and documentation/discovery/backtracking-exploration/algorithm_fit.md
    for the DFS-with-retrace result this step's exploration phase reuses
    unchanged.

    The belief state - what has been sensed, known, visited and cleared -
    lives in a BeliefStore (discovery/core/belief_store.py). The default
    keeps it in memory; discovery/typedb/ keeps it in TypeDB. The walk is
    the same either way.
    """

    def __init__(
        self,
        environment: DiscoveryEnvironment,
        start_id: str,
        beliefs: Optional[BeliefStore] = None,
    ):
        self._environment = environment
        self._start_id = start_id
        self._beliefs: BeliefStore = (
            beliefs if beliefs is not None else InMemoryBeliefStore()
        )

    @property
    def beliefs(self) -> BeliefStore:
        return self._beliefs

    def walk(self) -> DiscoveryWalkResult:
        beliefs = self._beliefs
        current = self._start_id
        path = [current]
        # LIFO stack - backtrack always goes to the immediate parent, the
        # node the agent arrived from.
        parents: List[str] = []
        nodes_sensed = 0
        total_cost = 0

        def sense(node_id: str) -> None:
            # SENSE -> RECORD: the exogenous facts first, then the agent's
            # own belief that it has heard of every id they name.
            nonlocal nodes_sensed
            if beliefs.has_sensed(node_id):
                return
            notifies = self._environment.sense_edges(node_id)
            requires = self._environment.sense_requires(node_id)
            beliefs.record_sensed(node_id, notifies, requires)
            beliefs.record_known((node_id, *notifies, *requires))
            nodes_sensed += 1

        def is_cleared(node_id: str) -> bool:
            return node_id in beliefs.cleared()

        def explore_phase() -> None:
            nonlocal current, total_cost
            while True:
                sense(current)
                beliefs.record_visited(current)
                if not is_cleared(current) and all(
                    is_cleared(r) for r in beliefs.requires_of(current)
                ):
                    beliefs.record_cleared(current)

                visited = beliefs.visited()
                candidates = (
                    [n for n in beliefs.notifies_of(current) if n not in visited]
                    if is_cleared(current)
                    else []
                )
                if candidates:
                    next_id = min(candidates)
                    total_cost += self._environment.get_move_cost(current, next_id)
                    parents.append(current)
                    current = next_id
                    path.append(current)
                    continue

                if not parents:
                    return
                parent = parents.pop()
                total_cost += self._environment.get_move_cost(current, parent)
                current = parent
                path.append(current)

        explore_phase()

        while True:
            cleared = beliefs.cleared()
            blocked = beliefs.visited() - cleared
            clearable = sorted(
                n for n in blocked if all(r in cleared for r in beliefs.requires_of(n))
            )
            if not clearable:
                break
            target = clearable[0]
            route = _known_route(
                beliefs.sensed_edges(), current, target, beliefs.visited()
            )
            for hop in route[1:]:
                total_cost += self._environment.get_move_cost(current, hop)
                parents.append(current)
                current = hop
                path.append(current)
            explore_phase()

        visited = beliefs.visited()
        return DiscoveryWalkResult(
            path=path,
            nodes_sensed=nodes_sensed,
            goal_reached=any(not beliefs.notifies_of(n) for n in visited),
            total_cost=total_cost,
            blocked_nodes=sorted(visited - beliefs.cleared()),
        )
