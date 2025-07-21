import requests
import json

try:
    response = requests.get("http://localhost:8080/api/v1/health", timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text}")
    
    if response.status_code == 200:
        try:
            json_data = response.json()
            print(f"JSON Data: {json.dumps(json_data, indent=2)}")
        except:
            print("Response is not JSON")
            
except Exception as e:
    print(f"Error: {e}")