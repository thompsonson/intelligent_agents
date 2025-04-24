from .base import UninformedSearch


class DepthFirstSearch(UninformedSearch):
    """Depth-First Search implementation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, frontier_name="stack", **kwargs)

    def _initialize_frontier(self, start):
        """Initialize a stack with the start node."""
        return [start]

    def _get_next_node(self, frontier):
        """Get the next node from the stack (LIFO)."""
        return frontier.pop()
