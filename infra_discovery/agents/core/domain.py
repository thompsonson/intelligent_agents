"""Domain types for infrastructure discovery.

Implements step0_schema.md's compound NodeId, Facet, and Edge types.
Separate domain/kind/id instead of bare strings per D-001.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Tuple


@dataclass(frozen=True)
class NodeId:
    """Compound node identity: (domain, kind, id).
    
    Per D-001: `id` alone is not globally unique - only the full triple is.
    
    Attributes:
        domain: Which handler owns it (github_actions, kubernetes, gcp, ...).
                A registered key in DSA-CATALOGUE.
        kind: A closed type within the domain (Deployment, Pod, job, ...).
              Declared by the domain, not global.
        id: An identity string, unique only within (domain, kind).
            Domain/kind-specific format (GitHub job id is numeric,
            Kubernetes Pod id is DNS-1123 name, etc.).
    """
    domain: str
    kind: str
    id: str

    def __repr__(self) -> str:
        return f"NodeId({self.domain!r}, {self.kind!r}, {self.id!r})"


@dataclass(frozen=True)
class Facet:
    """One independently-sensed, independently-timestamped observable property.
    
    Per step0_schema.md: SOSA/SSN-grounded (one Observation per property,
    not one flat value). A node's state is Dict[str, Facet], keyed by
    facet name (rollout, replica_readiness, conclusion, etc.).
    
    Attributes:
        value: The observed value (type varies by facet name).
        observed_at: When this observation was made (UTC).
        sensed_by: Which DSA produced this facet - a key into DSA-CATALOGUE,
                   not a free-text label.
    """
    value: Any
    observed_at: datetime
    sensed_by: str


@dataclass(frozen=True)
class Edge:
    """A discovered relationship claim: (from, to, edge_type, evidence).
    
    Per step0_schema.md and F-001 fix: both directions need to be discovered
    (from via edge.to, to via edge.from). Not directly observed, inferred
    from artifact content via RESOLVE-BRIDGES.
    
    Attributes:
        from_: Source NodeId (renamed from 'from' to avoid Python keyword).
        to: Target NodeId.
        edge_type: Domain-native verb (owns, selects) or cross-domain bridge
                   verb (applies-to, exposes, triggers, etc.).
        evidence: What artifact/observation produced this claim - provenance.
    """
    from_: NodeId
    to: NodeId
    edge_type: str
    evidence: str

    def __repr__(self) -> str:
        return (
            f"Edge({self.from_!r} --{self.edge_type}--> {self.to!r}, "
            f"evidence={self.evidence!r})"
        )
