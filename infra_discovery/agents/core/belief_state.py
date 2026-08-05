"""BeliefState: persistent, entity-indexed world-belief store.

Per step0_ubiquitous_language.md: a shared, persistent, entity-indexed
(domain, kind, id) world-belief store. Not the environment (which is the
real infrastructure itself); not local per-walk bookkeeping.

Implements RECORD, RECORD-EDGE, RECORD-REQUIRES, RECORD-UNKNOWABLE,
RECORD-BLOCKED operations from step3_agent_function.md.

FIX: Tracks (dsa_name, subject) pairs for proper de-duplication per D-003.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

from .domain import NodeId, Facet, Edge


@dataclass
class BeliefState:
    """The persistent world-belief store.
    
    Holds:
    - facets_by_node: Dict[NodeId, Dict[str, Facet]] - a node's state is
      accumulated facets from multiple DSAs
    - edges: List[Edge] - discovered relationships
    - requires_by_node: Dict[NodeId, Tuple[NodeId, ...]] - declared or
      discovered dependencies
    - cleared: Set[NodeId] - monotonically-growing set of subjects whose
      requires are all themselves in cleared (D1, F-002 fix)
    - unknowable: Set[NodeId] - subjects that failed permanently (rmax exhausted)
    - blocked: Set[NodeId] - subjects that escalated/stagnated
    - recorded: Set[Tuple[str, NodeId]] - (dsa_name, subject) pairs already invoked
      per D-003 for proper de-duplication with multiple DSAs per kind
    """

    facets_by_node: Dict[NodeId, Dict[str, Facet]] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    requires_by_node: Dict[NodeId, Tuple[NodeId, ...]] = field(
        default_factory=dict
    )
    cleared: Set[NodeId] = field(default_factory=set)
    unknowable: Set[NodeId] = field(default_factory=set)
    blocked: Set[NodeId] = field(default_factory=set)
    recorded: Set[Tuple[str, NodeId]] = field(default_factory=set)

    def record(self, subject: NodeId, facets: Dict[str, Facet]) -> None:
        """Merge facets into subject's state.
        
        Does NOT replace prior facets - new facets are added/updated,
        prior ones from other DSAs survive. This allows multiple senses
        of the same subject to accumulate independent timestamped observations.
        
        Args:
            subject: The NodeId being sensed.
            facets: Dict[facet_name, Facet] to merge.
        """
        if subject not in self.facets_by_node:
            self.facets_by_node[subject] = {}
        self.facets_by_node[subject].update(facets)

    def record_edge(self, edge: Edge) -> None:
        """Record a discovered relationship claim.
        
        Args:
            edge: The Edge to record.
        """
        self.edges.append(edge)

    def record_requires(
        self, subject: NodeId, requires: Tuple[NodeId, ...]
    ) -> None:
        """Record a subject's declared or discovered dependencies.
        
        Args:
            subject: The NodeId with dependencies.
            requires: Tuple of required NodeIds.
        """
        self.requires_by_node[subject] = requires

    def record_unknowable(self, subject: NodeId) -> None:
        """Mark a subject as permanently unknowable (rmax exhausted).
        
        Propagates: nothing requiring subject can ever clear (F-002 fix).
        
        Args:
            subject: The NodeId that failed permanently.
        """
        self.unknowable.add(subject)

    def record_blocked(self, subject: NodeId) -> None:
        """Mark a subject as blocked/escalated/stagnated.
        
        Same propagation as unknowable - blocks clearance of dependents.
        
        Args:
            subject: The NodeId that escalated.
        """
        self.blocked.add(subject)

    def facets_for(self, subject: NodeId) -> Dict[str, Facet]:
        """Get all facets for a subject.
        
        Returns an empty dict if the subject has no recorded facets yet.
        
        Args:
            subject: The NodeId to query.
        
        Returns:
            Dict[facet_name, Facet].
        """
        return self.facets_by_node.get(subject, {})

    def edges_from(self, subject: NodeId) -> list[Edge]:
        """Get all edges where subject is the source.
        
        Args:
            subject: The NodeId to query.
        
        Returns:
            List of Edge where edge.from_ == subject.
        """
        return [e for e in self.edges if e.from_ == subject]

    def edges_to(self, subject: NodeId) -> list[Edge]:
        """Get all edges where subject is the target.
        
        Per F-001 (bidirectional discovery), this direction needs to be
        queryable, not just edges_from().
        
        Args:
            subject: The NodeId to query.
        
        Returns:
            List of Edge where edge.to == subject.
        """
        return [e for e in self.edges if e.to == subject]

    def is_recorded(self, dsa_name: str, subject: NodeId) -> bool:
        """Check if (dsa_name, subject) has already been invoked.
        
        FIX: Tracks (dsa_name, subject) pairs for proper de-duplication
        per D-003, allowing multiple DSAs per (domain, kind).
        
        Args:
            dsa_name: Name of the DSA (e.g., "DSA-K8S-DEPLOYMENT-GET").
            subject: The NodeId to query.
        
        Returns:
            True if (dsa_name, subject) has been recorded.
        """
        return (dsa_name, subject) in self.recorded

    def mark_recorded(self, dsa_name: str, subject: NodeId) -> None:
        """Mark a (dsa_name, subject) pair as recorded.
        
        Args:
            dsa_name: Name of the DSA.
            subject: The NodeId that was sensed.
        """
        self.recorded.add((dsa_name, subject))

    def recorded_subjects(self) -> Set[NodeId]:
        """Get all subjects that have been recorded.
        
        Used by SWEEP-CLEARED to check requires.
        
        Returns:
            Set of NodeIds that have facets.
        """
        return set(self.facets_by_node.keys())

    def get_requires(self, subject: NodeId) -> Tuple[NodeId, ...]:
        """Get a subject's requires.
        
        Args:
            subject: The NodeId to query.
        
        Returns:
            Tuple of required NodeIds, or empty tuple if none.
        """
        return self.requires_by_node.get(subject, ())

    def sweep_cleared(self) -> None:
        """Iterative fixed-point pass to maintain cleared monotonically.
        
        Per F-002 (cycle-safety fix): cleared is membership-check only,
        never recursive. Once a subject enters, it never leaves (D1).
        
        This is called each turn of the agent loop to update cleared based
        on the current state of the requires graph.
        """
        changed = True
        while changed:
            changed = False
            # Check subjects not yet cleared
            for subject in self.recorded_subjects() - self.cleared:
                # Get requires; if all are cleared or the subject is blocked,
                # mark subject as cleared
                requires = self.get_requires(subject)
                blocked_or_unknowable = (
                    subject in self.unknowable or subject in self.blocked
                )

                if blocked_or_unknowable or all(
                    r in self.cleared for r in requires
                ):
                    self.cleared.add(subject)
                    changed = True
