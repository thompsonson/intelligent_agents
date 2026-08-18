#!/usr/bin/env python3
"""Run Step 1 capability demonstrations.

Shows what Step 1 can discover across different topology shapes:
- Simple topology (3 nodes, 4 edges)
- Fan-out topology (1 root → 5 leaves)
- Chain topology (4 hops across domains)
"""

import sys
import json
from pathlib import Path

# Add intelligent_agents to path
sys.path.insert(0, str(Path(__file__).parent))

from infra_discovery.agents.core.domain import NodeId
from infra_discovery.agents.core.agent_loop import InfraDiscoveryAgent, DSACatalogueEntry


def mock_agent_for_scenario(scenario_name: str, fixtures_dir: Path):
    """Create mocked agent for a scenario."""

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

    agent = InfraDiscoveryAgent(workflow_id=f"demo-{scenario_name}")

    # Register DSAs for all fixture files
    for fixture_file in sorted(fixtures_dir.glob("*.json")):
        # Parse filename: domain-kind-id.json
        parts = fixture_file.stem.split("-")
        if len(parts) >= 2:
            domain = parts[0]
            kind = "-".join(parts[1:-1]) if len(parts) > 2 else parts[1]

            mock_pair = MockActionPair(fixture_file)
            entry = DSACatalogueEntry(domain, kind, mock_pair)
            agent.dsa_catalogue[(domain, kind)] = entry

    # Patch invoke to use mocked DualStateAgent
    def mock_invoke(dsa_entry, subject):
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
            print(f"  ✗ Failed to invoke: {e}")
            return None

    agent.invoke = mock_invoke
    return agent


def run_scenario(scenario_name: str, root: NodeId, max_steps: int = 100):
    """Run a scenario and print results."""
    fixtures_dir = Path(__file__).parent / "infra_discovery" / "agents" / "fixtures" / scenario_name

    if not fixtures_dir.exists():
        print(f"⚠ Fixtures not found: {fixtures_dir}")
        return None

    print(f"\n{'='*70}")
    print(f"Scenario: {scenario_name.upper()}")
    print(f"{'='*70}")
    print(f"Root: {root.domain}/{root.kind}/{root.id}")
    print(f"Fixtures: {list(fixtures_dir.glob('*.json'))}")

    agent = mock_agent_for_scenario(scenario_name, fixtures_dir)
    status = agent.run_episode([root], max_steps=max_steps)

    # Print results
    discovered_nodes = agent.belief_state.facets_by_node.keys()
    edges = agent.belief_state.edges

    print(f"\nResults:")
    print(f"  Status: {status}")
    print(f"  Nodes discovered: {len(discovered_nodes)}")
    print(f"  Edges discovered: {len(edges)}")

    print(f"\nNodes:")
    for node in sorted(discovered_nodes, key=lambda n: (n.domain, n.kind, n.id)):
        facets = agent.belief_state.facets_for(node)
        facet_list = ", ".join(sorted(facets.keys()))
        print(f"    {node.domain:20} {node.kind:20} {node.id:15} → {len(facets)} facet(s): {facet_list}")

    print(f"\nEdges:")
    for edge in edges:
        print(f"    {edge.from_.domain}/{edge.from_.kind}/{edge.from_.id}")
        print(f"      --{edge.edge_type}--> {edge.to.domain}/{edge.to.kind}/{edge.to.id}")

    # Bidirectional check
    print(f"\nBidirectional verification (F-001 fix):")
    verified = 0
    for edge in edges:
        edges_from = agent.belief_state.edges_from(edge.from_)
        edges_to = agent.belief_state.edges_to(edge.to)
        from_found = any(
            e.from_ == edge.from_ and e.to == edge.to and e.edge_type == edge.edge_type
            for e in edges_from
        )
        to_found = any(
            e.from_ == edge.from_ and e.to == edge.to and e.edge_type == edge.edge_type
            for e in edges_to
        )
        if from_found and to_found:
            verified += 1
            print(f"    ✓ Edge {edge.from_.id} → {edge.to.id} queryable both ways")

    print(f"  {verified}/{len(edges)} edges verified bidirectional")

    return {
        "status": status,
        "nodes": len(discovered_nodes),
        "edges": len(edges),
        "bidirectional_verified": verified,
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("STEP 1 CAPABILITY DEMONSTRATIONS")
    print("="*70)

    results = {}

    # Simple topology
    results["simple_topology"] = run_scenario(
        "simple_topology",
        NodeId("github_actions", "job", "deploy"),
    )

    # Fan-out topology
    results["fan_out_topology"] = run_scenario(
        "fan_out_topology",
        NodeId("github_actions", "job", "deploy"),
    )

    # Chain topology
    results["chain_topology"] = run_scenario(
        "chain_topology",
        NodeId("github_actions", "job", "deploy"),
    )

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for scenario, result in results.items():
        if result:
            status = "✓ PASS" if result["status"] == "done" else f"⚠ {result['status']}"
            print(
                f"{scenario:25} {status:10} "
                f"nodes={result['nodes']:2} edges={result['edges']:2} "
                f"bidirectional={result['bidirectional_verified']}/{result['edges']}"
            )
