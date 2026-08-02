import pytest

from maze_solver.core.config import Config
from maze_solver.core.environment import CellState, MazeEnvironment


@pytest.fixture
def env():
    # maze_size=5, maze_id=7: the maintenance_lite scenario
    # (documentation/path-maintenance/scenario.md). A*'s path is a fixed,
    # hand-verified 17-cell corridor - see that doc for the full listing.
    return MazeEnvironment(Config(maze_size=5, maze_id=7, show_exploration=False))


@pytest.fixture
def belief_path(env):
    from maze_solver.algorithms.informed.a_star_search import AStarSearch

    return AStarSearch(env).search(env.start, env.end).path


def first_wall(env):
    rows, cols = env.grid.shape
    for r in range(rows):
        for c in range(cols):
            if env.grid[r, c] == 1:
                return (r, c)
    raise AssertionError("maze has no walls - fixture is degenerate")


class TestGetCellState:
    def test_open_cell_defaults_to_open(self, env, belief_path):
        assert env.get_cell_state(belief_path[3]) == CellState.OPEN

    def test_wall_cell_raises(self, env):
        with pytest.raises(ValueError):
            env.get_cell_state(first_wall(env))

    def test_out_of_bounds_raises(self, env):
        rows, cols = env.grid.shape
        with pytest.raises(ValueError):
            env.get_cell_state((rows, cols))


class TestInjectRepairs:
    def test_marks_cells_needs_repair(self, env, belief_path):
        target = belief_path[6]
        env.inject_repairs([target], belief_path)
        assert env.get_cell_state(target) == CellState.NEEDS_REPAIR

    def test_leaves_other_path_cells_open(self, env, belief_path):
        env.inject_repairs([belief_path[6]], belief_path)
        assert env.get_cell_state(belief_path[3]) == CellState.OPEN

    def test_multiple_cells_in_one_call(self, env, belief_path):
        env.inject_repairs([belief_path[6], belief_path[11]], belief_path)
        assert env.get_cell_state(belief_path[6]) == CellState.NEEDS_REPAIR
        assert env.get_cell_state(belief_path[11]) == CellState.NEEDS_REPAIR

    def test_wall_cell_rejected(self, env, belief_path):
        wall = first_wall(env)
        with pytest.raises(ValueError):
            env.inject_repairs([wall], belief_path + [wall])

    def test_cell_not_on_path_rejected(self, env, belief_path):
        off_path = next(
            cell
            for cell in env.graph
            if cell not in belief_path and cell != env.start and cell != env.end
        )
        with pytest.raises(ValueError):
            env.inject_repairs([off_path], belief_path)

    def test_already_needs_repair_rejected(self, env, belief_path):
        target = belief_path[6]
        env.inject_repairs([target], belief_path)
        with pytest.raises(ValueError):
            env.inject_repairs([target], belief_path)


class TestRepairCell:
    def test_transitions_needs_repair_to_open(self, env, belief_path):
        target = belief_path[6]
        env.inject_repairs([target], belief_path)
        env.repair_cell(target)
        assert env.get_cell_state(target) == CellState.OPEN

    def test_already_open_cell_rejected(self, env, belief_path):
        with pytest.raises(ValueError):
            env.repair_cell(belief_path[3])

    def test_wall_cell_rejected(self, env):
        with pytest.raises(ValueError):
            env.repair_cell(first_wall(env))
