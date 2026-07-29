from dataclasses import dataclass
from typing import Tuple


@dataclass
class RealCheckNode:
    """A real, deterministic Guard: a command run against the environment's
    current working tree. Deliberately smaller than task_graph_solver's
    TaskNode - see documentation/task-graph/real-guards/environment_design.md.

    No pass_probability - a real check has no probability, it has an
    answer. No rmax/r_patience/retry_flavor either: those exist to bound
    and classify RETRY, and nothing in this environment ever retries - a
    deterministic check run twice without an intervening repair gives the
    same answer both times. All three return once repair exists (see the
    design doc's "What comes after this document").

    Attributes:
        id: Unique identifier within a RealCheckEnvironment.
        command: Argv to run, e.g. ("mypy", "src/") - executed with cwd set
            to the environment's current working tree.
        requires: AND-dependencies, identical semantics to TaskNode's.
    """

    id: str
    command: Tuple[str, ...]
    requires: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError(f"command must not be empty for node {self.id!r}")
