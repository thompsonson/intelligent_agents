import pytest

from maze_solver.agents.path_maintenance import PathMaintenanceAgent
from maze_solver.algorithms.informed.a_star_search import AStarSearch
from maze_solver.core.config import Config
from maze_solver.core.environment import CellState, MazeEnvironment


@pytest.fixture
def env():
    return MazeEnvironment(Config(maze_size=5, maze_id=7, show_exploration=False))


@pytest.fixture
def belief_path(env):
    return AStarSearch(env).search(env.start, env.end).path


class TestPathMaintenanceAgentWalk:
    def test_no_repairs_needed(self, env, belief_path):
        result = PathMaintenanceAgent(env, belief_path).walk()
        assert result.repairs_performed == []
        assert result.success is True
        assert result.path == belief_path

    def test_repairs_injected_cells_in_walk_order(self, env, belief_path):
        env.inject_repairs([belief_path[6], belief_path[11]], belief_path)
        result = PathMaintenanceAgent(env, belief_path).walk()
        assert result.repairs_performed == [belief_path[6], belief_path[11]]

    def test_repaired_cells_end_up_open(self, env, belief_path):
        env.inject_repairs([belief_path[6]], belief_path)
        PathMaintenanceAgent(env, belief_path).walk()
        assert env.get_cell_state(belief_path[6]) == CellState.OPEN

    def test_never_senses_cells_off_the_path(self, env, belief_path):
        sensed = []
        original = env.get_cell_state

        def spy(cell):
            sensed.append(cell)
            return original(cell)

        env.get_cell_state = spy
        PathMaintenanceAgent(env, belief_path).walk()
        assert all(cell in belief_path for cell in sensed)

    def test_does_not_sense_the_start_cell(self, env, belief_path):
        sensed = []
        original = env.get_cell_state

        def spy(cell):
            sensed.append(cell)
            return original(cell)

        env.get_cell_state = spy
        PathMaintenanceAgent(env, belief_path).walk()
        assert belief_path[0] not in sensed

    def test_result_path_is_identical_to_input_path(self, env, belief_path):
        result = PathMaintenanceAgent(env, belief_path).walk()
        assert result.path == belief_path
