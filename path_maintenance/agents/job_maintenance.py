from typing import Dict, List

from ..core.domain import JobState
from ..core.environment import JobGraphEnvironment
from ..core.results import JobWalkResult


class PathMaintenanceAgent:
    """Walks a fixed topological order over a job-lifecycle-aware AND-DAG,
    waiting for each node to resolve and repairing FAILED nodes.

    New module, not a modification of graph-topology's
    agents/path_maintenance.py - see
    documentation/path-maintenance/job-lifecycle/environment_design.md.
    """

    def __init__(self, environment: JobGraphEnvironment, order: List[str]):
        self._environment = environment
        self._order = order

    def walk(self) -> JobWalkResult:
        repairs_performed = []
        senses_performed: Dict[str, int] = {}
        satisfied = {self._order[0]}
        for node_id in self._order[1:]:
            senses = 1
            state = self._environment.get_job_state(node_id)
            while state in (JobState.PENDING, JobState.IN_PROGRESS):
                self._environment.advance_jobs(satisfied)
                state = self._environment.get_job_state(node_id)
                senses += 1
            senses_performed[node_id] = senses
            if state == JobState.FAILED:
                self._environment.repair_node(node_id)
                repairs_performed.append(node_id)
            satisfied.add(node_id)
        return JobWalkResult(
            path=self._order,
            repairs_performed=repairs_performed,
            senses_performed=senses_performed,
            success=True,
        )
