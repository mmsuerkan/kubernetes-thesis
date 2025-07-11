"""
Test script for Go service integration
"""
import httpx
import json
from datetime import datetime

# Sample Go service request
go_request = {
    "pod_name": "test-nginx-pod",
    "namespace": "default",
    "error_type": "ImagePullBackOff",
    "real_k8s_data": {
        "pod_spec": {
            "metadata": {
                "name": "test-nginx-pod",
                "namespace": "default"
            },
            "spec": {
                "containers": [{
                    "name": "nginx",
                    "image": "nginx:nonexistent-tag"
                }]
            },
            "status": {
                "phase": "Pending",
                "conditions": [{
                    "type": "ContainersReady",
                    "status": "False",
                    "reason": "ContainersNotReady"
                }]
            }
        },
        "events": [
            {
                "type": "Warning",
                "reason": "Failed",
                "message": "Failed to pull image \"nginx:nonexistent-tag\": rpc error: code = Unknown desc = Error response from daemon: manifest for nginx:nonexistent-tag not found"
            },
            {
                "type": "Warning", 
                "reason": "Failed",
                "message": "Error: ImagePullBackOff"
            }
        ],
        "logs": [
            "Error: image nginx:nonexistent-tag not found",
            "Failed to pull image",
            "Back-off pulling image \"nginx:nonexistent-tag\""
        ],
        "container_statuses": [{
            "name": "nginx",
            "ready": False,
            "state": {
                "waiting": {
                    "reason": "ImagePullBackOff",
                    "message": "Back-off pulling image \"nginx:nonexistent-tag\""
                }
            }
        }]
    }
}

async def test_go_integration():
    """Test the Go integration endpoint"""
    async with httpx.AsyncClient() as client:
        print("🚀 Testing Go Integration Endpoint...")
        print(f"📡 Sending request to: http://localhost:8000/api/v1/reflexion/process-with-k8s-data")
        print(f"📦 Pod: {go_request['pod_name']}")
        print(f"❌ Error: {go_request['error_type']}")
        
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/reflexion/process-with-k8s-data",
                json=go_request,
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ Success! Reflexion Response:")
                print(f"   Workflow ID: {result['workflow_id']}")
                print(f"   Success: {result['success']}")
                print(f"   Strategy: {result['final_strategy'].get('type', 'N/A')}")
                print(f"   Confidence: {result['final_strategy'].get('confidence', 0)}")
                print(f"   Used Real K8s Data: {result['reflexion_summary'].get('used_real_k8s_data', False)}")
                print(f"   Reflections: {result['reflexion_summary'].get('reflections_performed', 0)}")
                print(f"   Learning Velocity: {result['reflexion_summary'].get('learning_velocity', 0)}")
                
                print("\n📊 Strategy Details:")
                print(json.dumps(result['final_strategy'], indent=2))
                
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"\n❌ Request failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_go_integration())