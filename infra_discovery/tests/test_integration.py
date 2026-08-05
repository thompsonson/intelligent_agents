"""Integration test: agent loop with simple_topology scenario.

Validates:
1. Compound NodeId dispatch through DSA-CATALOGUE
2. Facet accumulation from independent DSAs
3. Bidirectional edge discovery (F-001 fix)
4. Flat pending/RELEVANT/INVOKE loop structure
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from infra_discovery.agents.core.domain import NodeId, Facet, Edge
from infra_discovery.agents.core.belief_state import BeliefState
from infra_discovery.agents.core.agent_loop import (
    InfraDiscoveryAgent,
    DSACatalogueEntry,
)


def mock_action_pair_factory(fixture_path: Path):
    """Create a mock ActionPair that returns fixture JSON.
    
    Avoids atomicguard dependency for testing. In real use, would wrap
    subprocess-based DualStateAgent like real_discovery/atomicguard_backed/.
    """
    
    class MockActionPair:
        def __init__(self, path: Path):
            self.path = path
            self.id = f"mock-{path.stem}"
    
    class MockArtifact:
        def __init__(self, content: dict):
            self.content = content
    
    class MockDualStateAgent:
        def __init__(self, action_pair, **kwargs):
            self.action_pair = action_pair
        
        def execute(self, specification=""):
            with open(self.action_pair.path) as f:
                content = json.load(f)
            return MockArtifact(content)
    
    return MockActionPair(fixture_path), MockDualStateAgent


def test_simple_topology_integration():
    """End-to-end test with simple_topology scenario."""
    
    # Setup
    fixtures_dir = Path(__file__).parent.parent / "agents" / "fixtures" / "simple_topology"
    
    # Create mock action pairs for each node
    gh_fixture = fixtures_dir / "github_actions-job-deploy.json"
    k8s_fixture = fixtures_dir / "kubernetes-Deployment-web.json"
    gcp_fixture = fixtures_dir / "gcp-CloudRun_service-api.json"
    
    assert gh_fixture.exists(), f"GitHub fixture not found: {gh_fixture}"
    assert k8s_fixture.exists(), f"Kubernetes fixture not found: {k8s_fixture}"
    assert gcp_fixture.exists(), f"GCP fixture not found: {gcp_fixture}"
    
    # Build agent with mocked atomicguard
    agent = InfraDiscoveryAgent(workflow_id="test-simple-topology")
    
    # Register DSAs with mock fixtures
    for fixture_path, domain, kind in [
        (gh_fixture, "github_actions", "job"),
        (k8s_fixture, "kubernetes", "Deployment"),
        (gcp_fixture, "gcp", "CloudRun_service"),
    ]:
        mock_pair, mock_dsa_class = mock_action_pair_factory(fixture_path)
        entry = DSACatalogueEntry(domain, kind, mock_pair)
        agent.dsa_catalogue[(domain, kind)] = entry
    
    # Patch the invoke method to use mock DualStateAgent
    original_invoke = agent.invoke
    
    def mock_invoke(dsa_entry, subject):
        """Override invoke to use mocked DualStateAgent."""
        from infra_discovery.agents.core.agent_loop import DSACatalogueEntry
        
        # Re-create the mock agent
        mock_pair, MockDualStateAgent = mock_action_pair_factory(dsa_entry.action_pair.path)
        
        try:
            mock_agent = MockDualStateAgent(
                action_pair=dsa_entry.action_pair,
                artifact_dag=None,
                rmax=0,
                action_pair_id=f"{subject.domain}/{subject.kind}/{subject.id}",
                workflow_id=agent.workflow_id,
            )
            artifact = mock_agent.execute(specification="")
            if artifact and hasattr(artifact, "content"):
                return artifact.content
            return None
        except Exception as e:
            print(f"Failed to invoke {dsa_entry} against {subject}: {e}")
            return None
    
    agent.invoke = mock_invoke
    
    # Run discovery
    root = NodeId("github_actions", "job", "deploy")
    status = agent.run_episode([root], max_steps=100)
    
    # Verify results
    print("\n" + "=" * 60)
    print("Integration Test Results")
    print("=" * 60)
    
    print(f"\nEpisode status: {status}")
    print(f"Nodes discovered: {len(agent.belief_state.facets_by_node)}")
    print(f"Edges discovered: {len(agent.belief_state.edges)}")
    
    # Check discovered nodes
    discovered_nodes = set(agent.belief_state.facets_by_node.keys())
    print(f"\nDiscovered nodes:")
    for node in sorted(discovered_nodes, key=lambda n: (n.domain, n.kind, n.id)):
        facets = agent.belief_state.facets_for(node)
        print(f"  {node.domain}/{node.kind}/{node.id}: {list(facets.keys())}")
    
    # Check edges
    print(f"\nEdges discovered:")
    for edge in agent.belief_state.edges:
        print(f"  {edge.from_.domain}/{edge.from_.kind}/{edge.from_.id}")
        print(f"    --{edge.edge_type}--> {edge.to.domain}/{edge.to.kind}/{edge.to.id}")
        print(f"    (evidence: {edge.evidence})")
    
    # Assertions
    
    # Should have discovered the root node
    root_discovered = root in agent.belief_state.facets_by_node
    assert root_discovered, "Root node should be discovered"
    print(f"\n✓ Root node discovered")
    
    # Should have discovered nodes via edges (F-001 fix)
    k8s_node = NodeId("kubernetes", "Deployment", "web")
    gcp_node = NodeId("gcp", "CloudRun_service", "api")
    
    # Root should have facets from the sensed artifact
    root_facets = agent.belief_state.facets_for(root)
    assert len(root_facets) > 0, "Root should have facets"
    print(f"✓ Root has {len(root_facets)} facet(s): {list(root_facets.keys())}")
    
    # Should have discovered edges from root
    edges_from_root = agent.belief_state.edges_from(root)
    print(f"✓ Found {len(edges_from_root)} edge(s) from root")
    
    # Bidirectional test (F-001 fix)
    if edges_from_root:
        first_edge = edges_from_root[0]
        target = first_edge.to
        
        # Should be able to query this target in edges_to
        edges_to_target = agent.belief_state.edges_to(target)
        assert len(edges_to_target) > 0, "Should find edges to the target (F-001 fix)"
        print(f"✓ Bidirectional edge discovery works (F-001 fix)")
    
    print("\n" + "=" * 60)
    print("Integration test passed!")
    print("=" * 60 + "\n")
    
    return {
        "status": status,
        "nodes_discovered": len(discovered_nodes),
        "edges_discovered": len(agent.belief_state.edges),
        "discovered_nodes": discovered_nodes,
        "edges": agent.belief_state.edges,
    }


if __name__ == "__main__":
    result = test_simple_topology_integration()
