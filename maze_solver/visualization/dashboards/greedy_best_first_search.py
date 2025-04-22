from .base import SearchAlgorithmDashboard

class GreedyBestFirstDashboard(SearchAlgorithmDashboard):
    """Educational dashboard for visualizing Greedy Best-First Search algorithm."""

    def get_frontier_name(self) -> str:
        return "Priority Queue (Frontier)"

    def _extract_history_data(self):
        self.steps_data = []

        for i, state in enumerate(self.result.exploration_history):
            closed_set, frontier, current_path, step_info = state

            # Extract just the node coordinates from frontier tuples (h_value, node)
            frontier_nodes = [node for _, node in frontier] if isinstance(frontier[0], tuple) else frontier

            self.steps_data.append({
                'step': step_info['step'],
                'expanded_node': step_info['expanded_node'],
                'expanded_node_h': step_info['expanded_node_h'],
                'neighbors_added': step_info['neighbors_added'],
                'frontier_before': step_info.get('frontier_before', []),
                'frontier_after': step_info.get('frontier_after', []),
                'frontier': frontier,  # Keep original frontier for priority queue visualization
                'frontier_nodes': frontier_nodes,  # Add extracted node coordinates
                'visited': list(closed_set),
                'current_path': current_path,
                'visited_count': len(closed_set),
                'frontier_size': len(frontier)
            })

    def _plot_algorithm_state(self, ax, step_data):
        ax.axis('off')

        def format_node(node):
            return f"({node[0]},{node[1]})"

        # Create main metrics table with heuristic value
        table_data = [
            ["Step", str(step_data['step'])],
            ["Expanded Node", format_node(step_data['expanded_node'])],
            ["Heuristic (h)", f"{step_data['expanded_node_h']:.2f}"],
            ["Visited Nodes", str(step_data['visited_count'])],
            ["Path Length", str(len(step_data['current_path']) if step_data['current_path'] else 0)]
        ]

        # Draw main table
        main_table = ax.table(
            cellText=table_data,
            colLabels=["Metric", "Value"],
            colWidths=[0.3, 0.7],
            loc='center',
            cellLoc='center',
            bbox=[0.1, 0.65, 0.8, 0.3]
        )
        main_table.auto_set_font_size(False)
        main_table.set_fontsize(12)

        # Style table
        for i in range(len(table_data) + 1):
            for j in range(2):
                cell = main_table[i, j]
                cell.set_edgecolor('black')
                if i == 0:  # Header
                    cell.set_facecolor('#4472C4')
                    cell.set_text_props(color='white', fontweight='bold')
                else:
                    cell.set_facecolor('#D9E1F2' if i % 2 else '#E9EDF4')

        # Draw priority queue visualization
        self._draw_frontier_table(ax, step_data)

        # Add explanation
        explanation = [
            f"Greedy Best-First Search:",
            f"• Expands nodes with lowest heuristic (h) value",
            f"• Current node h = {step_data['expanded_node_h']:.2f}",
            f"• Prioritizes nodes that appear closest to goal",
            f"• Does not consider path cost to node"
        ]
        ax.text(0.5, 0.1, "\n".join(explanation), ha='center', va='center',
                fontsize=10, bbox=dict(boxstyle="round,pad=0.5", facecolor='#FFFFCC', alpha=0.5))

    def _draw_frontier_table(self, ax, step_data):
        """Draw priority queue table with heuristic values."""
        def format_node(node):
            return f"({node[0]},{node[1]})"

        # Draw priority queue
        ax.text(0.5, 0.5, "Priority Queue (sorted by h-value)", ha='center', va='center',
                fontsize=14, fontweight='bold')

        queue_data = []
        if isinstance(step_data['frontier'], list) and step_data['frontier']:
            for i, (h, node) in enumerate(step_data['frontier']):
                queue_data.append([f"{i+1}", format_node(node), f"{h:.2f}"])

        if queue_data:
            queue_table = ax.table(
                cellText=queue_data,
                colLabels=["Position", "Node", "h-value"],
                colWidths=[0.15, 0.25, 0.2],
                loc='center',
                cellLoc='center',
                bbox=[0.2, 0.2, 0.6, 0.25]
            )
            queue_table.auto_set_font_size(False)
            queue_table.set_fontsize(12)

            # Style table
            for i in range(len(queue_data) + 1):
                for j in range(3):
                    cell = queue_table[i, j]
                    cell.set_edgecolor('black')
                    if i == 0:  # Header
                        cell.set_facecolor('#70AD47')
                        cell.set_text_props(color='white', fontweight='bold')
                    else:
                        cell.set_facecolor('#E2EFDA' if i % 2 else '#EAF5E0')
        else:
            ax.text(0.5, 0.3, "Queue is empty", ha='center', va='center', fontsize=12, color='red')

    def _print_step_explanation(self, step_data):
        def format_node(node):
            return f"({node[0]},{node[1]})"

        expanded_node = format_node(step_data['expanded_node'])
        print(f"🔍 Greedy Best-First Search Step {step_data['step']} Explanation:")
        print(f"---------------------------")
        print(f"Currently expanding: {expanded_node} with h={step_data['expanded_node_h']:.2f}")

        print("\n1️⃣ Algorithm Process:")
        print(f"   - Selected node {expanded_node} with lowest heuristic value h={step_data['expanded_node_h']:.2f}")
        print(f"   - Checked if it's the goal (it's {'the goal! 🎉' if step_data['expanded_node'] == self.env.end else 'not the goal'})")

        if step_data['expanded_node'] != self.env.end:
            if isinstance(step_data['neighbors_added'], list) and step_data['neighbors_added']:
                neighbors_text = ", ".join([f"{format_node(n)} (h={h:.2f})" for h, n in step_data['neighbors_added']])
                print(f"\n2️⃣ Discovered neighbors with heuristic values: {neighbors_text}")
                print("   These neighbors were added to the priority queue sorted by h-value.")
            else:
                print("\n2️⃣ No new neighbors were discovered (all neighbors are already visited)")

        print("\n3️⃣ Greedy Best-First Search Properties:")
        print("   - Always expands node closest to goal according to heuristic")
        print("   - Can find solutions quickly but not guaranteed to be optimal")
        print("   - May get stuck in local minima without considering path cost")