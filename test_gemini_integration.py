#!/usr/bin/env python3
"""
Test script for Gemini API integration

This script tests the Gemini API integration without requiring a full server startup.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.settings import settings
from src.utils.gemini_client import gemini_client


async def test_gemini_integration():
    """Test Gemini API integration."""
    print("🧪 Testing Gemini API Integration")
    print("=" * 50)
    
    # Check configuration
    print(f"✅ Gemini Model: {settings.gemini_model}")
    print(f"✅ Temperature: {settings.gemini_temperature}")
    print(f"✅ Max Tokens: {settings.gemini_max_tokens}")
    print(f"✅ API Key Configured: {'Yes' if settings.gemini_api_key else 'No'}")
    
    if not settings.gemini_api_key:
        print("\n❌ GEMINI_API_KEY not set!")
        print("Please set your Gemini API key in the environment or .env file")
        return False
    
    try:
        # Test basic text generation
        print("\n🔄 Testing basic text generation...")
        response = await gemini_client.generate_response(
            prompt="Say hello and introduce yourself as a travel planning AI assistant.",
            system_prompt="You are a helpful travel planning assistant."
        )
        print(f"✅ Response: {response[:100]}...")
        
        # Test JSON generation
        print("\n🔄 Testing JSON generation...")
        json_response = await gemini_client.generate_json_response(
            prompt="Create a simple travel preference profile for a user who likes adventure travel.",
            system_prompt="You are a travel profiling assistant.",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "travel_style": {"type": "string"},
                    "interests": {"type": "array", "items": {"type": "string"}},
                    "budget_range": {"type": "string"}
                }
            }
        )
        print(f"✅ JSON Response: {json_response}")
        
        # Test model info
        print("\n🔄 Testing model info...")
        model_info = gemini_client.get_model_info()
        print(f"✅ Model Info: {model_info}")
        
        print("\n🎉 All tests passed! Gemini API integration is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        return False


async def test_agent_integration():
    """Test agent integration with Gemini."""
    print("\n🧪 Testing Agent Integration")
    print("=" * 50)
    
    try:
        from src.agents.profiler_agent import ProfilerAgent
        
        # Create a test agent
        agent = ProfilerAgent()
        
        # Test AI response generation
        print("🔄 Testing agent AI response generation...")
        response = await agent.generate_ai_response(
            prompt="Generate a friendly greeting for a new user starting their travel planning journey.",
            context={"user_type": "new_user"}
        )
        print(f"✅ Agent Response: {response[:100]}...")
        
        # Test JSON response generation
        print("\n🔄 Testing agent JSON response generation...")
        json_response = await agent.generate_ai_json_response(
            prompt="Create a list of 3 travel questions to ask a new user.",
            schema={
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "question": {"type": "string"},
                                "type": {"type": "string"}
                            }
                        }
                    }
                }
            }
        )
        print(f"✅ Agent JSON Response: {json_response}")
        
        print("\n🎉 Agent integration test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent integration test failed: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("🚀 AI Travel Planner - Gemini API Integration Test")
    print("=" * 60)
    
    # Test basic integration
    basic_success = await test_gemini_integration()
    
    if basic_success:
        # Test agent integration
        agent_success = await test_agent_integration()
        
        if agent_success:
            print("\n✅ All integration tests passed!")
            print("🎯 Your AI Travel Planner is ready to use Gemini API!")
        else:
            print("\n⚠️  Basic integration works, but agent integration needs attention.")
    else:
        print("\n❌ Basic integration failed. Please check your API key and configuration.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 