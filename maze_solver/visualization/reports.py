import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

from ..core.config import Config
from ..core.environment import MazeEnvironment
from ..algorithms.uninformed.breadth_first_search import BreadthFirstSearch
from ..algorithms.uninformed.depth_first_search import DepthFirstSearch
from ..algorithms.informed.greedy_best_first_search import GreedyBestFirstSearch
from ..algorithms.informed.a_star_search import AStarSearch


def compare_search_algorithms(maze_size=10, maze_id=None, show_visualizations=False):
    """Compare performance of different search algorithms on the same maze."""
    # Create a maze environment
    config = Config(maze_size=maze_size, maze_id=maze_id, show_exploration=True)
    env = MazeEnvironment(config)

    # Create algorithm instances
    algorithms = [
        BreadthFirstSearch(env),
        DepthFirstSearch(env),
        GreedyBestFirstSearch(env),
        AStarSearch(env)
    ]

    # Run all algorithms and collect results
    results = {}
    for algo in algorithms:
        print(f"Running {algo.name}...")
        result = algo.run()
        results[algo.name] = result

        # Show visualization if requested
        if show_visualizations:
            algo.visualize_search(result)

    # Create comparison dataframe
    comparison_data = []
    for algo_name, result in results.items():
        data = {
            'Algorithm': algo_name,
            'Success': result.success,
            'Steps': result.steps,
            'Path Length': len(result.path) if result.path else 0,
            'Visited Nodes': len(result.visited),
            'Execution Time (s)': result.execution_time,
            'Path Efficiency (%)': round(len(result.path) / len(result.visited) * 100, 2) if result.path else 0
        }
        comparison_data.append(data)

    comparison_df = pd.DataFrame(comparison_data)

    # Display comparison table
    print("\nAlgorithm Comparison:")
    display(comparison_df)

    # Plot comparisons
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))

    # Execution time
    axs[0, 0].bar(comparison_df['Algorithm'], comparison_df['Execution Time (s)'])
    axs[0, 0].set_title('Execution Time (s)')
    axs[0, 0].set_ylabel('Seconds')

    # Path length
    axs[0, 1].bar(comparison_df['Algorithm'], comparison_df['Path Length'])
    axs[0, 1].set_title('Path Length')
    axs[0, 1].set_ylabel('Steps')

    # Visited nodes
    axs[1, 0].bar(comparison_df['Algorithm'], comparison_df['Visited Nodes'])
    axs[1, 0].set_title('Nodes Visited')
    axs[1, 0].set_ylabel('Count')

    # Efficiency
    axs[1, 1].bar(comparison_df['Algorithm'], comparison_df['Path Efficiency (%)'])
    axs[1, 1].set_title('Path Efficiency (Path Length / Visited Nodes)')
    axs[1, 1].set_ylabel('Percentage (%)')

    plt.tight_layout()
    plt.show()

    return comparison_df, results, env