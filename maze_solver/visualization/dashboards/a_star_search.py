from .base import SearchAlgorithmDashboard


class AStarDashboard(SearchAlgorithmDashboard):
    """Educational dashboard for visualizing A* Search algorithm."""

    def get_frontier_name(self) -> str:
        return "Priority Queue (Frontier)"

    def _extract_history_data(self):
        self.steps_data = []

        for i, state in enumerate(self.result.exploration_history):
            closed_set, frontier, current_path, step_info = state

            # Extract just the node coordinates from frontier tuples (f, g, node)
            frontier_nodes = [node for _, _, node in frontier] if frontier and isinstance(frontier[0], tuple) else frontier

            self.steps_data.append({
                'step': step_info['step'],
                'expanded_node': step_info['expanded_node'],
                'expanded_node_f': step_info['expanded_node_f'],
                'expanded_node_g': step_info['expanded_node_g'],
                'expanded_node_h': step_info['expanded_node_h'],
                'neighbors_added': step_info['neighbors_added'],
                'frontier_before': step_info.get('frontier_before', []),
                'frontier_after': step_info.get('frontier_after', []),
                'frontier_nodes': frontier_nodes,
                'frontier': frontier,
                'visited': list(closed_set),
                'current_path': current_path,
                'visited_count': len(closed_set),
                'frontier_size': len(frontier)
            })

    def _plot_algorithm_state(self, ax, step_data):
        ax.axis('off')

        def format_node(node):
            return f"({node[0]},{node[1]})"

        # Create main metrics table with f, g, h values
        table_data = [
            ["Step", str(step_data['step'])],
            ["Expanded Node", format_node(step_data['expanded_node'])],
            ["f = g + h", f"{step_data['expanded_node_f']:.2f}"],
            ["g (path cost)", f"{step_data['expanded_node_g']:.2f}"],
            ["h (heuristic)", f"{step_data['expanded_node_h']:.2f}"],
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
            bbox=[0.1, 0.7, 0.8, 0.25]
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
            f"A* Search Algorithm:",
            f"• Expands nodes with lowest f = g + h value",
            f"• g = cost from start to node ({step_data['expanded_node_g']:.2f})",
            f"• h = estimated cost to goal ({step_data['expanded_node_h']:.2f})",
            f"• f = total estimated cost ({step_data['expanded_node_f']:.2f})",
            f"• Balances path cost and goal proximity"
        ]
        ax.text(0.5, 0.15, "\n".join(explanation), ha='center', va='center',
                fontsize=10, bbox=dict(boxstyle="round,pad=0.5", facecolor='#FFFFCC', alpha=0.5))

    def _draw_frontier_table(self, ax, step_data):
        """Draw priority queue table with f, g, h values."""
        def format_node(node):
            return f"({node[0]},{node[1]})"

        # Draw priority queue
        ax.text(0.5, 0.55, "Priority Queue (sorted by f-value)", ha='center', va='center',
                fontsize=14, fontweight='bold')

        queue_data = []
        if isinstance(step_data['frontier'], list) and step_data['frontier']:
            for i, (f, g, node) in enumerate(step_data['frontier']):
                h = f - g  # Calculate h from f and g
                queue_data.append([f"{i+1}", format_node(node), f"{f:.2f}", f"{g:.2f}", f"{h:.2f}"])

        if queue_data:
            queue_table = ax.table(
                cellText=queue_data,
                colLabels=["Position", "Node", "f-value", "g-value", "h-value"],
                colWidths=[0.1, 0.2, 0.15, 0.15, 0.15],
                loc='center',
                cellLoc='center',
                bbox=[0.1, 0.3, 0.8, 0.2]
            )
            queue_table.auto_set_font_size(False)
            queue_table.set_fontsize(12)

            # Style table
            for i in range(len(queue_data) + 1):
                for j in range(5):
                    cell = queue_table[i, j]
                    cell.set_edgecolor('black')
                    if i == 0:  # Header
                        cell.set_facecolor('#70AD47')
                        cell.set_text_props(color='white', fontweight='bold')
                    else:
                        cell.set_facecolor('#E2EFDA' if i % 2 else '#EAF5E0')
        else:
            ax.text(0.5, 0.4, "Queue is empty", ha='center', va='center', fontsize=12, color='red')

    def _print_step_explanation(self, step_data):
        def format_node(node):
            return f"({node[0]},{node[1]})"

        expanded_node = format_node(step_data['expanded_node'])
        print(f"🔍 A* Search Step {step_data['step']} Explanation:")
        print(f"---------------------------")
        print(f"Currently expanding: {expanded_node} with f={step_data['expanded_node_f']:.2f} (g={step_data['expanded_node_g']:.2f}, h={step_data['expanded_node_h']:.2f})")

        print("\n1️⃣ Algorithm Process:")
        print(f"   - Selected node {expanded_node} with lowest f-value")
        print(f"   - f(n) = g(n) + h(n) = {step_data['expanded_node_g']:.2f} + {step_data['expanded_node_h']:.2f} = {step_data['expanded_node_f']:.2f}")
        print(f"   - Checked if it's the goal (it's {'the goal! 🎉' if step_data['expanded_node'] == self.env.end else 'not the goal'})")

        if step_data['expanded_node'] != self.env.end:
            if isinstance(step_data['neighbors_added'], list) and step_data['neighbors_added']:
                neighbors_text = ", ".join([f"{format_node(n)} (f={f:.2f}, g={g:.2f})" for f, g, n in step_data['neighbors_added']])
                print(f"\n2️⃣ Discovered neighbors with evaluation: {neighbors_text}")
                print("   These neighbors were added to the priority queue sorted by f-value.")
            else:
                print("\n2️⃣ No new neighbors were discovered (all neighbors are already visited)")

        print("\n3️⃣ A* Search Properties:")
        print("   - Combines benefits of Dijkstra's (optimal path) and Greedy (goal-directed)")
        print("   - Guaranteed to find optimal path if heuristic is admissible (never overestimates)")
        print("   - Balances exploration of promising paths with consideration of path cost")