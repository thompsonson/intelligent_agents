"""AND-join topology scenario: a requires-gated deployment target.

Per step5_agent_program.md's build-sequence Step 2 ("`requires`/
`SWEEP-CLEARED`, re-validated under the flat loop"): a fixture scenario
reusing an AND-join shape, translated from `discovery/`'s
`documentation/discovery/and-joins/scenario.md` (`merge-gate.requires =
(lint, integration-tests)`) into this ontology's typed nodes.

Topology:
- github_actions/workflow_run/ci (root)
  -> github_actions/job/lint                  (edge_type "triggers")
  -> gcp/CloudBuild_trigger/integration-tests  (edge_type "triggers")
  -> kubernetes/Deployment/web-app             (edge_type "applies-to")
- github_actions/job/lint                       (leaf, requires=())
- gcp/CloudBuild_trigger/integration-tests       (leaf, requires=())
- kubernetes/Deployment/web-app                  (leaf, requires=(lint, integration-tests))

Every node is a distinct `(domain, kind)` pair on purpose - `DSACatalogueEntry`
binds one fixed fixture per registration, so two sibling nodes needing
*different* content can't safely share a `(domain, kind)` key yet (nothing
in the current flat loop parameterizes a DSA's content by subject id; two
DSAs registered under the same key both fire against every subject of that
kind, per D-003's "run all applicable sensing DSAs" - correct for genuinely
different DSAs on one kind, wrong for reusing one kind to mean "another
instance"). Real infrastructure backs this up anyway: a lint check
(`github_actions/job`) and an integration-test run (commonly a
`gcp/CloudBuild_trigger` kicked off by the workflow, not a second GH job)
are plausibly different kinds, not a modeling shortcut.

`web-app` is discovered directly off the root workflow_run - independent of
the lint/integration-test branches, mirroring a real deploy step triggered
in parallel with CI checks - but per RECORD-REQUIRES's static declaration
below, it can only enter `belief_state.cleared` once *both* `lint` and
`integration-tests` have themselves been sensed and cleared. This is the
concrete case `and-joins/environment_design.md`'s own Purpose section
names: an AND-join node that's fully reachable and sensed is still not
"done" until every prerequisite branch has actually finished.
"""

from pathlib import Path
from typing import Dict, Tuple
import json

from infra_discovery.agents.core.domain import NodeId


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "and_join_topology"


def build_and_join_fixtures() -> None:
    """Create fixture files for the AND-join scenario."""
    fixtures_dir = FIXTURES_DIR
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    ci_fixture = {
        "conclusion": "success",
        "edges": [
            {
                "to": ["github_actions", "job", "lint"],
                "type": "triggers",
                "evidence": "workflow fan-out: ci triggers lint job",
            },
            {
                "to": ["gcp", "CloudBuild_trigger", "integration-tests"],
                "type": "triggers",
                "evidence": "workflow fan-out: ci triggers integration-tests build",
            },
            {
                "to": ["kubernetes", "Deployment", "web-app"],
                "type": "applies-to",
                "evidence": "step: kubectl apply -f web-app.yaml",
            },
        ],
    }

    lint_fixture = {
        "conclusion": "success",
    }

    integration_tests_fixture = {
        "status": "SUCCESS",
    }

    web_app_fixture = {
        "status": "Progressing",
    }

    with open(fixtures_dir / "github_actions-workflow_run-ci.json", "w") as f:
        json.dump(ci_fixture, f, indent=2)

    with open(fixtures_dir / "github_actions-job-lint.json", "w") as f:
        json.dump(lint_fixture, f, indent=2)

    with open(fixtures_dir / "gcp-CloudBuild_trigger-integration-tests.json", "w") as f:
        json.dump(integration_tests_fixture, f, indent=2)

    with open(fixtures_dir / "kubernetes-Deployment-web-app.json", "w") as f:
        json.dump(web_app_fixture, f, indent=2)


def root_node() -> NodeId:
    """Root to start discovery."""
    return NodeId("github_actions", "workflow_run", "ci")


def lint_node() -> NodeId:
    return NodeId("github_actions", "job", "lint")


def integration_tests_node() -> NodeId:
    return NodeId("gcp", "CloudBuild_trigger", "integration-tests")


def web_app_node() -> NodeId:
    return NodeId("kubernetes", "Deployment", "web-app")


def requires_catalogue() -> Dict[NodeId, Tuple[NodeId, ...]]:
    """Static, catalogue-declared requires per step5_agent_program.md Step 2.

    Only `web-app` has a real AND-join gate; everything else clears
    trivially (requires=()), same as every node in every scenario before
    this one - `requires` existing at all doesn't change behavior for
    graphs that don't use it.
    """
    return {
        web_app_node(): (lint_node(), integration_tests_node()),
    }


def all_nodes() -> Dict[str, NodeId]:
    """All nodes in the topology, by short name."""
    return {
        "ci": root_node(),
        "lint": lint_node(),
        "integration-tests": integration_tests_node(),
        "web-app": web_app_node(),
    }
