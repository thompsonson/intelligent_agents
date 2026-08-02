from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DiscoveryWalkResult:
    """Result of a DiscoveryAgent's walk. See
    documentation/discovery/environment_design.md."""

    path: List[str]
    nodes_sensed: int
    goal_reached: bool
