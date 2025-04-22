from .base import SearchAlgorithmDashboard

class BFSDashboard(SearchAlgorithmDashboard):
    """Educational dashboard for visualizing Breadth-First Search algorithm."""

    def get_frontier_name(self) -> str:
        return "Queue (Frontier)"

    def _extract_history_data(self):
        self.steps_data = []

        for i, state in enumerate(self.result.exploration_history):
            visited, frontier, current_path, step_info = state

            # Get queue-specific information
            frontier_before = step_info.get('queue_before', [])
            frontier_after = step_info.get('queue_after', [])

            self.steps_data.append({
                'step': step_info['step'],
                'expanded_node': step_info['expanded_node'],
                'neighbors_added': step_info['neighbors_added'],
                'frontier_before': frontier_before,
                'frontier_after': frontier_after,
                'frontier': frontier_after,
                'visited': list(visited),
                'current_path': current_path,
                'visited_count': len(visited),
                'frontier_size': len(frontier)
            })

    def _plot_algorithm_state(self, ax, step_data):
        ax.axis('off')

        def format_node(node):
            return f"({node[0]},{node[1]})"

        # Create main metrics table
        table_data = [
            ["Step", str(step_data['step'])],
            ["Expanded Node", format_node(step_data['expanded_node'])],
            ["Visited Nodes", str(step_data['visited_count'])],
            ["Path Length", str(len(step_data['current_path']) if step_data['current_path'] else 0)]
        ]

        # Format neighbors
        neighbors_text = (", ".join([format_node(n) for n in step_data['neighbors_added']])
                          if step_data['neighbors_added'] else "None (all neighbors already visited)")
        table_data.append(["Neighbors Added", neighbors_text])

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

        # Queue visualization
        self._draw_frontier_table(ax, step_data, "Queue BEFORE", "Queue AFTER")

        # Add operation explanation
        operation_explanation = [
            f"1. Dequeued {format_node(step_data['expanded_node'])} from front of queue",
            f"2. Checked if it's the goal node",
            f"3. Examined unvisited neighbors"
        ]
        if step_data['neighbors_added']:
            neighbors = ", ".join([format_node(n) for n in step_data['neighbors_added']])
            operation_explanation.append(f"4. Added neighbors to queue: {neighbors}")
        else:
            operation_explanation.append("4. No new neighbors to add")

        # Draw explanation box
        ax.text(0.5, 0.1, "\n".join(operation_explanation), ha='center', va='center',
                fontsize=10, bbox=dict(boxstyle="round,pad=0.5", facecolor='#FFFFCC', alpha=0.5))

    def _draw_frontier_table(self, ax, step_data, before_label, after_label):
        """Draw frontier tables (before and after expansion)."""
        def format_node(node):
            return f"({node[0]},{node[1]})"

        # Draw "BEFORE" label and table
        ax.text(0.3, 0.5, before_label, ha='center', va='center', fontsize=14, fontweight='bold')

        queue_before_data = []
        for i, node in enumerate(step_data['frontier_before']):
            queue_before_data.append([f"Queue[{i}]", format_node(node)])

        if queue_before_data:
            queue_before_table = ax.table(
                cellText=queue_before_data,
                colLabels=["Index", "Node"],
                colWidths=[0.15, 0.25],
                loc='center',
                cellLoc='center',
                bbox=[0.05, 0.2, 0.4, 0.25]
            )
            queue_before_table.auto_set_font_size(False)
            queue_before_table.set_fontsize(12)

            # Style table
            for i in range(len(queue_before_data) + 1):
                for j in range(2):
                    cell = queue_before_table[i, j]
                    cell.set_edgecolor('black')
                    if i == 0:  # Header
                        cell.set_facecolor('#ED7D31')
                        cell.set_text_props(color='white', fontweight='bold')
                    else:
                        cell.set_facecolor('#FBE5D6' if i % 2 else '#FDF2EA')
        else:
            ax.text(0.3, 0.3, "Queue was empty", ha='center', va='center', fontsize=12, color='red')

        # Draw "AFTER" label and table
        ax.text(0.7, 0.5, after_label, ha='center', va='center', fontsize=14, fontweight='bold')

        queue_after_data = []
        for i, node in enumerate(step_data['frontier_after']):
            queue_after_data.append([f"Queue[{i}]", format_node(node)])

        if queue_after_data:
            queue_after_table = ax.table(
                cellText=queue_after_data,
                colLabels=["Index", "Node"],
                colWidths=[0.15, 0.25],
                loc='center',
                cellLoc='center',
                bbox=[0.55, 0.2, 0.4, 0.25]
            )
            queue_after_table.auto_set_font_size(False)
            queue_after_table.set_fontsize(12)

            # Style table
            for i in range(len(queue_after_data) + 1):
                for j in range(2):
                    cell = queue_after_table[i, j]
                    cell.set_edgecolor('black')
                    if i == 0:  # Header
                        cell.set_facecolor('#70AD47')
                        cell.set_text_props(color='white', fontweight='bold')
                    else:
                        cell.set_facecolor('#E2EFDA' if i % 2 else '#EAF5E0')
        else:
            ax.text(0.7, 0.3, "Queue is now empty", ha='center', va='center', fontsize=12, color='red')

    def _print_step_explanation(self, step_data):
        def format_node(node):
            return f"({node[0]},{node[1]})"

        expanded_node = format_node(step_data['expanded_node'])
        print(f"🔍 BFS Step {step_data['step']} Explanation:")
        print(f"---------------------------")
        print(f"Currently expanding: {expanded_node}")

        print("\n1️⃣ BFS Algorithm Process:")
        print(f"   - Dequeued node {expanded_node} from the front of the queue")
        print(f"   - Checked if it's the goal (it's {'the goal! 🎉' if step_data['expanded_node'] == self.env.end else 'not the goal'})")

        if step_data['expanded_node'] != self.env.end:
            if step_data['neighbors_added']:
                neighbors_text = ", ".join([format_node(n) for n in step_data['neighbors_added']])
                print(f"\n2️⃣ Discovered {len(step_data['neighbors_added'])} unvisited neighbors: {neighbors_text}")
                print("   These neighbors were added to the back of the queue for later exploration.")
                print("   💡 This is why BFS explores nodes in order of their distance from the start.")
            else:
                print("\n2️⃣ No new neighbors were discovered (all neighbors are already visited)")

        print(f"\n3️⃣ Queue status:")
        if step_data['frontier']:
            queue_text = ", ".join([format_node(n) for n in step_data['frontier']])
            print(f"   Queue now contains: {queue_text}")
            print(f"   Next node to explore will be: {format_node(step_data['frontier'][0])}")
        else:
            print("   Queue is now empty. Search will terminate.")

        print("\n4️⃣ BFS Properties:")
        print("   - BFS always finds the shortest path in unweighted graphs")
        print("   - Time complexity: O(V + E) where V is vertices and E is edges")
        print("   - Space complexity: O(V) for the queue and visited set")

        print(f"\n📊 Current Statistics:")
        print(f"   - Visited {step_data['visited_count']} nodes so far")
        print(f"   - Queue size: {step_data['frontier_size']}")
        print(f"   - Current path length: {len(step_data['current_path']) if step_data['current_path'] else 0}")


