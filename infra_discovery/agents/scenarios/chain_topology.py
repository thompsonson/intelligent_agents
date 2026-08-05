"""Chain topology scenario: sequential discovery across domains.

Demonstrates Step 1 capabilities:
- Cross-domain traversal (GH → K8s → GCP → external)
- Deep discovery (linear chain, not fan-out)
- Bidirectional edges at each hop
- Dead-end detection (external service, no DSA)

Scenario: Deploy flow traces through 4 hops
- github_actions/job/deploy
  → kubernetes/Deployment/api (via applies-to)
  ← kubernetes/Deployment/api (via deployed-by — F-001)
  → gcp/CloudRun_service/backend (via enables)
  ← gcp/CloudRun_service/backend (via enabled-by — F-001)
  → external/database/postgres (no DSA — dead-end)
"""

from pathlib import Path
import json

from infra_discovery.agents.core.domain import NodeId


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "chain_topology"


def build_chain_fixtures() -> None:
    """Create fixture files for chain scenario."""
    fixtures_dir = FIXTURES_DIR
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Deploy job
    job_fixture = {
        "status": "success",
        "edges": [
            {
                "to": ["kubernetes", "Deployment", "api"],
                "type": "applies-to",
                "evidence": "step: kubectl apply -f deployment.yaml",
            },
        ],
    }

    # Step 2: K8s deployment (discovered, then discovers backend)
    deploy_fixture = {
        "replicas": 2,
        "ready": 2,
        "edges": [
            {
                "to": ["gcp", "CloudRun_service", "backend"],
                "type": "enables",
                "evidence": "selector matches GCP workload identity",
            },
            {
                "to": ["github_actions", "job", "deploy"],
                "type": "deployed-by",
                "evidence": "metadata.ownerReferences (F-001 reverse)",
            },
        ],
    }

    # Step 3: GCP backend (discovered, then discovers database)
    backend_fixture = {
        "status": "RUNNING",
        "replicas": 4,
        "edges": [
            {
                "to": ["external", "database", "postgres"],
                "type": "depends-on-external",
                "evidence": "CLOUDSQL_CONNECTION_NAME env var",
            },
            {
                "to": ["kubernetes", "Deployment", "api"],
                "type": "enabled-by",
                "evidence": "ingress from K8s namespace (F-001 reverse)",
            },
        ],
    }

    # Step 4: External database (not catalogued — dead-end)
    # (no fixture, will fail RELEVANT check)

    # Write fixtures
    with open(fixtures_dir / "github_actions-job-deploy.json", "w") as f:
        json.dump(job_fixture, f, indent=2)

    with open(fixtures_dir / "kubernetes-Deployment-api.json", "w") as f:
        json.dump(deploy_fixture, f, indent=2)

    with open(fixtures_dir / "gcp-CloudRun_service-backend.json", "w") as f:
        json.dump(backend_fixture, f, indent=2)


def root_node() -> NodeId:
    """Root to start discovery."""
    return NodeId("github_actions", "job", "deploy")


def expected_discovery() -> dict:
    """Expected discovery trace."""
    return {
        "nodes_discovered": 3,  # job, deployment, backend (external unregistered)
        "edges": 5,  # 2 forward, 3 reverse (F-001)
        "max_depth": 3,
        "dead_ends": 1,  # external/database/postgres (OQ-015)
    }
