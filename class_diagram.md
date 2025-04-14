```mermaid
classDiagram
      class Config {
          +int maze_size
          +Optional~int~ maze_id
          +float visualization_delay
          +bool show_exploration
          +Optional~int~ max_steps
      }

      class MazeEnvironment {
          -Maze _maze
          -int seed
          +Config config
          +ndarray grid
          +Tuple start
          +Tuple end
          +List optimal_path
          +int optimal_path_length
          +Dict graph
          +generate() void
          -_calculate_optimal_path() void
          -_create_graph() void
          +get_minimum_steps() Optional~int~
          +is_valid_move(state) bool
          +visualize(path, visited, show_optimal, save_path, title) void
      }

      class SearchResult {
          +Optional~List~ path
          +List visited
          +bool success
          +int steps
          +float execution_time
          +List exploration_history
          +Dict node_discovery
          +Dict node_expansion
          +__str__() str
          -_format_success_output() str
          -_format_failure_output() str
          -_calculate_avg_branching_factor() float
          +to_dict() Dict
          +generate_educational_report() str
          -_get_max_queue_size() int
          -_estimate_traversable_nodes() int
      }

      class SearchAlgorithmBase {
          <<abstract>>
          +MazeEnvironment env
          +Config config
          +str name
          +__init__(env) void
          +search(start, goal)* SearchResult
          +run(start, goal) SearchResult
          +visualize_search(result, delay) void
      }

      class BreadthFirstSearch {
          -_reconstruct_path(parent, start, goal) List
          +search(start, goal) SearchResult
          +visualize_search(result, delay) void
      }

      class MazeSearchVisualizer {
          +MazeEnvironment env
          +Dict algorithms
          +visualize_search_step_by_step(algorithm_name, delay) SearchResult
          +compare_algorithms(algorithm_names) DataFrame
          +visualize_comparison(comparison_df) void
      }

      class MazeExperiments {
          +Path base_path
          +str experiment_id
          +run_maze_size_experiment(algorithm_classes, maze_sizes, iterations) DataFrame
          +visualize_maze_size_experiment(df) void
      }

      class BFSEducationalDashboard {
          +MazeEnvironment env
          +SearchResult result
          -List steps_data
          +animate_bfs_on_graph(output_file, fps, size) void
          +visualize_maze_graph(highlight_path, size) void
          +create_maze_graph() Graph
          -_extract_history_data() void
          +visualize_step(step_idx) void
          -_plot_maze(ax, step_data) void
          -_plot_bfs_state(ax, step_data) void
          +create_gif(filename, fps, dpi) void
          -_print_step_explanation(step_data) void
          +run_animation(delay) void
          +create_interactive_widget() void
      }

      SearchAlgorithmBase <|-- BreadthFirstSearch : Inherits
      MazeEnvironment o-- Config : Contains
      SearchAlgorithmBase o-- MazeEnvironment : References
      SearchAlgorithmBase ..> SearchResult : Creates
      MazeSearchVisualizer o-- MazeEnvironment : References
      MazeSearchVisualizer o-- SearchAlgorithmBase : References
      BFSEducationalDashboard o-- MazeEnvironment : References
      BFSEducationalDashboard o-- SearchResult : References
      MazeExperiments ..> SearchAlgorithmBase : Uses
      MazeExperiments ..> MazeEnvironment : Creates