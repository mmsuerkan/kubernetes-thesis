#!/usr/bin/env python3
"""Test detailed endpoint manually"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.workflow import ReflexiveK8sWorkflow

async def test_workflow():
    # Initialize workflow like the service does
    workflow = ReflexiveK8sWorkflow(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        go_service_url="http://localhost:8080",
        reflection_depth="medium"
    )
    
    print("Workflow initialized successfully")
    print(f"Reflection engine: {workflow.reflection_engine}")
    print(f"Workflow instance: {workflow}")
    
if __name__ == "__main__":
    asyncio.run(test_workflow())