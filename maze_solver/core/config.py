from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration parameters for maze generation and search algorithms.

    This class centralizes all configuration options for maze environments and search
    algorithms to ensure consistent parameter usage throughout the system.

    Attributes:
        maze_size (int): Grid dimensions (nxn) of the maze. Default is 5x5.
        maze_id (Optional[int]): Seed for reproducible maze generation. If None, a random seed is used.
        visualization_delay (float): Delay in seconds between search algorithm steps for visualization. Default is 0.5.
        show_exploration (bool): Whether to visualize the exploration process. Default is True.
        max_steps (Optional[int]): Maximum steps for search algorithm execution before termination.
                                  None means unlimited steps allowed.
    """
    # Maze parameters
    maze_size: int = 5  # Grid dimensions (nxn)
    maze_id: Optional[int] = None  # Seed for reproducible maze generation

    # Visualization parameters
    visualization_delay: float = 0.5  # Delay between search steps
    show_exploration: bool = True  # Whether to visualize exploration

    # Search parameters
    max_steps: Optional[int] = None  # Maximum steps for search (None for unlimited)