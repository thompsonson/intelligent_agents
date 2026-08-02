from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from real_discovery.atomicguard_backed.core.domain import StatefulDiscoveryNode


def make_action_pair(command):
    return ActionPair(
        generator=SubprocessGenerator(command=command),
        guard=ExitCodeGuard(),
        prompt_template=PromptTemplate(role="", constraints="", task=""),
    )


class TestStatefulDiscoveryNode:
    def test_holds_id_and_check_action_pair(self):
        check_ap = make_action_pair(["true"])
        node = StatefulDiscoveryNode(id="commit", check_action_pair=check_ap)

        assert node.id == "commit"
        assert node.check_action_pair is check_ap

    def test_requires_defaults_to_empty(self):
        node = StatefulDiscoveryNode(
            id="commit", check_action_pair=make_action_pair(["true"])
        )
        assert node.requires == ()

    def test_requires_can_be_set(self):
        node = StatefulDiscoveryNode(
            id="merge-gate",
            check_action_pair=make_action_pair(["true"]),
            requires=("lint", "integration-tests"),
        )
        assert node.requires == ("lint", "integration-tests")

    def test_has_no_notifies_field(self):
        # notifies isn't node config here - it's read off the check's own
        # Artifact content at sense time. See core/environment.py's
        # sense_edges() and environment_design.md's "Where notifies lives".
        node = StatefulDiscoveryNode(
            id="commit", check_action_pair=make_action_pair(["true"])
        )
        assert not hasattr(node, "notifies")

    def test_has_no_repair_action_pair_field(self):
        # Small steps: this experiment is solely about making nodes
        # stateful, not about repair. See environment_design.md.
        node = StatefulDiscoveryNode(
            id="commit", check_action_pair=make_action_pair(["true"])
        )
        assert not hasattr(node, "repair_action_pair")
