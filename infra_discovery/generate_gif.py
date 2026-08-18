#!/usr/bin/env python3
"""Generate an animated GIF of InfraDiscoveryAgent's Step 1 discovery loop.

Uses the same fixture-backed simple_topology scenario and the same
test_mocks.py (real-atomicguard-interface-shaped) mocks test_integration.py
already validates, not a separate ad hoc mock - so the GIF shows the same
code path the passing tests exercise, not a prettier stand-in for it.

Run:
    PYTHONPATH=. python3 infra_discovery/generate_gif.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from infra_discovery.agents.core.agent_loop import InfraDiscoveryAgent
from infra_discovery.agents.core.domain import NodeId
from infra_discovery.agents.visualization.infra_discovery_view import animate_discovery
from infra_discovery.tests.test_mocks import MockArtifactDAG, create_fixture_action_pair


def build_agent(scenario: str) -> InfraDiscoveryAgent:
    fixtures_dir = Path(__file__).parent / "agents" / "fixtures" / scenario
    agent = InfraDiscoveryAgent(
        artifact_dag=MockArtifactDAG(), workflow_id=f"gif-{scenario}"
    )

    # (domain, kind, dsa_name) inferred from filename: domain-kind-id.json
    for fixture_path in sorted(fixtures_dir.glob("*.json")):
        with open(fixture_path) as f:
            content = json.load(f)
        domain, kind, node_id = fixture_path.stem.split("-", 2)
        agent.register_dsa(
            domain=domain,
            kind=kind,
            action_pair=create_fixture_action_pair(content),
            dsa_name=f"DSA-{domain.upper()}-{kind.upper()}-{node_id.upper()}",
        )

    return agent


def main() -> None:
    animations_dir = Path(__file__).parent / "animations"
    animations_dir.mkdir(exist_ok=True)

    agent = build_agent("simple_topology")
    root = NodeId(domain="github_actions", kind="job", id="deploy")

    save_path = str(animations_dir / "simple_topology.gif")
    frames = animate_discovery(
        agent,
        roots=[root],
        save_path=save_path,
        fps=0.8,
        title="Infra Discovery Step 1: simple_topology",
    )

    print(f"Wrote {len(frames)} frames to {save_path}")
    for i, frame in enumerate(frames):
        print(f"  {i + 1}. {frame.caption}")


if __name__ == "__main__":
    main()
