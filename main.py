"""
K8s Reflexion Service - FastAPI Server
Enhanced Kubernetes error resolution with LangGraph + Reflexion
"""
import asyncio
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
import uvicorn
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.workflow import ReflexiveK8sWorkflow
from src.memory.strategy_db import StrategyDatabase
from src.memory.episodic_memory import EpisodicMemoryManager
from src.memory.performance_tracker import PerformanceTracker
from src.executor.ai_command_generator import AICommandGenerator

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# FastAPI app setup
app = FastAPI(
    title="K8s Reflexion Service",
    description="Autonomous Kubernetes error resolution with LangGraph + Reflexion",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global workflow instance
workflow_instance: Optional[ReflexiveK8sWorkflow] = None

# Global memory instances  
strategy_db: Optional[StrategyDatabase] = None
episodic_memory: Optional[EpisodicMemoryManager] = None
performance_tracker: Optional[PerformanceTracker] = None
ai_command_generator: Optional[AICommandGenerator] = None

# Request/Response Models
class PodErrorRequest(BaseModel):
    pod_name: str = Field(..., description="Name of the failing pod")
    namespace: str = Field(default="default", description="Kubernetes namespace")
    error_type: str = Field(..., description="Type of error (e.g., ImagePullBackOff)")
    thread_id: Optional[str] = Field(None, description="Thread ID for workflow state persistence")

# NEW: Real K8s data from Go service
class RealK8sData(BaseModel):
    pod_spec: Dict[str, Any] = Field(..., description="Full pod specification")
    events: list[Dict[str, Any]] = Field(..., description="Pod events")
    logs: list[str] = Field(..., description="Pod logs")
    container_statuses: Optional[list[Dict[str, Any]]] = Field(None, description="Container statuses")

class GoServiceErrorRequest(BaseModel):
    """Request from Go k8s-ai-agent-mvp service with real K8s data"""
    pod_name: str = Field(..., description="Name of the failing pod")
    namespace: str = Field(default="default", description="Kubernetes namespace")
    error_type: str = Field(..., description="Type of error (e.g., ImagePullBackOff)")
    real_k8s_data: RealK8sData = Field(..., description="Real Kubernetes data from Go service")
    thread_id: Optional[str] = Field(None, description="Thread ID for workflow state persistence")

class ReflexionResponse(BaseModel):
    workflow_id: str
    success: bool
    pod_name: str
    final_strategy: Dict[str, Any]
    resolution_time: float
    requires_human_intervention: bool
    reflexion_summary: Dict[str, Any]
    error: Optional[str] = None

# HealthResponse model removed - using simple dict responses

class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    current_step: str
    progress: float
    reflexion_metrics: Dict[str, Any]

# NEW: Command execution models
class CommandExecutionRequest(BaseModel):
    pod_name: str = Field(..., description="Name of the pod")
    namespace: str = Field(default="default", description="Kubernetes namespace")
    error_type: str = Field(..., description="Type of error (e.g., ImagePullBackOff)")
    strategy: Dict[str, Any] = Field(..., description="Strategy from reflexion")
    real_k8s_data: RealK8sData = Field(..., description="Real Kubernetes data")
    dry_run: bool = Field(default=False, description="Whether to execute in dry-run mode")

class CommandExecutionResponse(BaseModel):
    pod_name: str
    namespace: str
    error_type: str
    commands_generated: int
    commands_executed: int
    success: bool
    execution_time: float
    commands: Dict[str, Any]  # Generated commands
    go_service_url: str = Field(..., description="URL to call Go service for execution")
    message: str

# NEW: Execution feedback models
class ExecutionFeedbackRequest(BaseModel):
    workflow_id: str = Field(..., description="Original workflow ID")
    pod_name: str = Field(..., description="Pod name")
    namespace: str = Field(default="default", description="Namespace")
    error_type: str = Field(..., description="Error type")
    strategy_used: Dict[str, Any] = Field(..., description="Strategy that was used")
    execution_result: Dict[str, Any] = Field(..., description="Execution results")
    timestamp: str = Field(..., description="Timestamp of execution")

class ExecutionFeedbackResponse(BaseModel):
    workflow_id: str
    feedback_processed: bool
    reflexion_updated: bool
    strategy_confidence_updated: bool
    learning_summary: Dict[str, Any]
    message: str

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize the reflexion workflow"""
    global workflow_instance
    
    logger.info("Starting K8s Reflexion Service...")
    
    # Get configuration from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        raise RuntimeError("OpenAI API key required")
    
    # No Go service needed for Phase 2
    reflection_depth = os.getenv("REFLECTION_DEPTH", "medium")
    
    try:
        # Initialize memory systems first
        global strategy_db, episodic_memory, performance_tracker, ai_command_generator
        strategy_db = StrategyDatabase()
        episodic_memory = EpisodicMemoryManager()
        performance_tracker = PerformanceTracker()
        ai_command_generator = AICommandGenerator(openai_api_key)
        logger.info("Persistent memory systems initialized successfully")
        
        # Initialize workflow
        workflow_instance = ReflexiveK8sWorkflow(
            openai_api_key=openai_api_key,
            go_service_url="",
            reflection_depth=reflection_depth
        )
        logger.info("Reflexion workflow initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize workflow", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down K8s Reflexion Service...")

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    
    status = "healthy" if openai_configured else "degraded"
    
    return {
        "status": status,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "openai_configured": openai_configured,
        "phase": "reflexion_only"
    }

@app.get("/api/v1/health")
async def api_health():
    """API health check"""
    return {"status": "ok", "service": "k8s-reflexion", "timestamp": datetime.now().isoformat()}

# Core reflexion endpoints
@app.post("/api/v1/reflexion/process", response_model=ReflexionResponse)
async def process_pod_error(request: PodErrorRequest):
    """
    Process a pod error through the reflexive workflow
    
    This is the main endpoint that triggers the autonomous learning cycle:
    1. Analyze error with K8sGPT
    2. Select strategy based on learned knowledge
    3. Execute fix
    4. Observe outcome
    5. Reflect on action
    6. Learn and evolve strategies
    """
    if not workflow_instance:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    logger.info("Processing pod error request", 
                pod_name=request.pod_name, 
                error_type=request.error_type)
    
    try:
        # Process through reflexive workflow
        result = await workflow_instance.process_pod_error(
            pod_name=request.pod_name,
            namespace=request.namespace,
            error_type=request.error_type,
            thread_id=request.thread_id
        )
        
        return ReflexionResponse(**result)
        
    except Exception as e:
        logger.error("Workflow processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

# NEW: Endpoint for Go service with real K8s data
@app.post("/api/v1/reflexion/process-with-k8s-data", response_model=ReflexionResponse)
async def process_pod_error_with_real_data(request: GoServiceErrorRequest):
    """
    Process a pod error with real K8s data from Go service
    
    This endpoint receives real Kubernetes data from k8s-ai-agent-mvp
    and processes it through the reflexive workflow with enhanced context.
    """
    if not workflow_instance:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    logger.info("Processing pod error with real K8s data", 
                pod_name=request.pod_name, 
                error_type=request.error_type,
                has_real_data=True)
    
    try:
        # Create enhanced initial state with real K8s data
        from src.state import ReflexiveK8sState
        
        initial_state: ReflexiveK8sState = {
            "pod_name": request.pod_name,
            "namespace": request.namespace,
            "error_type": request.error_type,
            "retry_count": 0,
            "success": False,
            "workflow_id": f"go_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            # Real K8s data from Go service
            "k8sgpt_analysis": {
                "confidence": 0.95,  # High confidence with real data
                "analysis": f"Real K8s data analysis for {request.error_type}",
                "real_data": True,
                "pod_spec": request.real_k8s_data.pod_spec,
                "events": request.real_k8s_data.events,
                "logs": request.real_k8s_data.logs
            },
            "real_k8s_data": {
                "pod": request.real_k8s_data.pod_spec,
                "events": request.real_k8s_data.events,
                "logs": request.real_k8s_data.logs,
                "container_statuses": request.real_k8s_data.container_statuses
            },
            # Standard fields
            "current_strategy": {},
            "execution_result": {},
            "detailed_observation": {},
            "observation_timestamp": datetime.now(),
            "current_reflection": None,
            "reflection_history": [],
            "reflection_depth": 0,
            "episodic_memory": [],
            "past_attempts": [],
            "strategy_database": {},
            "strategy_evolution": [],
            "meta_learning": {},
            "self_awareness_level": 0.5,
            "learning_velocity": 0.0,
            "environment_context": {},
            "temporal_context": {},
            "performance_metrics": {},
            "improvement_trajectory": [],
            "execution_start_time": datetime.now(),
            "workflow_id": f"go_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Process through reflexive workflow
        result = await workflow_instance.compiled_workflow.ainvoke(initial_state)
        
        # Prepare response
        response = {
            "workflow_id": result.get("workflow_id"),
            "success": result.get("success", False),
            "pod_name": request.pod_name,
            "final_strategy": result.get("current_strategy", {}),
            "resolution_time": result.get("resolution_time", 0),
            "requires_human_intervention": result.get("requires_human_intervention", False),
            "reflexion_summary": {
                "reflections_performed": len(result.get("reflection_history", [])),
                "strategies_learned": len(result.get("strategy_database", {})),
                "self_awareness_level": result.get("self_awareness_level", 0.0),
                "learning_velocity": result.get("learning_velocity", 0.0),
                "used_real_k8s_data": True
            }
        }
        
        logger.info("Successfully processed with real K8s data",
                   workflow_id=response["workflow_id"],
                   strategy_type=response["final_strategy"].get("type"))
        
        return ReflexionResponse(**response)
        
    except Exception as e:
        logger.error("Workflow processing with real data failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

@app.post("/api/v1/reflexion/process-async")
async def process_pod_error_async(request: PodErrorRequest, background_tasks: BackgroundTasks):
    """
    Process pod error asynchronously
    Returns immediately with workflow_id for status tracking
    """
    if not workflow_instance:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    workflow_id = f"async_{request.pod_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Add to background tasks
    background_tasks.add_task(
        _process_pod_error_background,
        request,
        workflow_id
    )
    
    return {
        "workflow_id": workflow_id,
        "status": "processing",
        "message": "Reflexion workflow started in background"
    }

# Workflow management endpoints
@app.get("/api/v1/reflexion/workflow/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """Get status of a running workflow"""
    # In production, this would query a workflow state store
    # For now, return mock data
    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        status="running",
        current_step="reflect_on_action",
        progress=0.6,
        reflexion_metrics={
            "reflections_completed": 2,
            "strategies_learned": 1,
            "self_awareness_level": 0.7
        }
    )

@app.get("/api/v1/reflexion/metrics")
async def get_reflexion_metrics():
    """Get overall reflexion system metrics"""
    # In production, this would aggregate from persistent storage
    return {
        "total_workflows": 42,
        "success_rate": 0.85,
        "average_resolution_time": 45.2,
        "total_strategies_learned": 15,
        "average_self_awareness": 0.72,
        "learning_velocity": 0.15,
        "timestamp": datetime.now().isoformat()
    }

# Strategy and knowledge endpoints
@app.get("/api/v1/reflexion/strategies")
async def get_learned_strategies():
    """Get all learned strategies from the knowledge base"""
    # This would query the persistent strategy database
    return {
        "strategies": [
            {
                "id": "temporal_1234",
                "type": "temporal_optimization",
                "confidence": 0.85,
                "usage_count": 5,
                "success_rate": 0.8,
                "description": "Timing-based optimization for CrashLoopBackOff"
            },
            {
                "id": "resource_5678",
                "type": "resource_optimization",
                "confidence": 0.92,
                "usage_count": 8,
                "success_rate": 0.875,
                "description": "Resource adjustment strategy for memory issues"
            }
        ],
        "total_count": 2,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/reflexion/memory/episodic")
async def get_episodic_memory():
    """Get episodic memory entries"""
    return {
        "episodes": [
            {
                "episode_id": "ep_001",
                "context": {"pod_name": "test-pod", "error_type": "ImagePullBackOff"},
                "action_taken": {"type": "image_tag_replacement"},
                "outcome": {"success": True, "resolution_time": 30},
                "lessons_learned": ["Image tag validation is crucial"],
                "timestamp": "2024-07-10T10:30:00"
            }
        ],
        "total_episodes": 15,
        "memory_utilization": 0.3
    }

# Configuration endpoints
@app.get("/api/v1/config")
async def get_configuration():
    """Get current service configuration"""
    return {
        "reflection_depth": os.getenv("REFLECTION_DEPTH", "medium"),
        "go_service_url": os.getenv("GO_SERVICE_URL", "http://localhost:8080"),
        "openai_model": "gpt-4-turbo-preview",
        "max_reflection_depth": 5,
        "strategy_confidence_threshold": 0.7
    }

@app.post("/api/v1/config/reflection-depth")
async def update_reflection_depth(depth: str):
    """Update reflection depth setting"""
    valid_depths = ["shallow", "medium", "deep"]
    if depth not in valid_depths:
        raise HTTPException(status_code=400, detail=f"Invalid depth. Must be one of: {valid_depths}")
    
    # In production, this would update the workflow configuration
    return {"message": f"Reflection depth updated to {depth}", "timestamp": datetime.now().isoformat()}

# Debug and development endpoints
@app.post("/api/v1/debug/test-gpt4-direct")
async def test_gpt4_direct(request: dict):
    """Test GPT-4 directly with a custom prompt"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo-preview",
            temperature=0.7,
            timeout=30
        )
        
        prompt = request.get("prompt", "Analyze a Kubernetes ImagePullBackOff error")
        
        messages = [
            SystemMessage(content="You are an AI analyzing Kubernetes errors."),
            HumanMessage(content=prompt)
        ]
        
        response = await llm.ainvoke(messages)
        
        return {
            "success": True,
            "prompt": prompt,
            "response": response.content,
            "model": "gpt-4-turbo-preview",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/v1/debug/openai-status")
async def check_openai_status():
    """Check OpenAI configuration and connectivity"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    status = {
        "api_key_exists": bool(api_key),
        "api_key_length": len(api_key) if api_key else 0,
        "api_key_prefix": api_key[:20] + "..." if api_key and len(api_key) > 20 else "None",
        "api_key_suffix": "..." + api_key[-10:] if api_key and len(api_key) > 10 else "None",
    }
    
    # Try a simple OpenAI call
    if api_key:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            
            llm = ChatOpenAI(
                api_key=api_key,
                model="gpt-3.5-turbo",
                temperature=0.1,
                timeout=10
            )
            
            messages = [
                SystemMessage(content="Test"),
                HumanMessage(content="Reply with 'OK' only")
            ]
            
            response = await llm.ainvoke(messages)
            status["openai_test"] = "success"
            status["openai_response"] = response.content
            
        except Exception as e:
            status["openai_test"] = "failed"
            status["openai_error"] = str(e)
            status["error_type"] = type(e).__name__
    else:
        status["openai_test"] = "skipped"
        status["reason"] = "No API key found"
    
    return status

@app.post("/api/v1/debug/reflection-full")
async def simulate_reflection_detailed(
    error_type: str = "ImagePullBackOff", 
    success: bool = True,
    resolution_time: float = 45.0
):
    """Simulate a reflection process with detailed output"""
    if not workflow_instance:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    # Create mock state for reflection
    from src.state import ReflexiveK8sState
    from datetime import datetime
    
    mock_state: ReflexiveK8sState = {
        "pod_name": "debug-pod",
        "namespace": "default", 
        "error_type": error_type,
        "success": success,
        "resolution_time": resolution_time,
        "retry_count": 0,
        "workflow_id": f"debug_{datetime.now().strftime('%H%M%S')}",
        "k8sgpt_analysis": {"confidence": 0.9, "analysis": "Mock analysis"},
        "current_strategy": {"type": "debug_strategy", "confidence": 0.8},
        "execution_result": {"success": success},
        "detailed_observation": {"mock": True},
        "observation_timestamp": datetime.now(),
        "current_reflection": None,
        "reflection_history": [],
        "reflection_depth": 0,
        "episodic_memory": [],
        "past_attempts": [],
        "strategy_database": {},
        "strategy_evolution": [],
        "meta_learning": {
            "total_reflections": 0, 
            "total_learning_cycles": 0,
            "learning_success_rate": 0.0,
            "reflection_quality_avg": 0.0
        },
        "self_awareness_level": 0.5,
        "learning_velocity": 0.0,
        "environment_context": {},
        "temporal_context": {},
        "performance_metrics": {},
        "improvement_trajectory": []
    }
    
    # Run reflection directly
    try:
        reflection_result = await workflow_instance.reflection_engine.reflect_on_action_node(mock_state)
    except Exception as e:
        logger.error("Reflection endpoint error", error=str(e))
        return {
            "debug_reflection": True,
            "error": str(e),
            "error_type": type(e).__name__,
            "self_awareness_level": 0.5,
            "insights_generated": 0,
            "insights": [],
            "reflection_quality": 0.0,
            "reflection_text_preview": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
    
    # Extract reflection data correctly
    current_reflection = reflection_result.get("current_reflection")
    self_awareness = reflection_result.get("self_awareness_level", 0.5)
    
    # Extract reflection details from the ReflectionEntry object
    if current_reflection and hasattr(current_reflection, 'reflection_text'):
        reflection_text = current_reflection.reflection_text
        insights = current_reflection.insights_gained if hasattr(current_reflection, 'insights_gained') else []
        quality_score = current_reflection.meta_quality_score if hasattr(current_reflection, 'meta_quality_score') else 0.5
    else:
        reflection_text = "No reflection generated"
        insights = []
        quality_score = 0.0
    
    return {
        "debug_reflection": True,
        "self_awareness_level": self_awareness,
        "insights_generated": len(insights),
        "insights": insights,
        "reflection_quality": quality_score,
        "reflection_text_preview": reflection_text[:1000] if reflection_text else "No text",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/debug/simulate-reflection")
async def simulate_reflection(
    error_type: str = "ImagePullBackOff", 
    success: bool = True,
    resolution_time: float = 45.0
):
    """Simulate a reflection process for testing"""
    if not workflow_instance:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    # Create mock state for reflection
    from src.state import ReflexiveK8sState
    from datetime import datetime
    
    mock_state: ReflexiveK8sState = {
        "pod_name": "debug-pod",
        "namespace": "default", 
        "error_type": error_type,
        "success": success,
        "resolution_time": resolution_time,
        "retry_count": 0,
        "workflow_id": f"debug_{datetime.now().strftime('%H%M%S')}",
        "k8sgpt_analysis": {"confidence": 0.9, "analysis": "Mock analysis"},
        "current_strategy": {"type": "debug_strategy", "confidence": 0.8},
        "execution_result": {"success": success},
        "detailed_observation": {"mock": True},
        "observation_timestamp": datetime.now(),
        "current_reflection": None,
        "reflection_history": [],
        "reflection_depth": 0,
        "episodic_memory": [],
        "past_attempts": [],
        "strategy_database": {},
        "strategy_evolution": [],
        "meta_learning": {
            "total_reflections": 0, 
            "total_learning_cycles": 0,
            "learning_success_rate": 0.0,
            "reflection_quality_avg": 0.0
        },
        "self_awareness_level": 0.5,
        "learning_velocity": 0.0,
        "environment_context": {},
        "temporal_context": {},
        "performance_metrics": {},
        "improvement_trajectory": []
    }
    
    # Run reflection directly
    try:
        reflection_result = await workflow_instance.reflection_engine.reflect_on_action_node(mock_state)
    except Exception as e:
        logger.error("Reflection endpoint error", error=str(e))
        return {
            "debug_reflection": True,
            "error": str(e),
            "error_type": type(e).__name__,
            "self_awareness_level": 0.5,
            "insights_generated": 0,
            "insights": [],
            "reflection_quality": 0.0,
            "reflection_text_preview": f"Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
    
    # Handle the result based on its type
    if isinstance(reflection_result, dict):
        self_awareness = reflection_result.get("self_awareness_level", 0.5)
        current_reflection = reflection_result.get("current_reflection", {})
    else:
        # If it's a typed state object, access attributes directly
        self_awareness = getattr(reflection_result, "self_awareness_level", 0.5)
        current_reflection = getattr(reflection_result, "current_reflection", {})
    
    # Extract insights and quality score
    insights_count = 0
    quality_score = 0.5
    
    if current_reflection:
        if isinstance(current_reflection, dict):
            insights_count = len(current_reflection.get("insights_gained", []))
            quality_score = current_reflection.get("meta_quality_score", 0.5)
        else:
            # Handle typed object
            insights = getattr(current_reflection, "insights_gained", [])
            insights_count = len(insights) if insights else 0
            quality_score = getattr(current_reflection, "meta_quality_score", 0.5)
    
    return {
        "debug_reflection": True,
        "self_awareness_level": self_awareness,
        "insights_generated": insights_count,
        "reflection_quality": quality_score,
        "timestamp": datetime.now().isoformat()
    }

# Helper functions
# Go service health check removed - Phase 2 is standalone

async def _process_pod_error_background(request: PodErrorRequest, workflow_id: str):
    """Background task for async processing"""
    try:
        logger.info("Starting background workflow", workflow_id=workflow_id)
        
        result = await workflow_instance.process_pod_error(
            pod_name=request.pod_name,
            namespace=request.namespace,
            error_type=request.error_type,
            thread_id=workflow_id
        )
        
        logger.info("Background workflow completed", 
                   workflow_id=workflow_id, 
                   success=result.get("success", False))
                   
    except Exception as e:
        logger.error("Background workflow failed", 
                    workflow_id=workflow_id, 
                    error=str(e))

# === Persistent Memory API Endpoints (Phase 1) ===

@app.get("/api/v1/memory/strategies")
async def get_strategies(error_type: str = None):
    """Get stored strategies from persistent database"""
    if not strategy_db:
        raise HTTPException(status_code=503, detail="Strategy database not initialized")
    
    try:
        if error_type:
            strategies = strategy_db.get_strategies_for_error(error_type)
            strategy_list = [{
                "id": s.id,
                "error_type": s.error_type,
                "conditions": s.conditions,
                "actions": s.actions,
                "confidence": s.confidence,
                "success_rate": s.success_rate,
                "usage_count": s.usage_count,
                "source": s.source,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat()
            } for s in strategies]
        else:
            # Get statistics for all strategies
            stats = strategy_db.get_strategy_statistics()
            strategy_list = stats.get("top_strategies", [])
        
        return {
            "strategies": strategy_list,
            "count": len(strategy_list),
            "error_type_filter": error_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/memory/episodes")
async def get_episodes(error_type: str = None, limit: int = 10):
    """Get episodic memory entries"""
    if not episodic_memory:
        raise HTTPException(status_code=503, detail="Episodic memory not initialized")
    
    try:
        if error_type:
            episodes = episodic_memory.get_similar_episodes(error_type, {}, limit)
        else:
            # Get all recent episodes when no specific error_type
            episodes = episodic_memory.get_similar_episodes("ImagePullBackOff", {}, limit)
            if not episodes:
                episodes = episodic_memory.get_similar_episodes("CrashLoopBackOff", {}, limit)
            if not episodes:
                # If still no episodes, get from any error type
                with sqlite3.connect(episodic_memory.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM episodes 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (limit,))
                    
                    episodes = []
                    for row in cursor.fetchall():
                        from src.memory.episodic_memory import EpisodicMemory as PersistentEpisodicMemory
                        episode = PersistentEpisodicMemory(
                            id=row[0],
                            pod_name=row[1],
                            namespace=row[2],
                            error_type=row[3],
                            context=json.loads(row[4]),
                            actions_taken=json.loads(row[5]),
                            outcome=json.loads(row[6]),
                            lessons_learned=json.loads(row[7]),
                            confidence_before=row[8],
                            confidence_after=row[9],
                            resolution_time=row[10],
                            timestamp=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
                            reflection_quality=row[12],
                            insights_generated=row[13]
                        )
                        episodes.append(episode)
        
        episode_list = [{
            "id": e.id,
            "pod_name": e.pod_name,
            "namespace": e.namespace,
            "error_type": e.error_type,
            "context": e.context,
            "outcome": e.outcome,
            "lessons_learned": e.lessons_learned,
            "confidence_gain": e.confidence_after - e.confidence_before,
            "resolution_time": e.resolution_time,
            "reflection_quality": e.reflection_quality,
            "insights_generated": e.insights_generated,
            "timestamp": e.timestamp.isoformat()
        } for e in episodes]
        
        return {
            "episodes": episode_list,
            "count": len(episode_list),
            "error_type_filter": error_type,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/memory/performance")
async def get_performance_insights(days: int = 7):
    """Get performance insights and trends"""
    if not performance_tracker:
        raise HTTPException(status_code=503, detail="Performance tracker not initialized")
    
    try:
        insights = performance_tracker.get_performance_insights(days)
        rankings = performance_tracker.get_strategy_ranking()
        
        return {
            "performance_insights": insights,
            "strategy_rankings": rankings[:10],  # Top 10
            "analysis_period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/memory/learning-progression")
async def get_learning_progression(days: int = 30):
    """Get learning progression over time"""
    if not episodic_memory:
        raise HTTPException(status_code=503, detail="Episodic memory not initialized")
    
    try:
        progression = episodic_memory.get_learning_progression(days)
        
        return {
            "learning_progression": progression,
            "analysis_period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get learning progression: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/memory/statistics")
async def get_memory_statistics():
    """Get overall memory system statistics"""
    if not all([strategy_db, episodic_memory, performance_tracker]):
        raise HTTPException(status_code=503, detail="Memory systems not initialized")
    
    try:
        strategy_stats = strategy_db.get_strategy_statistics()
        episode_stats = episodic_memory.get_memory_statistics()
        performance_insights = performance_tracker.get_performance_insights(7)
        
        return {
            "strategy_database": strategy_stats,
            "episodic_memory": episode_stats,
            "performance_summary": performance_insights.get("overall_performance", {}),
            "system_status": "operational",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get memory statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Legacy API Endpoints ===

@app.get("/api/v1/reflexion/strategies")
async def get_reflexion_strategies():
    """Legacy endpoint - redirect to new memory API"""
    return await get_strategies()

@app.get("/api/v1/reflexion/memory/episodic")
async def get_reflexion_episodic_memory():
    """Legacy endpoint - redirect to new memory API"""
    return await get_episodes()

# Error handlers

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": request.url.path}
    )

# NEW: Phase 3.3 - kubectl Command Execution Endpoint
@app.post("/api/v1/executor/generate-commands", response_model=CommandExecutionResponse)
async def generate_kubectl_commands(request: CommandExecutionRequest):
    """
    Generate kubectl commands for pod error fixing
    
    This endpoint uses AI to generate kubectl commands based on the error type
    and real K8s data, then returns the command URL for Go service execution.
    """
    if not ai_command_generator:
        raise HTTPException(status_code=503, detail="AI Command Generator not initialized")
    
    logger.info("Generating kubectl commands", 
                pod_name=request.pod_name, 
                error_type=request.error_type,
                dry_run=request.dry_run)
    
    start_time = datetime.now()
    
    try:
        # Convert real K8s data to the format expected by AI generator
        ai_real_k8s_data = {
            "pod": request.real_k8s_data.pod_spec,
            "events": request.real_k8s_data.events,
            "logs": request.real_k8s_data.logs
        }
        
        # Generate commands using AI
        commands = await ai_command_generator.generate_kubectl_commands(
            error_type=request.error_type,
            pod_name=request.pod_name,
            namespace=request.namespace,
            strategy=request.strategy,
            real_k8s_data=ai_real_k8s_data
        )
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Count total commands
        total_commands = sum(len(cmd_list) for cmd_list in commands.values())
        
        # Prepare Go service URL for command execution
        go_service_url = f"http://localhost:8080/api/v1/execute-commands"
        
        response = CommandExecutionResponse(
            pod_name=request.pod_name,
            namespace=request.namespace,
            error_type=request.error_type,
            commands_generated=total_commands,
            commands_executed=0,  # Will be updated by Go service
            success=True,
            execution_time=execution_time,
            commands=commands,
            go_service_url=go_service_url,
            message=f"Generated {total_commands} kubectl commands for {request.error_type}"
        )
        
        logger.info("kubectl commands generated successfully",
                   pod_name=request.pod_name,
                   commands_count=total_commands,
                   execution_time=execution_time)
        
        return response
        
    except Exception as e:
        logger.error("Failed to generate kubectl commands", error=str(e))
        raise HTTPException(status_code=500, detail=f"Command generation failed: {str(e)}")

# NEW: Phase 3.7 - Execution Feedback for Reflexion Learning
@app.post("/api/v1/reflexion/execution-feedback", response_model=ExecutionFeedbackResponse)
async def process_execution_feedback(request: ExecutionFeedbackRequest):
    """
    Process execution feedback for reflexion learning
    
    This endpoint receives execution results from Go service and updates
    the reflexion system with real-world performance data.
    """
    if not workflow_instance:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    
    logger.info("="*80)
    logger.info("🔄 EXECUTION FEEDBACK PROCESSING")
    logger.info(f"   🆔 Workflow ID: {request.workflow_id}")
    logger.info(f"   📱 Pod: {request.pod_name} (namespace: {request.namespace})")
    logger.info(f"   🚨 Error Type: {request.error_type}")
    logger.info(f"   🎯 Strategy Used: {request.strategy_used.get('id', 'unknown')}")
    logger.info(f"   📊 Execution Status: {request.execution_result.get('status')}")
    logger.info(f"   ✅ Success: {request.execution_result.get('success', False)}")
    logger.info(f"   📋 Commands: {request.execution_result.get('success_count', 0)}/{request.execution_result.get('total_commands', 0)} successful")
    logger.info("="*80)
    
    start_time = datetime.now()
    
    try:
        # Extract execution results
        execution_success = request.execution_result.get("success", False)
        partial_success = request.execution_result.get("partial_success", False)
        success_count = request.execution_result.get("success_count", 0)
        total_commands = request.execution_result.get("total_commands", 0)
        
        # Calculate execution time and success rate
        execution_time = (datetime.now() - start_time).total_seconds()
        success_rate = success_count / total_commands if total_commands > 0 else 0.0
        
        # Update strategy database with real execution results
        strategy_id = request.strategy_used.get("id", "unknown")
        strategy_confidence_updated = False
        
        if strategy_db:
            try:
                strategy_db.update_strategy_performance(
                    strategy_id=strategy_id,
                    success=execution_success or partial_success,
                    execution_time=execution_time,
                    pod_name=request.pod_name,
                    namespace=request.namespace,
                    feedback=f"Real execution: {success_count}/{total_commands} commands succeeded"
                )
                strategy_confidence_updated = True
                logger.info("="*80)
                logger.info("📈 STRATEGY DATABASE PERFORMANCE UPDATE")
                logger.info(f"   🎯 Strategy ID: {strategy_id}")
                logger.info(f"   ✅ Execution Success: {execution_success}")
                logger.info(f"   📈 Success Rate: {success_rate:.2%}")
                logger.info(f"   📋 Commands Success: {success_count}/{total_commands}")
                logger.info(f"   ⏱️  Execution Time: {execution_time:.2f}s")
                logger.info(f"   🧠 Learning Update: APPLIED TO PERSISTENT DATABASE")
                logger.info("="*80)
            except Exception as e:
                logger.error("Failed to update strategy performance", error=str(e))
        
        # Update episodic memory with real execution outcome
        reflexion_updated = False
        if episodic_memory:
            try:
                episode_data = {
                    "workflow_id": request.workflow_id,
                    "pod_name": request.pod_name,
                    "error_type": request.error_type,
                    "strategy_used": request.strategy_used,
                    "execution_result": request.execution_result,
                    "success_rate": success_rate,
                    "lessons_learned": [
                        f"Strategy {strategy_id} achieved {success_rate:.1%} success rate",
                        f"Execution pattern: {success_count}/{total_commands} commands succeeded"
                    ]
                }
                
                from src.memory.episodic_memory import EpisodicMemory
                
                # Generate unique episode ID
                import time
                episode_id = f"execution_feedback_{request.workflow_id}_{int(time.time())}"
                
                episode = EpisodicMemory(
                    id=episode_id,
                    pod_name=request.pod_name,
                    namespace=request.namespace,
                    error_type=request.error_type,
                    context={"workflow_id": request.workflow_id, "timestamp": request.timestamp},
                    actions_taken=[request.strategy_used],  # List format
                    outcome={"success": execution_success, "success_rate": success_rate, "status": request.execution_result.get("status")},
                    lessons_learned=episode_data["lessons_learned"],
                    confidence_before=request.strategy_used.get("confidence", 0.0),
                    confidence_after=request.strategy_used.get("confidence", 0.0) * (success_rate if success_rate > 0 else 0.5),
                    resolution_time=execution_time,
                    timestamp=datetime.now(),
                    reflection_quality=0.8,  # High quality for real execution feedback
                    insights_generated=len(episode_data["lessons_learned"])
                )
                
                episodic_memory.store_episode(episode)
                reflexion_updated = True
                logger.info("="*80)
                logger.info("🧠 EPISODIC MEMORY UPDATE")
                logger.info(f"   🆔 Episode ID: {episode.id}")
                logger.info(f"   📱 Pod: {request.pod_name}")
                logger.info(f"   🎯 Strategy: {strategy_id}")
                logger.info(f"   ✅ Execution Success: {execution_success}")
                logger.info(f"   📈 Success Rate: {success_rate:.2%}")
                logger.info(f"   📚 Lessons Learned: {len(episode.lessons_learned)} insights")
                logger.info(f"   🧠 Memory Update: STORED IN PERSISTENT DATABASE")
                logger.info("="*80)
            except Exception as e:
                logger.error("Failed to update episodic memory", error=str(e))
        
        # Prepare learning summary
        learning_summary = {
            "strategy_id": strategy_id,
            "original_confidence": request.strategy_used.get("confidence", 0.0),
            "execution_success_rate": success_rate,
            "commands_executed": total_commands,
            "commands_succeeded": success_count,
            "learning_outcome": "success" if execution_success else "partial" if partial_success else "failure",
            "reflexion_cycle_completed": reflexion_updated and strategy_confidence_updated
        }
        
        response = ExecutionFeedbackResponse(
            workflow_id=request.workflow_id,
            feedback_processed=True,
            reflexion_updated=reflexion_updated,
            strategy_confidence_updated=strategy_confidence_updated,
            learning_summary=learning_summary,
            message=f"Reflexion learning completed for {request.pod_name} with {success_rate:.1%} success rate"
        )
        
        logger.info("Execution feedback processed successfully",
                   workflow_id=request.workflow_id,
                   reflexion_updated=reflexion_updated,
                   strategy_updated=strategy_confidence_updated,
                   success_rate=success_rate)
        
        return response
        
    except Exception as e:
        logger.error("Failed to process execution feedback", error=str(e))
        raise HTTPException(status_code=500, detail=f"Feedback processing failed: {str(e)}")

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Internal server error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
    )

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )