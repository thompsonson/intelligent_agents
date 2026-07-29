import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from task_graph_solver.core.domain import AttemptOutcome

from .config import RealCheckConfig
from .domain import RealCheckNode


class RealCheckEnvironment:
    """Same public shape as task_graph_solver's TaskGraphEnvironment -
    ready_nodes(), attempt(), check_invariant(), retries_spent(),
    break_task()/fix_task(), drain_changed_tasks(), is_goal_reached() - so
    TopologicalExecutor, AOStarExecutor, DStarLiteExecutor, and
    PlanningExecutor all run against this environment with ZERO code
    changes. See documentation/task-graph/real-guards/environment_design.md.

    A node's Guard is a real subprocess call against the environment's
    current working tree (`self._workdir`), reset between runs from
    `fixtures_dir/{state_name}/` snapshots via reset_to_state() - the
    equivalent of TaskGraphConfig's seed: the thing that makes a run
    reproducible.

    `self.groups` is always empty - no GroupNode equivalent exists yet, kept
    only so AOStarExecutor/PlanningExecutor (which read `env.groups`
    unconditionally) don't need special-casing to run against this
    environment.
    """

    def __init__(
        self,
        nodes: Dict[str, RealCheckNode],
        config: RealCheckConfig,
        fixtures_dir: Path,
        goal: Optional[str] = None,
        broken_states: Optional[Dict[str, str]] = None,
        workdir: Optional[Path] = None,
    ):
        self._validate_graph(nodes, goal)

        self.nodes = nodes
        self.groups: Dict[str, object] = {}
        self.goal = goal
        self.config = config
        self._fixtures_dir = Path(fixtures_dir)
        self._broken_states = broken_states or {}
        self._workdir = (
            Path(workdir) if workdir is not None else Path(tempfile.mkdtemp())
        )
        self._workdir_ready = False
        self._current_state: Optional[str] = None
        self._attempts_made: Dict[str, int] = {}
        self._time_spent: Dict[str, float] = {}
        self._changed_since_drain: Set[str] = set()

    @staticmethod
    def _validate_graph(nodes: Dict[str, RealCheckNode], goal: Optional[str]) -> None:
        for node_id, node in nodes.items():
            for dep in node.requires:
                if dep not in nodes:
                    raise ValueError(f"node {node_id!r} requires unknown node {dep!r}")

        if goal is not None and goal not in nodes:
            raise ValueError(f"goal references unknown node {goal!r}")

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in nodes}

        def visit(node_id: str, path: List[str]) -> None:
            color[node_id] = GRAY
            for dep in nodes[node_id].requires:
                if color[dep] == GRAY:
                    cycle = " -> ".join(path + [dep])
                    raise ValueError(f"cycle detected in requires graph: {cycle}")
                if color[dep] == WHITE:
                    visit(dep, path + [dep])
            color[node_id] = BLACK

        for node_id in nodes:
            if color[node_id] == WHITE:
                visit(node_id, [node_id])

    def _is_satisfied(self, dep_id: str, satisfied: Set[str]) -> bool:
        if dep_id in self.groups:
            return any(m in satisfied for m in self.groups[dep_id].members)  # type: ignore[attr-defined]
        return dep_id in satisfied

    def ready_nodes(self, satisfied: Set[str]) -> List[str]:
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node_id not in satisfied
            and all(self._is_satisfied(dep, satisfied) for dep in node.requires)
        ]

    def is_goal_reached(self, satisfied: Set[str]) -> bool:
        if self.goal is not None:
            return self.goal in satisfied
        return all(node_id in satisfied for node_id in self.nodes)

    def reset_to_state(self, state_name: str) -> None:
        """Wipe the scratch working tree and copy fixtures_dir/state_name/
        into it - the Driver-only setup hook that makes a run reproducible.
        Marks every node changed, conservatively: swapping the whole
        working tree can change any check's answer."""
        source = self._fixtures_dir / state_name
        if not source.is_dir():
            raise ValueError(
                f"unknown fixture state {state_name!r} (looked in {source})"
            )

        if self._workdir.exists():
            shutil.rmtree(self._workdir)
        shutil.copytree(source, self._workdir)

        self._current_state = state_name
        self._workdir_ready = True
        self._changed_since_drain |= set(self.nodes.keys())

    def _ensure_ready(self) -> None:
        if not self._workdir_ready:
            raise RuntimeError(
                "reset_to_state() must be called before attempt()/check_invariant() - "
                "there is no working tree to run a check against yet"
            )

    def _run_check(self, node: RealCheckNode) -> bool:
        start = time.monotonic()
        try:
            result = subprocess.run(
                node.command,
                cwd=self._workdir,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
            passed = result.returncode == 0
        except subprocess.TimeoutExpired:
            passed = False
        self._time_spent[node.id] = time.monotonic() - start
        return passed

    def attempt(self, node_id: str) -> AttemptOutcome:
        """One real check. Consumes retry budget (retries_spent()) but
        never returns RETRY - a deterministic check run again without an
        intervening repair gives the same answer, so there is nothing to
        retry toward."""
        self._ensure_ready()
        node = self.nodes[node_id]
        passed = self._run_check(node)
        self._attempts_made[node_id] = self._attempts_made.get(node_id, 0) + 1
        return AttemptOutcome.PASS if passed else AttemptOutcome.FATAL

    def check_invariant(self, node_id: str) -> bool:
        """The identical real check as attempt(), without recording to
        retries_spent() - see the design doc for why this is still useful
        for PlanningExecutor even though GuardFirstExecutor gets nothing
        from it here (check and attempt are the same operation without a
        repair to skip paying for)."""
        self._ensure_ready()
        return self._run_check(self.nodes[node_id])

    def retries_spent(self, node_id: str) -> int:
        return self._attempts_made.get(node_id, 0)

    def time_spent(self, node_id: str) -> float:
        """Wall-clock seconds the real command took, the last time it was
        run (via attempt() or check_invariant()). 0.0 if never run."""
        return self._time_spent.get(node_id, 0.0)

    def break_task(self, node_id: str) -> None:
        """Convenience wrapper over reset_to_state(): swaps the whole
        working tree to node_id's mapped broken fixture state."""
        if node_id not in self._broken_states:
            raise ValueError(
                f"node {node_id!r} has no manufactured broken state configured"
            )
        self.reset_to_state(self._broken_states[node_id])

    def fix_task(self, node_id: str) -> None:
        """Convenience wrapper over reset_to_state(): resets to 'clean'.
        node_id is accepted for interface parity with TaskGraphEnvironment
        but not otherwise used - v1 only supports one broken thing at a
        time, matching pr_merge_lite's D* Lite experiments."""
        self.reset_to_state("clean")

    def drain_changed_tasks(self) -> List[str]:
        changed = sorted(self._changed_since_drain)
        self._changed_since_drain.clear()
        return changed
