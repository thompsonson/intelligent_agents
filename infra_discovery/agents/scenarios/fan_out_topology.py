"""Fan-out topology scenario: root → many leaves.

Demonstrates Step 1 capabilities:
- Wide discovery (root discovers N independent targets)
- Facet accumulation (same node sensed by multiple DSAs)
- Unidirectional edges (simpler than bidirectional)
- Scalability (pendulum pool doesn't explode with width)

Scenario: CI/CD job deploys to 5 independent services
- github_actions/job/deploy (root)
  → kubernetes/Service/web
  → kubernetes/Service/api
  → gcp/CloudRun_service/gateway
  → gcp/CloudRun_service/worker
  → aws/EC2_instance/cache (unimplemented — tests OQ-015 behavior)
"""

from pathlib import Path
from typing import Dict
import json

from infra_discovery.agents.core.domain import NodeId


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "fan_out_topology"


def build_fan_out_fixtures() -> None:
    """Create fixture files for fan-out scenario."""
    fixtures_dir = FIXTURES_DIR
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Root: job discovers 5 targets
    root_fixture = {
        "status": "success",
        "edges": [
            {
                "to": ["kubernetes", "Service", "web"],
                "type": "applies-to",
                "evidence": "kubectl apply -f svc-web.yaml",
            },
            {
                "to": ["kubernetes", "Service", "api"],
                "type": "applies-to",
                "evidence": "kubectl apply -f svc-api.yaml",
            },
            {
                "to": ["gcp", "CloudRun_service", "gateway"],
                "type": "applies-to",
                "evidence": "gcloud run deploy gateway --image ...",
            },
            {
                "to": ["gcp", "CloudRun_service", "worker"],
                "type": "applies-to",
                "evidence": "gcloud run deploy worker --image ...",
            },
            {
                "to": ["aws", "EC2_instance", "cache"],
                "type": "applies-to",
                "evidence": "terraform apply -target aws_instance.cache",
            },
        ],
    }

    # K8s services
    svc_web_fixture = {"replicas": 3, "ready_replicas": 3, "status": "Active"}
    svc_api_fixture = {"replicas": 2, "ready_replicas": 2, "status": "Active"}

    # GCP services
    gcp_gateway_fixture = {"status": "RUNNING", "uri": "https://gateway-xxx.run.app"}
    gcp_worker_fixture = {"status": "RUNNING", "uri": "https://worker-xxx.run.app"}

    # Write fixtures
    with open(fixtures_dir / "github_actions-job-deploy.json", "w") as f:
        json.dump(root_fixture, f, indent=2)

    with open(fixtures_dir / "kubernetes-Service-web.json", "w") as f:
        json.dump(svc_web_fixture, f, indent=2)

    with open(fixtures_dir / "kubernetes-Service-api.json", "w") as f:
        json.dump(svc_api_fixture, f, indent=2)

    with open(fixtures_dir / "gcp-CloudRun_service-gateway.json", "w") as f:
        json.dump(gcp_gateway_fixture, f, indent=2)

    with open(fixtures_dir / "gcp-CloudRun_service-worker.json", "w") as f:
        json.dump(gcp_worker_fixture, f, indent=2)


def root_node() -> NodeId:
    """Root to start discovery."""
    return NodeId("github_actions", "job", "deploy")


def expected_nodes() -> Dict[str, int]:
    """Expected discoverable nodes and their facet counts."""
    return {
        "github_actions/job/deploy": 1,  # status
        "kubernetes/Service/web": 3,  # replicas, ready_replicas, status
        "kubernetes/Service/api": 3,
        "gcp/CloudRun_service/gateway": 2,  # status, uri
        "gcp/CloudRun_service/worker": 2,
        "aws/EC2_instance/cache": 0,  # Not catalogued (OQ-015)
    }
