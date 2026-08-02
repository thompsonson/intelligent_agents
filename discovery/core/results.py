from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DiscoveryWalkResult:
    """Result of a DiscoveryAgent's walk. See
    documentation/discovery/environment_design.md and, for backtracking,
    documentation/discovery/backtracking-exploration/algorithm_fit.md."""

    path: List[str]  # every node landed on, in order - repeats included
    # once backtracking is possible (a node reached twice via two branches
    # appears twice); this is the full move log, not first-visit order,
    # per backtracking-exploration/algorithm_fit.md's "Not decided" -> resolved.
    nodes_sensed: int  # distinct sense_edges() calls - cached on revisit
    goal_reached: bool  # True if any node with no notifies was visited,
    # not necessarily where the walk ended (full exploration doesn't stop
    # at the first one)
    total_cost: int  # sum of get_move_cost() over every move, forward and
    # backtrack alike - a real, counted move, not a free rewind
