from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import os
import tempfile
import imageio

from ...core.environment import MazeEnvironment
from ...core.results import SearchResult

class SearchAlgorithmDashboard(ABC):
    """Abstract base class for search algorithm educational dashboards."""

    def __init__(self, env: MazeEnvironment, result: SearchResult):
        """Initialize the educational dashboard with search results."""
        self.env = env
        self.result = result
        self.algorithm_name = self.__class__.__name__.replace("Dashboard", "")
        self.steps_data = []
        self._extract_history_data()

    @abstractmethod
    def _extract_history_data(self):
        """Process exploration history into data for visualization."""
        pass

    @abstractmethod
    def get_frontier_name(self) -> str:
        """Return name of frontier data structure (Queue, Stack, etc.)."""
        pass

    def create_maze_graph(self):
        """Create a NetworkX graph from maze data."""
        G = nx.Graph()

        # Add nodes for all valid positions
        for r in range(self.env.grid.shape[0]):
            for c in range(self.env.grid.shape[1]):
                if self.env.grid[r, c] == 0:  # If not a wall
                    G.add_node((r, c))

        # Add edges between adjacent nodes
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for node in G.nodes():
            r, c = node
            for dr, dc in directions:
                neighbor = (r + dr, c + dc)
                if neighbor in G:  # If neighbor exists in graph
                    G.add_edge(node, neighbor)

        return G

    def _plot_maze(self, ax, step_data):
        """Plot the maze with current path and visited nodes."""
        rows, cols = self.env.grid.shape
        viz_grid = np.ones((rows, cols)) * 5  # Initialize with unvisited path value

        # Fill in walls
        viz_grid[self.env.grid == 1] = 0  # Walls

        # Fill in visited paths
        for pos in step_data['visited']:
            r, c = pos
            if self.env.grid[r, c] == 0:  # Only if it's a path
                viz_grid[r, c] = 1  # Visited paths

        # Fill in current frontier
        # Use frontier_nodes if available (for informed search), otherwise use frontier
        frontier_to_plot = step_data.get('frontier_nodes', step_data['frontier'])
        for pos in frontier_to_plot:
            r, c = pos
            if pos != self.env.start and pos != self.env.end:
                viz_grid[r, c] = 6  # Frontier nodes

        # Fill in expanded node
        if step_data['expanded_node'] != self.env.start and step_data['expanded_node'] != self.env.end:
            r, c = step_data['expanded_node']
            viz_grid[r, c] = 7  # Current expanded node

        # Fill in current path
        if step_data['current_path']:
            for pos in step_data['current_path']:
                if pos != self.env.start and pos != self.env.end:
                    r, c = pos
                    viz_grid[r, c] = 2  # Current path

        # Mark start and end
        viz_grid[self.env.start] = 3  # Start
        viz_grid[self.env.end] = 4    # Goal

        # Define colors with enhanced palette
        cmap = plt.cm.colors.ListedColormap([
            'black',     # 0: Wall
            'yellow',    # 1: Visited
            'green',     # 2: Current path
            'blue',      # 3: Start
            'purple',    # 4: Goal
            'white',     # 5: Unvisited path
            'lightblue', # 6: Frontier
            'red'        # 7: Currently expanded node
        ])
        bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
        norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)

        # Plot the maze
        ax.imshow(viz_grid, cmap=cmap, norm=norm)
        ax.set_title(f"{self.algorithm_name} Search - Step {step_data['step']}")
        ax.set_xticks([])
        ax.set_yticks([])

        # Add legend
        legend_elements = [
            plt.Rectangle((0,0), 1, 1, color='white', label='Path'),
            plt.Rectangle((0,0), 1, 1, color='yellow', label='Visited'),
            plt.Rectangle((0,0), 1, 1, color='lightblue', label=self.get_frontier_name()),
            plt.Rectangle((0,0), 1, 1, color='red', label='Current Node'),
            plt.Rectangle((0,0), 1, 1, color='green', label='Current Path'),
            plt.Rectangle((0,0), 1, 1, color='blue', label='Start'),
            plt.Rectangle((0,0), 1, 1, color='purple', label='Goal'),
            plt.Rectangle((0,0), 1, 1, color='black', label='Wall')
        ]
        ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3)

    @abstractmethod
    def _plot_algorithm_state(self, ax, step_data):
        """Plot algorithm-specific state visualization."""
        pass

    @abstractmethod
    def _print_step_explanation(self, step_data):
        """Print algorithm-specific educational explanations."""
        pass

    def visualize_step(self, step_idx: int):
        """Display a single step of the algorithm with educational information."""
        if not self.steps_data or step_idx >= len(self.steps_data):
            print("Invalid step index")
            return

        step_data = self.steps_data[step_idx]
        fig = plt.figure(figsize=(18, 8))

        ax1 = plt.subplot2grid((1, 2), (0, 0))
        self._plot_maze(ax1, step_data)

        ax2 = plt.subplot2grid((1, 2), (0, 1))
        self._plot_algorithm_state(ax2, step_data)

        plt.tight_layout()
        plt.show()

        self._print_step_explanation(step_data)

    def animate_on_graph(self, output_file=None, fps=1, size=5):
        """Animate algorithm on graph representation."""
        if output_file is None:
            output_file = f"{self.algorithm_name.lower()}_graph.gif"

        try:
            G = self.create_maze_graph()
            pos = {node: (node[1], -node[0]) for node in G.nodes()}

            node_size = 300
            edge_width = 1
            path_edge_width = 3

            colors = {
                'regular': 'lightgray',
                'visited': 'yellow',
                'frontier': 'lightblue',
                'path': 'green',
                'start': 'blue',
                'end': 'purple',
                'expanded': 'red'
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                frame_files = []

                # Create frames for each step
                for i, step_data in enumerate(self.steps_data):
                    plt.figure(figsize=(size, size))

                    # Draw base graph elements and all nodes
                    nx.draw_networkx_nodes(G, pos, node_color=colors['regular'], node_size=node_size)

                    # Draw visited nodes
                    visited_only = [n for n in step_data['visited']
                                if n not in step_data['frontier']
                                and (not step_data['current_path'] or n not in step_data['current_path'])
                                and n != self.env.start
                                and n != self.env.end
                                and n != step_data['expanded_node']]
                    if visited_only:
                        nx.draw_networkx_nodes(G, pos, nodelist=visited_only,
                                            node_color=colors['visited'], node_size=node_size)

                    # Draw frontier nodes - use frontier_nodes if available
                    frontier_to_plot = step_data.get('frontier_nodes', step_data['frontier'])
                    frontier_only = [n for n in frontier_to_plot
                                if (not step_data['current_path'] or n not in step_data['current_path'])
                                and n != self.env.start
                                and n != self.env.end
                                and n != step_data['expanded_node']]
                    if frontier_only:
                        nx.draw_networkx_nodes(G, pos, nodelist=frontier_only,
                                            node_color=colors['frontier'], node_size=node_size)

                    # Draw current path
                    if step_data['current_path']:
                        path_only = [n for n in step_data['current_path']
                                    if n != self.env.start
                                    and n != self.env.end
                                    and n != step_data['expanded_node']]
                        if path_only:
                            nx.draw_networkx_nodes(G, pos, nodelist=path_only,
                                                node_color=colors['path'], node_size=node_size)

                        path_edges = list(zip(step_data['current_path'][:-1], step_data['current_path'][1:]))
                        nx.draw_networkx_edges(G, pos, edgelist=path_edges,
                                            width=path_edge_width, edge_color=colors['path'])

                    # Draw special nodes
                    nx.draw_networkx_nodes(G, pos, nodelist=[step_data['expanded_node']],
                                        node_color=colors['expanded'], node_size=node_size)

                    nx.draw_networkx_nodes(G, pos, nodelist=[self.env.start],
                                        node_color=colors['start'], node_size=node_size)
                    nx.draw_networkx_nodes(G, pos, nodelist=[self.env.end],
                                        node_color=colors['end'], node_size=node_size)

                    # Draw all edges
                    nx.draw_networkx_edges(G, pos, width=edge_width, alpha=0.5)

                    # Add labels
                    nx.draw_networkx_labels(G, pos, labels={node: f"{node[0]},{node[1]}" for node in G.nodes()})

                    plt.title(f"{self.algorithm_name} Graph Traversal - Step {step_data['step']} / {len(self.steps_data)}")
                    plt.axis('off')

                    frame_file = os.path.join(temp_dir, f"frame_{i:03d}.png")
                    plt.savefig(frame_file)
                    frame_files.append(frame_file)
                    plt.close()

                # Add final frame if search was successful
                if self.result.success and self.result.path:
                    self._create_final_frame(G, pos, colors, edge_width, path_edge_width, temp_dir, frame_files)

                # Create GIF
                with imageio.get_writer(output_file, mode='I', fps=fps) as writer:
                    for frame_file in frame_files:
                        image = imageio.imread(frame_file)
                        writer.append_data(image)

                print(f"Graph animation saved to {output_file}")

        except Exception as e:
            print(f"Error in {self.algorithm_name} graph animation: {e}")

    def _create_final_frame(self, G, pos, colors, edge_width, path_edge_width, temp_dir, frame_files):
        """Create final frame showing complete solution."""
        plt.figure(figsize=(6, 6))

        # Draw regular nodes
        nx.draw_networkx_nodes(G, pos, node_color=colors['regular'], node_size=300)

        # Draw visited nodes
        visited_only = [n for n in self.result.visited
                    if n not in self.result.path
                    and n != self.env.start
                    and n != self.env.end]
        if visited_only:
            nx.draw_networkx_nodes(G, pos, nodelist=visited_only,
                                node_color=colors['visited'], node_size=300)

        # Draw path nodes
        path_only = [n for n in self.result.path
                    if n != self.env.start
                    and n != self.env.end]
        if path_only:
            nx.draw_networkx_nodes(G, pos, nodelist=path_only,
                                node_color=colors['path'], node_size=300)

        # Draw start and end
        nx.draw_networkx_nodes(G, pos, nodelist=[self.env.start],
                            node_color=colors['start'], node_size=300)
        nx.draw_networkx_nodes(G, pos, nodelist=[self.env.end],
                            node_color=colors['end'], node_size=300)

        # Draw all edges
        nx.draw_networkx_edges(G, pos, width=edge_width, alpha=0.5)

        # Highlight path edges
        if self.result.path:
            path_edges = list(zip(self.result.path[:-1], self.result.path[1:]))
            nx.draw_networkx_edges(G, pos, edgelist=path_edges,
                                width=path_edge_width, edge_color=colors['path'])

        # Add labels
        nx.draw_networkx_labels(G, pos, labels={node: f"{node[0]},{node[1]}" for node in G.nodes()})

        plt.title(f"{self.algorithm_name} Graph Traversal - Final Path ({len(self.result.path)-1 if self.result.path else 0} steps)")
        plt.axis('off')

        frame_file = os.path.join(temp_dir, "frame_final.png")
        plt.savefig(frame_file)
        frame_files.append(frame_file)
        plt.close()

    def create_gif(self, filename=None, fps=1, dpi=100):
        """Create a GIF animation from algorithm steps."""
        if filename is None:
            filename = f"{self.algorithm_name.lower()}_animation.gif"

        print(f"Creating GIF with {len(self.steps_data)} frames...")

        with tempfile.TemporaryDirectory() as temp_dir:
            frame_files = []
            # Create frames for each exploration step
            for i, step_data in enumerate(self.steps_data):
                fig = plt.figure(figsize=(18, 8))

                ax1 = plt.subplot2grid((1, 2), (0, 0))
                self._plot_maze(ax1, step_data)

                ax2 = plt.subplot2grid((1, 2), (0, 1))
                self._plot_algorithm_state(ax2, step_data)

                plt.tight_layout()

                frame_file = os.path.join(temp_dir, f"frame_{i:03d}.png")
                plt.savefig(frame_file, dpi=dpi)
                frame_files.append(frame_file)
                plt.close(fig)

            # Add final solution frame if search was successful
            if self.result.success and self.result.path:
                # Create final frame showing complete solution
                fig = plt.figure(figsize=(18, 8))

                # Left side: maze with complete solution path
                ax1 = plt.subplot2grid((1, 2), (0, 0))

                # Create a mock step_data for the final state
                final_step_data = {
                    'step': self.steps_data[-1]['step'] + 1 if self.steps_data else 1,
                    'expanded_node': self.env.end,
                    'neighbors_added': [],
                    'frontier_before': [],
                    'frontier_after': [],
                    'frontier': [],
                    'visited': self.result.visited,
                    'current_path': self.result.path,
                    'visited_count': len(self.result.visited),
                    'frontier_size': 0
                }

                self._plot_maze(ax1, final_step_data)
                ax1.set_title(f"{self.algorithm_name} Search - Final Solution")

                # Right side: solution metrics
                ax2 = plt.subplot2grid((1, 2), (0, 1))
                ax2.axis('off')

                # Create solution summary table
                table_data = [
                    ["Total Steps", str(self.result.steps)],
                    ["Path Length", str(len(self.result.path))],
                    ["Visited Nodes", str(len(self.result.visited))],
                    ["Execution Time", f"{self.result.execution_time:.3f}s"],
                    ["Efficiency", f"{len(self.result.path)/len(self.result.visited)*100:.1f}%"]
                ]

                solution_table = ax2.table(
                    cellText=table_data,
                    colLabels=["Metric", "Value"],
                    colWidths=[0.3, 0.7],
                    loc='center',
                    cellLoc='center',
                    bbox=[0.1, 0.4, 0.8, 0.5]
                )
                solution_table.auto_set_font_size(False)
                solution_table.set_fontsize(12)

                # Style table
                for i in range(len(table_data) + 1):
                    for j in range(2):
                        cell = solution_table[i, j]
                        cell.set_edgecolor('black')
                        if i == 0:  # Header
                            cell.set_facecolor('#4472C4')
                            cell.set_text_props(color='white', fontweight='bold')
                        else:
                            cell.set_facecolor('#D9E1F2' if i % 2 else '#E9EDF4')

                # Add completion message
                ax2.text(0.5, 0.8, "SEARCH COMPLETED", ha='center', va='center',
                        fontsize=18, fontweight='bold', color='green')
                ax2.text(0.5, 0.2, f"Solution path found with {len(self.result.path)-1} steps",
                        ha='center', va='center', fontsize=14)

                plt.tight_layout()

                frame_file = os.path.join(temp_dir, "frame_final.png")
                plt.savefig(frame_file, dpi=dpi)
                frame_files.append(frame_file)
                plt.close(fig)

            # Create GIF
            with imageio.get_writer(filename, mode='I', fps=fps) as writer:
                for frame_file in frame_files:
                    image = imageio.imread(frame_file)
                    writer.append_data(image)

        print(f"GIF animation saved to {filename}")


