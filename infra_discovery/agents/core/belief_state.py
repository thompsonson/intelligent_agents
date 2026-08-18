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
    
    Attributes:
        facets_by_node: Maps NodeId -> facets dict.
        edges: List of discovered relationships.
        requires_by_node: Maps NodeId -> requires tuple (prerequisites).
        cleared: Set of NodeIds that have passed all requires.
        unknowable: Set of NodeIds that failed to be sensed.
        blocked: Set of NodeIds that were blocked/escalated/stagnated.
        recorded: Set of (dsa_name, subject) pairs already invoked.
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
        
        Args:
            subject: The node to record facets for.
            facets: The facets to record.
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
            subject: The node to record requires for.
            requires: The prerequisite NodeIds.
        """
        self.requires_by_node[subject] = requires

    def record_unknowable(self, subject: NodeId) -> None:
        """Mark a subject as permanently unknowable (rmax exhausted).
        
        Args:
            subject: The node that failed to be sensed.
        """
        self.unknowable.add(subject)

    def record_blocked(self, subject: NodeId) -> None:
        """Mark a subject as blocked/escalated/stagnated.
        
        Args:
            subject: The node that was blocked.
        """
        self.blocked.add(subject)

    def facets_for(self, subject: NodeId) -> Dict[str, Facet]:
        """Get all facets for a subject.
        
        Args:
            subject: The node to get facets for.
        
        Returns:
            A dict of facets for the subject.
        """
        return self.facets_by_node.get(subject, {})

    def edges_from(self, subject: NodeId) -> list[Edge]:
        """Get all edges where subject is the source.
        
        Args:
            subject: The node to get outgoing edges for.
        
        Returns:
            List of Edge objects where subject is from.
        """
        return [e for e in self.edges if e.from_ == subject]

    def edges_to(self, subject: NodeId) -> list[Edge]:
        """Get all edges where subject is the target.
        
        Args:
            subject: The node to get incoming edges for.
        
        Returns:
            List of Edge objects where subject is to.
        """
        return [e for e in self.edges if e.to == subject]

    def is_recorded(self, dsa_name: str, subject: NodeId) -> bool:
        """Check if (dsa_name, subject) has already been invoked.
        
        Args:
            dsa_name: The DSA name.
            subject: The node to check.
        
        Returns:
            True if already invoked.
        """
        return (dsa_name, subject) in self.recorded

    def mark_recorded(self, dsa_name: str, subject: NodeId) -> None:
        """Mark a (dsa_name, subject) pair as recorded.
        
        Args:
            dsa_name: The DSA name.
            subject: The node that was invoked.
        """
        self.recorded.add((dsa_name, subject))

    def recorded_subjects(self) -> Set[NodeId]:
        """Get all subjects that have been recorded.
        
        Returns:
            Set of NodeIds that have been recorded.
        """
        return set(self.facets_by_node.keys())

    def get_requires(self, subject: NodeId) -> Tuple[NodeId, ...]:
        """Get a subject's requires.
        
        Args:
            subject: The node to get requires for.
        
        Returns:
            Tuple of prerequisite NodeIds.
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
                # Subjects that failed to be sensed should NEVER be cleared
                # as they would allow their dependents to clear incorrectly
                if subject in self.unknowable or subject in self.blocked:
                    continue  # Don't allow blocked/unknowable subjects to clear
                
                # Get requires; if all are cleared, mark subject as cleared
                requires = self.get_requires(subject)
                
                if all(r in self.cleared for r in requires):
                    self.cleared.add(subject)
                    changed = True

    def __repr__(self) -> str:
        return f"BeliefState(cleared={len(self.cleared)}, recorded={len(self.recorded)}, unknowable={len(self.unknowable)}, blocked={len(self.blocked)})"