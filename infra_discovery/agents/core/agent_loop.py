"""InfraDiscoveryAgent: flat pending/RELEVANT/INVOKE loop.

Per step5_agent_program.md Step 1: a new, minimal flat pending-pool loop
replacing any stack/phase/position-based structure. Implements the core
of step3_agent_function.md's AGENT-FUNCTION pseudocode.

FIXES (from PR #16 review):
- F-001: Both edge.to and edge.from_ enqueued (bidirectional discovery)
- D-003: Multiple DSAs per (domain, kind) supported
- Real atomicguard interfaces: ActionPair, DualStateAgent, InMemoryArtifactDAG
- Track (dsa_name, subject) for proper de-duplication per D-003
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timezone

from .domain import NodeId, Facet, Edge
from .belief_state import BeliefState

if TYPE_CHECKING:
    from atomicguard.application.action_pair import ActionPair
    from atomicguard.infrastructure.persistence.memory import InMemoryArtifactDAG


class DSACatalogueEntry:
    """Entry in DSA-CATALOGUE: (domain, kind) -> DSAs.
    
    Hashable by (domain, kind, dsa_name) only; action_pair not used for hashing.
    This allows tuples like (DSACatalogueEntry, NodeId) to be used in sets.
    """

    def __init__(
        self,
        domain: str,
        kind: str,
        dsa_name: str,
        action_pair: "ActionPair" = None,
        is_sensing: bool = True,
    ):
        self.domain = domain
        self.kind = kind
        self.dsa_name = dsa_name
        self.action_pair = action_pair
        # Per step3_agent_function.md's ELIGIBLE(): sensing DSAs always pass
        # regardless of `cleared` (OQ-018's stated default); acting DSAs
        # (Step 5, none registered yet) will need subject ∈ cleared.
        self.is_sensing = is_sensing

    def __hash__(self) -> int:
        """Hash based on domain, kind, dsa_name only (not action_pair)."""
        return hash((self.domain, self.kind, self.dsa_name))

    def __eq__(self, other: object) -> bool:
        """Equality based on domain, kind, dsa_name only."""
        if not isinstance(other, DSACatalogueEntry):
            return NotImplemented
        return (
            self.domain == other.domain
            and self.kind == other.kind
            and self.dsa_name == other.dsa_name
        )

    def __repr__(self) -> str:
        return f"DSACatalogueEntry({self.domain}/{self.kind}@{self.dsa_name})"


@dataclass
class InfraDiscoveryAgent:
    """The flat pending-pool infrastructure discovery agent.
    
    Attributes:
        dsa_catalogue: Dict[(domain, kind), List[DSACatalogueEntry]]
                       Supports multiple DSAs per (domain, kind) per D-003
        belief_state: Shared persistent store.
        artifact_dag: Real atomicguard ArtifactDAG for storing results.
        workflow_id: For artifact tracking (atomicguard pattern).
        pending: Current episode's pending (dsa_entry, subject) pairs.
        resolved_bridges: Set of (from, to, edge_type) already discovered.
    """

    dsa_catalogue: Dict[Tuple[str, str], List[DSACatalogueEntry]] = field(
        default_factory=dict
    )
    belief_state: BeliefState = field(default_factory=BeliefState)
    artifact_dag: Optional["InMemoryArtifactDAG"] = field(default=None)
    workflow_id: str = field(default="infra-discovery-1")
    pending: Set[Tuple[DSACatalogueEntry, NodeId]] = field(
        default_factory=set
    )
    resolved_bridges: Set[Tuple[NodeId, NodeId, str]] = field(
        default_factory=set
    )
    # Per step5_agent_program.md Step 2: `requires` is static and
    # catalogue-declared for this step, not sensed - a NodeId -> its
    # declared prerequisite NodeIds, fed to RECORD-REQUIRES at sense time.
    requires_catalogue: Dict[NodeId, Tuple[NodeId, ...]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Initialize artifact_dag if not provided.
        
        Lazy-imports InMemoryArtifactDAG with fallback to mock for testing.
        """
        if self.artifact_dag is None:
            try:
                from atomicguard.infrastructure.persistence.memory import InMemoryArtifactDAG
            except ImportError:
                # Fallback to mock for testing without atomicguard installed
                from infra_discovery.tests.test_mocks import MockArtifactDAG as InMemoryArtifactDAG
            object.__setattr__(self, "artifact_dag", InMemoryArtifactDAG())

    def register_dsa(
        self,
        domain: str,
        kind: str,
        action_pair: "ActionPair",
        dsa_name: str,
        is_sensing: bool = True,
    ) -> None:
        """Register a DSA in the catalogue.
        
        Supports multiple DSAs per (domain, kind) per D-003.
        
        Args:
            domain: The domain this DSA handles.
            kind: The kind within that domain.
            action_pair: The ActionPair to invoke.
            dsa_name: Stable identifier for this DSA.
            is_sensing: Whether this DSA only reads (default). Acting DSAs
                        (Step 5, none exist yet) pass False and are gated by
                        ELIGIBLE on subject ∈ cleared.
        """
        entry = DSACatalogueEntry(domain, kind, dsa_name, action_pair, is_sensing)
        key = (domain, kind)
        if key not in self.dsa_catalogue:
            self.dsa_catalogue[key] = []
        self.dsa_catalogue[key].append(entry)

    def register_requires(
        self, subject: NodeId, requires: Tuple[NodeId, ...]
    ) -> None:
        """Statically declare a subject's requires (catalogue-declared, not sensed).
        
        Per step5_agent_program.md Step 2: `requires` is static for this
        step - a NodeId's prerequisites are fixed at scenario-build time,
        not derived from a DSA's artifact content. `step()` looks this up
        at RECORD-REQUIRES time for every sensed subject.
        
        Args:
            subject: The NodeId whose requires are being declared.
            requires: The NodeIds subject depends on (may be empty).
        """
        self.requires_catalogue[subject] = requires

    def _relevant(
        self,
        dsa_entries: List[DSACatalogueEntry],
        subject: NodeId,
        in_scope_fn: Optional[Callable[[NodeId], bool]] = None,
    ) -> Set[Tuple[DSACatalogueEntry, NodeId]]:
        """De-duplicate and scope-check candidates before adding to pending.
        
        Per step3_agent_function.md RELEVANT():
        - Not already in pending
        - Not already recorded (by dsa_name, subject) per D-003
        - IN-SCOPE (for Step 1, everything is in-scope by default)
        
        Args:
            dsa_entries: Candidate DSA entries to consider.
            subject: The NodeId to invoke them against.
            in_scope_fn: Optional function to check if subject is in scope.
        
        Returns:
            Set of (dsa_entry, subject) pairs to add to pending.
        """
        result: Set[Tuple[DSACatalogueEntry, NodeId]] = set()

        # Step 1: everything is in-scope by construction
        if in_scope_fn and not in_scope_fn(subject):
            return result

        for dsa_entry in dsa_entries:
            # Not already pending
            if (dsa_entry, subject) in self.pending:
                continue

            # Not already recorded (by dsa_name, subject) per D-003
            if self.belief_state.is_recorded(dsa_entry.dsa_name, subject):
                continue

            result.add((dsa_entry, subject))

        return result

    def _resolve_bridges(
        self, subject: NodeId, artifact_content: Dict
    ) -> List[Edge]:
        """Free: pattern-match edges directly off an already-fetched artifact.
        
        Per step3_agent_function.md RESOLVE-BRIDGES: no new DSA invocation.
        
        FIX FOR F-001: Creates edges where sensed node can be EITHER
        edge.from_ OR edge.to, not just one direction.
        
        Args:
            subject: The NodeId that was just sensed.
            artifact_content: The Artifact.content (dict) from the DSA.
        
        Returns:
            List of discovered Edge objects (both directions).
        """
        discovered: List[Edge] = []

        # Pattern: 'edges' list in artifact content
        # Each edge: {"to": (domain, kind, id), "type": edge_type, "evidence": ...}
        # FIX: Also handle "from" for reverse-direction edges
        edges_data = artifact_content.get("edges", [])
        for edge_data in edges_data:
            edge_type = edge_data.get("type", "unknown")
            evidence = edge_data.get("evidence", "artifact")

            # Case 1: to node (forward edge from subject)
            to_tuple = edge_data.get("to")
            if to_tuple and isinstance(to_tuple, (list, tuple)) and len(to_tuple) == 3:
                to_node = NodeId(domain=to_tuple[0], kind=to_tuple[1], id=to_tuple[2])
                edge_forward = Edge(
                    from_=subject, to=to_node, edge_type=edge_type, evidence=evidence
                )
                discovered.append(edge_forward)

            # Case 2: from node (reverse edge, F-001 fix)
            from_tuple = edge_data.get("from")
            if from_tuple and isinstance(from_tuple, (list, tuple)) and len(from_tuple) == 3:
                from_node = NodeId(
                    domain=from_tuple[0], kind=from_tuple[1], id=from_tuple[2]
                )
                edge_reverse = Edge(
                    from_=from_node, to=subject, edge_type=edge_type, evidence=evidence
                )
                discovered.append(edge_reverse)

        return discovered

    def _eligible(self) -> Set[Tuple[DSACatalogueEntry, NodeId]]:
        """ELIGIBLE(pending, belief_state): sweep cleared, then filter pending.
        
        Per step5_agent_program.md Step 2 and step3_agent_function.md's
        pseudocode: SWEEP-CLEARED runs every turn of the flat loop (not
        between exploration phases - there are no phases here). A pair is
        eligible if its DSA is sensing (always passes, per OQ-018's stated
        default) or its subject is already cleared. Step 2 registers only
        sensing DSAs, so this is a structural no-op on selection today -
        the mechanism being proven is `cleared` itself, via belief_state.
        
        Returns:
            The subset of pending that's safe to act on this turn.
        """
        self.belief_state.sweep_cleared()
        return {
            (dsa_entry, subject)
            for (dsa_entry, subject) in self.pending
            if dsa_entry.is_sensing or subject in self.belief_state.cleared
        }

    def _select_next(
        self, eligible: Set[Tuple[DSACatalogueEntry, NodeId]]
    ) -> Optional[Tuple[DSACatalogueEntry, NodeId]]:
        """Pick the next (dsa, subject) to invoke from eligible.
        
        Step 1/2 scope: arbitrary/insertion order. SCORE stays named-not-defined.
        Just pop from the set arbitrarily.
        
        Args:
            eligible: The ELIGIBLE-filtered candidates for this turn.
        
        Returns:
            A (dsa_entry, subject) pair, or None if eligible is empty.
        """
        if not eligible:
            return None
        return eligible.pop()

    def invoke(
        self, dsa_entry: DSACatalogueEntry, subject: NodeId
    ) -> Optional[Dict]:
        """Invoke a DSA against a subject.
        
        Per step3_agent_function.md INVOKE(): construct a fresh, stateless
        DualStateAgent bound to dsa's ActionPair, run it, return the result.
        
        FIX: Uses real atomicguard interfaces (ActionPair, DualStateAgent, artifact_dag).
        Works with both real DualStateAgent (from atomicguard) and mock (from tests).
        
        Args:
            dsa_entry: The DSA to invoke.
            subject: The NodeId to invoke it against.
        
        Returns:
            The artifact content (dict) on success, or None on failure.
        """
        try:
            # Try real atomicguard first
            try:
                from atomicguard.application.agent import DualStateAgent
            except ImportError:
                # Fall back to mock for testing
                from infra_discovery.tests.test_mocks import MockDualStateAgent as DualStateAgent

            # Construct fresh agent per invocation
            agent = DualStateAgent(
                action_pair=dsa_entry.action_pair,
                artifact_dag=self.artifact_dag,  # Use real DAG
                rmax=0,  # Deterministic fixtures only (Step 1)
                action_pair_id=dsa_entry.dsa_name,  # Use dsa_name, not action_pair.id
                workflow_id=self.workflow_id,
            )

            artifact = agent.execute(specification="")
            if artifact and hasattr(artifact, "content"):
                return artifact.content
            return None
        except Exception as e:
            print(f"Failed to invoke {dsa_entry.dsa_name} against {subject}: {e}")
            return None

    def step(self) -> Optional[str]:
        """Execute one step of the agent loop.
        
        Returns:
            A status string ("done", "escalated", "working"), or None on error.
        """
        # Step 2: sweep before deciding whether there's anything left - a
        # subject recorded on the immediately preceding turn needs a sweep
        # of its own before `cleared` reflects it. Without this, "done"
        # (fired the instant `pending` empties) can land one sweep short
        # of the true fixed point - the last subject recorded never gets
        # swept again. ELIGIBLE (below) sweeps again per turn regardless;
        # this call is what covers the final turn specifically.
        self.belief_state.sweep_cleared()

        if not self.pending:
            return "done"

        eligible = self._eligible()
        next_work = self._select_next(eligible)
        if not next_work:
            return "escalated"

        dsa_entry, subject = next_work
        self.pending.discard(next_work)

        # INVOKE
        artifact_content = self.invoke(dsa_entry, subject)

        if artifact_content is None:
            # RECORD-UNKNOWABLE or RECORD-BLOCKED
            self.belief_state.record_unknowable(subject)
            self.belief_state.mark_recorded(dsa_entry.dsa_name, subject)
            return "working"

        # Mark this (dsa_name, subject) pair as recorded per D-003
        self.belief_state.mark_recorded(dsa_entry.dsa_name, subject)

        # RECORD: merge facets
        facets = {}
        for key, value in artifact_content.items():
            if key != "edges" and isinstance(value, (str, int, float, bool)):
                facets[key] = Facet(
                    value=value,
                    observed_at=datetime.now(timezone.utc),
                    sensed_by=dsa_entry.dsa_name,  # Use dsa_name
                )
        if facets:
            self.belief_state.record(subject, facets)

        # RECORD-REQUIRES: static, catalogue-declared (Step 2 scope) - not
        # auto-enqueued into `pending` (OQ-017's reachability risk stands;
        # every requires target here must be independently reachable via
        # RESOLVE-BRIDGES, same as any other node)
        self.belief_state.record_requires(
            subject, self.requires_catalogue.get(subject, ())
        )

        # RESOLVE-BRIDGES: discover edges (FIX: both directions for F-001)
        edges = self._resolve_bridges(subject, artifact_content)
        for edge in edges:
            edge_key = (edge.from_, edge.to, edge.edge_type)
            if edge_key not in self.resolved_bridges:
                self.belief_state.record_edge(edge)
                self.resolved_bridges.add(edge_key)

                # FIX FOR F-001: Enqueue BOTH ends
                # RELEVANT for edge.to
                to_dsa_entries = self.dsa_catalogue.get(
                    (edge.to.domain, edge.to.kind), []
                )
                self.pending.update(self._relevant(to_dsa_entries, edge.to))

                # RELEVANT for edge.from_ (the F-001 fix)
                from_dsa_entries = self.dsa_catalogue.get(
                    (edge.from_.domain, edge.from_.kind), []
                )
                self.pending.update(self._relevant(from_dsa_entries, edge.from_))

        # RELEVANT: also enqueue more DSAs for the subject itself
        subject_dsa_entries = self.dsa_catalogue.get(
            (subject.domain, subject.kind), []
        )
        self.pending.update(self._relevant(subject_dsa_entries, subject))

        return "working"

    def run_episode(self, roots: list[NodeId], max_steps: int = 1000) -> str:
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
            root_dsa_entries = self.dsa_catalogue.get(
                (root.domain, root.kind), []
            )
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
