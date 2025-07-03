#!/usr/bin/env python3
"""Standalone runner for GSM8K benchmark proof of concept.

This script runs the GSM8K benchmark with the self-consistency agent
to demonstrate the effectiveness of multiple attempts vs single attempts,
following Tyler Burleigh's blog methodology.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm_agents.common.interfaces import LiteLLMAdapter
from llm_agents.benchmark import GSM8KBenchmark


def main():
    """Run the GSM8K benchmark demonstration."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GSM8K Mathematical Reasoning Benchmark')
    parser.add_argument('--model', '-m', 
                       help='LLM model to use (e.g., qwen2-math-7b, deepseek-math-7b, claude-3-haiku)')
    parser.add_argument('--attempts', '-a', nargs='+', type=int, default=[1, 3, 5, 10],
                       help='Number of attempts to test (default: 1 3 5 10)')
    
    args = parser.parse_args()
    
    print("🚀 GSM8K Benchmark Proof of Concept")
    print("=" * 50)
    print("Testing self-consistency agent effectiveness with mathematical reasoning")
    print("Following Tyler Burleigh's blog methodology: https://tylerburleigh.com/blog/2023/12/04/")
    print()
    
    # Initialize LLM interface with specified model
    print("🔧 Initializing LLM interface...")
    if args.model:
        llm_interface = LiteLLMAdapter(model=args.model)
        print(f"   Using specified model: {args.model}")
    else:
        llm_interface = LiteLLMAdapter()  # Uses default from .env
        print(f"   Using default model from environment: {llm_interface.model}")
    
    print(f"   Timeout configured: {llm_interface.timeout:.0f} seconds")
    if "math" in llm_interface.model.lower():
        print("   ℹ️  Mathematical models may take longer to respond due to complex reasoning")
    
    # Create benchmark
    benchmark = GSM8KBenchmark(llm_interface)
    
    # Run benchmark with specified attempt configurations
    print(f"📊 Running benchmark with configurations: {args.attempts} attempts")
    print("Expected results: Accuracy should improve with more attempts")
    print()
    
    try:
        # Run the benchmark
        report = benchmark.run_benchmark(attempt_counts=args.attempts)
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎯 BENCHMARK COMPLETE")
        print("=" * 60)
        print(report.summary)
        
        # Print detailed results
        benchmark.print_detailed_results(report)
        
        # Export results
        output_file = "gsm8k_benchmark_results.txt"
        benchmark.export_results(report, output_file)
        
        print(f"\n📁 Full results exported to: {output_file}")
        print("🎉 Benchmark completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running benchmark: {e}")
        print("Please ensure your LLM interface is properly configured.")
        print("Check environment variables: LLM_MODEL, LLM_BASE_URL, LLM_API_KEY")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())