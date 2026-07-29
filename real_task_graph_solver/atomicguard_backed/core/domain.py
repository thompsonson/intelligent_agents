from dataclasses import dataclass
from typing import Optional, Tuple

from atomicguard.application.action_pair import ActionPair


@dataclass
class AtomicGuardCheckNode:
    """A node whose Guard is a real atomicguard ActionPair - see
    documentation/task-graph/atomicguard-variant/environment_design.md.

    Unlike RealCheckNode, this node can genuinely repair itself:
    `check_action_pair` is a free sensor (no side effects - e.g. `ruff
    check src/`, no `--fix`); `repair_action_pair`, if set, is a real
    Generator+Effector pair invoked only when the check fails (e.g. `ruff
    check --fix src/`), giving GuardFirstExecutor's check-then-repair
    pattern a real repair action for the first time in this project.

    Attributes:
        id: Unique identifier within an AtomicGuardCheckEnvironment.
        check_action_pair: The free-check ActionPair - no world mutation.
        repair_action_pair: The real repair ActionPair, or None if this
            node has no repair capability yet (behaves like RealCheckNode:
            attempt() just re-runs the check).
        requires: AND-dependencies, identical semantics to RealCheckNode's.
    """

    id: str
    check_action_pair: ActionPair
    repair_action_pair: Optional[ActionPair] = None
    requires: Tuple[str, ...] = ()
