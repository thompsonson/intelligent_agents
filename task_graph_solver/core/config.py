from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskGraphConfig:
    """Configuration for a task graph environment.

    Node-level retry parameters (rmax, r_patience, pass_probability) live on
    each TaskNode itself - this only holds environment-wide settings.

    Attributes:
        seed: Seed for the environment's random number generator, so guard
            outcomes are reproducible for teaching. None means unseeded.
    """
    seed: Optional[int] = None
