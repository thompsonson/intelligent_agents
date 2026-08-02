import pytest

from maze_solver.agents.path_maintenance import PathMaintenanceAgent
from maze_solver.algorithms.informed.a_star_search import AStarSearch
from maze_solver.core.config import Config
from maze_solver.core.environment import CellState, MazeEnvironment
from maze_solver.visualization.path_maintenance_view import record_walk


@pytest.fixture
def env():
    return MazeEnvironment(Config(maze_size=5, maze_id=7, show_exploration=False))


@pytest.fixture
def belief_path(env):
    return AStarSearch(env).search(env.start, env.end).path


class TestRecordWalk:
    def test_no_repairs_produces_only_arrive_events(self, env, belief_path):
        agent = PathMaintenanceAgent(env, belief_path)
        result, events = record_walk(env, agent)

        assert result.repairs_performed == []
        assert len(events) == len(belief_path) - 1
        assert all(kind == "arrive" for kind, *_ in events)

    def test_repair_produces_arrive_then_repair_for_that_cell(self, env, belief_path):
        target = belief_path[6]
        env.inject_repairs([target], belief_path)
        agent = PathMaintenanceAgent(env, belief_path)
        result, events = record_walk(env, agent)

        arrive_at_target = ("arrive", target, CellState.NEEDS_REPAIR)
        repair_target = ("repair", target)
        assert arrive_at_target in events
        assert repair_target in events
        assert events.index(arrive_at_target) < events.index(repair_target)

    def test_events_restore_original_env_methods(self, env, belief_path):
        original_get = env.get_cell_state
        original_repair = env.repair_cell
        record_walk(env, PathMaintenanceAgent(env, belief_path))
        assert env.get_cell_state == original_get
        assert env.repair_cell == original_repair
