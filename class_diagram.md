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
          +calculate_manhattan_distance(state, goal) int
          +calculate_euclidean_distance(state, goal) float
          +get_step_cost(state1, state2) int
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
          +visualize_search(result, delay)* void
          +_reconstruct_path(parent, start, goal) List
          +create_search_result(path, visited_order, success, steps, exploration_history) SearchResult
      }

      class UninformedSearch {
          <<abstract>>
          +search(start, goal) SearchResult
          +_initialize_frontier(start)* void
          +_get_next_node(frontier)* node
          +_add_to_frontier(frontier, node)* void
          +_frontier_representation(frontier)* List
          +_create_step_info(current_node, steps, neighbors_added, frontier_before, frontier_after) Dict
      }

      class InformedSearch {
          <<abstract>>
          +_initialize_metrics(start, goal) Dict
          +_calculate_f(g, h)* float
          +_should_update_node(neighbor, tentative_g, g_value, frontier_dict)* bool
          +_create_step_info(current_node, steps, neighbors_added, frontier_before, frontier_after, metrics) Dict
      }

      class BreadthFirstSearch {
          +_initialize_frontier(start) deque
          +_get_next_node(frontier) node
          +_add_to_frontier(frontier, node) void
          +_frontier_representation(frontier) List
          +_create_step_info(current_node, steps, neighbors_added, frontier_before, frontier_after) Dict
      }

      class DepthFirstSearch {
          +_initialize_frontier(start) List
          +_get_next_node(frontier) node
          +_add_to_frontier(frontier, node) void
          +_frontier_representation(frontier) List
          +_create_step_info(current_node, steps, neighbors_added, frontier_before, frontier_after) Dict
      }

      class GreedyBestFirstSearch {
          +_calculate_f(g, h) float
          +_should_update_node(neighbor, tentative_g, g_value, frontier_dict) bool
          +search(start, goal) SearchResult
          +visualize_search(result, delay) void
      }

      class AStarSearch {
          +_calculate_f(g, h) float
          +_should_update_node(neighbor, tentative_g, g_value, frontier_dict) bool
          +search(start, goal) SearchResult
          +visualize_search(result, delay) void
      }

      class SearchAlgorithmDashboard {
          <<abstract>>
          +MazeEnvironment env
          +SearchResult result
          +str algorithm_name
          -List steps_data
          +_extract_history_data()* void
          +get_frontier_name()* str
          +create_maze_graph() Graph
          +_plot_maze(ax, step_data) void
          +_plot_algorithm_state(ax, step_data)* void
          +_print_step_explanation(step_data)* void
          +visualize_step(step_idx) void
          +animate_on_graph(output_file, fps, size) void
          +create_gif(filename, fps, dpi) void
          -_create_final_frame(G, pos, colors, edge_width, path_edge_width, temp_dir, frame_files) void
      }

      class BFSDashboard {
          +get_frontier_name() str
          +_extract_history_data() void
          +_plot_algorithm_state(ax, step_data) void
          +_draw_frontier_table(ax, step_data, before_label, after_label) void
          +_print_step_explanation(step_data) void
      }
      
      class DFSDashboard {
          +get_frontier_name() str
          +_extract_history_data() void
          +_plot_algorithm_state(ax, step_data) void
          +_draw_frontier_table(ax, step_data, before_label, after_label) void
          +_print_step_explanation(step_data) void
      }
      
      class GreedyBestFirstDashboard {
          +get_frontier_name() str
          +_extract_history_data() void
          +_plot_algorithm_state(ax, step_data) void
          +_draw_frontier_table(ax, step_data) void
          +_print_step_explanation(step_data) void
      }
      
      class AStarDashboard {
          +get_frontier_name() str
          +_extract_history_data() void
          +_plot_algorithm_state(ax, step_data) void
          +_draw_frontier_table(ax, step_data) void
          +_print_step_explanation(step_data) void
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

      SearchAlgorithmBase <|-- UninformedSearch : Inherits
      SearchAlgorithmBase <|-- InformedSearch : Inherits
      UninformedSearch <|-- BreadthFirstSearch : Inherits
      UninformedSearch <|-- DepthFirstSearch : Inherits
      InformedSearch <|-- GreedyBestFirstSearch : Inherits
      InformedSearch <|-- AStarSearch : Inherits
      
      SearchAlgorithmDashboard <|-- BFSDashboard : Inherits
      SearchAlgorithmDashboard <|-- DFSDashboard : Inherits
      SearchAlgorithmDashboard <|-- GreedyBestFirstDashboard : Inherits
      SearchAlgorithmDashboard <|-- AStarDashboard : Inherits
      
      MazeEnvironment o-- Config : Contains
      SearchAlgorithmBase o-- MazeEnvironment : References
      SearchAlgorithmBase ..> SearchResult : Creates
      
      MazeSearchVisualizer o-- MazeEnvironment : References
      MazeSearchVisualizer o-- SearchAlgorithmBase : References
      
      SearchAlgorithmDashboard o-- MazeEnvironment : References
      SearchAlgorithmDashboard o-- SearchResult : References
      
      MazeExperiments ..> SearchAlgorithmBase : Uses
      MazeExperiments ..> MazeEnvironment : Creates