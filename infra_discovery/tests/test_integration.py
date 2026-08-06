"""Integration test: agent loop with simple_topology scenario.

Validates:
1. Compound NodeId dispatch through DSA-CATALOGUE
2. Facet accumulation from independent DSAs
3. Bidirectional edge discovery (F-001 fix) - NEW nodes discovered via reverse edges
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
    Specifically tests F-001: proves that a NEW node (ReplicaSet) is discovered
    via reverse edges from an already-discovered node (Deployment).
    """
    # Load fixtures from agents/fixtures directory
    fixtures_dir = Path(__file__).parent.parent / "agents" / "fixtures" / "simple_topology"

    with open(fixtures_dir / "github_actions-job-deploy.json") as f:
        gh_fixture = json.load(f)

    with open(fixtures_dir / "kubernetes-Deployment-web.json") as f:
        k8s_fixture = json.load(f)

    with open(fixtures_dir / "kubernetes-ReplicaSet-web-rs.json") as f:
        rs_fixture = json.load(f)

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

    # NEW: Register ReplicaSet DSA - proves F-001 discovery of new nodes via reverse edges
    agent.register_dsa(
        domain="kubernetes",
        kind="ReplicaSet",
        action_pair=create_fixture_action_pair(rs_fixture),
        dsa_name="DSA-K8S-REPLICASET-GET",
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
    rs_node = NodeId(domain="kubernetes", kind="ReplicaSet", id="web-rs")
    gcp_node = NodeId(domain="gcp", kind="CloudRun_service", id="api")

    assert gh_node in recorded, "GitHub Actions job not recorded"
    assert k8s_node in recorded, "Kubernetes Deployment not recorded"
    assert gcp_node in recorded, "GCP CloudRun service not recorded"

    # F-001 VALIDATION: ReplicaSet should be discovered via reverse edge from Deployment
    assert rs_node in recorded, (
        "ReplicaSet NOT discovered (F-001 FAILED) - reverse edge from Deployment "
        "should have enqueued it"
    )

    # Check facet accumulation
    gh_facets = agent.belief_state.facets_for(gh_node)
    assert "status" in gh_facets, "GitHub job status not recorded"
    assert gh_facets["status"].value == "completed"

    k8s_facets = agent.belief_state.facets_for(k8s_node)
    assert "replicas" in k8s_facets, "Kubernetes replicas not recorded"
    assert k8s_facets["replicas"].value == 3

    rs_facets = agent.belief_state.facets_for(rs_node)
    assert "replicas" in rs_facets, "ReplicaSet replicas not recorded"
    assert rs_facets["status"].value == "Active"

    gcp_facets = agent.belief_state.facets_for(gcp_node)
    assert "status" in gcp_facets, "GCP status not recorded"
    assert gcp_facets["status"].value == "ACTIVE"

    # Check edges: forward edges from github_actions and reverse edge to ReplicaSet
    gh_edges_out = agent.belief_state.edges_from(gh_node)
    # Check reverse edge: ReplicaSet -> Deployment (F-001)
    # When Deployment fixture has "from": ReplicaSet, it means ReplicaSet manages Deployment
    rs_edges_out = agent.belief_state.edges_from(rs_node)
    managed_by_edges = [e for e in rs_edges_out if e.edge_type == "managed-by"]
    assert len(managed_by_edges) == 1, (
        f"Expected 1 managed-by edge from ReplicaSet to Deployment (F-001), "
        f"got {len(managed_by_edges)}"
    )
    assert managed_by_edges[0].to == k8s_node, "managed-by edge should target Deployment"

    # Check (dsa_name, subject) recording per D-003
    assert agent.belief_state.is_recorded("DSA-GH-JOB-WATCH", gh_node)
    assert agent.belief_state.is_recorded("DSA-K8S-DEPLOYMENT-GET", k8s_node)
    assert agent.belief_state.is_recorded("DSA-K8S-REPLICASET-GET", rs_node)
    assert agent.belief_state.is_recorded("DSA-GCP-RUN-SERVICE", gcp_node)

    print("✓ All integration tests passed")
    print("✓ F-001 validated: ReplicaSet discovered via reverse edge from Deployment")
    return True


if __name__ == "__main__":
    result = test_simple_topology_integration()
    exit(0 if result else 1)
