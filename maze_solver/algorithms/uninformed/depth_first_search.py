from .base import UninformedSearch


class DepthFirstSearch(UninformedSearch):
    """Depth-First Search implementation."""

    def _initialize_frontier(self, start):
        """Initialize a stack with the start node."""
        return [start]

    def _get_next_node(self, frontier):
        """Get the next node from the stack (LIFO)."""
        return frontier.pop()

    def _create_step_info(
        self, current_node, steps, neighbors_added, frontier_before, frontier_after
    ):
        """Create step info with stack terminology."""
        info = super()._create_step_info(
            current_node, steps, neighbors_added, frontier_before, frontier_after
        )
        info["stack_before"] = frontier_before
        info["stack_after"] = frontier_after
        return info
