#!/usr/bin/env python3
"""
Test LangSmith Integration
"""
import os
from dotenv import load_dotenv
load_dotenv()

from langsmith import traceable
from langchain_openai import ChatOpenAI

@traceable(name="test_langsmith_connection")
def test_langsmith():
    """Test LangSmith connection"""
    print("🧪 Testing LangSmith integration...")
    
    # Check environment variables
    print(f"✅ LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
    print(f"✅ LANGCHAIN_ENDPOINT: {os.getenv('LANGCHAIN_ENDPOINT')}")
    print(f"✅ LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
    
    api_key = os.getenv('LANGCHAIN_API_KEY')
    if api_key:
        print(f"✅ LANGCHAIN_API_KEY: {api_key[:20]}...")
    else:
        print("❌ LANGCHAIN_API_KEY not found")
        return
    
    try:
        # Test with ChatOpenAI
        llm = ChatOpenAI(model="gpt-3.5-turbo")
        response = llm.invoke("Hello from K8s Reflexion System! This is a LangSmith test.")
        
        print(f"🤖 LLM Response: {response.content}")
        print("✅ LangSmith integration successful!")
        print("🔗 Check your LangSmith dashboard: https://smith.langchain.com")
        
    except Exception as e:
        print(f"❌ LangSmith test failed: {e}")

if __name__ == "__main__":
    test_langsmith()