from typing import List, Optional

import matplotlib

matplotlib.use("Agg")  # headless-safe: exercised by pytest, not only notebooks
import matplotlib.pyplot as plt

# LRTA*'s interesting output isn't a single graph state (nothing about the
# environment changes between trials) - it's h(s) converging over repeated
# trials, per documentation/lrta/beyond_the_maze.md. A line chart of the
# learned estimate per trial is the right visualization, not a DAG render.


def plot_h_convergence(
    h_history: List[float],
    node_id: str,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Plot a node's learned h(s) estimate across trials. `h_history` is the
    value of `learner.h_table[node_id]` recorded after each `run_trial()`
    call - the caller builds this list since LRTAStarLearner doesn't keep
    per-trial history itself (only the current h_table).
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    trials = list(range(1, len(h_history) + 1))
    ax.plot(trials, h_history, marker="o", color="#1976D2")

    ax.set_xlabel("Trial")
    ax.set_ylabel(f"h({node_id})")
    ax.set_title(title or f"LRTA* learned cost for {node_id!r} over trials")
    ax.grid(True, alpha=0.3)

    if save_path:
        plt.savefig(save_path, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
