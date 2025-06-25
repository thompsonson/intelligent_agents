#!/usr/bin/env python3
"""
Test script to diagnose LiteLLM connection issues.
Run with: python test_litellm_connection.py
"""

import os
import sys
import time
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from llm_agents.self_consistency.interfaces import LiteLLMAdapter
    from llm_agents.self_consistency.domain import LLMResponse
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def test_environment():
    """Test environment configuration."""
    print("🔧 Environment Configuration:")
    env_vars = {
        'LLM_MODEL': os.getenv('LLM_MODEL', 'NOT SET'),
        'LLM_BASE_URL': os.getenv('LLM_BASE_URL', 'NOT SET'),
        'LLM_TEMPERATURE': os.getenv('LLM_TEMPERATURE', 'NOT SET'),
        'LLM_API_KEY': os.getenv('LLM_API_KEY', 'NOT SET'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'NOT SET'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', 'NOT SET'),
    }
    
    for key, value in env_vars.items():
        if value != 'NOT SET' and 'API_KEY' in key:
            # Mask API keys for security
            masked_value = value[:8] + '...' if len(value) > 8 else value
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: {value}")
    
    return env_vars


def test_litellm_server():
    """Test basic LiteLLM server connectivity."""
    print("\n🔌 Testing LiteLLM Server:")
    
    base_url = os.getenv('LLM_BASE_URL', 'http://localhost:4000')
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Health check: {base_url}/health")
        else:
            print(f"  ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        return False
    
    # Test models endpoint with authentication
    try:
        headers = {'Authorization': 'Bearer sk-1234'}
        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"  ✅ Models endpoint accessible")
            print(f"  📋 Available models: {[m['id'] for m in models.get('data', [])]}")
        else:
            print(f"  ❌ Models endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Models endpoint failed: {e}")
        return False
    
    return True


def test_adapter_creation():
    """Test LiteLLMAdapter creation."""
    print("\n🔧 Testing LiteLLMAdapter Creation:")
    
    try:
        adapter = LiteLLMAdapter()
        print(f"  ✅ Adapter created successfully")
        print(f"  🤖 Model: {adapter.model}")
        print(f"  🌡️  Temperature: {adapter.temperature}")
        print(f"  🔗 Base URL: {adapter.base_url}")
        print(f"  🔑 API Key: {adapter.api_key[:8]}..." if adapter.api_key else "None")
        return adapter
    except Exception as e:
        print(f"  ❌ Adapter creation failed: {e}")
        return None


def test_chat_completion_direct():
    """Test chat completion using direct requests."""
    print("\n🗨️  Testing Direct Chat Completion:")
    
    base_url = os.getenv('LLM_BASE_URL', 'http://localhost:4000')
    
    payload = {
        "model": "claude-3-haiku",
        "messages": [{"role": "user", "content": "Say 'Hello World'"}],
        "max_tokens": 10
    }
    
    headers = {
        'Authorization': 'Bearer sk-1234',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            print(f"  ✅ Direct chat completion successful")
            print(f"  📝 Response: {content}")
            return True
        else:
            print(f"  ❌ Direct chat completion failed: {response.status_code}")
            print(f"  📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Direct chat completion failed: {e}")
        return False


def test_adapter_chat_completion(adapter):
    """Test chat completion using LiteLLMAdapter."""
    print("\n🤖 Testing Adapter Chat Completion:")
    
    if not adapter:
        print("  ❌ No adapter available")
        return False
    
    try:
        start_time = time.time()
        response = adapter.generate_llm_response(
            prompt="Think step by step and provide your reasoning.",
            question="What is 2 + 2?"
        )
        end_time = time.time()
        
        print(f"  ✅ Adapter chat completion successful ({end_time - start_time:.2f}s)")
        print(f"  💭 Reasoning: {response.reasoning[:100]}...")
        print(f"  🎯 Answer: {response.answer}")
        return True
        
    except Exception as e:
        print(f"  ❌ Adapter chat completion failed: {e}")
        print(f"  📋 Exception type: {type(e).__name__}")
        return False


def main():
    """Run all tests."""
    print("🧪 LiteLLM Connection Diagnostic Test")
    print("=" * 50)
    
    # Test environment
    env_vars = test_environment()
    
    # Test LiteLLM server
    server_ok = test_litellm_server()
    
    # Test adapter creation
    adapter = test_adapter_creation()
    
    # Test direct chat completion
    direct_ok = test_chat_completion_direct()
    
    # Test adapter chat completion
    adapter_ok = test_adapter_chat_completion(adapter)
    
    # Summary
    print("\n📊 Test Summary:")
    print("=" * 50)
    print(f"  Environment: {'✅' if env_vars else '❌'}")
    print(f"  LiteLLM Server: {'✅' if server_ok else '❌'}")
    print(f"  Adapter Creation: {'✅' if adapter else '❌'}")
    print(f"  Direct Chat: {'✅' if direct_ok else '❌'}")
    print(f"  Adapter Chat: {'✅' if adapter_ok else '❌'}")
    
    if all([server_ok, adapter, direct_ok, adapter_ok]):
        print("\n🎉 All tests passed! LiteLLM connection is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        
        if server_ok and direct_ok and not adapter_ok:
            print("\n💡 Diagnosis: LiteLLM server works, but adapter has issues.")
            print("   This suggests a problem with the LiteLLMAdapter implementation.")
        elif not server_ok:
            print("\n💡 Diagnosis: LiteLLM server is not responding.")
            print("   Run: make litellm-status")
            print("   Run: make litellm-install (if needed)")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())