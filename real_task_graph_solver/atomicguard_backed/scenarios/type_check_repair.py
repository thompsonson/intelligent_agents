from pathlib import Path
from typing import Dict, Optional, Tuple

from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)
from atomicguard.infrastructure.gym.precommit_generators import (
    LLMContainerFixGenerator,
)
from atomicguard.infrastructure.guards.container_subprocess_guard import (
    ContainerSubprocessGuard,
)

from ..core.domain import AtomicGuardCheckNode
from ..core.llm_config import DEFAULT_MODEL, OPENROUTER_PROVIDER, openrouter_api_key

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "example_pkg"

# Reuses real_task_graph_solver/fixtures/example_pkg unmodified - the
# manufactured break is a return-type annotation that says `str` but a
# function that returns `float`. See
# documentation/task-graph/atomicguard-variant/environment_design.md.
BROKEN_STATES = {"type-check": "typing_broken"}

_CHECK_PROMPT = PromptTemplate(role="", constraints="", task="")

_REPAIR_PROMPT = PromptTemplate(
    role="You are a Python developer fixing a type-checking error flagged by mypy.",
    constraints=(
        "Preserve all existing behavior and formatting except what is needed "
        "to satisfy mypy. Do not add unrelated changes, comments, or imports."
    ),
    task=(
        "The file below fails `mypy` with the feedback shown. Fix the type "
        "error and return the complete, corrected file content."
    ),
    # Required whenever feedback_history is non-empty (PromptTemplate.render()
    # raises ValueError otherwise, caught only by an actual dry run against a
    # real DualStateAgent - see environment_design.md's "Not decided" note on
    # this). feedback_history is non-empty on this repair's very first call:
    # check_action_pair and repair_action_pair share one action_pair_id, so
    # the check's real rejection is already in the shared DAG before
    # LLMContainerFixGenerator.generate() ever runs.
    feedback_wrapper="mypy reported this error:\n{feedback}",
)


def build_type_check_repair(
    workdir: Path,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
) -> Tuple[Dict[str, AtomicGuardCheckNode], str]:
    """One node, `type-check`, whose check_action_pair is a free `mypy
    src/` sensor and whose repair_action_pair is a real, LLM-based fix -
    unlike lint/build-check, no auto-fix tool understands *intended*
    types, so this needs an LLM to read mypy's real error and correct
    the annotation. See
    documentation/task-graph/atomicguard-variant/environment_design.md.

    Uses atomicguard's own `LLMContainerFixGenerator` (host mode,
    `container_id=None`) against OpenRouter - `model` defaults to
    `llm_config.DEFAULT_MODEL` (see that module for why neither
    candidate model's exact slug could be verified from this sandbox).
    `api_key` defaults to `None`, meaning "resolve from the real OR_KEY
    environment variable" via `llm_config.openrouter_api_key()"` (raises
    immediately, with a clear message, if unset) - pass an explicit
    `api_key` (e.g. in tests) to bypass that requirement entirely.

    `ContainerSubprocessGuard`, unlike `SubprocessGenerator`, has no
    `cwd` parameter - its own `validate()` always runs the command
    relative to the current process's cwd. Worked around here the same
    way `release_pipeline.py`'s marker commands do: wrap the real
    command in a `cd {workdir} &&` shell prefix, rather than patching
    atomicguard.

    `workdir` must be decided before calling this - see
    `lint_repair.build_lint_repair`'s docstring for why (atomicguard's
    generators/guards don't resolve `cwd` lazily per call).
    """
    workdir = Path(workdir)
    target_path = workdir / "src" / "example_pkg" / "domain.py"
    resolved_api_key = api_key if api_key is not None else openrouter_api_key()

    check_action_pair = ActionPair(
        generator=SubprocessGenerator(command=["mypy", "src/"], cwd=str(workdir)),
        guard=ExitCodeGuard(),
        prompt_template=_CHECK_PROMPT,
    )
    repair_action_pair = ActionPair(
        generator=LLMContainerFixGenerator(
            model=model,
            provider=OPENROUTER_PROVIDER,
            base_url="",
            api_key=resolved_api_key,
            container_id=None,
            target_path=str(target_path),
        ),
        guard=ContainerSubprocessGuard(
            command=["sh", "-c", f"cd {workdir} && mypy src/"],
            container_id=None,
        ),
        prompt_template=_REPAIR_PROMPT,
    )

    nodes = {
        "type-check": AtomicGuardCheckNode(
            id="type-check",
            check_action_pair=check_action_pair,
            repair_action_pair=repair_action_pair,
        )
    }

    return nodes, "type-check"
