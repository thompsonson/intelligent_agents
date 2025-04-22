from typing import Tuple
from IPython.display import clear_output
from matplotlib import pyplot as plt

from .base import InformedSearch
from ...core.results import SearchResult


class AStarSearch(InformedSearch):
    """A* Search implementation with educational output.

    A* combines the cost-so-far (g-value) with a heuristic estimate (h-value)
    to guide search. It balances finding a short path with finding it quickly,
    and is guaranteed to find the optimal path if the heuristic is admissible.
    """

    def _reconstruct_path(self, parent, start, goal):
        """Reconstruct the solution path from parent pointers."""
        # Same as in previous implementations
        path = [goal]
        current = goal
        while current != start:
            current = parent[current]
            path.append(current)
        return path[::-1]

    def search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> SearchResult:
        """Perform A* Search from start to goal."""
        # Initialize metrics using base class method
        metrics = self._initialize_metrics(start, goal)

        # Extract tracking dictionaries from metrics for easier access
        node_discovery = metrics["node_discovery"]
        node_expansion = metrics["node_expansion"]
        node_h_value = metrics["node_h_value"]
        node_g_value = metrics["node_g_value"]
        node_f_value = metrics["node_f_value"]

        # Priority queue (list that we'll sort)
        # Each entry is (f_value, g_value, node) - f = g + h
        frontier = [(node_f_value[start], 0, start)]  # f=h+g, g=0 for start node
        frontier_dict = {start: node_f_value[start]}  # Maps node -> f_value

        # Tracking variables
        closed_set = set()  # Nodes already expanded
        visited_order = [start]
        parent = {start: None}
        g_value = {start: 0}  # Cost from start to node

        exploration_history = []

        steps = 0
        max_steps = self.config.max_steps or float('inf')

        while frontier and steps < max_steps:
            steps += 1

            # Sort by f_value (and break ties with g_value)
            frontier.sort(key=lambda x: (x[0], -x[1]))  # Sort by f, then by -g (prefer higher g if same f)
            f, g, current_node = frontier.pop(0)
            del frontier_dict[current_node]

            # Add to closed set
            closed_set.add(current_node)
            node_expansion[current_node] = steps

            # Goal check
            if current_node == goal:
                final_path = self._reconstruct_path(parent, start, goal)

                # Use create_search_result to include all metrics
                return self.create_search_result(
                    path=final_path,
                    visited_order=visited_order,
                    success=True,
                    steps=steps,
                    exploration_history=exploration_history,
                    node_discovery=node_discovery,
                    node_expansion=node_expansion,
                    node_h_value=node_h_value,
                    node_g_value=node_g_value,
                    node_f_value=node_f_value
                )

            # Process neighbors
            neighbors_added = []
            frontier_before = frontier.copy() if self.config.show_exploration else None

            for neighbor in self.env.graph.get(current_node, []):
                if neighbor in closed_set:
                    continue

                # Calculate new g-value
                tentative_g = g_value[current_node] + self.env.get_step_cost(current_node, neighbor)

                # If this node is new OR we found a better path to it
                if self._should_update_node(neighbor, tentative_g, g_value, frontier_dict):
                    # Update tracking info
                    parent[neighbor] = current_node
                    g_value[neighbor] = tentative_g

                    # Calculate f-value
                    h = self.env.calculate_manhattan_distance(neighbor, goal)
                    f = self._calculate_f(tentative_g, h)

                    # Add to educational tracking
                    if neighbor not in node_discovery:
                        node_discovery[neighbor] = steps
                        visited_order.append(neighbor)

                    node_h_value[neighbor] = h
                    node_g_value[neighbor] = tentative_g
                    node_f_value[neighbor] = f

                    # Update frontier
                    if neighbor in frontier_dict:
                        # Remove old entry
                        frontier = [(f_val, g_val, n) for f_val, g_val, n in frontier if n != neighbor]

                    frontier.append((f, tentative_g, neighbor))
                    frontier_dict[neighbor] = f
                    neighbors_added.append((f, tentative_g, neighbor))

            # Record exploration history
            if self.config.show_exploration:
                current_partial_path = self._reconstruct_path(parent, start, current_node) if current_node != start else [start]

                # Use _create_step_info from base class
                step_info = self._create_step_info(
                    current_node, steps, neighbors_added,
                    frontier_before, frontier.copy(),
                    metrics
                )

                exploration_history.append((
                    closed_set.copy(),
                    frontier.copy(),
                    current_partial_path,
                    step_info
                ))

        # No path found - use create_search_result to include all metrics
        return self.create_search_result(
            path=None,
            visited_order=visited_order,
            success=False,
            steps=steps,
            exploration_history=exploration_history,
            node_discovery=node_discovery,
            node_expansion=node_expansion,
            node_h_value=node_h_value,
            node_g_value=node_g_value,
            node_f_value=node_f_value
        )

    def visualize_search(self, result: SearchResult, delay: float = None) -> None:
        """Visualize A* Search with educational information about f, g, h values."""
        if not result.exploration_history:
            print(f"No exploration history available for {self.name}")
            return

        delay = delay if delay is not None else self.config.visualization_delay

        for i, state in enumerate(result.exploration_history):
            # Clear previous output
            clear_output(wait=True)

            # Unpack exploration history
            closed_set, frontier, current_path, step_info = state

            # Format node coordinates for display
            def format_node(node):
                return f"({node[0]},{node[1]})"

            # Educational commentary specific to A* Search
            expanded_node = format_node(step_info["expanded_node"])
            f_value = step_info["expanded_node_f"]
            g_value = step_info["expanded_node_g"]
            h_value = step_info["expanded_node_h"]

            commentary = [
                f"Step {step_info['step']}: Expanding node {expanded_node}",
                f"f(n) = g(n) + h(n) = {g_value:.2f} + {h_value:.2f} = {f_value:.2f}"
            ]

            # Add information about neighbors
            if step_info["neighbors_added"]:
                neighbors_text = ", ".join(
                    [f"{format_node(n)} (f={f:.2f})" for f, g, n in step_info["neighbors_added"]]
                )
                commentary.append(f"Discovered neighbors: {neighbors_text}")
            else:
                commentary.append(f"No new neighbors were discovered")

            # Display title based on progress
            if i == len(result.exploration_history) - 1 and result.success:
                title = f"{self.name} - Path found! ({result.steps} steps, {result.execution_time:.3f}s)"
                current_path = result.path
            else:
                title = f"{self.name} - Step {i+1}/{len(result.exploration_history)}"

            # Display the maze visualization
            self.env.visualize(path=current_path, visited=closed_set, title=title)

            # Display educational commentary
            print("\n".join(commentary))

            # Additional stats
            print(f"\nExpanded nodes: {len(closed_set)}")
            print(f"Frontier size: {len(frontier)}")
            print(f"Current path length: {len(current_path) if current_path else 0}")

            plt.pause(delay)

        # Show final state if exploration wasn't saved
        if not self.config.show_exploration:
            clear_output(wait=True)
            if result.success:
                title = f"{self.name} - Path found! ({result.steps} steps, {result.execution_time:.3f}s)"
            else:
                title = f"{self.name} - No path found. ({result.steps} steps, {result.execution_time:.3f}s)"

            self.env.visualize(path=result.path, visited=set(result.visited), title=title)

        print(result)

    # Add these missing abstract method implementations
    def _calculate_f(self, g, h):
        """Calculate f-value using g + h formula for A* search."""
        return g + h

    def _should_update_node(self, neighbor, tentative_g, g_value, frontier_dict):
        """Determine if a node should be updated based on A* criteria.

        Update if:
        1. Node is not in frontier yet, or
        2. We found a better (lower g-value) path to it
        """
        return (neighbor not in frontier_dict) or (tentative_g < g_value.get(neighbor, float('inf')))


