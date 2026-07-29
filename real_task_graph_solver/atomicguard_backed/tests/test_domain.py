from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from real_task_graph_solver.atomicguard_backed.core.domain import AtomicGuardCheckNode


def make_action_pair(command):
    return ActionPair(
        generator=SubprocessGenerator(command=command),
        guard=ExitCodeGuard(),
        prompt_template=PromptTemplate(role="", constraints="", task=""),
    )


class TestAtomicGuardCheckNode:
    def test_holds_id_check_action_pair_and_requires(self):
        check_ap = make_action_pair(["true"])
        node = AtomicGuardCheckNode(id="lint", check_action_pair=check_ap)

        assert node.id == "lint"
        assert node.check_action_pair is check_ap
        assert node.requires == ()

    def test_repair_action_pair_defaults_to_none(self):
        node = AtomicGuardCheckNode(
            id="lint", check_action_pair=make_action_pair(["true"])
        )
        assert node.repair_action_pair is None

    def test_repair_action_pair_can_be_set(self):
        check_ap = make_action_pair(["true"])
        repair_ap = make_action_pair(["true"])
        node = AtomicGuardCheckNode(
            id="lint", check_action_pair=check_ap, repair_action_pair=repair_ap
        )
        assert node.repair_action_pair is repair_ap

    def test_requires_can_be_set(self):
        node = AtomicGuardCheckNode(
            id="release-ready",
            check_action_pair=make_action_pair(["true"]),
            requires=("lint",),
        )
        assert node.requires == ("lint",)
