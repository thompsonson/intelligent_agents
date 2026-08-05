"""Simple topology scenario for Step 1 validation.

A minimal 3-node fixture scenario:
- github_actions:job-deploy (sensed first)
  → discovers kubernetes:Deployment-web via 'applies-to' edge
  → discovers gcp:CloudRun_service-api via 'applies-to' edge
- kubernetes:Deployment-web (discovered via edge)
  ← discovers github_actions:job-deploy via reverse edge (F-001 fix)
- gcp:CloudRun_service-api (discovered via edge)
  ← discovers github_actions:job-deploy via reverse edge (F-001 fix)

This validates:
1. Compound NodeId lookup in DSA-CATALOGUE
2. Facet accumulation from independent DSAs
3. Bidirectional edge discovery (F-001 fix)
4. Flat pending/RELEVANT/INVOKE loop
5. (dsa_name, subject) de-duplication per D-003
"""

from pathlib import Path
from typing import Dict

from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from ..core.domain import NodeId
from ..core.agent_loop import InfraDiscoveryAgent

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "simple_topology"


def _cat_action_pair(fixture_file: Path) -> ActionPair:
    """Create an ActionPair that cats a fixture file.
    
    Deterministic, subprocess-backed, matches real_discovery/atomicguard_backed/
    precedent.
    """
    prompt = PromptTemplate(role="", constraints="", task="")
    return ActionPair(
        generator=SubprocessGenerator(command=["cat", str(fixture_file)]),
        guard=ExitCodeGuard(),
        prompt_template=prompt,
    )


def build_simple_topology_agent() -> InfraDiscoveryAgent:
    """Build the agent with simple topology scenario.
    
    Registers three DSAs (one per node) that read from fixture JSON files.
    
    Returns:
        InfraDiscoveryAgent ready to run.
    """
    agent = InfraDiscoveryAgent()

    # Fixtures must exist (created separately)
    gh_job_fixture = FIXTURES_DIR / "github_actions-job-deploy.json"
    k8s_deployment_fixture = FIXTURES_DIR / "kubernetes-Deployment-web.json"
    gcp_cloudrun_fixture = FIXTURES_DIR / "gcp-CloudRun_service-api.json"

    # Register DSAs: (domain, kind, ActionPair, dsa_name)
    agent.register_dsa(
        domain="github_actions",
        kind="job",
        action_pair=_cat_action_pair(gh_job_fixture),
        dsa_name="DSA-GH-JOB-WATCH",
    )

    agent.register_dsa(
        domain="kubernetes",
        kind="Deployment",
        action_pair=_cat_action_pair(k8s_deployment_fixture),
        dsa_name="DSA-K8S-DEPLOYMENT-GET",
    )

    agent.register_dsa(
        domain="gcp",
        kind="CloudRun_service",
        action_pair=_cat_action_pair(gcp_cloudrun_fixture),
        dsa_name="DSA-GCP-RUN-SERVICE",
    )

    return agent


def root_nodes() -> list[NodeId]:
    """Root nodes to start discovery from.
    
    Returns:
        List with single root: github_actions/job/deploy.
    """
    return [NodeId(domain="github_actions", kind="job", id="deploy")]
