from collections import deque

from .base import UninformedSearch


class BreadthFirstSearch(UninformedSearch):
    """Breadth-First Search implementation."""

    def _initialize_frontier(self, start):
        """Initialize a queue with the start node."""
        return deque([start])

    def _get_next_node(self, frontier):
        """Get the next node from the queue (FIFO)."""
        return frontier.popleft()

    def _create_step_info(
        self, current_node, steps, neighbors_added, frontier_before, frontier_after
    ):
        """Create step info with queue terminology."""
        info = super()._create_step_info(
            current_node, steps, neighbors_added, frontier_before, frontier_after
        )
        info["queue_before"] = frontier_before
        info["queue_after"] = frontier_after
        return info
