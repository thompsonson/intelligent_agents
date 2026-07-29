import sys
from pathlib import Path
from typing import Dict, Tuple

from ..core.domain import RealCheckNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "example_pkg"

# Node id -> fixture state name where exactly that node's real check fails.
# "unit-tests" has no manufactured failure yet - see
# documentation/task-graph/real-guards/environment_design.md's "Not decided".
BROKEN_STATES = {
    "type-check": "typing_broken",
    "lint": "lint_broken",
    "architecture-test": "architecture_broken",
    "build-check": "publish_broken",
}


def _marker_command(check_command: str, marker: str) -> Tuple[str, ...]:
    """Run `check_command`; on success (and only on success, since `&&`
    short-circuits) touch a status marker file. `release-ready` reads
    these markers rather than re-running the other five checks itself -
    the same pattern GitHub branch protection uses (query stored check
    status, don't re-derive it) and the reason `release-ready`'s own
    check is genuinely non-vacuous rather than an always-true no-op."""
    return (
        "sh",
        "-c",
        f"{check_command} && mkdir -p .status && touch .status/{marker}",
    )


def build_release_pipeline() -> Tuple[Dict[str, RealCheckNode], str]:
    """Five independent real checks feeding one AND-join, `release-ready` -
    see documentation/task-graph/real-guards/environment_design.md.

    Returns a (nodes, goal) tuple ready to unpack into
    RealCheckEnvironment(nodes, config, fixtures_dir=FIXTURES_DIR,
    goal=goal, broken_states=BROKEN_STATES).
    """
    python = sys.executable

    nodes: Dict[str, RealCheckNode] = {
        "type-check": RealCheckNode(
            id="type-check",
            command=_marker_command("mypy src/", "type-check.ok"),
        ),
        "lint": RealCheckNode(
            id="lint",
            command=_marker_command("ruff check src/", "lint.ok"),
        ),
        "architecture-test": RealCheckNode(
            id="architecture-test",
            command=_marker_command(
                f"{python} -m pytest tests/architecture/ -q", "architecture-test.ok"
            ),
        ),
        "unit-tests": RealCheckNode(
            id="unit-tests",
            command=_marker_command(
                f"{python} -m pytest tests/ --ignore=tests/architecture -q",
                "unit-tests.ok",
            ),
        ),
        "build-check": RealCheckNode(
            id="build-check",
            command=_marker_command(
                f"{python} -m build --no-isolation --sdist --wheel --outdir dist",
                "build-check.ok",
            ),
        ),
        "release-ready": RealCheckNode(
            id="release-ready",
            command=(
                "sh",
                "-c",
                "test -f .status/type-check.ok "
                "&& test -f .status/lint.ok "
                "&& test -f .status/architecture-test.ok "
                "&& test -f .status/unit-tests.ok "
                "&& test -f .status/build-check.ok",
            ),
            requires=(
                "type-check",
                "lint",
                "architecture-test",
                "unit-tests",
                "build-check",
            ),
        ),
    }

    return nodes, "release-ready"
