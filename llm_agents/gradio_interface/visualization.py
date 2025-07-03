"""Visualization utilities for Gradio interface.

This module provides chart generation and plotting functions for displaying
agent results, probability distributions, and convergence analysis.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from io import BytesIO
import base64
import sqlite3

from .agent_wrapper import UnifiedResult


def setup_plot_style():
    """Set up consistent plot styling."""
    plt.style.use('default')
    sns.set_palette("husl")
    plt.rcParams.update({
        'figure.figsize': (10, 6),
        'axes.titlesize': 14,
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 11
    })


def create_probability_distribution_chart(result: UnifiedResult) -> plt.Figure:
    """Create bar chart showing probability distribution of answers.
    
    Args:
        result: UnifiedResult containing answer distribution
        
    Returns:
        matplotlib Figure object
    """
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    answers = list(result.answer_distribution.keys())
    probabilities = list(result.answer_distribution.values())
    
    # Create bar chart
    bars = ax.bar(answers, probabilities, alpha=0.7, color=sns.color_palette("husl", len(answers)))
    
    # Highlight the final answer
    for i, answer in enumerate(answers):
        if answer == result.final_answer:
            bars[i].set_color('#e74c3c')
            bars[i].set_alpha(0.9)
    
    ax.set_title(f'{result.agent_type} - Answer Distribution')
    ax.set_xlabel('Answers')
    ax.set_ylabel('Probability')
    ax.set_ylim(0, 1.0)
    
    # Add value labels on bars
    for bar, prob in zip(bars, probabilities):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{prob:.2f}', ha='center', va='bottom')
    
    # Rotate x-axis labels if needed
    if max(len(str(answer)) for answer in answers) > 10:
        plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    return fig


def create_confidence_evolution_chart(result: UnifiedResult) -> Optional[plt.Figure]:
    """Create line chart showing confidence evolution over time.
    
    Args:
        result: UnifiedResult containing convergence analysis
        
    Returns:
        matplotlib Figure object or None if no convergence data
    """
    if not result.convergence_analysis or 'confidence_evolution' not in result.convergence_analysis:
        return None
    
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    confidence_evolution = result.convergence_analysis['confidence_evolution']
    response_numbers = list(range(1, len(confidence_evolution) + 1))
    
    # Plot confidence evolution
    ax.plot(response_numbers, confidence_evolution, 'o-', linewidth=2, markersize=6)
    
    # Add confidence threshold line if early stopping was used
    if result.early_stopping:
        ax.axhline(y=0.8, color='red', linestyle='--', alpha=0.7, label='Confidence Threshold')
    
    # Mark early stopping point
    if result.early_stopping and len(confidence_evolution) < 10:
        ax.axvline(x=len(confidence_evolution), color='green', linestyle='--', alpha=0.7, 
                  label='Early Stopping')
    
    ax.set_title(f'{result.agent_type} - Confidence Evolution')
    ax.set_xlabel('Response Number')
    ax.set_ylabel('Confidence Score')
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3)
    
    if ax.get_legend_handles_labels()[0]:  # If there are legend items
        ax.legend()
    
    plt.tight_layout()
    return fig


def create_comparison_chart(results: Dict[str, UnifiedResult]) -> plt.Figure:
    """Create comparison chart between different agents.
    
    Args:
        results: Dictionary mapping agent names to UnifiedResult objects
        
    Returns:
        matplotlib Figure object
    """
    setup_plot_style()
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    agent_names = list(results.keys())
    
    # 1. Confidence comparison
    confidences = [results[agent].confidence for agent in agent_names]
    bars1 = ax1.bar(agent_names, confidences, alpha=0.7, color=['#3498db', '#e74c3c'])
    ax1.set_title('Final Confidence Comparison')
    ax1.set_ylabel('Confidence Score')
    ax1.set_ylim(0, 1.0)
    
    for bar, conf in zip(bars1, confidences):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{conf:.3f}', ha='center', va='bottom')
    
    # 2. Response count comparison
    response_counts = [results[agent].total_responses for agent in agent_names]
    bars2 = ax2.bar(agent_names, response_counts, alpha=0.7, color=['#3498db', '#e74c3c'])
    ax2.set_title('Total Responses Used')
    ax2.set_ylabel('Number of Responses')
    
    for bar, count in zip(bars2, response_counts):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{count}', ha='center', va='bottom')
    
    # 3. Processing time comparison (if available)
    if all(results[agent].processing_time for agent in agent_names):
        processing_times = [results[agent].processing_time for agent in agent_names]
        bars3 = ax3.bar(agent_names, processing_times, alpha=0.7, color=['#3498db', '#e74c3c'])
        ax3.set_title('Processing Time Comparison')
        ax3.set_ylabel('Time (seconds)')
        
        for bar, time in zip(bars3, processing_times):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{time:.2f}s', ha='center', va='bottom')
    else:
        ax3.text(0.5, 0.5, 'Processing time\nnot available', 
                ha='center', va='center', transform=ax3.transAxes)
        ax3.set_title('Processing Time Comparison')
    
    # 4. Early stopping indicator
    early_stopping = [results[agent].early_stopping for agent in agent_names]
    colors = ['#27ae60' if stopped else '#95a5a6' for stopped in early_stopping]
    bars4 = ax4.bar(agent_names, [1 if stopped else 0 for stopped in early_stopping], 
                   alpha=0.7, color=colors)
    ax4.set_title('Early Stopping Usage')
    ax4.set_ylabel('Early Stopping Used')
    ax4.set_ylim(0, 1.2)
    ax4.set_yticks([0, 1])
    ax4.set_yticklabels(['No', 'Yes'])
    
    plt.tight_layout()
    return fig


def create_uncertainty_analysis_chart(result: UnifiedResult) -> plt.Figure:
    """Create chart analyzing uncertainty patterns.
    
    Args:
        result: UnifiedResult containing uncertainty information
        
    Returns:
        matplotlib Figure object
    """
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Uncertainty level pie chart
    uncertainty_colors = {
        'low': '#27ae60',
        'medium': '#f39c12', 
        'high': '#e74c3c'
    }
    
    uncertainty_data = {'low': 0, 'medium': 0, 'high': 0}
    uncertainty_data[result.uncertainty_level] = 1
    
    colors = [uncertainty_colors[level] for level in uncertainty_data.keys()]
    sizes = list(uncertainty_data.values())
    
    wedges, texts, autotexts = ax1.pie(sizes, labels=list(uncertainty_data.keys()), 
                                      colors=colors, autopct='%1.0f%%', startangle=90)
    ax1.set_title(f'Uncertainty Level: {result.uncertainty_level.title()}')
    
    # 2. Answer distribution entropy
    probabilities = list(result.answer_distribution.values())
    entropy = -sum(p * np.log2(p) if p > 0 else 0 for p in probabilities)
    max_entropy = np.log2(len(probabilities)) if len(probabilities) > 1 else 1
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
    
    # Create entropy bar
    ax2.bar(['Current', 'Maximum'], [entropy, max_entropy], alpha=0.7, 
           color=['#3498db', '#95a5a6'])
    ax2.set_title('Answer Distribution Entropy')
    ax2.set_ylabel('Entropy (bits)')
    
    # Add entropy explanation text
    ax2.text(0.5, 0.95, f'Normalized Entropy: {normalized_entropy:.3f}\n'
                       f'Lower = More Certain\nHigher = More Uncertain',
            transform=ax2.transAxes, ha='center', va='top',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
    
    plt.tight_layout()
    return fig


def save_figure_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64 string for web display.
    
    Args:
        fig: matplotlib Figure object
        
    Returns:
        Base64 encoded string of the figure
    """
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close(fig)
    
    return image_base64


