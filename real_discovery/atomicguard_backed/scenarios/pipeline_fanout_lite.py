from pathlib import Path
from typing import Dict

from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from ..core.domain import StatefulDiscoveryNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pipeline_fanout_lite"

# Same topology as discovery/scenarios/pipeline_fanout_lite.py, reused
# deliberately rather than reinvented - the whole point of this experiment
# is running the identical DiscoveryAgent over the identical shape, this
# time backed by real, guard-checked nodes instead of static dataclass
# fields. See documentation/discovery/atomicguard-bridge/environment_design.md.
_NODE_IDS = (
    "commit",
    "lint",
    "unit-tests",
    "integration-tests",
    "merge-gate",
    "deploy",
)

_CHECK_PROMPT = PromptTemplate(role="", constraints="", task="")


def _check_action_pair(node_id: str) -> ActionPair:
    """A real `cat` over node_id's own fixture file - a genuine subprocess
    call, real Generator/Guard/ActionPair machinery, no LLM required. The
    same deterministic, no-argument-Guard pattern
    real_task_graph_solver/atomicguard_backed/scenarios/lint_repair.py
    already proved for `ruff check`."""
    fixture = FIXTURES_DIR / f"{node_id}.json"
    return ActionPair(
        generator=SubprocessGenerator(command=["cat", str(fixture)]),
        guard=ExitCodeGuard(),
        prompt_template=_CHECK_PROMPT,
    )


def build_pipeline_fanout_lite() -> Dict[str, StatefulDiscoveryNode]:
    """commit -> lint, unit-tests; lint -> merge-gate; unit-tests ->
    integration-tests, merge-gate; integration-tests -> merge-gate;
    merge-gate -> deploy; deploy -> (nothing) - read off real fixture
    files via real `cat` calls, not declared as dataclass fields. No
    `requires` anywhere in this variant - see
    build_pipeline_fanout_lite_gated() for the AND-join version."""
    return {
        node_id: StatefulDiscoveryNode(
            id=node_id, check_action_pair=_check_action_pair(node_id)
        )
        for node_id in _NODE_IDS
    }


def build_pipeline_fanout_lite_gated() -> Dict[str, StatefulDiscoveryNode]:
    """Identical topology to build_pipeline_fanout_lite(), plus
    merge-gate.requires = (lint, integration-tests) - the same AND-join
    discovery/scenarios/pipeline_fanout_lite.py's own gated variant uses.
    `requires` is declared node config here, exactly like atomicguard's own
    WorkflowStep bundles `requires` with `action_pair` at declaration time -
    it is never itself sensed."""
    nodes = build_pipeline_fanout_lite()
    nodes["merge-gate"] = StatefulDiscoveryNode(
        id="merge-gate",
        check_action_pair=_check_action_pair("merge-gate"),
        requires=("lint", "integration-tests"),
    )
    return nodes
