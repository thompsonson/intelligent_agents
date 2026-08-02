from dataclasses import dataclass
from typing import Tuple

from atomicguard.application.action_pair import ActionPair


@dataclass(frozen=True)
class StatefulDiscoveryNode:
    """A discovery/ node whose truth is read fresh from the real world via
    a guard-checked atomicguard.ActionPair, instead of carried as static
    dataclass fields. No `notifies` field: what a node notifies is read
    off its check's own Artifact content at sense time, not declared here
    - see core/environment.py's sense_edges(). No `repair_action_pair`:
    this experiment is solely about making nodes stateful, small steps -
    see documentation/discovery/atomicguard-bridge/environment_design.md.

    `requires` stays declared, static config here, exactly like
    atomicguard's own WorkflowStep bundles `requires` with `action_pair`
    at declaration time - satisfaction tracking (what's cleared) is
    cross-node bookkeeping the agent/environment does, not the node
    itself, the same requires/cleared split discovery/'s own DiscoveryNode
    already uses.
    """

    id: str
    check_action_pair: ActionPair
    requires: Tuple[str, ...] = ()
