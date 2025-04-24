from abc import abstractmethod
from typing import Tuple, List
from IPython.display import clear_output
import matplotlib.pyplot as plt

from ..base import SearchAlgorithmBase
from ...core.results import SearchResult


class UninformedSearch(SearchAlgorithmBase):
    """Base class for uninformed search algorithms (BFS, DFS).

    Uninformed search algorithms don't use domain knowledge beyond the problem definition.
    They differ primarily in their frontier data structure and expansion strategy.
    """

    def __init__(self, *args, frontier_name="frontier", **kwargs):
        super().__init__(*args, **kwargs)
        self.frontier_name = frontier_name

    @abstractmethod
    def _initialize_frontier(self, start):
        """Initialize frontier data structure with start node."""
        raise NotImplementedError("Subclasses must implement _initialize_frontier")

    @abstractmethod
    def _get_next_node(self, frontier):
        """Get the next node from frontier based on search strategy (FIFO, LIFO, etc.)."""
        raise NotImplementedError("Subclasses must implement _get_next_node")

    def _add_to_frontier(self, frontier, node):
        """Add a node to frontier according to search strategy."""
        frontier.append(node)

    def _frontier_representation(self, frontier):
        """Return a representation of frontier suitable for visualization."""
        return list(frontier)

    def search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> SearchResult:
        """Generic uninformed search implementation."""
        # Initialize data structures
        frontier = self._initialize_frontier(start)
        visited = set([start])
        visited_order = [start]
        parent = {start: None}
        exploration_history = []
        node_discovery = {start: 0}
        node_expansion = {}

        steps = 0
        max_steps = self.config.max_steps or float("inf")

        while frontier and steps < max_steps:
            steps += 1

            # Save frontier state for visualization if needed
            frontier_before = (
                self._frontier_representation(frontier)
                if self.config.show_exploration
                else None
            )

            # Get next node to explore (algorithm-specific)
            current_node = self._get_next_node(frontier)
            node_expansion[current_node] = steps

            # Check if goal is reached
            if current_node == goal:
                final_path = self._reconstruct_path(parent, start, goal)
                return self.create_search_result(
                    path=final_path,
                    visited_order=visited_order,
                    success=True,
                    steps=steps,
                    exploration_history=exploration_history,
                    node_discovery=node_discovery,
                    node_expansion=node_expansion,
                )

            # Process neighbors
            neighbors_added = []
            for neighbor in self.env.graph.get(current_node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    visited_order.append(neighbor)
                    parent[neighbor] = current_node
                    self._add_to_frontier(frontier, neighbor)
                    node_discovery[neighbor] = steps
                    neighbors_added.append(neighbor)

            # Record exploration history
            if self.config.show_exploration:
                current_partial_path = (
                    self._reconstruct_path(parent, start, current_node)
                    if current_node != start
                    else [start]
                )

                # Create step info dictionary (using algorithm-specific names)
                step_info = self._create_step_info(
                    current_node,
                    steps,
                    neighbors_added,
                    frontier_before,
                    self._frontier_representation(frontier),
                )

                exploration_history.append(
                    (
                        visited.copy(),
                        self._frontier_representation(frontier),
                        current_partial_path,
                        step_info,
                    )
                )

        # No path found
        return self.create_search_result(
            path=None,
            visited_order=visited_order,
            success=False,
            steps=steps,
            exploration_history=exploration_history,
            node_discovery=node_discovery,
            node_expansion=node_expansion,
        )

    def _create_step_info(
        self, current_node, steps, neighbors_added, frontier_before, frontier_after
    ):
        """Create step info dictionary for visualization."""
        info = {
            "step": steps,
            "expanded_node": current_node,
            "neighbors_added": neighbors_added,
            "frontier_before": frontier_before,
            "frontier_after": frontier_after,
            f"{self.frontier_name}_before": frontier_before,
            f"{self.frontier_name}_after": frontier_after,
        }
        return info

    def visualize_search(self, result: SearchResult, delay: float = None) -> None:
        """Visualize the search process step by step."""
        if not result.exploration_history:
            print(f"No exploration history available for {self.name}")
            return

        delay = delay if delay is not None else self.config.visualization_delay

        for i, state in enumerate(result.exploration_history):
            # Clear previous output
            clear_output(wait=True)

            # Unpack exploration history
            visited, frontier, current_path, step_info = state

            # Display title based on search progress
            if i == len(result.exploration_history) - 1 and result.success:
                title = f"{self.name} - Path found! ({result.steps} steps, {result.execution_time:.3f}s)"
                current_path = result.path
            else:
                title = f"{self.name} - Step {i+1}/{len(result.exploration_history)}"

            # Display the maze visualization
            self.env.visualize(path=current_path, visited=visited, title=title)

            # Format node coordinates for display
            def format_node(node):
                return f"({node[0]},{node[1]})"

            # Display educational commentary
            print(
                f"Step {step_info['step']}: Expanding node {format_node(step_info['expanded_node'])}"
            )

            # Display frontier information (generic terms)
            print(f"Frontier size: {len(frontier)}")
            print(f"Visited nodes: {len(visited)}")
            print(f"Current path length: {len(current_path) if current_path else 0}")

            plt.pause(delay)

        # Show final state if exploration wasn't saved
        if not self.config.show_exploration:
            clear_output(wait=True)
            if result.success:
                title = f"{self.name} - Path found! ({result.steps} steps, {result.execution_time:.3f}s)"
            else:
                title = f"{self.name} - No path found. ({result.steps} steps, {result.execution_time:.3f}s)"

            self.env.visualize(
                path=result.path, visited=set(result.visited), title=title
            )

        print(result)
