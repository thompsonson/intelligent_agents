import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from atomicguard.application.action_pair import ActionPair
from atomicguard.application.agent import DualStateAgent
from atomicguard.domain.exceptions import RmaxExhausted
from atomicguard.infrastructure.persistence.filesystem import FilesystemArtifactDAG
from task_graph_solver.core.domain import AttemptOutcome

from .domain import AtomicGuardCheckNode


class AtomicGuardCheckEnvironment:
    """Same public shape as RealCheckEnvironment/TaskGraphEnvironment -
    ready_nodes(), attempt(), check_invariant(), retries_spent(),
    break_task()/fix_task(), drain_changed_tasks(), is_goal_reached() - so
    every executor in this repo runs against this environment with ZERO
    code changes. See
    documentation/task-graph/atomicguard-variant/environment_design.md.

    Unlike RealCheckEnvironment, a node's Guard is a real, production
    `atomicguard.ActionPair`, wrapped in a real `DualStateAgent` rather
    than called bare - `DualStateAgent` owns EnvironmentState (the retry
    loop, feedback threading, an `rmax` bound), the layer this project's
    own bare-`ActionPair` calls were reinventing a weaker version of. Both
    `check_invariant()` (`rmax=0` - run once, no retry, still real
    `atomicguard` usage: `PreCommitGym` puts check-only APs through the
    identical `DualStateAgent` path as fix APs) and `attempt()`
    (`repair_rmax`) share one `FilesystemArtifactDAG` per environment, and
    `check_action_pair`/`repair_action_pair` share one `action_pair_id`
    (the node's own `id`) so a repair's `DualStateAgent` call automatically
    inherits the check's real failure feedback - no extra plumbing.
    `ExitCodeGuard` never sets `fatal=True`, so the only exception either
    wrapper needs to catch is `RmaxExhausted`.

    A load-bearing difference from RealCheckEnvironment worth recording:
    RealCheckEnvironment's commands are resolved against `self._workdir`
    lazily, at each check (`subprocess.run(node.command, cwd=self._workdir)`),
    so the same RealCheckNode works against any workdir. atomicguard's
    `SubprocessGenerator` bakes `cwd` in at construction instead - so here,
    `workdir` must be decided *before* building the nodes' ActionPairs
    (though the directory itself need not exist yet - only reset_to_state()
    needs it to), and the same path handed to this environment.

    The DAG's `base_dir` lives *outside* `workdir` deliberately:
    `reset_to_state()` wipes `workdir` on every call, and would destroy the
    audit trail this DAG exists to keep if it lived underneath it.
    """

    def __init__(
        self,
        nodes: Dict[str, AtomicGuardCheckNode],
        fixtures_dir: Path,
        workdir: Path,
        goal: Optional[str] = None,
        broken_states: Optional[Dict[str, str]] = None,
        dag_dir: Optional[Path] = None,
        repair_rmax: int = 3,
        workflow_id: str = "atomicguard-backed",
    ):
        self._validate_graph(nodes, goal)

        self.nodes = nodes
        self.groups: Dict[str, object] = {}
        self.goal = goal
        self._fixtures_dir = Path(fixtures_dir)
        self._workdir = Path(workdir)
        self._broken_states = broken_states or {}
        self._workdir_ready = False
        self._current_state: Optional[str] = None
        self._attempts_made: Dict[str, int] = {}
        self._time_spent: Dict[str, float] = {}
        self._changed_since_drain: Set[str] = set()
        self._repair_rmax = repair_rmax
        self._workflow_id = workflow_id
        dag_dir = Path(dag_dir) if dag_dir is not None else self._workdir.parent / "dag"
        self._dag = FilesystemArtifactDAG(base_dir=str(dag_dir))

    @staticmethod
    def _validate_graph(
        nodes: Dict[str, AtomicGuardCheckNode], goal: Optional[str]
    ) -> None:
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
        into it. Marks every node changed, conservatively: swapping the
        whole working tree can change any check's answer."""
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

    def _run(self, action_pair: ActionPair, node_id: str, rmax: int) -> bool:
        """Wrap action_pair in a DualStateAgent sharing this environment's
        DAG and node_id as action_pair_id - see the class docstring for
        why. `DualStateAgent.execute()` composes its own Context; this
        environment no longer builds one. `ExitCodeGuard` (the only Guard
        used anywhere in this environment so far) never sets `fatal=True`,
        so `RmaxExhausted` is the only exception a caller needs to catch."""
        start = time.monotonic()
        agent = DualStateAgent(
            action_pair=action_pair,
            artifact_dag=self._dag,
            rmax=rmax,
            action_pair_id=node_id,
            workflow_id=self._workflow_id,
        )
        try:
            agent.execute(specification="")
            passed = True
        except RmaxExhausted:
            passed = False
        self._time_spent[node_id] = time.monotonic() - start
        return passed

    def attempt(self, node_id: str) -> AttemptOutcome:
        """If the node has a repair_action_pair, run it - a real Generator
        (and, where wired, Effector) genuinely attempting to fix the
        problem, via a DualStateAgent bounded by `repair_rmax` - then
        re-run check_action_pair for the real, final verdict: a repair
        generator's own exit code isn't always a trustworthy proxy for
        "the underlying problem is now fixed" (`ruff --fix`'s is, empirically
        verified; a plain `sed` edit's isn't - it only proves the edit
        itself ran, not that whatever it edited now satisfies the real
        check), so this environment never trusts a repair's own Guard
        as the final word. A node with no repair_action_pair just
        re-runs its check once (`rmax=0`), matching RealCheckNode:
        nothing here can turn a RETRY into a different answer without an
        intervening repair, so this never returns RETRY."""
        self._ensure_ready()
        node = self.nodes[node_id]
        self._attempts_made[node_id] = self._attempts_made.get(node_id, 0) + 1
        if node.repair_action_pair is not None:
            repaired = self._run(node.repair_action_pair, node_id, self._repair_rmax)
            if not repaired:
                return AttemptOutcome.FATAL
            passed = self._run(node.check_action_pair, node_id, rmax=0)
        else:
            passed = self._run(node.check_action_pair, node_id, rmax=0)
        return AttemptOutcome.PASS if passed else AttemptOutcome.FATAL

    def check_invariant(self, node_id: str) -> bool:
        """The free sensor: runs only check_action_pair, via a
        DualStateAgent with rmax=0 (one real call, no retry) - the thing
        GuardFirstExecutor calls before ever paying for attempt()."""
        self._ensure_ready()
        return self._run(self.nodes[node_id].check_action_pair, node_id, rmax=0)

    def retries_spent(self, node_id: str) -> int:
        return self._attempts_made.get(node_id, 0)

    def time_spent(self, node_id: str) -> float:
        """Wall-clock seconds the last-run Action Pair took (via attempt()
        or check_invariant()). 0.0 if never run."""
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
        node_id is accepted for interface parity but not otherwise used -
        v1 only supports one broken thing at a time."""
        self.reset_to_state("clean")

    def drain_changed_tasks(self) -> List[str]:
        changed = sorted(self._changed_since_drain)
        self._changed_since_drain.clear()
        return changed
