from collections import deque

from .base import UninformedSearch


class BreadthFirstSearch(UninformedSearch):
    """Breadth-First Search implementation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, frontier_name="queue", **kwargs)

    def _initialize_frontier(self, start):
        """Initialize a queue with the start node."""
        return deque([start])

    def _get_next_node(self, frontier):
        """Get the next node from the queue (FIFO)."""
        return frontier.popleft()