def create_cost_analysis_chart(
    cost_estimates: Dict[str, Dict[str, Any]], 
    agent_names: List[str]
) -> plt.Figure:
    """Create chart showing cost analysis for different agents.
    
    Args:
        cost_estimates: Dictionary mapping agent names to cost estimates
        agent_names: List of agent names to include
        
    Returns:
        matplotlib Figure object
    """
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Cost comparison
    costs = [cost_estimates[agent]['estimated_cost'] for agent in agent_names]
    bars1 = ax1.bar(agent_names, costs, alpha=0.7, color=['#3498db', '#e74c3c'])
    ax1.set_title('Estimated Cost Comparison')
    ax1.set_ylabel('Estimated Cost ($)')
    
    for bar, cost in zip(bars1, costs):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'${cost:.4f}', ha='center', va='bottom')
    
    # 2. Response efficiency
    responses = [cost_estimates[agent]['expected_responses'] for agent in agent_names]
    bars2 = ax2.bar(agent_names, responses, alpha=0.7, color=['#3498db', '#e74c3c'])
    ax2.set_title('Expected Response Count')
    ax2.set_ylabel('Number of Responses')
    
    for bar, resp in zip(bars2, responses):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{resp}', ha='center', va='bottom')
    
    plt.tight_layout()
    return fig


