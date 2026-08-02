import json
from typing import Dict, List, Tuple

from atomicguard.application.agent import DualStateAgent
from atomicguard.infrastructure.persistence.memory import InMemoryArtifactDAG

from .domain import StatefulDiscoveryNode


def _validate_requires_graph(nodes: Dict[str, StatefulDiscoveryNode]) -> None:
    """Unknown-target and cycle detection over `.requires` only - the same
    pattern as discovery/core/environment.py's own
    _validate_requires_graph() (cross-package, not imported, same
    precedent every prior step in this repo has followed). Unlike that
    function, there's no `.notifies` half to skip validating here: this
    node shape has no `.notifies` field at all - see sense_edges() below
    for where that content actually comes from."""
    for node_id, node in nodes.items():
        for dep in node.requires:
            if dep not in nodes:
                raise ValueError(f"node {node_id!r} requires unknown node {dep!r}")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in nodes}

    def visit(node_id: str, path: List[str]) -> None:
        color[node_id] = GRAY
        for dep in nodes[node_id].requires:
            if color[dep] == GRAY:
                cycle = " -> ".join(path + [dep])
                raise ValueError(f"cycle detected in requires graph: {cycle}")
            if color[dep] == WHITE:
                visit(dep, path + [dep])
        color[node_id] = BLACK

    for node_id in nodes:
        if color[node_id] == WHITE:
            visit(node_id, [node_id])


class StatefulDiscoveryEnvironment:
    """Same public shape as discovery.core.environment.DiscoveryEnvironment
    - sense_edges()/sense_requires()/get_move_cost(), nothing else - so
    discovery.agents.discovery_agent.DiscoveryAgent runs against this
    environment with ZERO code changes. See
    documentation/discovery/atomicguard-bridge/environment_design.md.

    Unlike DiscoveryEnvironment, a node's notifies isn't a static field to
    read: sense_edges() actually runs the node's check_action_pair, through
    a real DualStateAgent (rmax=0 - one real call, no retry, the same
    "free sensor" shape AtomicGuardCheckEnvironment.check_invariant() already
    established), and reads `notifies` off the returned Artifact's content,
    parsed as JSON. The node represents the state of the world; sense_edges()
    reads it fresh, every call - no caching here, since
    DiscoveryAgent.walk() already never re-senses an already-known node
    (see its own `sense()` closure).
    """

    def __init__(
        self,
        nodes: Dict[str, StatefulDiscoveryNode],
        workflow_id: str = "real-discovery",
    ):
        _validate_requires_graph(nodes)
        self.nodes = nodes
        self._dag = InMemoryArtifactDAG()
        self._workflow_id = workflow_id

    def sense_edges(self, node_id: str) -> Tuple[str, ...]:
        """Runs node_id's check_action_pair for real (DualStateAgent,
        rmax=0) and reads `notifies` off the resulting Artifact's content,
        parsed as JSON. Raises ValueError if node_id isn't a real node, or
        if a sensed notifies target isn't one either - the same
        unknown-target check discovery/'s DiscoveryEnvironment does at
        construction time, done here at sense time instead, since a
        target's existence genuinely isn't knowable before the check that
        names it actually runs. A failing check (RmaxExhausted) is left to
        propagate uncaught - unlike check_invariant()'s pass/fail boolean,
        there's no sensible notifies to return for a check that never
        produced one.

        Raises:
            ValueError: if `node_id`, or a target it notifies, isn't a
                node in this graph.
        """
        if node_id not in self.nodes:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        node = self.nodes[node_id]
        agent = DualStateAgent(
            action_pair=node.check_action_pair,
            artifact_dag=self._dag,
            rmax=0,
            action_pair_id=node_id,
            workflow_id=self._workflow_id,
        )
        artifact = agent.execute(specification="")
        notifies = tuple(json.loads(artifact.content)["notifies"])
        for target in notifies:
            if target not in self.nodes:
                raise ValueError(f"node {node_id!r} notifies unknown node {target!r}")
        return notifies

    def sense_requires(self, node_id: str) -> Tuple[str, ...]:
        """The queried node's own declared requires - static config, not
        sensed, exactly like discovery/'s sense_requires(). Satisfaction
        (what's cleared) stays entirely the agent's own bookkeeping; this
        environment never tracks it, mirroring how atomicguard's own
        WorkflowState is held external to WorkflowStep.

        Raises:
            ValueError: if `node_id` is not a node in this graph.
        """
        if node_id not in self.nodes:
            raise ValueError(f"{node_id!r} is not a node in this graph")
        return self.nodes[node_id].requires

    def get_move_cost(self, from_id: str, to_id: str) -> int:
        """Always 1. Same flat-for-now, concept-for-later precedent as
        every other environment in this repo (MazeEnvironment.get_step_cost(),
        DiscoveryEnvironment.get_move_cost())."""
        return 1
