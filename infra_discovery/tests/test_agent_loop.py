"""Integration tests for the agent loop with simple_topology scenario.

Tests:
1. Compound NodeId lookup in DSA-CATALOGUE
2. Facet accumulation from independent DSAs
3. Bidirectional edge discovery (F-001 fix)
4. Flat pending/RELEVANT/INVOKE loop
"""

import pytest

from infra_discovery.agents.core.domain import NodeId, Edge, Facet
from infra_discovery.agents.scenarios.simple_topology import (
    build_simple_topology_agent,
    root_nodes,
)


class TestSimpleTopologyScenario:
    """Test the simple topology scenario end-to-end."""

    def test_agent_initialization(self):
        """Agent should initialize with DSA catalogue."""
        agent = build_simple_topology_agent()

        # Should have 4 DSAs registered (job, Deployment, CloudRun_service,
        # ReplicaSet - the ReplicaSet DSA was added later for the F-001
        # reverse-edge validation; this assertion never actually ran until
        # now, since _cat_action_pair's atomicguard import always failed
        # first)
        assert len(agent.dsa_catalogue) == 4

        # Check that compound keys work
        assert (
            agent.dsa_catalogue.get(("github_actions", "job")) is not None
        )
        assert (
            agent.dsa_catalogue.get(("kubernetes", "Deployment")) is not None
        )
        assert agent.dsa_catalogue.get(("gcp", "CloudRun_service")) is not None
        assert agent.dsa_catalogue.get(("kubernetes", "ReplicaSet")) is not None

    def test_node_id_equality(self):
        """NodeId should support equality and hashing."""
        node1 = NodeId(domain="github_actions", kind="job", id="deploy")
        node2 = NodeId(domain="github_actions", kind="job", id="deploy")
        node3 = NodeId(domain="github_actions", kind="job", id="test")

        assert node1 == node2
        assert node1 != node3
        assert hash(node1) == hash(node2)
        assert hash(node1) != hash(node3)

    def test_facet_accumulation(self):
        """Multiple facets for same subject should accumulate."""
        from infra_discovery.agents.core.belief_state import BeliefState
        from datetime import datetime, timezone

        state = BeliefState()
        subject = NodeId(
            domain="kubernetes", kind="Deployment", id="web"
        )

        facet1 = Facet(
            value=3,
            observed_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            sensed_by="DSA-K8S-DEPLOYMENT-GET",
        )
        facet2 = Facet(
            value="Progressing",
            observed_at=datetime(2026, 1, 1, 10, 0, 1, tzinfo=timezone.utc),
            sensed_by="DSA-K8S-ROLLOUT",
        )

        state.record(subject, {"replicas": facet1})
        state.record(subject, {"status": facet2})

        # Both facets should be present
        facets = state.facets_for(subject)
        assert "replicas" in facets
        assert "status" in facets
        assert facets["replicas"].value == 3
        assert facets["status"].value == "Progressing"

    def test_edge_discovery_forward(self):
        """Edges should be discoverable in forward direction."""
        from infra_discovery.agents.core.belief_state import BeliefState

        state = BeliefState()

        edge = Edge(
            from_=NodeId("github_actions", "job", "deploy"),
            to=NodeId("kubernetes", "Deployment", "web"),
            edge_type="applies-to",
            evidence="step: kubectl apply -f deployment.yaml",
        )

        state.record_edge(edge)

        from_subject = NodeId("github_actions", "job", "deploy")
        edges_from = state.edges_from(from_subject)

        assert len(edges_from) == 1
        assert edges_from[0] == edge

    def test_edge_discovery_backward(self):
        """Edges should be discoverable in backward direction (F-001 fix)."""
        from infra_discovery.agents.core.belief_state import BeliefState

        state = BeliefState()

        edge = Edge(
            from_=NodeId("github_actions", "job", "deploy"),
            to=NodeId("kubernetes", "Deployment", "web"),
            edge_type="applies-to",
            evidence="step: kubectl apply -f deployment.yaml",
        )

        state.record_edge(edge)

        to_subject = NodeId("kubernetes", "Deployment", "web")
        edges_to = state.edges_to(to_subject)

        assert len(edges_to) == 1
        assert edges_to[0] == edge

    def test_bidirectional_discovery(self):
        """F-001 fix: both edge.to and edge.from should be discovered."""
        from infra_discovery.agents.core.belief_state import BeliefState

        state = BeliefState()

        # Simulate discovering an edge from node A
        edge_ab = Edge(
            from_=NodeId("github_actions", "job", "deploy"),
            to=NodeId("kubernetes", "Deployment", "web"),
            edge_type="applies-to",
            evidence="forward discovery",
        )

        # And discovering the same relationship from node B's perspective
        edge_ba = Edge(
            from_=NodeId("kubernetes", "Deployment", "web"),
            to=NodeId("github_actions", "job", "deploy"),
            edge_type="deployed-by",
            evidence="backward discovery",
        )

        state.record_edge(edge_ab)
        state.record_edge(edge_ba)

        # Both directions should be queryable
        node_a = NodeId("github_actions", "job", "deploy")
        node_b = NodeId("kubernetes", "Deployment", "web")

        # From A's perspective, A -> B
        assert any(
            e.to == node_b for e in state.edges_from(node_a)
        )

        # From B's perspective, B <- A (or B -> A)
        assert any(
            e.from_ == node_a for e in state.edges_to(node_b)
        )
        assert any(
            e.to == node_a for e in state.edges_from(node_b)
        )
