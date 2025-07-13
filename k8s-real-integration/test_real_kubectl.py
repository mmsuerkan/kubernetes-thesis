"""
Test script for Real Kubectl Execution
"""
import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.executor.real_kubectl_executor import RealKubectlExecutor, KubectlSecurityValidator

async def test_kubectl_detection():
    """Test kubectl binary detection"""
    print("🔍 Testing kubectl detection...")
    
    executor = RealKubectlExecutor(dry_run=True)
    print(f"   Kubectl path: {executor.kubectl_path}")
    print(f"   Platform: {executor.platform}")
    print(f"   Dry run: {executor.dry_run}")

async def test_security_validation():
    """Test security validation"""
    print("\n🛡️ Testing security validation...")
    
    validator = KubectlSecurityValidator()
    
    test_commands = [
        "kubectl get pods",                                    # Safe
        "kubectl delete pod test-pod -n default",            # Medium risk
        "kubectl delete namespace production",                # Forbidden
        "kubectl get pods | grep Running",                   # Dangerous char
        "kubectl exec test-pod -- /bin/bash",               # High risk
        "",                                                  # Empty
        "docker ps",                                         # Non-kubectl
    ]
    
    for cmd in test_commands:
        result = validator.validate_command(cmd)
        print(f"   Command: {cmd}")
        print(f"   Safe: {result.is_safe}, Risk: {result.risk_level}")
        if result.warnings:
            print(f"   Warnings: {result.warnings}")
        if result.blocked_reason:
            print(f"   Blocked: {result.blocked_reason}")
        print()

async def test_dry_run_execution():
    """Test dry run command execution"""
    print("🧪 Testing dry run execution...")
    
    executor = RealKubectlExecutor(dry_run=True)
    
    test_commands = [
        "kubectl get pods -n default",
        "kubectl get nodes",
        "kubectl version --client"
    ]
    
    for cmd in test_commands:
        print(f"   Executing: {cmd}")
        result = await executor.execute_command(cmd)
        print(f"   Success: {result.success}")
        print(f"   Stdout: {result.stdout}")
        print(f"   Time: {result.execution_time:.2f}s")
        print()

async def test_real_execution_safe():
    """Test real execution with safe commands only"""
    print("⚡ Testing real execution (SAFE commands only)...")
    
    # Only run if kubectl is available
    executor = RealKubectlExecutor(dry_run=False)
    
    # Very safe commands
    safe_commands = [
        "kubectl version --client",
        "kubectl cluster-info --request-timeout=5s",
    ]
    
    for cmd in safe_commands:
        print(f"   Executing: {cmd}")
        try:
            result = await executor.execute_command(cmd)
            print(f"   Success: {result.success}")
            print(f"   Exit code: {result.exit_code}")
            if result.success:
                print(f"   Output: {result.stdout[:100]}...")
            else:
                print(f"   Error: {result.stderr[:100]}...")
            print(f"   Time: {result.execution_time:.2f}s")
        except Exception as e:
            print(f"   Exception: {e}")
        print()

async def test_command_sequence():
    """Test command sequence execution"""
    print("🔗 Testing command sequence...")
    
    executor = RealKubectlExecutor(dry_run=True)
    
    commands = [
        "kubectl version --client",
        "kubectl get namespaces", 
        "kubectl get pods -n default"
    ]
    
    results = await executor.execute_command_sequence(commands)
    
    print(f"   Executed {len(results)} commands")
    for i, result in enumerate(results):
        print(f"   Command {i+1}: Success={result.success}, Time={result.execution_time:.2f}s")

async def test_ai_commands_dict():
    """Test AI commands dictionary execution"""
    print("🤖 Testing AI commands dict execution...")
    
    executor = RealKubectlExecutor(dry_run=True)
    
    # Simulate AI generated commands
    ai_commands = {
        "backup_commands": [
            "kubectl get pod test-pod -n default -o yaml"
        ],
        "fix_commands": [
            "kubectl delete pod test-pod -n default",
            "kubectl run test-pod --image=nginx:latest --restart=Never -n default"
        ],
        "validation_commands": [
            "kubectl get pod test-pod -n default",
            "kubectl describe pod test-pod -n default"
        ],
        "rollback_commands": [
            "kubectl delete pod test-pod -n default"
        ]
    }
    
    results = await executor.execute_kubectl_commands_dict(ai_commands)
    analysis = executor.analyze_execution_results(results)
    
    print(f"   Overall success: {analysis['overall_success']}")
    print(f"   Commands: {analysis['successful_commands']}/{analysis['total_commands']}")
    print(f"   Total time: {analysis['total_execution_time']:.2f}s")
    print(f"   Categories: {analysis['categories_executed']}")

async def main():
    """Run all tests"""
    print("🚀 REAL KUBECTL EXECUTOR TESTS")
    print("=" * 50)
    
    await test_kubectl_detection()
    await test_security_validation()
    await test_dry_run_execution()
    
    # Skip real commands in automated testing
    print("\n⏭️ Skipping real kubectl commands (automated test)")
    # await test_real_execution_safe()
    
    await test_command_sequence()
    await test_ai_commands_dict()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())