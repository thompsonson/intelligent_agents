from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DiscoveryNode:
    """A node carrying both edge directions: `notifies` (push, node-local -
    who this node tells) and `requires` (pull, mirrors GraphNode/JobNode -
    what this node needs before its own `notifies` are walkable). See
    documentation/discovery/environment_design.md and, for `requires`,
    documentation/discovery/and-joins/environment_design.md."""

    id: str
    notifies: Tuple[str, ...] = ()
    requires: Tuple[str, ...] = ()