def create_entropy_evolution_benchmark_chart(db_path: str, run_id: int) -> plt.Figure:
    """Create entropy evolution chart from benchmark database."""
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get entropy evolution data
        cursor.execute('''
            SELECT 
                response_num,
                AVG(normalized_entropy) as avg_entropy,
                AVG(confidence) as avg_confidence
            FROM entropy_evolution ee
            JOIN question_results qr ON ee.result_id = qr.id
            WHERE qr.run_id = ?
            GROUP BY response_num
            ORDER BY response_num
        ''', (run_id,))
        
        evolution_data = cursor.fetchall()
    
    if not evolution_data:
        ax1.text(0.5, 0.5, 'No entropy data available', 
                ha='center', va='center', transform=ax1.transAxes)
        ax2.text(0.5, 0.5, 'No confidence data available',
                ha='center', va='center', transform=ax2.transAxes)
        return fig
    
    response_nums = [d[0] for d in evolution_data]
    avg_entropy = [d[1] for d in evolution_data]
    avg_confidence = [d[2] for d in evolution_data]
    
    # Plot entropy evolution
    ax1.plot(response_nums, avg_entropy, 'o-', color='red', label='Normalized Entropy', linewidth=2, markersize=6)
    ax1.set_title('Average Entropy Evolution Across All Questions')
    ax1.set_xlabel('Response Number')
    ax1.set_ylabel('Normalized Entropy')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_ylim(0, 1.0)
    
    # Plot confidence evolution
    ax2.plot(response_nums, avg_confidence, 'o-', color='blue', label='Confidence', linewidth=2, markersize=6)
    ax2.set_title('Average Confidence Evolution Across All Questions')
    ax2.set_xlabel('Response Number')
    ax2.set_ylabel('Confidence Score')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim(0, 1.0)
    
    plt.tight_layout()
    return fig


def create_early_stopping_analysis_chart(db_path: str, run_id: int) -> plt.Figure:
    """Create early stopping analysis chart."""
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Early stopping distribution
        cursor.execute('''
            SELECT total_responses, COUNT(*) as count, 
                   SUM(CASE WHEN early_stopping THEN 1 ELSE 0 END) as early_stops
            FROM question_results 
            WHERE run_id = ?
            GROUP BY total_responses
            ORDER BY total_responses
        ''', (run_id,))
        
        response_data = cursor.fetchall()
        
        if response_data:
            responses = [r[0] for r in response_data]
            counts = [r[1] for r in response_data]
            early_stops = [r[2] for r in response_data]
            
            # Stacked bar chart
            ax1.bar(responses, early_stops, label='Early Stops', alpha=0.7, color='green')
            ax1.bar(responses, [c - e for c, e in zip(counts, early_stops)], 
                   bottom=early_stops, label='Full Runs', alpha=0.7, color='red')
            
            ax1.set_title('Response Distribution')
            ax1.set_xlabel('Number of Responses Used')
            ax1.set_ylabel('Number of Questions')
            ax1.legend()
        else:
            ax1.text(0.5, 0.5, 'No response data available', 
                    ha='center', va='center', transform=ax1.transAxes)
        
        # Accuracy by early stopping
        cursor.execute('''
            SELECT early_stopping, 
                   COUNT(*) as total,
                   SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM question_results 
            WHERE run_id = ?
            GROUP BY early_stopping
        ''', (run_id,))
        
        accuracy_data = cursor.fetchall()
        
        if accuracy_data:
            categories = []
            accuracies = []
            
            for early_stop, total, correct in accuracy_data:
                accuracy = correct / total if total > 0 else 0
                if early_stop:
                    categories.append('Early Stop')
                    accuracies.append(accuracy)
                else:
                    categories.append('Full Run')
                    accuracies.append(accuracy)
            
            colors = ['green' if 'Early' in cat else 'red' for cat in categories]
            bars = ax2.bar(categories, accuracies, alpha=0.7, color=colors)
            ax2.set_title('Accuracy by Stopping Type')
            ax2.set_ylabel('Accuracy')
            ax2.set_ylim(0, 1.0)
            
            # Add value labels
            for bar, acc in zip(bars, accuracies):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{acc:.2f}', ha='center', va='bottom')
        else:
            ax2.text(0.5, 0.5, 'No accuracy data available',
                    ha='center', va='center', transform=ax2.transAxes)
    
    plt.tight_layout()
    return fig