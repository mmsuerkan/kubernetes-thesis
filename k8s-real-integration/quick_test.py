import os
import requests
from dotenv import load_dotenv

load_dotenv()

print("=== Quick Connection Test ===")

# 1. Test OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")
print(f"OpenAI API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"Key format OK: {'Yes' if api_key.startswith('sk-') else 'No'}")
    print(f"Key length: {len(api_key)} characters")

# 2. Test FastAPI Backend
try:
    response = requests.get("http://localhost:8000/health", timeout=3)
    print(f"FastAPI Backend: {'Online' if response.status_code == 200 else 'Error'}")
except:
    print("FastAPI Backend: Offline")

# 3. Test Go Watcher Service
try:
    response = requests.get("http://localhost:8080/api/v1/health", timeout=3)
    print(f"Go Watcher Service: {'Online' if response.status_code == 200 else 'Error'}")
except:
    print("Go Watcher Service: Offline")

# 4. Test OpenAI Status from FastAPI
try:
    response = requests.get("http://localhost:8000/api/v1/debug/openai-status", timeout=3)
    if response.status_code == 200:
        data = response.json()
        configured = data.get('configured') or data.get('api_key_exists') or data.get('openai_test') == 'success'
        print(f"FastAPI OpenAI Status: {'Configured' if configured else 'Not Configured'}")
    else:
        print("FastAPI OpenAI Status: Error")
except:
    print("FastAPI OpenAI Status: Cannot connect")