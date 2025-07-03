#!/usr/bin/env python3
"""Standalone runner for GSM8K benchmark proof of concept.

This script runs the GSM8K benchmark with the self-consistency agent
to demonstrate the effectiveness of multiple attempts vs single attempts,
following Tyler Burleigh's blog methodology.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm_agents.common.interfaces import LiteLLMAdapter
from llm_agents.benchmark import GSM8KBenchmark


def main():
    """Run the GSM8K benchmark demonstration."""
    print("🚀 GSM8K Benchmark Proof of Concept")
    print("=" * 50)
    print("Testing self-consistency agent effectiveness with mathematical reasoning")
    print("Following Tyler Burleigh's blog methodology: https://tylerburleigh.com/blog/2023/12/04/")
    print()
    
    # Initialize LLM interface
    print("🔧 Initializing LLM interface...")
    llm_interface = LiteLLMAdapter()
    
    # Create benchmark
    benchmark = GSM8KBenchmark(llm_interface)
    
    # Run benchmark with different attempt configurations
    print("📊 Running benchmark with configurations: [1, 3, 5, 10] attempts")
    print("Expected results: Accuracy should improve with more attempts")
    print()
    
    try:
        # Run the benchmark
        report = benchmark.run_benchmark(attempt_counts=[1, 3, 5, 10])
        
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