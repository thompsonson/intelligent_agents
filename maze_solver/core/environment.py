from typing import Tuple, List, Optional, Set
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mazelib import Maze
from mazelib.generate.Sidewinder import Sidewinder
from mazelib.solve.BacktrackingSolver import BacktrackingSolver

from .config import Config

class MazeEnvironment:
    """Handles maze generation, state management and visualization.

    This class encapsulates all maze-related functionality, including generating mazes,
    managing maze state, creating graph representations for search algorithms, and
    providing visualization capabilities.

    Attributes:
        config (Config): Configuration parameters for the maze.
        grid (numpy.ndarray): Binary maze representation (0=path, 1=wall).
        start (Tuple[int, int]): Starting position, typically (1,1).
        end (Tuple[int, int]): Goal position, typically at the bottom-right corner.
        optimal_path (List[Tuple[int, int]]): Shortest solution path from start to end.
        optimal_path_length (int): Length of the shortest solution path.
        graph (Dict): Graph representation of maze for search algorithms.
    """

    def __init__(self, config: Config):
        """Initialize the maze environment with given configuration.

        Args:
            config: Configuration parameters for maze generation and visualization.
        """
        self.config = config
        self.grid = None
        self.start = None
        self.end = None
        self._maze = None
        self.seed = None
        self.optimal_path = None
        self.optimal_path_length = None
        self.graph = None
        self.generate()

    def generate(self) -> None:
        """Creates new maze using Sidewinder algorithm.

        Generates a random maze based on configuration parameters, establishes
        start and end positions, calculates optimal path, and creates graph
        representation for search algorithms.
        """
        # Use config maze_id if provided, otherwise generate random seed
        self.seed = self.config.maze_id if self.config.maze_id is not None else np.random.randint(1, 1000)

        self._maze = Maze(self.seed)
        self._maze.generator = Sidewinder(self.config.maze_size, self.config.maze_size)
        self._maze.generate()
        self._maze.generate_entrances()

        self.grid = self._maze.grid

        # Set the start to the first valid cell inside grid
        self.start = (1, 1)
        # Set the end to the last valid cell inside grid
        self.end = (self.grid.shape[0]-2, self.grid.shape[1]-2)

        # After maze generation, calculate optimal path
        self._calculate_optimal_path()

        # Create graph representation for search algorithms
        self._create_graph()

    def _calculate_optimal_path(self) -> None:
        """Calculate optimal path using maze's solver.

        Uses the BacktrackingSolver to find the optimal solution path from
        start to end. Sets optimal_path and optimal_path_length attributes.
        """
        # Set up solver
        self._maze.solver = BacktrackingSolver()
        self._maze.start = self.start
        self._maze.end = self.end

        # Solve
        self._maze.solve()

        if self._maze.solutions:
            self.optimal_path = self._maze.solutions[0]  # Store first solution
            self.optimal_path_length = len(self.optimal_path) + 1
        else:
            # Handle case where no solution is found
            self.optimal_path = None
            self.optimal_path_length = None

    def _create_graph(self) -> None:
        """Creates graph representation for search algorithms.

        Transforms the grid-based maze into an adjacency list graph representation
        where each non-wall cell is a node, and edges connect to adjacent non-wall cells.
        """
        self.graph = {}
        rows, cols = self.grid.shape

        # Define possible moves: up, right, down, left
        directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]

        for r in range(rows):
            for c in range(cols):
                # Skip walls
                if self.grid[r][c] == 1:
                    continue

                node = (r, c)
                neighbors = []

                # Check all four directions
                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    # Check if the neighbor is valid
                    if self.is_valid_move((nr, nc)):
                        neighbors.append((nr, nc))

                self.graph[node] = neighbors

    def get_minimum_steps(self) -> Optional[int]:
        """Returns the length of optimal path if it exists.

        Returns:
            The number of steps in the optimal path from start to end,
            or None if no path exists.
        """
        return self.optimal_path_length

    def is_valid_move(self, state: Tuple[int, int]) -> bool:
        """Checks if a move to the given state is legal.

        Args:
            state: Coordinates (row, col) to check for validity.

        Returns:
            True if the move is valid (within bounds and not a wall),
            False otherwise.
        """
        row, col = state
        # check if the move goes outside of the grid or into a wall (1)
        if (row < 0 or row >= self.grid.shape[0] or
            col < 0 or col >= self.grid.shape[1] or
            self.grid[state] == 1):
            return False
        # move is valid
        return True

    def visualize(self, path: Optional[List[Tuple[int, int]]] = None,
                  visited: Optional[Set[Tuple[int, int]]] = None,
                  show_optimal: bool = False,
                  save_path: Optional[Path] = None,
                  title: Optional[str] = None) -> None:
        """Displays or saves maze visualization with optional path and visited nodes.

        Creates a color-coded visualization of the maze showing walls, paths,
        visited nodes, and solution paths.

        Args:
            path: Optional list of positions showing a solution path.
            visited: Optional set of visited positions during search.
            show_optimal: Whether to display the optimal path.
            save_path: If provided, saves figure to this path instead of displaying.
            title: Optional title for the plot.
        """
        plt.figure(figsize=(8, 8))

        # Add title showing Maze ID and minimum steps
        if title:
            plt.title(title)
        else:
            plt.title(f"Maze #{self.seed} - Min Steps: {self.get_minimum_steps()}")

        # Create a visualization grid filled with appropriate values for coloring
        rows, cols = self.grid.shape
        viz_grid = np.ones((rows, cols)) * 5  # Initialize with unvisited path value

        # Fill in walls
        viz_grid[self.grid == 1] = 0  # Walls

        # Fill in visited paths
        if visited:
            for pos in visited:
                r, c = pos
                if self.grid[r, c] == 0:  # Only if it's a path
                    viz_grid[r, c] = 1  # Visited paths

        # Fill in final path
        if path:
            for pos in path:
                if pos != self.start and pos != self.end:
                    r, c = pos
                    viz_grid[r, c] = 2  # Final path

        # Mark start and end
        viz_grid[self.start] = 3  # Start
        viz_grid[self.end] = 4    # Goal

        # Define colors: Wall, Visited, Final Path, Start, Goal, Unvisited
        cmap = plt.cm.colors.ListedColormap(['black', 'yellow', 'green', 'blue', 'purple', 'white'])
        bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)

        # Plot the maze
        plt.imshow(viz_grid, cmap=cmap, norm=norm)
        plt.xticks([])
        plt.yticks([])

        # Add legend
        legend_elements = [
            plt.Rectangle((0,0), 1, 1, color='white', label='Path'),
            plt.Rectangle((0,0), 1, 1, color='yellow', label='Visited'),
            plt.Rectangle((0,0), 1, 1, color='black', label='Wall'),
            plt.Rectangle((0,0), 1, 1, color='green', label='Final Path'),
            plt.Rectangle((0,0), 1, 1, color='blue', label='Start'),
            plt.Rectangle((0,0), 1, 1, color='purple', label='Goal')
        ]
        plt.legend(handles=legend_elements, loc='upper center',
                  bbox_to_anchor=(0.5, -0.05), ncol=3)

        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def calculate_manhattan_distance(self, state: Tuple[int, int], goal: Tuple[int, int]) -> int:
        """Calculate Manhattan distance heuristic from state to goal."""
        return abs(state[0] - goal[0]) + abs(state[1] - goal[1])

    def calculate_euclidean_distance(self, state: Tuple[int, int], goal: Tuple[int, int]) -> float:
        """Calculate Euclidean distance heuristic from state to goal."""
        return ((state[0] - goal[0]) ** 2 + (state[1] - goal[1]) ** 2) ** 0.5

    def get_step_cost(self, state1: Tuple[int, int], state2: Tuple[int, int]) -> int:
        """Calculate cost of moving from state1 to state2."""
        # For uniform cost in grid-based maze, return 1
        return 1