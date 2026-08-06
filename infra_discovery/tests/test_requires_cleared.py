"""Worked-example tests: `requires`/`SWEEP-CLEARED` under the flat loop.

Per step5_agent_program.md's build-sequence Step 2. Proves two things the
AND-join fixture scenario (`and_join_topology.py`) is built to exercise:

1. A fully-discovered-and-sensed AND-join target still clears once every
   requires branch has landed (the positive case).
2. A fully-discovered-and-sensed AND-join target does NOT clear while any
   requires branch is missing - even though it has its own facets
   recorded, proving `cleared` tracks "requires satisfied," not
   "subject sensed" (the concrete bug `and-joins/environment_design.md`'s
   Purpose section names: sensed-but-not-actually-done).
"""

from infra_discovery.agents.core.agent_loop import InfraDiscoveryAgent
from infra_discovery.agents.scenarios import and_join_topology as scenario

from .test_mocks import create_fixture_action_pair, MockArtifactDAG


def _load_fixture(name: str) -> dict:
    import json

    with open(scenario.FIXTURES_DIR / name) as f:
        return json.load(f)


def _register_common_dsas(agent: InfraDiscoveryAgent) -> None:
    """Register the root and web-app DSAs, common to every test below."""
    agent.register_dsa(
        domain="github_actions",
        kind="workflow_run",
        action_pair=create_fixture_action_pair(
            _load_fixture("github_actions-workflow_run-ci.json")
        ),
        dsa_name="DSA-GH-RUN-WATCH",
    )
    agent.register_dsa(
        domain="kubernetes",
        kind="Deployment",
        action_pair=create_fixture_action_pair(
            _load_fixture("kubernetes-Deployment-web-app.json")
        ),
        dsa_name="DSA-K8S-DEPLOYMENT-GET",
    )


def test_and_join_full_topology_clears_web_app():
    """Both branches sensed: the AND-join target clears."""
    agent = InfraDiscoveryAgent(artifact_dag=MockArtifactDAG())
    _register_common_dsas(agent)
    agent.register_dsa(
        domain="github_actions",
        kind="job",
        action_pair=create_fixture_action_pair(
            _load_fixture("github_actions-job-lint.json")
        ),
        dsa_name="DSA-GH-JOB-WATCH",
    )
    agent.register_dsa(
        domain="gcp",
        kind="CloudBuild_trigger",
        action_pair=create_fixture_action_pair(
            _load_fixture("gcp-CloudBuild_trigger-integration-tests.json")
        ),
        dsa_name="DSA-GCP-BUILD-TRIGGER",
    )
    for subject, requires in scenario.requires_catalogue().items():
        agent.register_requires(subject, requires)

    result = agent.run_episode(roots=[scenario.root_node()], max_steps=100)
    assert result == "done", f"Episode ended with status: {result}"

    nodes = scenario.all_nodes()
    recorded = agent.belief_state.recorded_subjects()
    for name, node in nodes.items():
        assert node in recorded, f"{name} was never sensed"

    cleared = agent.belief_state.cleared
    for name, node in nodes.items():
        assert node in cleared, f"{name} should be cleared, isn't: {cleared}"


def test_and_join_partial_topology_blocks_web_app():
    """Only `lint` sensed, `integration-tests` never invoked: web-app must
    stay recorded-but-not-cleared, even though it has its own facets.

    Deliberately does NOT register a DSA for (gcp, CloudBuild_trigger) -
    `integration-tests` is still discovered as an edge target (RESOLVE-BRIDGES
    fires off `ci`'s fixture regardless), but RELEVANT() finds no DSA to
    enqueue for it, so it's never sensed and never enters `recorded_subjects()`
    at all - the exact OQ-017 reachability shape, deliberately triggered here
    to isolate the AND-join-blocks-clearance claim from discovery itself.
    """
    agent = InfraDiscoveryAgent(artifact_dag=MockArtifactDAG())
    _register_common_dsas(agent)
    agent.register_dsa(
        domain="github_actions",
        kind="job",
        action_pair=create_fixture_action_pair(
            _load_fixture("github_actions-job-lint.json")
        ),
        dsa_name="DSA-GH-JOB-WATCH",
    )
    for subject, requires in scenario.requires_catalogue().items():
        agent.register_requires(subject, requires)

    result = agent.run_episode(roots=[scenario.root_node()], max_steps=100)
    assert result == "done", f"Episode ended with status: {result}"

    recorded = agent.belief_state.recorded_subjects()
    cleared = agent.belief_state.cleared

    ci = scenario.root_node()
    lint = scenario.lint_node()
    integration_tests = scenario.integration_tests_node()
    web_app = scenario.web_app_node()

    # ci and lint have no requires - they clear trivially.
    assert ci in cleared
    assert lint in cleared

    # integration-tests was never sensed at all (no DSA registered for it).
    assert integration_tests not in recorded
    assert integration_tests not in cleared

    # web-app WAS sensed - it has its own facets - but its requires include
    # integration-tests, which never cleared. It must not be cleared either.
    assert web_app in recorded, "web-app should still be independently discovered/sensed"
    assert web_app not in cleared, (
        "web-app cleared despite integration-tests never landing - "
        "the AND-join gate isn't blocking clearance"
    )


def test_eligible_sweeps_cleared_every_call():
    """_eligible() must call SWEEP-CLEARED every turn, not just at episode end.

    Directly exercises the mechanism step5_agent_program.md's Step 2 is
    about: SWEEP-CLEARED as an iterative fixed-point pass running every
    turn of the flat loop, not between phases (there are no phases here).
    """
    agent = InfraDiscoveryAgent(artifact_dag=MockArtifactDAG())
    _register_common_dsas(agent)
    agent.register_dsa(
        domain="github_actions",
        kind="job",
        action_pair=create_fixture_action_pair(
            _load_fixture("github_actions-job-lint.json")
        ),
        dsa_name="DSA-GH-JOB-WATCH",
    )
    agent.register_dsa(
        domain="gcp",
        kind="CloudBuild_trigger",
        action_pair=create_fixture_action_pair(
            _load_fixture("gcp-CloudBuild_trigger-integration-tests.json")
        ),
        dsa_name="DSA-GCP-BUILD-TRIGGER",
    )
    for subject, requires in scenario.requires_catalogue().items():
        agent.register_requires(subject, requires)

    agent.pending.update(
        agent._relevant(
            agent.dsa_catalogue.get(
                (scenario.root_node().domain, scenario.root_node().kind), []
            ),
            scenario.root_node(),
        )
    )

    web_app = scenario.web_app_node()
    saw_uncleared_after_sense = False
    steps = 0
    while steps < 100:
        # web-app may already be recorded (sensed) while its requires are
        # still outstanding - that's the state this test is watching for.
        if web_app in agent.belief_state.recorded_subjects() and web_app not in agent.belief_state.cleared:
            saw_uncleared_after_sense = True
        status = agent.step()
        steps += 1
        if status in ("done", "escalated", None):
            break

    assert saw_uncleared_after_sense, (
        "never observed web-app sensed-but-not-cleared - the AND-join gate "
        "never had a chance to matter during this run"
    )
    assert web_app in agent.belief_state.cleared, "web-app should clear by run's end"
