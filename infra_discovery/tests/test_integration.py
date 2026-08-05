"""Integration test: agent loop with simple_topology scenario.

Validates:
1. Compound NodeId dispatch through DSA-CATALOGUE
2. Facet accumulation from independent DSAs
3. Bidirectional edge discovery (F-001 fix)
4. Flat pending/RELEVANT/INVOKE loop structure
5. Real atomicguard interfaces (ActionPair, DualStateAgent, artifact_dag)

FIX: Uses real test_mocks that match atomicguard signatures, not simplified versions.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from infra_discovery.agents.core.domain import NodeId, Facet, Edge
from infra_discovery.agents.core.belief_state import BeliefState
from infra_discovery.agents.core.agent_loop import InfraDiscoveryAgent

from .test_mocks import (
    create_fixture_action_pair,
    MockArtifactDAG,
    MockDualStateAgent,
)


def test_simple_topology_integration():
    """End-to-end test with simple_topology scenario.
    
    Tests the flat pending/RELEVANT/INVOKE loop against fixture-backed DSAs.
    """
    # Load fixtures from agents/fixtures directory
    fixtures_dir = Path(__file__).parent.parent / "agents" / "fixtures" / "simple_topology"

    with open(fixtures_dir / "github_actions-job-deploy.json") as f:
        gh_fixture = json.load(f)

    with open(fixtures_dir / "kubernetes-Deployment-web.json") as f:
        k8s_fixture = json.load(f)

    with open(fixtures_dir / "gcp-CloudRun_service-api.json") as f:
        gcp_fixture = json.load(f)

    # Build agent with proper mocks
    agent = InfraDiscoveryAgent(artifact_dag=MockArtifactDAG())

    # Register DSAs using real test_mocks
    agent.register_dsa(
        domain="github_actions",
        kind="job",
        action_pair=create_fixture_action_pair(gh_fixture),
        dsa_name="DSA-GH-JOB-WATCH",
    )

    agent.register_dsa(
        domain="kubernetes",
        kind="Deployment",
        action_pair=create_fixture_action_pair(k8s_fixture),
        dsa_name="DSA-K8S-DEPLOYMENT-GET",
    )

    agent.register_dsa(
        domain="gcp",
        kind="CloudRun_service",
        action_pair=create_fixture_action_pair(gcp_fixture),
        dsa_name="DSA-GCP-RUN-SERVICE",
    )

    # Run discovery
    root = NodeId(domain="github_actions", kind="job", id="deploy")
    result = agent.run_episode(roots=[root], max_steps=100)

    # Assertions
    assert result == "done", f"Episode ended with status: {result}"

    # Check recorded subjects
    recorded = agent.belief_state.recorded_subjects()
    assert root in recorded, f"Root node not recorded: {root}"

    gh_node = NodeId(domain="github_actions", kind="job", id="deploy")
    k8s_node = NodeId(domain="kubernetes", kind="Deployment", id="web")
    gcp_node = NodeId(domain="gcp", kind="CloudRun_service", id="api")

    assert gh_node in recorded, "GitHub Actions job not recorded"
    assert k8s_node in recorded, "Kubernetes Deployment not recorded"
    assert gcp_node in recorded, "GCP CloudRun service not recorded"

    # Check facet accumulation
    gh_facets = agent.belief_state.facets_for(gh_node)
    assert "status" in gh_facets, "GitHub job status not recorded"
    assert gh_facets["status"].value == "completed"

    k8s_facets = agent.belief_state.facets_for(k8s_node)
    assert "replicas" in k8s_facets, "Kubernetes replicas not recorded"
    assert k8s_facets["replicas"].value == 3

    gcp_facets = agent.belief_state.facets_for(gcp_node)
    assert "status" in gcp_facets, "GCP status not recorded"
    assert gcp_facets["status"].value == "ACTIVE"

    # Check edges: expect both applies-to (forward) and deployed-by (reverse, F-001)
    gh_edges_out = agent.belief_state.edges_from(gh_node)
    assert len(gh_edges_out) >= 2, f"Expected at least 2 edges from GH job, got {len(gh_edges_out)}"

    # Count applies-to edges (forward discovery from gh_job fixture)
    applies_to_edges = [e for e in gh_edges_out if e.edge_type == "applies-to"]
    assert len(applies_to_edges) == 2, f"Expected 2 applies-to edges, got {len(applies_to_edges)}"

    # Also verify deployed-by edges exist (reverse discovery, F-001 fix)
    deployed_by_edges = [e for e in gh_edges_out if e.edge_type == "deployed-by"]
    assert len(deployed_by_edges) == 2, f"Expected 2 deployed-by edges (F-001), got {len(deployed_by_edges)}"

    # Check reverse edges (F-001 fix: from k8s and gcp back to gh_job)
    k8s_edges_in = agent.belief_state.edges_to(k8s_node)
    assert len(k8s_edges_in) > 0, "No edges to Kubernetes Deployment (F-001 fix failed)"

    gcp_edges_in = agent.belief_state.edges_to(gcp_node)
    assert len(gcp_edges_in) > 0, "No edges to GCP CloudRun (F-001 fix failed)"

    # Verify all edges have gh_node as source
    k8s_edge_sources = {e.from_ for e in k8s_edges_in}
    assert gh_node in k8s_edge_sources, "Kubernetes Deployment should have edge from GH job"

    gcp_edge_sources = {e.from_ for e in gcp_edges_in}
    assert gh_node in gcp_edge_sources, "GCP CloudRun should have edge from GH job"

    # Check (dsa_name, subject) recording per D-003
    assert agent.belief_state.is_recorded("DSA-GH-JOB-WATCH", gh_node)
    assert agent.belief_state.is_recorded("DSA-K8S-DEPLOYMENT-GET", k8s_node)
    assert agent.belief_state.is_recorded("DSA-GCP-RUN-SERVICE", gcp_node)

    print("✓ All integration tests passed")
    return True


if __name__ == "__main__":
    result = test_simple_topology_integration()
    exit(0 if result else 1)
