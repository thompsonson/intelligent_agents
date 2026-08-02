from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DiscoveryNode:
    """A node whose only edge field is `notifies` - push-direction,
    node-local, the reverse of GraphNode/JobNode's pull-direction
    `requires`. No `requires` yet: AND-joins are deferred to a later step.
    See documentation/discovery/environment_design.md."""

    id: str
    notifies: Tuple[str, ...] = ()
