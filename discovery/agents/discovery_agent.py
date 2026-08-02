from ..core.environment import DiscoveryEnvironment
from ..core.results import DiscoveryWalkResult


class DiscoveryAgent:
    """Walks forward from `start_id`, sensing each node's `notifies` on
    arrival and committing to the lexicographically smallest unvisited
    id among them - never backtracking, since the environment offers no
    way to. Stops on reaching a node with no `notifies` (the goal), or
    once every notified id from the current node has already been
    visited (stuck - no forward move remains). See
    documentation/discovery/environment_design.md and algorithm_fit.md
    for why this tie-break, not classical DFS/BFS, is the right fit.
    """

    def __init__(self, environment: DiscoveryEnvironment, start_id: str):
        self._environment = environment
        self._start_id = start_id

    def walk(self) -> DiscoveryWalkResult:
        current = self._start_id
        path = [current]
        visited: set = set()
        nodes_sensed = 0

        while True:
            notifies = self._environment.sense_edges(current)
            nodes_sensed += 1
            visited.add(current)

            if not notifies:
                return DiscoveryWalkResult(
                    path=path, nodes_sensed=nodes_sensed, goal_reached=True
                )

            candidates = [n for n in notifies if n not in visited]
            if not candidates:
                return DiscoveryWalkResult(
                    path=path, nodes_sensed=nodes_sensed, goal_reached=False
                )

            current = min(candidates)
            path.append(current)
