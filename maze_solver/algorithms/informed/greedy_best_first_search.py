from typing import Tuple
from IPython.display import clear_output
from matplotlib import pyplot as plt

from .base import InformedSearch
from ...core.results import SearchResult

class GreedyBestFirstSearch(InformedSearch):
    """Greedy Best-First Search implementation."""

    def _calculate_f(self, g, h):
        """For Greedy Best-First Search, f = h."""
        return h

    def _should_update_node(self, neighbor, tentative_g, g_value, frontier_dict):
        """Update if node is not in frontier."""
        return neighbor not in frontier_dict

    def search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> SearchResult:
        """Perform Greedy Best-First Search."""
        # Initialize metrics
        metrics = self._initialize_metrics(start, goal)

        # Initialize priority queue (using list with sorting)
        frontier = [(metrics["node_h_value"][start], start)]  # (f=h, node)
        frontier_dict = {start: metrics["node_h_value"][start]}

        # Initialize tracking variables
        visited_order = [start]
        closed_set = set()  # Nodes already expanded
        parent = {start: None}
        g_value = {start: 0}  # Still tracking g for path reconstruction
        exploration_history = []

        steps = 0
        max_steps = self.config.max_steps or float('inf')

        while frontier and steps < max_steps:
            steps += 1

            # Sort frontier by h-value (which is f for Greedy)
            frontier.sort(key=lambda x: x[0])
            frontier_before = frontier.copy() if self.config.show_exploration else None

            # Get node with lowest h-value
            h_value, current_node = frontier.pop(0)
            del frontier_dict[current_node]

            # Add to closed set
            closed_set.add(current_node)
            metrics["node_expansion"][current_node] = steps

            # Check if goal reached
            if current_node == goal:
                final_path = self._reconstruct_path(parent, start, goal)
                return self.create_search_result(
                    path=final_path,
                    visited_order=visited_order,
                    success=True,
                    steps=steps,
                    exploration_history=exploration_history,
                    **metrics
                )

            # Process neighbors
            neighbors_added = []
            for neighbor in self.env.graph.get(current_node, []):
                if neighbor in closed_set:
                    continue

                # Calculate tentative g-value (not used for expansion decisions but for tracking)
                tentative_g = g_value[current_node] + self.env.get_step_cost(current_node, neighbor)

                # Check if we should update this node
                if self._should_update_node(neighbor, tentative_g, g_value, frontier_dict):
                    # Update path info
                    parent[neighbor] = current_node
                    g_value[neighbor] = tentative_g

                    # Calculate heuristic
                    h = self.env.calculate_manhattan_distance(neighbor, goal)
                    f = self._calculate_f(tentative_g, h)  # For Greedy, f = h

                    # Update metrics
                    if neighbor not in metrics["node_discovery"]:
                        metrics["node_discovery"][neighbor] = steps
                        visited_order.append(neighbor)

                    metrics["node_h_value"][neighbor] = h
                    metrics["node_g_value"][neighbor] = tentative_g
                    metrics["node_f_value"][neighbor] = f

                    # Update frontier
                    if neighbor in frontier_dict:
                        # Remove old entry (frontier contains tuples)
                        frontier = [(f_val, n) for f_val, n in frontier if n != neighbor]

                    # Add with new values
                    frontier.append((f, neighbor))
                    frontier_dict[neighbor] = f
                    neighbors_added.append((f, neighbor))

            # Record exploration history
            if self.config.show_exploration:
                current_partial_path = self._reconstruct_path(parent, start, current_node) if current_node != start else [start]

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

        # No path found
        return self.create_search_result(
            path=None,
            visited_order=visited_order,
            success=False,
            steps=steps,
            exploration_history=exploration_history,
            **metrics
        )

    def visualize_search(self, result: SearchResult, delay: float = None) -> None:
        """Visualize Greedy Best-First Search with heuristic information."""
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

            # Educational commentary specific to Greedy Best-First Search
            expanded_node = format_node(step_info["expanded_node"])
            commentary = [
                f"Step {step_info['step']}: Expanding node {expanded_node} with h={step_info['expanded_node_h']:.2f}",
                f"Greedy Best-First Search always expands the node with the lowest heuristic value."
            ]

            # Add information about neighbors discovered
            if step_info["neighbors_added"]:
                neighbors_text = ", ".join(
                    [f"{format_node(n)} (h={h:.2f})" for h, n in step_info["neighbors_added"]]
                )
                commentary.append(f"Discovered neighbors: {neighbors_text}")
            else:
                commentary.append(f"No new neighbors were discovered.")

            # Information about frontier
            frontier_text = ", ".join(
                [f"{format_node(n)} (h={h:.2f})" for h, n in frontier]
            )
            commentary.append(f"Frontier: [{frontier_text}]")

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