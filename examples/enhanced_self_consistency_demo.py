#!/usr/bin/env python3
"""Demonstration of the Enhanced Self-Consistency Agent with Token Confidence Data Collection.

This script shows how to use the enhanced self-consistency agent to collect
token-level confidence data alongside traditional consensus-based decision making.

Usage:
    python examples/enhanced_self_consistency_demo.py

Requirements:
    - LiteLLM server running (make litellm-start)
    - Environment variables configured (.env file)
    - Model that supports structured outputs + logprobs (OpenRouter GPT-4o-mini recommended)
    - OPENROUTER_API_KEY set in environment for token confidence features

Recommended Models for Token Confidence:
    - openrouter/gpt-4o-mini (default, best performance/cost ratio)
    - openrouter/gpt-4o (higher quality, more expensive)
    - gpt-4o-mini (direct OpenAI, requires OPENAI_API_KEY)
    - gpt-4o (direct OpenAI, requires OPENAI_API_KEY)
"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print(f"   📁 Loaded environment from .env file")
    else:
        print(f"   ⚠️  No .env file found at {env_path}")

# Load .env at startup
load_env_file()

from llm_agents.self_consistency import (
    EnhancedSelfConsistencyAgent,
    ConfidenceDataExporter,
    AgentConfig
)
from llm_agents.common.interfaces import EnhancedLiteLLMAdapter


def check_model_compatibility(model_name: str) -> tuple[bool, str]:
    """Check if the model supports structured outputs and logprobs.
    
    Args:
        model_name: The model name to check
        
    Returns:
        Tuple of (is_compatible, recommendation_message)
    """
    # Models known to support structured outputs + logprobs
    compatible_models = [
        'gpt-4o', 'gpt-4o-mini',
        'openrouter/gpt-4o', 'openrouter/gpt-4o-mini'
    ]
    
    # Check for exact match or pattern match
    is_compatible = any(
        model_name == compat_model or 
        model_name.endswith(compat_model.split('/')[-1])
        for compat_model in compatible_models
    )
    
    if is_compatible:
        return True, f"✅ Model '{model_name}' supports token confidence features"
    
    recommendation = (
        f"❌ Model '{model_name}' may not support structured outputs + logprobs.\n"
        "   Recommended models for token confidence:\n"
        "   • Set LLM_MODEL=openrouter/gpt-4o-mini (best performance/cost)\n" 
        "   • Set LLM_MODEL=openrouter/gpt-4o (higher quality)\n"
        "   • Ensure OPENROUTER_API_KEY is set in your .env file\n"
        "   • Restart LiteLLM after changing: make litellm-stop && make litellm-start"
    )
    
    return False, recommendation


def get_recommended_model() -> str:
    """Get the recommended model for token confidence features."""
    # Check if OpenRouter API key is available
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if openrouter_key:
        return 'openrouter/gpt-4o-mini'
    elif openai_key:
        return 'gpt-4o-mini'
    else:
        return 'openrouter/gpt-4o-mini'  # Default recommendation


def demo_enhanced_agent():
    """Demonstrate the enhanced self-consistency agent with token confidence data."""
    
    print("🚀 Enhanced Self-Consistency Agent with Token Confidence Demo")
    print("=" * 65)
    
    # Initialize enhanced LLM adapter with recommended model
    print("1. Initializing Enhanced LiteLLM Adapter...")
    
    # Show current environment for debugging
    current_model_env = os.getenv('LLM_MODEL', 'not set')
    openrouter_key_status = '✅ SET' if os.getenv('OPENROUTER_API_KEY') else '❌ NOT SET'
    print(f"   🔧 Environment: LLM_MODEL={current_model_env}, OPENROUTER_API_KEY={openrouter_key_status}")
    
    # Use recommended model if no specific model is set or if using unsupported model
    current_model = os.getenv('LLM_MODEL', 'claude-3-haiku')
    is_compatible, compatibility_msg = check_model_compatibility(current_model)
    
    if not is_compatible:
        print(f"   ⚠️  Current model compatibility check:")
        print(f"   {compatibility_msg}")
        recommended_model = get_recommended_model()
        print(f"\n   🔄 Using recommended model: {recommended_model}")
        # Override the model for this demo
        os.environ['LLM_MODEL'] = recommended_model
        current_model = recommended_model
    else:
        print(f"   {compatibility_msg}")
    
    try:
        enhanced_adapter = EnhancedLiteLLMAdapter()
        print(f"   ✅ Using model: {enhanced_adapter.model}")
        print(f"   🌐 Base URL: {enhanced_adapter.base_url}")
    except Exception as e:
        print(f"   ❌ Failed to initialize adapter: {e}")
        print("   💡 Make sure LiteLLM is running: make litellm-status")
        print("   💡 Ensure OpenRouter models are configured in litellm_config.yaml")
        return
    
    # Create agent configuration
    print("\n2. Creating Agent Configuration...")
    config = AgentConfig(
        llm_interface=enhanced_adapter,
        target_responses=3,  # Use fewer responses for demo
        prompt_template="Think step by step:"
    )
    print(f"   ✅ Configured for {config.target_responses} responses")
    
    # Test question
    question = "What is 15 + 27?"
    print(f"\n3. Processing Question: '{question}'")
    
    # Initialize and run enhanced agent
    print("   🔄 Running enhanced agent with token confidence data collection...")
    agent = EnhancedSelfConsistencyAgent(config, question)
    
    try:
        result = agent.process_question()
        
        print("\n4. 📊 Results Analysis:")
        print("-" * 40)
        
        # Traditional consensus results
        print("🗳️  Traditional Consensus Results:")
        print(f"   Final Answer: {result.final_answer}")
        print(f"   Vote Count: {result.vote_count}")
        print(f"   Consensus Confidence: {result.confidence:.3f}")
        
        # Token confidence data  
        print(f"\n🧠 Token Confidence Data (Normalized 0-1 Scale):")
        report = result.confidence_report
        reasoning_conf_pct = report.token_confidence_reasoning * 100
        answer_conf_pct = report.token_confidence_answer * 100
        print(f"   Reasoning Confidence: {report.token_confidence_reasoning:.3f} ({reasoning_conf_pct:.1f}%)")
        print(f"   Answer Confidence: {report.token_confidence_answer:.3f} ({answer_conf_pct:.1f}%)")
        
        # Individual response analysis
        print(f"\n📝 Individual Response Analysis:")
        for i, resp_data in enumerate(report.individual_response_data):
            status = "✅ CONSENSUS" if resp_data["matches_consensus"] else "❌ OUTLIER"
            print(f"   Response {i+1}: '{resp_data['answer']}' {status}")
            reasoning_pct = resp_data['reasoning_confidence'] * 100
            answer_pct = resp_data['answer_confidence'] * 100
            print(f"     Reasoning: {resp_data['reasoning_token_count']} tokens, "
                  f"confidence {resp_data['reasoning_confidence']:.3f} ({reasoning_pct:.1f}%)")
            print(f"     Answer: {resp_data['answer_token_count']} tokens, "
                  f"confidence {resp_data['answer_confidence']:.3f} ({answer_pct:.1f}%)")
        
        # Export demonstration
        print(f"\n5. 📁 Data Export Demonstration:")
        export_data = ConfidenceDataExporter.export_to_dict(result)
        print("   Dictionary export (first 3 fields):")
        for key, value in list(export_data.items())[:3]:
            print(f"     {key}: {value}")
        
        csv_rows = ConfidenceDataExporter.export_to_csv_rows(result)
        print(f"   CSV export: {len(csv_rows)} rows generated")
        
        # Success indicators
        print(f"\n6. ✅ Success Metrics:")
        has_token_data = any(resp['reasoning_confidence'] != 0.0 or resp['answer_confidence'] != 0.0 
                           for resp in report.individual_response_data)
        print(f"   Token confidence data collected: {'✅ YES' if has_token_data else '❌ NO'}")
        print(f"   Consensus achieved: {'✅ YES' if result.confidence >= 0.5 else '❌ NO'}")
        print(f"   Data export ready: ✅ YES")
        
    except Exception as e:
        print(f"   ❌ Error processing question: {e}")
        
        # Check if it's a logprobs support error
        error_str = str(e).lower()
        if 'logprobs' in error_str or 'unsupportedparamserror' in error_str:
            print(f"   💡 This model doesn't support logprobs parameter")
            print(f"   💡 Try using: LLM_MODEL=openrouter/gpt-4o-mini")
            print(f"   💡 Ensure OPENROUTER_API_KEY is set in your .env file")
        elif 'authentication' in error_str or 'no auth credentials' in error_str:
            print(f"   💡 API key authentication failed")
            if 'openrouter' in current_model.lower():
                print(f"   💡 For OpenRouter models:")
                print(f"     • Ensure OPENROUTER_API_KEY is set in your .env file")
                print(f"     • Restart LiteLLM to pick up the key: make litellm-stop && make litellm-clean && make litellm-install")
            else:
                print(f"   💡 Check your API key configuration for model: {current_model}")
        else:
            print(f"   💡 Make sure LiteLLM is running: make litellm-status")
            print(f"   💡 Check model configuration in litellm_config.yaml")
        return
    
    print(f"\n🎉 Demo completed successfully!")
    print(f"💡 The enhanced agent successfully collected token confidence data")
    print(f"💡 Traditional consensus logic maintained while adding empirical evidence")


if __name__ == "__main__":
    demo_enhanced_agent()