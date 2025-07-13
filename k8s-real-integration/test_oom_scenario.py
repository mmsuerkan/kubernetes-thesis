#!/usr/bin/env python3
"""
Test OOMKilled scenario with AI command generation
"""

import asyncio
import json
from src.executor.ai_command_generator import AICommandGenerator
import os

async def test_oom_scenario():
    """Test how AI handles OOMKilled scenarios"""
    
    print("🧪 Testing OOMKilled Scenario AI Response")
    print("=" * 60)
    
    # Initialize AI command generator
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return
    
    ai_generator = AICommandGenerator(openai_api_key, model="gpt-3.5-turbo")
    
    # Test context for OOMKilled pod
    test_context = {
        "error_type": "OOMKilled",
        "pod_name": "memory-stress-test",
        "namespace": "default",
        "strategy": {
            "id": "oom_strategy_test",
            "type": "default",
            "confidence": 0.5,
            "selection_reason": "default_fallback"
        },
        "real_k8s_data": {
            "pod": {
                "metadata": {
                    "name": "memory-stress-test",
                    "namespace": "default"
                },
                "spec": {
                    "containers": [
                        {
                            "name": "memory-eater",
                            "image": "polinux/stress",
                            "resources": {
                                "limits": {
                                    "memory": "50Mi",
                                    "cpu": "0.1"
                                },
                                "requests": {
                                    "memory": "10Mi", 
                                    "cpu": "0.05"
                                }
                            }
                        }
                    ]
                },
                "status": {
                    "phase": "Failed",
                    "containerStatuses": [
                        {
                            "state": {
                                "terminated": {
                                    "exitCode": 137,
                                    "reason": "OOMKilled"
                                }
                            }
                        }
                    ]
                }
            },
            "events": [
                {
                    "type": "Warning",
                    "message": "Container was OOMKilled (exit code 137)"
                },
                {
                    "type": "Warning", 
                    "message": "Memory limit of 50Mi exceeded, process killed"
                }
            ],
            "logs": [
                "stress: info: [1] dispatching hogs: 1 cpu, 0 io, 1 vm, 0 hdd",
                "stress: info: [1] successful run completed in 0s",
                "Killed"
            ],
            "lessons_learned": []
        }
    }
    
    print(f"📱 Pod Name: {test_context['pod_name']}")
    print(f"🚨 Error Type: {test_context['error_type']}")
    print(f"💾 Memory Limit: 50Mi")
    print(f"📊 Exit Code: 137 (OOMKilled)")
    print()
    
    try:
        # Generate kubectl commands using AI
        print("🤖 Generating AI commands for OOMKilled scenario...")
        
        commands = await ai_generator.generate_kubectl_commands(
            error_type=test_context["error_type"],
            pod_name=test_context["pod_name"], 
            namespace=test_context["namespace"],
            strategy=test_context["strategy"],
            real_k8s_data=test_context["real_k8s_data"]
        )
        
        print("\n" + "="*60)
        print("✅ AI COMMAND GENERATION RESULTS")
        print("="*60)
        
        total_commands = sum(len(cmds) for cmds in commands.values())
        print(f"📊 Total Commands Generated: {total_commands}")
        print()
        
        for category, cmd_list in commands.items():
            if cmd_list:
                print(f"📋 {category.upper().replace('_', ' ')}:")
                for i, cmd in enumerate(cmd_list, 1):
                    print(f"   {i}. {cmd}")
                print()
        
        # Analyze AI's approach to memory issues
        print("🧠 AI ANALYSIS:")
        
        fix_commands = commands.get("fix_commands", [])
        if any("memory" in cmd.lower() or "resources" in cmd.lower() for cmd in fix_commands):
            print("   ✅ AI recognized memory-related issue")
        else:
            print("   ⚠️  AI may not have addressed memory limits specifically")
            
        if any("delete" in cmd and "run" in cmd for cmd in fix_commands):
            print("   ✅ AI using delete+recreate strategy")
        else:
            print("   ⚠️  AI not using standard pod recreation")
            
        print("\n" + "="*60)
        print("📊 MEMORY SCENARIO TEST COMPLETED")
        print("="*60)
        
        return commands
        
    except Exception as e:
        print(f"❌ Error during AI command generation: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_oom_scenario())