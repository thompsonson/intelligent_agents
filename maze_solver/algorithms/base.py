import time

from abc import ABC, abstractmethod

from ..core.environment import MazeEnvironment
from ..core.results import SearchResult
from typing import Tuple, Optional



class SearchAlgorithmBase(ABC):
    """Abstract base class for search algorithms with enhanced shared functionality."""

    def __init__(self, env: MazeEnvironment):
        """Initialize the search algorithm with an environment."""
        self.env = env
        self.config = env.config
        self.name = self.__class__.__name__

    def _reconstruct_path(self, parent, start, goal):
        """Reconstruct the solution path from parent pointers."""
        path = [goal]
        current = goal
        while current != start:
            current = parent[current]
            path.append(current)
        return path[::-1]  # Reverse to get start→goal

    def create_search_result(self, path, visited_order, success, steps, exploration_history, **kwargs):
        """Create a standardized SearchResult with support for additional metrics."""
        result = SearchResult(
            path=path,
            visited=visited_order,
            success=success,
            steps=steps,
            exploration_history=exploration_history
        )
        # Add additional metrics that vary by algorithm
        for key, value in kwargs.items():
            setattr(result, key, value)
        return result

    @abstractmethod
    def search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> SearchResult:
        """Search for a path from start to goal."""
        raise NotImplementedError("Subclasses must implement search method")

    def run(self, start: Optional[Tuple[int, int]] = None,
            goal: Optional[Tuple[int, int]] = None) -> SearchResult:
        """Run the search algorithm with timing and error handling."""
        # Use environment start/goal if not specified
        start = start if start is not None else self.env.start
        goal = goal if goal is not None else self.env.end

        start_time = time.time()
        try:
            result = self.search(start, goal)
        except Exception as e:
            print(f"Error in {self.name}: {str(e)}")
            result = SearchResult(success=False)

        result.execution_time = time.time() - start_time
        return result

    @abstractmethod
    def visualize_search(self, result: SearchResult, delay: float = None) -> None:
        """Visualize the search process step by step."""
        raise NotImplementedError("Subclasses must implement visualize_search method")