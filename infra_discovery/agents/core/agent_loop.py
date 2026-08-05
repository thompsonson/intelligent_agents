"""InfraDiscoveryAgent: flat pending/RELEVANT/INVOKE loop.

Per step5_agent_program.md Step 1: a new, minimal flat pending-pool loop
replacing any stack/phase/position-based structure. Implements the core
of step3_agent_function.md's AGENT-FUNCTION pseudocode.

No LIFO stack, no phases, no "current position" - just:
- pending: set of not-yet-invoked (dsa, subject) pairs
- RELEVANT: de-duplicate and scope-check before adding to pending
- INVOKE: construct fresh DualStateAgent, run it, process outcomes
- SELECT-NEXT: arbitrary/insertion order (Step 1 scope)
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple, Any

from .domain import NodeId, Facet, Edge
from .belief_state import BeliefState

if TYPE_CHECKING:
    from atomicguard.application.action_pair import ActionPair

@dataclass(frozen=True)
class DSACatalogueEntry:
    """Entry in DSA-CATALOGUE: (domain, kind) -> DSA info.
    
    Attributes:
        domain: The domain this DSA applies to.
        kind: The kind within that domain.
        action_pair: The ActionPair this DSA wraps (type: Any to avoid hard dependency).
    """
    domain: str
    kind: str
    action_pair: "ActionPair"  # Proper type, imported only for TYPE_CHECKING


@dataclass
class PendingWork:
    """A pending (dsa, subject) pair waiting to be invoked.
    
    Attributes:
        dsa_catalogue_entry: Which DSA to invoke.
        subject: Which NodeId to invoke it against.
    """
    dsa_catalogue_entry: DSACatalogueEntry
    subject: NodeId


@dataclass
class InfraDiscoveryAgent:
    """The flat pending-pool infrastructure discovery agent.
    
    Attributes:
        dsa_catalogue: Dict[(domain, kind), DSACatalogueEntry] - lookup table
                       of what DSAs can be invoked.
        bridge_catalogue: (Deferred Step 2) Dict[edge_type, DSA set].
        belief_state: Shared persistent store.
        workflow_id: For artifact tracking (atomicguard pattern).
        pending: Current episode's pending work (resets per episode).
        resolved_bridges: Set of (from, to, edge_type) already discovered
                         (de-duplication for edges).
    """

    dsa_catalogue: Dict[Tuple[str, str], DSACatalogueEntry] = field(
        default_factory=dict
    )
    bridge_catalogue: Dict[str, List[DSACatalogueEntry]] = field(
        default_factory=dict
    )
    belief_state: BeliefState = field(default_factory=BeliefState)
    workflow_id: str = field(default="infra-discovery-1")
    pending: Set[Tuple[DSACatalogueEntry, NodeId]] = field(
        default_factory=set
    )
    resolved_bridges: Set[Tuple[NodeId, NodeId, str]] = field(
        default_factory=set
    )

    def register_dsa(
        self, domain: str, kind: str, action_pair: "ActionPair"
    ) -> None:
        """Register a DSA in the catalogue.
        
        Args:
            domain: The domain this DSA handles.
            kind: The kind within that domain.
            action_pair: The ActionPair to invoke.
        """
        entry = DSACatalogueEntry(domain, kind, action_pair)
        self.dsa_catalogue[(domain, kind)] = entry

    def _relevant(
        self,
        dsa_entries: List[DSACatalogueEntry],
        subject: NodeId,
        in_scope_fn: Optional[Callable[[NodeId], bool]] = None,
    ) -> Set[Tuple[DSACatalogueEntry, NodeId]]:
        """De-duplicate and scope-check candidates before adding to pending.
        
        Per step3_agent_function.md RELEVANT():
        - Not already in pending
        - Not already recorded
        - IN-SCOPE (for Step 1, everything is in-scope by default)
        
        Args:
            dsa_entries: Candidate DSA entries to consider.
            subject: The NodeId to invoke them against.
            in_scope_fn: Optional function to check if subject is in scope.
        
        Returns:
            Set of (dsa_entry, subject) pairs to add to pending.
        """
        result: Set[Tuple[DSACatalogueEntry, NodeId]] = set()

        # Step 1: everything is in-scope by construction (small fixture graph)
        if in_scope_fn and not in_scope_fn(subject):
            return result

        for dsa_entry in dsa_entries:
            # Not already pending
            if (dsa_entry, subject) in self.pending:
                continue

            # Not already recorded (simplified: check if subject has facets)
            if self.belief_state.is_recorded(dsa_entry.action_pair.id, subject):
                continue

            result.add((dsa_entry, subject))

        return result

    def _resolve_bridges(
        self, subject: NodeId, artifact_content: Dict
    ) -> List[Edge]:
        """Free: pattern-match edges directly off an already-fetched artifact.
        
        Per step3_agent_function.md RESOLVE-BRIDGES: no new DSA invocation.
        Looks for edge patterns in the artifact JSON.
        
        For Step 1: simplified - check for 'edge_to' and 'edge_from' keys
        in the fixture artifact.
        
        Args:
            subject: The NodeId that was just sensed.
            artifact_content: The Artifact.content (dict) from the DSA.
        
        Returns:
            List of discovered Edge objects.
        """
        discovered: List[Edge] = []

        # Pattern: 'edges' list in artifact content
        # Each edge: {"to": (domain, kind, id), "type": edge_type, "evidence": ...}
        edges_data = artifact_content.get("edges", [])
        for edge_data in edges_data:
            to_tuple = edge_data.get("to")
            edge_type = edge_data.get("type", "unknown")
            evidence = edge_data.get("evidence", "artifact")

            if to_tuple and isinstance(to_tuple, (list, tuple)) and len(to_tuple) == 3:
                to_node = NodeId(domain=to_tuple[0], kind=to_tuple[1], id=to_tuple[2])

                # Bidirectional: this subject -> to_node
                edge_forward = Edge(
                    from_=subject, to=to_node, edge_type=edge_type, evidence=evidence
                )
                discovered.append(edge_forward)

        return discovered

    def _select_next(self) -> Optional[Tuple[DSACatalogueEntry, NodeId]]:
        """Pick the next (dsa, subject) to invoke from eligible.
        
        Step 1 scope: arbitrary/insertion order. SCORE stays named-not-defined.
        Just pop from the set arbitrarily.
        
        Returns:
            A (dsa_entry, subject) pair, or None if pending is empty.
        """
        if not self.pending:
            return None
        return self.pending.pop()

    def invoke(self, dsa_entry: DSACatalogueEntry, subject: NodeId) -> Optional[Dict]:
        """Invoke a DSA against a subject.
        
        Per step3_agent_function.md INVOKE(): construct a fresh, stateless
        DualStateAgent bound to dsa's ActionPair, run it, return the result.
        
        Args:
            dsa_entry: The DSA to invoke.
            subject: The NodeId to invoke it against.
        
        Returns:
            The artifact content (dict) on success, or None on failure.
        """
        # Lazy import atomicguard only when actually invoking
        from atomicguard.application.agent import DualStateAgent
        
        # For Step 1: use rmax=0 with deterministic cat-over-fixture DSAs
        # (matching real_discovery/atomicguard_backed/ precedent)
        try:
            # Construct fresh agent per invocation
            agent = DualStateAgent(
                action_pair=dsa_entry.action_pair,
                artifact_dag=None,  # Simplified for Step 1: no DAG persistence
                rmax=0,  # Deterministic fixtures only
                action_pair_id=f"{subject.domain}/{subject.kind}/{subject.id}",
                workflow_id=self.workflow_id,
            )

            artifact = agent.execute(specification="")
            if artifact and hasattr(artifact, "content"):
                return artifact.content
            return None
        except Exception as e:
            print(f"Failed to invoke {dsa_entry} against {subject}: {e}")
            return None

    def step(self) -> Optional[str]:
        """Execute one step of the agent loop.
        
        Returns:
            A status string ("done", "escalated", "working"), or None on error.
        """
        # Step 1 scope: no requires/SWEEP-CLEARED yet, no DECIDABLE check
        # Just: do we have pending work?

        if not self.pending:
            return "done"

        # ELIGIBLE (Step 1: all sensing DSAs, no acting)
        # SELECT-NEXT
        next_work = self._select_next()
        if not next_work:
            return "escalated"

        dsa_entry, subject = next_work

        # INVOKE
        artifact_content = self.invoke(dsa_entry, subject)

        if artifact_content is None:
            # RECORD-UNKNOWABLE or RECORD-BLOCKED
            self.belief_state.record_unknowable(subject)
            return "working"

        # RECORD: merge facets
        # Simplified for Step 1: take all top-level keys as facet names
        facets = {}
        for key, value in artifact_content.items():
            if key != "edges" and isinstance(value, (str, int, float, bool)):
                from datetime import datetime, timezone
                facets[key] = Facet(
                    value=value,
                    observed_at=datetime.now(timezone.utc),
                    sensed_by=dsa_entry.action_pair.id,
                )
        if facets:
            self.belief_state.record(subject, facets)

        # RECORD-REQUIRES (Step 1: empty, deferred)
        self.belief_state.record_requires(subject, ())

        # RESOLVE-BRIDGES: discover edges
        edges = self._resolve_bridges(subject, artifact_content)
        for edge in edges:
            edge_key = (edge.from_, edge.to, edge.edge_type)
            if edge_key not in self.resolved_bridges:
                self.belief_state.record_edge(edge)
                self.resolved_bridges.add(edge_key)

                # Per F-001 fix (bidirectional): enqueue both ends
                # RELEVANT for edge.to
                to_dsa_entries = [
                    self.dsa_catalogue.get((edge.to.domain, edge.to.kind))
                ]
                to_dsa_entries = [e for e in to_dsa_entries if e is not None]
                self.pending.update(self._relevant(to_dsa_entries, edge.to))

                # RELEVANT for edge.from_ (the fix)
                from_dsa_entries = [
                    self.dsa_catalogue.get((edge.from_.domain, edge.from_.kind))
                ]
                from_dsa_entries = [e for e in from_dsa_entries if e is not None]
                self.pending.update(self._relevant(from_dsa_entries, edge.from_))

        # RELEVANT: also enqueue more DSAs for the subject itself
        subject_dsa_entries = [
            self.dsa_catalogue.get((subject.domain, subject.kind))
        ]
        subject_dsa_entries = [e for e in subject_dsa_entries if e is not None]
        self.pending.update(self._relevant(subject_dsa_entries, subject))

        return "working"

    def run_episode(self, roots: List[NodeId], max_steps: int = 1000) -> str:
        """Run one discovery episode.
        
        Args:
            roots: Starting NodeIds to discover from.
            max_steps: Maximum steps before escalation.
        
        Returns:
            Final status ("done", "escalated", "error").
        """
        # Initialize pending with root subjects
        self.pending.clear()
        for root in roots:
            root_dsa_entries = [
                self.dsa_catalogue.get((root.domain, root.kind))
            ]
            root_dsa_entries = [e for e in root_dsa_entries if e is not None]
            self.pending.update(self._relevant(root_dsa_entries, root))

        steps = 0
        while steps < max_steps:
            status = self.step()
            steps += 1

            if status == "done":
                return "done"
            if status == "escalated":
                return "escalated"
            if status is None:
                return "error"

        return "escalated"
