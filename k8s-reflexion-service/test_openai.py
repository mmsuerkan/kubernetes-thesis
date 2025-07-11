#!/usr/bin/env python3
"""Quick OpenAI API test"""
import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

async def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API Key exists: {bool(api_key)}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    print(f"API Key prefix: {api_key[:20] if api_key else 'None'}...")
    
    try:
        print("\nTesting OpenAI connection...")
        
        # Create LLM instance
        llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-3.5-turbo",  # Using cheaper model for test
            temperature=0.1,
            timeout=30
        )
        
        # Simple test message
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Say 'Hello, I am working!' in exactly 5 words.")
        ]
        
        print("Sending request to OpenAI...")
        response = await llm.ainvoke(messages)
        
        print(f"\nSuccess! Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {str(e)}")
        
        # More detailed error info
        if hasattr(e, 'response'):
            print(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            print(f"Response text: {getattr(e.response, 'text', 'N/A')}")
        
        return False

if __name__ == "__main__":
    print("OpenAI API Connection Test")
    print("=" * 50)
    
    success = asyncio.run(test_openai())
    
    print("\n" + "=" * 50)
    print(f"Test {'PASSED' if success else 'FAILED'}")
    
    if not success:
        print("\nTroubleshooting tips:")
        print("1. Check if OPENAI_API_KEY environment variable is set correctly")
        print("2. Verify the API key is valid at https://platform.openai.com/api-keys")
        print("3. Check if you have API credits/quota available")
        print("4. Try using a VPN if OpenAI is blocked in your region")