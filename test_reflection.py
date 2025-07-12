#!/usr/bin/env python3
"""Direct test of reflection engine"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.nodes.reflect import ReflectionEngine
from src.state import ReflexiveK8sState
from datetime import datetime

async def test_reflection():
    # Create reflection engine
    engine = ReflectionEngine(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        reflection_depth="medium"
    )
    
    # Create test state
    test_state: ReflexiveK8sState = {
        "pod_name": "test-pod",
        "namespace": "default",
        "error_type": "ImagePullBackOff",
        "success": True,
        "resolution_time": 45.0,
        "retry_count": 0,
        "workflow_id": "test_123",
        "ai_analysis": {
            "confidence": 0.95,
            "analysis": "Image not found in registry"
        },
        "current_strategy": {
            "type": "image_replacement",
            "confidence": 0.9
        },
        "execution_result": {
            "success": True,
            "message": "Pod recreated with valid image"
        },
        "detailed_observation": {
            "success": True,
            "resolution_time": 45.0,
            "performance_score": 0.8
        },
        "observation_timestamp": datetime.now(),
        "current_reflection": None,
        "reflection_history": [],
        "reflection_depth": 0,
        "episodic_memory": [],
        "past_attempts": [],
        "strategy_database": {},
        "strategy_evolution": [],
        "meta_learning": {"total_reflections": 0},
        "self_awareness_level": 0.5,
        "learning_velocity": 0.0,
        "environment_context": {},
        "temporal_context": {},
        "performance_metrics": {},
        "improvement_trajectory": []
    }
    
    print("Testing reflection engine...")
    print("=" * 50)
    
    try:
        # Run reflection
        result = await engine.reflect_on_action_node(test_state)
        
        print(f"Success! Reflection completed")
        print(f"Self-awareness level: {result.get('self_awareness_level', 'N/A')}")
        
        reflection = result.get('current_reflection')
        if reflection:
            if hasattr(reflection, 'insights_gained'):
                insights = reflection.insights_gained
            else:
                insights = reflection.get('insights_gained', [])
            
            print(f"Insights generated: {len(insights) if insights else 0}")
            if insights:
                print("\nInsights:")
                for i, insight in enumerate(insights, 1):
                    print(f"{i}. {insight}")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reflection())