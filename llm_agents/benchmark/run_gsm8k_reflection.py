#!/usr/bin/env python3
"""Standalone runner for GSM8K SelfReflectionAgent benchmark."""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm_agents.common.interfaces import LiteLLMAdapter
from llm_agents.self_reflection.config import ReflectionConfig
from llm_agents.benchmark.gsm8k_reflection import GSM8KReflectionBenchmark


def main():
    parser = argparse.ArgumentParser(description='GSM8K SelfReflectionAgent Benchmark')
    parser.add_argument('--model', '-m', help='LLM model to use')
    parser.add_argument('--confidence-threshold', '-c', type=float, default=0.8,
                       help='Confidence threshold for early stopping (default: 0.8)')
    parser.add_argument('--entropy-mode', '-e', default='combined',
                       choices=['off', 'confidence_only', 'entropy_only', 'combined'],
                       help='Entropy calculation mode (default: combined)')
    parser.add_argument('--entropy-threshold', '-t', type=float, default=0.3,
                       help='Entropy threshold for early stopping (default: 0.3)')
    parser.add_argument('--entropy-weight', '-w', type=float, default=0.3,
                       help='Weight of entropy in combined mode (default: 0.3)')
    parser.add_argument('--target-responses', '-r', type=int, default=10,
                       help='Maximum number of responses to generate (default: 10)')
    parser.add_argument('--min-responses', '-min', type=int, default=3,
                       help='Minimum responses before early stopping (default: 3)')
    parser.add_argument('--db-path', '-d', help='SQLite database path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    print("🔍 GSM8K SelfReflectionAgent Benchmark")
    print("=" * 50)
    print("Testing entropy-aware early stopping with mathematical reasoning")
    print()
    
    # Initialize LLM interface
    llm_interface = LiteLLMAdapter(model=args.model) if args.model else LiteLLMAdapter()
    print(f"🤖 Model: {llm_interface.model}")
    
    # Create custom config
    config = ReflectionConfig(
        llm_interface=llm_interface,
        target_responses=args.target_responses,
        confidence_threshold=args.confidence_threshold,
        min_responses=args.min_responses,
        entropy_threshold=args.entropy_threshold,
        entropy_weight=args.entropy_weight,
        entropy_mode=args.entropy_mode,
        prompt_template="Solve this step by step, showing all work. Provide ONLY the final answer after 'Answer:'. Format: 'Answer: 42' (just the number/value, no extra text):"
    )
    
    print(f"⚙️ Configuration:")
    print(f"   Target responses: {config.target_responses}")
    print(f"   Confidence threshold: {config.confidence_threshold}")
    print(f"   Min responses: {config.min_responses}")
    print(f"   Entropy mode: {config.entropy_mode}")
    print(f"   Entropy threshold: {config.entropy_threshold}")
    print(f"   Entropy weight: {config.entropy_weight}")
    
    if args.db_path:
        print(f"💾 Database: {args.db_path}")
    
    print()
    
    # Run benchmark
    benchmark = GSM8KReflectionBenchmark(llm_interface, args.db_path)
    
    try:
        results = benchmark.run_benchmark(config)
        
        print("\n" + "=" * 60)
        print("🎯 REFLECTION BENCHMARK COMPLETE")
        print("=" * 60)
        
        # Core metrics
        print(f"✅ Accuracy: {results['accuracy']:.1%} ({results['correct_answers']}/{results['total_questions']})")
        print(f"⚡ Early stopping rate: {results['early_stopping_rate']:.1%} ({results['early_stops']}/{results['total_questions']})")
        print(f"🔄 Average responses: {results['avg_responses']:.1f}")
        print(f"🎯 Average confidence: {results['avg_confidence']:.3f}")
        print(f"⏱️ Average processing time: {results['avg_processing_time']:.1f}s")
        
        # Entropy analysis
        print(f"\n📊 Entropy Level Distribution:")
        for level, count in results['entropy_level_distribution'].items():
            percentage = (count / results['total_questions']) * 100
            print(f"   {level.capitalize()}: {count} ({percentage:.1f}%)")
        
        print(f"\n🤝 Consensus Type Distribution:")
        for consensus_type, count in results['consensus_type_distribution'].items():
            percentage = (count / results['total_questions']) * 100
            print(f"   {consensus_type.capitalize()}: {count} ({percentage:.1f}%)")
        
        # Detailed results if verbose
        if args.verbose:
            print(f"\n📋 Detailed Results:")
            for result in results['detailed_results']:
                status = "✅" if result['is_correct'] else "❌"
                early = "⚡" if result['early_stopping'] else "🔄"
                print(f"   {status} {result['question_id']}: {result['total_responses']} responses, "
                      f"conf={result['consensus_confidence']:.3f}, "
                      f"entropy={result['entropy_level']}, "
                      f"consensus={result['consensus_type']} {early}")
        
        # Database info
        print(f"\n💾 Database: {benchmark.database.db_path}")
        print(f"📊 Run ID: {results['run_id']}")
        
        # Analysis insights
        print(f"\n🔬 Analysis:")
        if results['early_stopping_rate'] > 0.5:
            efficiency_gain = (1 - results['avg_responses'] / config.target_responses) * 100
            print(f"   Early stopping achieved {efficiency_gain:.1f}% efficiency gain")
        
        if results['accuracy'] >= 0.8:
            print(f"   Excellent accuracy achieved with confidence-aware stopping")
        
        entropy_concentrated = results['entropy_level_distribution'].get('concentrated', 0)
        if entropy_concentrated > 0:
            print(f"   {entropy_concentrated} questions showed strong consensus (concentrated entropy)")
        
    except Exception as e:
        print(f"❌ Error during benchmark: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())