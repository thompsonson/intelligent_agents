from typing import Dict

from ..core.domain import DiscoveryNode


def build_pipeline_fanout_lite() -> Dict[str, DiscoveryNode]:
    """commit -> lint, unit-tests; lint -> merge-gate; unit-tests ->
    integration-tests, merge-gate; integration-tests -> merge-gate;
    merge-gate -> deploy; deploy -> (nothing).

    Six nodes, two fan-out branch points (commit, unit-tests),
    reconvergent at merge-gate, exactly one reachable no-notifies node
    (deploy - the goal). See
    documentation/discovery/scenario.md.
    """
    return {
        "commit": DiscoveryNode(id="commit", notifies=("lint", "unit-tests")),
        "lint": DiscoveryNode(id="lint", notifies=("merge-gate",)),
        "unit-tests": DiscoveryNode(
            id="unit-tests", notifies=("integration-tests", "merge-gate")
        ),
        "integration-tests": DiscoveryNode(
            id="integration-tests", notifies=("merge-gate",)
        ),
        "merge-gate": DiscoveryNode(id="merge-gate", notifies=("deploy",)),
        "deploy": DiscoveryNode(id="deploy"),
    }


def build_pipeline_fanout_lite_gated() -> Dict[str, DiscoveryNode]:
    """Identical topology to build_pipeline_fanout_lite(), plus
    merge-gate.requires = (lint, integration-tests) - the AND-join that
    forces both forks to actually finish before merge-gate can proceed to
    deploy. `unit-tests` isn't named separately: the only way to reach
    `integration-tests` at all is by first sensing `unit-tests`, so
    `integration-tests` clearing already implies `unit-tests` did too.
    See documentation/discovery/and-joins/scenario.md.
    """
    nodes = build_pipeline_fanout_lite()
    nodes["merge-gate"] = DiscoveryNode(
        id="merge-gate",
        notifies=("deploy",),
        requires=("lint", "integration-tests"),
    )
    return nodes


def build_pipeline_fanout_lite_with_orphan_requirement() -> Dict[str, DiscoveryNode]:
    """build_pipeline_fanout_lite_gated() plus one node nobody notifies:
    release-notes, added to merge-gate.requires as a third dependency.
    release-notes is a real node (construction-time unknown-target
    validation still passes) but can never be discovered - the reachability
    violation documentation/discovery/and-joins/environment_design.md warns
    about. merge-gate can never clear; deploy is never reached.
    See documentation/discovery/and-joins/algorithm_fit.md's "Resolved: a
    scenario exercising a genuine reachability violation".
    """
    nodes = build_pipeline_fanout_lite_gated()
    nodes["release-notes"] = DiscoveryNode(id="release-notes")
    nodes["merge-gate"] = DiscoveryNode(
        id="merge-gate",
        notifies=("deploy",),
        requires=("lint", "integration-tests", "release-notes"),
    )
    return nodes
