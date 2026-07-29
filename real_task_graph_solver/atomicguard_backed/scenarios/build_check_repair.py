import sys
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
# manufactured break as RealCheckEnvironment's "build-check" node: no
# `version` field (and no `dynamic = ["version"]` either) in pyproject.toml,
# so hatchling's build_sdist genuinely fails. See
# documentation/task-graph/atomicguard-variant/environment_design.md.
BROKEN_STATES = {"build-check": "publish_broken"}

_BUILD_PROMPT = PromptTemplate(role="", constraints="", task="")

# The second deterministic, no-LLM repair the design doc sketches
# alongside `lint`: "add a version field" needs a fixed edit, not an
# LLM's judgement about *what* to write. Inserted right after the
# `[project]` header - table-key order doesn't matter to TOML, and this
# leaves everything else in the file untouched.
_ADD_VERSION_COMMAND = (
    "sh",
    "-c",
    "sed -i '/^\\[project\\]/a version = \"0.1.0\"' pyproject.toml",
)


def build_build_check_repair(
    workdir: Path,
) -> Tuple[Dict[str, AtomicGuardCheckNode], str]:
    """One node, `build-check`, whose check_action_pair is a free
    `python -m build --sdist --wheel` sensor and whose repair_action_pair
    is a real, deterministic `sed` edit adding the missing `version`
    field - no LLM needed, same reasoning as `lint_repair.build_lint_repair`.
    `workdir` must be decided before calling this - see that function's
    docstring for why (atomicguard's SubprocessGenerator bakes `cwd` in at
    construction).

    Returns a (nodes, goal) tuple ready to unpack into
    AtomicGuardCheckEnvironment(nodes, fixtures_dir=FIXTURES_DIR,
    workdir=workdir, goal=goal, broken_states=BROKEN_STATES).
    """
    workdir = Path(workdir)
    python = sys.executable

    check_action_pair = ActionPair(
        generator=SubprocessGenerator(
            command=[
                python,
                "-m",
                "build",
                "--no-isolation",
                "--sdist",
                "--wheel",
                "--outdir",
                "dist",
            ],
            cwd=str(workdir),
        ),
        guard=ExitCodeGuard(),
        prompt_template=_BUILD_PROMPT,
    )
    repair_action_pair = ActionPair(
        generator=SubprocessGenerator(
            command=list(_ADD_VERSION_COMMAND), cwd=str(workdir)
        ),
        guard=ExitCodeGuard(),
        prompt_template=_BUILD_PROMPT,
    )

    nodes = {
        "build-check": AtomicGuardCheckNode(
            id="build-check",
            check_action_pair=check_action_pair,
            repair_action_pair=repair_action_pair,
        )
    }

    return nodes, "build-check"
