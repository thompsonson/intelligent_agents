from typing import Dict, List, Set, Tuple

from ..core.environment import DiscoveryEnvironment
from ..core.results import DiscoveryWalkResult


class DiscoveryAgent:
    """Walks from `start_id`, sensing each newly-reached node's `notifies`
    and committing to the lexicographically smallest unvisited id among
    them. When a node has no unvisited neighbor left, backtracks to the
    node it arrived from - retracing an already-walked edge, never a
    jump to an arbitrary known-but-unvisited id - and continues from
    there. Stops once backtracking has unwound all the way past `start_id`
    with nothing new left to reach: full exploration, not goal-seeking.
    See documentation/discovery/backtracking-exploration/algorithm_fit.md
    for why this (DFS with a free backtrack move), not BFS or a learned
    policy, is the right fit, and why it makes DFS/BFS a literal
    comparison again - step 1's agent, without backtracking, denied
    that comparison entirely.
    """

    def __init__(self, environment: DiscoveryEnvironment, start_id: str):
        self._environment = environment
        self._start_id = start_id

    def walk(self) -> DiscoveryWalkResult:
        current = self._start_id
        path = [current]
        visited: Set[str] = set()
        known_edges: Dict[str, Tuple[str, ...]] = {}
        parents: List[str] = []  # LIFO stack - backtrack always goes to
        # the immediate parent, the node the agent arrived from
        nodes_sensed = 0
        total_cost = 0

        while True:
            if current not in known_edges:
                known_edges[current] = self._environment.sense_edges(current)
                nodes_sensed += 1
            visited.add(current)

            candidates = [n for n in known_edges[current] if n not in visited]
            if candidates:
                next_id = min(candidates)
                total_cost += self._environment.get_move_cost(current, next_id)
                parents.append(current)
                current = next_id
                path.append(current)
                continue

            if not parents:
                break

            parent = parents.pop()
            total_cost += self._environment.get_move_cost(current, parent)
            current = parent
            path.append(current)

        return DiscoveryWalkResult(
            path=path,
            nodes_sensed=nodes_sensed,
            goal_reached=any(not known_edges[n] for n in visited),
            total_cost=total_cost,
        )
