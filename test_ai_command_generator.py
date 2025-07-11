"""
Test script for AI Command Generator
"""
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from src.executor.ai_command_generator import AICommandGenerator

load_dotenv()

async def test_ai_command_generator():
    """Test the AI Command Generator with various scenarios"""
    
    print("🤖 Testing AI Command Generator...")
    print("=" * 50)
    
    # Initialize AI Command Generator
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return
    
    generator = AICommandGenerator(openai_api_key)
    
    # Test case 1: ImagePullBackOff error
    test_case_1 = {
        "error_type": "ImagePullBackOff",
        "pod_name": "test-nginx-pod",
        "namespace": "default",
        "strategy": {
            "type": "fix_image_tag",
            "confidence": 0.95,
            "selection_reason": "ai_generated"
        },
        "real_k8s_data": {
            "pod": {
                "metadata": {
                    "name": "test-nginx-pod",
                    "namespace": "default"
                },
                "spec": {
                    "containers": [
                        {
                            "name": "nginx",
                            "image": "nginx:nonexistent-tag",
                            "resources": {
                                "limits": {"memory": "256Mi"},
                                "requests": {"memory": "128Mi"}
                            }
                        }
                    ]
                },
                "status": {
                    "phase": "Pending"
                }
            },
            "events": [
                {
                    "type": "Warning",
                    "reason": "Failed",
                    "message": "Failed to pull image 'nginx:nonexistent-tag': rpc error: code = Unknown desc = Error response from daemon: manifest for nginx:nonexistent-tag not found"
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
                "Back-off pulling image 'nginx:nonexistent-tag'"
            ]
        }
    }
    
    # Test case 2: CrashLoopBackOff error
    test_case_2 = {
        "error_type": "CrashLoopBackOff",
        "pod_name": "test-app-pod",
        "namespace": "default",
        "strategy": {
            "type": "resource_adjustment",
            "confidence": 0.85,
            "selection_reason": "learned_strategy"
        },
        "real_k8s_data": {
            "pod": {
                "metadata": {
                    "name": "test-app-pod",
                    "namespace": "default"
                },
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "myapp:latest",
                            "resources": {
                                "limits": {"memory": "128Mi"},
                                "requests": {"memory": "64Mi"}
                            }
                        }
                    ]
                },
                "status": {
                    "phase": "Running"
                }
            },
            "events": [
                {
                    "type": "Warning",
                    "reason": "BackOff",
                    "message": "Back-off restarting failed container"
                }
            ],
            "logs": [
                "java.lang.OutOfMemoryError: Java heap space",
                "Error: exit code 137",
                "Container terminated with exit code 137"
            ]
        }
    }
    
    # Run individual tests
    print("\n📋 Test Case 1: ImagePullBackOff")
    print("-" * 30)
    
    try:
        commands_1 = await generator.generate_kubectl_commands(
            error_type=test_case_1["error_type"],
            pod_name=test_case_1["pod_name"],
            namespace=test_case_1["namespace"],
            strategy=test_case_1["strategy"],
            real_k8s_data=test_case_1["real_k8s_data"]
        )
        
        print("✅ ImagePullBackOff commands generated successfully!")
        print(f"📦 Backup commands: {len(commands_1['backup_commands'])}")
        print(f"🔧 Fix commands: {len(commands_1['fix_commands'])}")
        print(f"✅ Validation commands: {len(commands_1['validation_commands'])}")
        print(f"🔙 Rollback commands: {len(commands_1['rollback_commands'])}")
        
        print("\n📋 Generated Commands:")
        for category, commands in commands_1.items():
            print(f"\n{category.upper()}:")
            for i, cmd in enumerate(commands, 1):
                print(f"  {i}. {cmd}")
        
    except Exception as e:
        print(f"❌ ImagePullBackOff test failed: {e}")
    
    print("\n" + "=" * 50)
    print("📋 Test Case 2: CrashLoopBackOff")
    print("-" * 30)
    
    try:
        commands_2 = await generator.generate_kubectl_commands(
            error_type=test_case_2["error_type"],
            pod_name=test_case_2["pod_name"],
            namespace=test_case_2["namespace"],
            strategy=test_case_2["strategy"],
            real_k8s_data=test_case_2["real_k8s_data"]
        )
        
        print("✅ CrashLoopBackOff commands generated successfully!")
        print(f"📦 Backup commands: {len(commands_2['backup_commands'])}")
        print(f"🔧 Fix commands: {len(commands_2['fix_commands'])}")
        print(f"✅ Validation commands: {len(commands_2['validation_commands'])}")
        print(f"🔙 Rollback commands: {len(commands_2['rollback_commands'])}")
        
        print("\n📋 Generated Commands:")
        for category, commands in commands_2.items():
            print(f"\n{category.upper()}:")
            for i, cmd in enumerate(commands, 1):
                print(f"  {i}. {cmd}")
        
    except Exception as e:
        print(f"❌ CrashLoopBackOff test failed: {e}")
    
    # Run batch test
    print("\n" + "=" * 50)
    print("📊 Batch Test Results")
    print("-" * 30)
    
    try:
        batch_results = await generator.test_command_generation([test_case_1, test_case_2])
        
        print(f"📊 Total Tests: {batch_results['total_tests']}")
        print(f"✅ Successful Tests: {batch_results['successful_tests']}")
        print(f"📈 Success Rate: {batch_results['success_rate']:.1%}")
        
        for result in batch_results['results']:
            status = "✅" if result['success'] else "❌"
            print(f"{status} Test Case {result['test_case']}: ", end="")
            
            if result['success']:
                print(f"{result['total_commands']} commands generated")
            else:
                print(f"Failed - {result['error']}")
        
    except Exception as e:
        print(f"❌ Batch test failed: {e}")
    
    print("\n🎉 AI Command Generator testing completed!")

if __name__ == "__main__":
    asyncio.run(test_ai_command_generator())