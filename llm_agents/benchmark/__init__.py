"""Benchmark module for evaluating LLM agent performance.

This module provides benchmarking capabilities for the self-consistency
and self-reflection agents, including GSM8K-style mathematical reasoning tests.
"""

from .gsm8k_poc import GSM8KBenchmark

__all__ = ['GSM8KBenchmark']