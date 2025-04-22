from abc import abstractmethod

from ..base import SearchAlgorithmBase

class InformedSearch(SearchAlgorithmBase):
    """Base class for informed search algorithms (Greedy Best-First, A*).

    Informed search algorithms use domain knowledge (heuristics) to guide the search.
    """

    def _initialize_metrics(self, start, goal):
        """Initialize common metrics for informed search algorithms."""
        h_start = self.env.calculate_manhattan_distance(start, goal)

        return {
            "node_discovery": {start: 0},
            "node_expansion": {},
            "node_h_value": {start: h_start},
            "node_g_value": {start: 0},
            "node_f_value": {start: self._calculate_f(0, h_start)}
        }

    @abstractmethod
    def _calculate_f(self, g, h):
        """Calculate f-value based on g and h (varies by algorithm)."""
        pass

    @abstractmethod
    def _should_update_node(self, neighbor, tentative_g, g_value, frontier_dict):
        """Determine if a node's path should be updated."""
        pass

    def _create_step_info(self, current_node, steps, neighbors_added, frontier_before,
                          frontier_after, metrics):
        """Create step info dictionary for informed search visualization."""
        return {
            "step": steps,
            "expanded_node": current_node,
            "expanded_node_f": metrics["node_f_value"][current_node],
            "expanded_node_g": metrics["node_g_value"][current_node],
            "expanded_node_h": metrics["node_h_value"][current_node],
            "neighbors_added": neighbors_added,
            "frontier_before": frontier_before,
            "frontier_after": frontier_after
        }