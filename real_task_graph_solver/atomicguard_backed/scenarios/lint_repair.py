from pathlib import Path
from typing import Dict, Tuple

from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from ..core.domain import AtomicGuardCheckNode

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "example_pkg"

# Reuses real_task_graph_solver/fixtures/example_pkg unmodified - same
# manufactured break as RealCheckEnvironment's "lint" node: one unused
# import (F401) in src/example_pkg/domain.py. See
# documentation/task-graph/atomicguard-variant/environment_design.md.
BROKEN_STATES = {"lint": "lint_broken"}

_LINT_PROMPT = PromptTemplate(role="", constraints="", task="")


def build_lint_repair(workdir: Path) -> Tuple[Dict[str, AtomicGuardCheckNode], str]:
    """One node, `lint`, whose check_action_pair is a free `ruff check
    src/` sensor and whose repair_action_pair is a real
    `ruff check --fix src/` - the deterministic, no-LLM repair path the
    design doc recommends building first. `workdir` must be decided
    before calling this: atomicguard's SubprocessGenerator bakes `cwd` in
    at construction, unlike RealCheckNode's command tuples which resolve
    `cwd` lazily at each check - see AtomicGuardCheckEnvironment's
    docstring for why. The directory need not exist yet; only
    env.reset_to_state() needs it to.

    Returns a (nodes, goal) tuple ready to unpack into
    AtomicGuardCheckEnvironment(nodes, fixtures_dir=FIXTURES_DIR,
    workdir=workdir, goal=goal, broken_states=BROKEN_STATES).
    """
    workdir = Path(workdir)

    check_action_pair = ActionPair(
        generator=SubprocessGenerator(
            command=["ruff", "check", "src/"], cwd=str(workdir)
        ),
        guard=ExitCodeGuard(),
        prompt_template=_LINT_PROMPT,
    )
    repair_action_pair = ActionPair(
        generator=SubprocessGenerator(
            command=["ruff", "check", "--fix", "src/"], cwd=str(workdir)
        ),
        guard=ExitCodeGuard(),
        prompt_template=_LINT_PROMPT,
    )

    nodes = {
        "lint": AtomicGuardCheckNode(
            id="lint",
            check_action_pair=check_action_pair,
            repair_action_pair=repair_action_pair,
        )
    }

    return nodes, "lint"
