#!/usr/bin/env python3
"""Test API key validity"""
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"API Key from env: {api_key[:20]}...{api_key[-10:]}")
else:
    print("API Key from env: None")

# Test with OpenAI directly
try:
    client = OpenAI(api_key=api_key)
    
    # Simple test
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a test bot."},
            {"role": "user", "content": "Reply with OK"}
        ],
        max_tokens=10
    )
    
    print(f"Success! Response: {response.choices[0].message.content}")
    print(f"Model: {response.model}")
    print(f"Usage: {response.usage}")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response}")