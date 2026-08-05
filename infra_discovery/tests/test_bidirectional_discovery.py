"""Property-based tests for bidirectional discovery (F-001 fix).

Per D-004: property-based testing starts at Step 1 for universal claims.
F-001 is a universal claim over any edge direction:
- A discovered edge from node.from_ must make node.to discoverable
- A discovered edge targeting node.to must make node.from_ discoverable

Uses hypothesis to generate arbitrary edge topologies.
"""

from hypothesis import given, strategies as st
import pytest

from infra_discovery.agents.core.domain import NodeId, Edge
from infra_discovery.agents.core.belief_state import BeliefState


# Strategies for generating test data
domain_strategy = st.sampled_from(["github_actions", "kubernetes", "gcp"])
kind_strategy = st.sampled_from(["job", "Deployment", "Pod", "CloudRun_service"])
id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=1, max_size=20
)

edge_type_strategy = st.sampled_from(
    ["applies-to", "deployed-by", "owns", "selects-from"]
)


def node_id_strategy():
    """Generate arbitrary NodeIds."""
    return st.builds(NodeId, domain=domain_strategy, kind=kind_strategy, id=id_strategy)


def edge_strategy():
    """Generate arbitrary Edges."""
    return st.builds(
        Edge,
        from_=node_id_strategy(),
        to=node_id_strategy(),
        edge_type=edge_type_strategy,
        evidence=st.text(min_size=1, max_size=50),
    )


class TestBidirectionalDiscovery:
    """Test the F-001 fix: bidirectional edge discovery."""

    @given(edges=st.lists(edge_strategy(), min_size=1, max_size=20))
    def test_edges_queryable_from_source(self, edges):
        """Every edge should be queryable from its source node."""
        state = BeliefState()

        for edge in edges:
            state.record_edge(edge)

        # For each edge, edges_from(edge.from_) should contain that edge
        for edge in edges:
            edges_from = state.edges_from(edge.from_)
            assert any(
                e.from_ == edge.from_ and e.to == edge.to and e.edge_type == edge.edge_type
                for e in edges_from
            ), f"Edge {edge} not found in edges_from({edge.from_})"

    @given(edges=st.lists(edge_strategy(), min_size=1, max_size=20))
    def test_edges_queryable_to_target(self, edges):
        """Every edge should be queryable to its target node (F-001 fix)."""
        state = BeliefState()

        for edge in edges:
            state.record_edge(edge)

        # For each edge, edges_to(edge.to) should contain that edge
        for edge in edges:
            edges_to = state.edges_to(edge.to)
            assert any(
                e.from_ == edge.from_ and e.to == edge.to and e.edge_type == edge.edge_type
                for e in edges_to
            ), f"Edge {edge} not found in edges_to({edge.to})"

    @given(edges=st.lists(edge_strategy(), min_size=1, max_size=20))
    def test_no_false_positives_from(self, edges):
        """edges_from should not return edges where node is not the source."""
        state = BeliefState()

        for edge in edges:
            state.record_edge(edge)

        # For each unique source node, check edges_from only returns its edges
        sources = set(e.from_ for e in edges)
        for source in sources:
            edges_from = state.edges_from(source)
            assert all(
                e.from_ == source for e in edges_from
            ), f"edges_from({source}) returned edges with different source"

    @given(edges=st.lists(edge_strategy(), min_size=1, max_size=20))
    def test_no_false_positives_to(self, edges):
        """edges_to should not return edges where node is not the target."""
        state = BeliefState()

        for edge in edges:
            state.record_edge(edge)

        # For each unique target node, check edges_to only returns its edges
        targets = set(e.to for e in edges)
        for target in targets:
            edges_to = state.edges_to(target)
            assert all(
                e.to == target for e in edges_to
            ), f"edges_to({target}) returned edges with different target"

    @given(edge=edge_strategy())
    def test_symmetric_queryability(self, edge):
        """An edge should be findable from both source and target."""
        state = BeliefState()
        state.record_edge(edge)

        # Should find edge from source
        edges_from_source = state.edges_from(edge.from_)
        assert len(edges_from_source) > 0
        assert edge in edges_from_source

        # Should find edge to target
        edges_to_target = state.edges_to(edge.to)
        assert len(edges_to_target) > 0
        assert edge in edges_to_target

    @given(
        edges=st.lists(edge_strategy(), min_size=2, max_size=20),
        query_node=node_id_strategy(),
    )
    def test_disconnected_nodes(self, edges, query_node):
        """Queries for disconnected nodes should return empty lists."""
        state = BeliefState()

        for edge in edges:
            state.record_edge(edge)

        # Check if query_node is actually in the graph
        all_nodes = set()
        for edge in edges:
            all_nodes.add(edge.from_)
            all_nodes.add(edge.to)

        if query_node not in all_nodes:
            # Node is disconnected
            assert state.edges_from(query_node) == []
            assert state.edges_to(query_node) == []

    @given(edges=st.lists(edge_strategy(), min_size=1, max_size=20))
    def test_edge_deduplication_not_enforced(self, edges):
        """Step 1 scope: edges list may contain duplicates (not deduplicated yet).
        
        This test documents the current behavior: belief_state doesn't
        automatically deduplicate. OQ-003 (edge de-duplication) is still open.
        """
        state = BeliefState()

        # Record same edge twice
        if edges:
            edge = edges[0]
            state.record_edge(edge)
            state.record_edge(edge)

            edges_from = state.edges_from(edge.from_)
            # May contain duplicates in Step 1
            # (deduplication is a decision for later)
            assert len(edges_from) >= 1
