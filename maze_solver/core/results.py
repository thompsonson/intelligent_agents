from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any

@dataclass
class SearchResult:
    """Enhanced container for search algorithm results with educational metrics.

    This class stores and analyzes the results of search algorithm execution, providing
    not only basic path information but also educational metrics and insights about
    algorithm performance. It includes capabilities for generating reports and
    visualizations of search results.

    Attributes:
        path (List[Tuple[int, int]]): Solution path from start to goal, if found.
        visited (List[Tuple[int, int]]): List of nodes visited during search, in order.
        success (bool): Whether the search found a valid path to the goal.
        steps (int): Number of algorithm steps executed during search.
        execution_time (float): Time taken for the search execution in seconds.
        exploration_history (List): History of algorithm state for visualization/analysis.
        node_discovery (Dict): Maps each node to the step when it was first discovered.
        node_expansion (Dict): Maps each node to the step when it was expanded.
    """
    path: Optional[List[Tuple[int, int]]] = None  # Solution path from start to goal
    visited: List[Tuple[int, int]] = field(default_factory=list)  # List of visited nodes
    success: bool = False  # Whether the search found a path
    steps: int = 0  # Number of algorithm steps executed
    execution_time: float = 0.0  # Time taken for the search
    exploration_history: List = field(default_factory=list)  # History of algorithm state (for visualization)

    # Educational tracking metrics
    node_discovery: Dict[Tuple[int, int], int] = field(default_factory=dict)  # When each node was discovered
    node_expansion: Dict[Tuple[int, int], int] = field(default_factory=dict)  # When each node was expanded

    def __str__(self) -> str:
        """Enhanced string representation of results with educational metrics.

        Returns:
            A formatted string with key performance metrics and educational information.
        """
        if self.success:
            return self._format_success_output()
        else:
            return self._format_failure_output()

    def _format_success_output(self) -> str:
        """Format output for successful search with educational information.

        Returns:
            A formatted string with performance metrics for successful searches.
        """
        avg_branching = self._calculate_avg_branching_factor()

        output = [
            f"✅ Search succeeded in {self.steps} steps ({self.execution_time:.3f}s)",
            f"📏 Path length: {len(self.path)} nodes",
            f"🔍 Visited nodes: {len(self.visited)} nodes ({(len(self.visited) / self.steps):.2f} nodes/step)",
            f"⚙️ Efficiency: {(len(self.path) / len(self.visited) * 100):.1f}% (path nodes / visited nodes)",
            f"🌲 Average branching factor: {avg_branching:.2f} neighbors/node",
            f"⏱️ Average time per step: {(self.execution_time / self.steps * 1000):.2f} ms"
        ]

        return "\n".join(output)

    def _format_failure_output(self) -> str:
        """Format output for failed search with educational information.

        Returns:
            A formatted string with performance metrics and possible failure reasons.
        """
        avg_branching = self._calculate_avg_branching_factor()

        output = [
            f"❌ Search failed after {self.steps} steps ({self.execution_time:.3f}s)",
            f"🔍 Visited nodes: {len(self.visited)} nodes ({(len(self.visited) / self.steps):.2f} nodes/step)",
            f"🌲 Average branching factor: {avg_branching:.2f} neighbors/node",
            f"⏱️ Average time per step: {(self.execution_time / self.steps * 1000):.2f} ms",
            f"💡 Possible reasons for failure:",
            f"   - No valid path exists between start and goal",
            f"   - Search exceeded maximum step limit ({self.steps} steps)",
            f"   - Maze structure prevents reaching the goal"
        ]

        return "\n".join(output)

    def _calculate_avg_branching_factor(self) -> float:
        """Calculate the average branching factor during search.

        Returns:
            The average number of new nodes discovered per expanded node,
            which approximates the branching factor of the search space.
        """
        if not self.node_expansion or len(self.node_expansion) <= 1:
            return 0.0

        # We can determine this from the ratio of discovered nodes to expanded nodes
        # Excluding the start node which doesn't have a parent
        discovered_count = len(self.node_discovery) - 1  # -1 for start node
        expanded_count = len(self.node_expansion)

        return discovered_count / expanded_count if expanded_count > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for analysis with educational metrics.

        Returns:
            Dictionary containing all metrics and performance data for analysis.
        """
        return {
            'success': self.success,
            'steps': self.steps,
            'execution_time': self.execution_time,
            'path_length': len(self.path) if self.path else None,
            'visited_nodes': len(self.visited),
            'path_to_visited_ratio': (len(self.path) / len(self.visited)
                                     if self.path and len(self.visited) > 0 else None),
            'avg_branching_factor': self._calculate_avg_branching_factor(),
            'discovery_to_expansion_ratio': (len(self.node_discovery) / len(self.node_expansion)
                                           if self.node_expansion else None),
            'nodes_per_step': len(self.visited) / self.steps if self.steps > 0 else 0
        }
