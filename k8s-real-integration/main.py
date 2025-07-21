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
from fastapi.responses import JSONResponse
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

# LangSmith Integration
from langsmith import traceable

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
        
        # Initialize workflow with kubectl dry-run option (always disabled for real execution)
        kubectl_dry_run = False
        
        workflow_instance = ReflexiveK8sWorkflow(
            openai_api_key=openai_api_key,
            go_service_url="",
            reflection_depth=reflection_depth,
            kubectl_dry_run=kubectl_dry_run
        )
        
        logger.info("⚡ KUBECTL REAL EXECUTION MODE ENABLED - All commands will be executed!")
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
    1. Analyze error with GPT-4
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
@traceable(name="process_pod_error_with_real_data")
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
            "ai_analysis": {
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
        
        # Process through reflexive workflow with limited recursion
        config = {"recursion_limit": 15}  # Reduce recursion limit to prevent infinite loops
        result = await workflow_instance.compiled_workflow.ainvoke(initial_state, config=config)
        
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
    if not strategy_db:
        raise HTTPException(status_code=503, detail="Strategy database not initialized")
    
    try:
        # Get all strategies from SQLite database
        all_strategies = strategy_db.get_all_strategies()
        
        strategies_data = []
        for strategy in all_strategies:
            strategies_data.append({
                "id": strategy.id,
                "type": strategy.error_type,
                "confidence": strategy.confidence,
                "usage_count": strategy.usage_count,
                "success_rate": strategy.success_rate,
                "description": f"{strategy.error_type} strategy (source: {strategy.source})",
                "created_at": strategy.created_at.isoformat(),
                "last_used": strategy.last_used.isoformat() if strategy.last_used else None
            })
        
        return {
            "strategies": strategies_data,
            "total_count": len(strategies_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        return {
            "strategies": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/v1/reflexion/memory/episodic")
async def get_episodic_memory(limit: int = 10):
    """Get episodic memory entries from SQLite database"""
    if not episodic_memory:
        raise HTTPException(status_code=503, detail="Episodic memory not initialized")
    
    try:
        # Get recent episodes from SQLite database
        recent_episodes = episodic_memory.get_recent_episodes(limit=limit)
        
        episodes_data = []
        for episode in recent_episodes:
            episodes_data.append({
                "episode_id": episode.id,
                "context": {
                    "pod_name": episode.pod_name,
                    "namespace": episode.namespace,
                    "error_type": episode.error_type
                },
                "action_taken": episode.actions_taken,
                "outcome": episode.outcome,
                "lessons_learned": episode.lessons_learned,
                "confidence_gain": episode.confidence_after - episode.confidence_before,
                "resolution_time": episode.resolution_time,
                "reflection_quality": episode.reflection_quality,
                "timestamp": episode.timestamp.isoformat()
            })
        
        # Get total statistics
        stats = episodic_memory.get_memory_statistics()
        
        return {
            "episodes": episodes_data,
            "total_episodes": stats.get("total_episodes", 0),
            "memory_utilization": min(1.0, stats.get("total_episodes", 0) / 5000),  # Based on config limit
            "avg_confidence_gain": stats.get("avg_confidence_gain", 0),
            "avg_resolution_time": stats.get("avg_resolution_time", 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get episodic memory: {e}")
        return {
            "episodes": [],
            "total_episodes": 0,
            "memory_utilization": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Configuration endpoints
@app.get("/api/v1/config")
async def get_configuration():
    """Get current service configuration"""
    return {
        "reflection_depth": os.getenv("REFLECTION_DEPTH", "medium"),
        "go_service_url": os.getenv("GO_SERVICE_URL", "http://localhost:8080"),
        "openai_model": "gpt-3.5-turbo",
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

# Memory management endpoints
@app.delete("/api/v1/memory/clear")
async def clear_all_memory():
    """Clear all learned strategies and episodic memory"""
    try:
        cleared_items = {
            "strategy_database": False,
            "episodic_memory": False,
            "performance_tracker": False
        }
        
        # Clear strategy database
        if strategy_db:
            strategy_db.clear_all_strategies()
            cleared_items["strategy_database"] = True
            logger.info("Strategy database cleared")
        
        # Clear episodic memory
        if episodic_memory:
            episodic_memory.clear_all_episodes()
            cleared_items["episodic_memory"] = True
            logger.info("Episodic memory cleared")
        
        # Clear performance tracker
        if performance_tracker:
            performance_tracker.clear_all_metrics()
            cleared_items["performance_tracker"] = True
            logger.info("Performance tracker cleared")
        
        return {
            "message": "Memory cleared successfully",
            "cleared_components": cleared_items,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to clear memory", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear memory: {str(e)}")

@app.delete("/api/v1/memory/strategies")
async def clear_strategy_memory():
    """Clear only learned strategies"""
    try:
        if not strategy_db:
            raise HTTPException(status_code=503, detail="Strategy database not initialized")
        
        strategy_db.clear_all_strategies()
        logger.info("Strategy database cleared")
        
        return {
            "message": "Strategy memory cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to clear strategy memory", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear strategy memory: {str(e)}")

@app.delete("/api/v1/memory/episodes")
async def clear_episodic_memory():
    """Clear only episodic memory"""
    try:
        if not episodic_memory:
            raise HTTPException(status_code=503, detail="Episodic memory not initialized")
        
        episodic_memory.clear_all_episodes()
        logger.info("Episodic memory cleared")
        
        return {
            "message": "Episodic memory cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to clear episodic memory", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear episodic memory: {str(e)}")

@app.post("/api/v1/memory/reset-nuclear") 
async def reset_nuclear_option():
    """NUCLEAR OPTION: Delete database files and reinitialize everything"""
    import os
    global strategy_db, episodic_memory, performance_tracker
    
    try:
        logger.warning("🔥 NUCLEAR RESET INITIATED - Deleting all database files!")
        
        # Database file paths
        db_files = [
            "reflexion_strategies.db",
            "reflexion_episodes.db", 
            "reflexion_performance.db",
            "reflexion_memory.json"
        ]
        
        deleted_files = 0
        for db_file in db_files:
            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
                    deleted_files += 1
                    logger.info(f"🗑️ Deleted: {db_file}")
            except Exception as e:
                logger.error(f"Failed to delete {db_file}: {e}")
        
        # Reinitialize all systems
        try:
            strategy_db = StrategyDatabase()
            episodic_memory = EpisodicMemoryManager()
            performance_tracker = PerformanceTracker()
            logger.info("✅ All memory systems reinitialized with fresh databases")
        except Exception as e:
            logger.error("Failed to reinitialize systems", error=str(e))
            
        return {
            "success": True,
            "message": "🔥 NUCLEAR RESET COMPLETE - All databases deleted and recreated",
            "files_deleted": deleted_files,
            "timestamp": datetime.now().isoformat(),
            "warning": "ALL DATA PERMANENTLY DESTROYED. System is completely fresh."
        }
        
    except Exception as e:
        logger.error("Nuclear reset failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Nuclear reset failed: {str(e)}")

@app.post("/api/v1/memory/reset-complete")
async def reset_complete_system():
    """Complete system reset - Fresh start with all AI learning data cleared"""
    global strategy_db, episodic_memory, performance_tracker
    
    try:
        logger.warning("🚨 COMPLETE SYSTEM RESET INITIATED - All AI learning will be permanently deleted")
        
        reset_summary = {
            "strategy_database": {"success": False, "items_cleared": 0, "error": None},
            "episodic_memory": {"success": False, "items_cleared": 0, "error": None},
            "performance_tracker": {"success": False, "items_cleared": 0, "error": None}
        }
        
        total_cleared = 0
        
        # 1. Reset Strategy Database
        try:
            if strategy_db:
                stats = strategy_db.get_strategy_statistics()
                strategies_count = stats.get("total_strategies", 0)
                
                strategy_db.clear_all_strategies()
                reset_summary["strategy_database"] = {
                    "success": True,
                    "items_cleared": strategies_count,
                    "message": f"Cleared {strategies_count} learned strategies"
                }
                total_cleared += strategies_count
                logger.info("✅ Strategy database reset", strategies_cleared=strategies_count)
            else:
                reset_summary["strategy_database"]["error"] = "Strategy database not initialized"
        except Exception as e:
            reset_summary["strategy_database"]["error"] = str(e)
            logger.error("❌ Strategy database reset failed", error=str(e))
        
        # 2. Reset Episodic Memory
        try:
            if episodic_memory:
                stats = episodic_memory.get_memory_statistics()
                episodes_count = stats.get("total_episodes", 0)
                
                episodic_memory.clear_all_episodes()
                reset_summary["episodic_memory"] = {
                    "success": True,
                    "items_cleared": episodes_count,
                    "message": f"Cleared {episodes_count} memory episodes"
                }
                total_cleared += episodes_count
                logger.info("✅ Episodic memory reset", episodes_cleared=episodes_count)
            else:
                reset_summary["episodic_memory"]["error"] = "Episodic memory not initialized"
        except Exception as e:
            reset_summary["episodic_memory"]["error"] = str(e)
            logger.error("❌ Episodic memory reset failed", error=str(e))
        
        # 3. Reset Performance Tracker
        try:
            if performance_tracker:
                performance_tracker.clear_all_metrics()
                reset_summary["performance_tracker"] = {
                    "success": True,
                    "items_cleared": "all_metrics",
                    "message": "Cleared all performance metrics and history"
                }
                logger.info("✅ Performance tracker reset")
            else:
                reset_summary["performance_tracker"]["error"] = "Performance tracker not initialized"
        except Exception as e:
            reset_summary["performance_tracker"]["error"] = str(e)
            logger.error("❌ Performance tracker reset failed", error=str(e))
        
        # 4. Force refresh memory systems (clear cached data)
        try:
            logger.info("🔄 Reinitializing memory systems to clear cached data...")
            
            # Reinitialize all memory systems to clear any cached statistics
            if strategy_db:
                strategy_db = StrategyDatabase()
                logger.info("Strategy database reinitialized")
                
            if episodic_memory:
                episodic_memory = EpisodicMemoryManager()
                logger.info("Episodic memory reinitialized")
                
            if performance_tracker:
                performance_tracker = PerformanceTracker()
                logger.info("Performance tracker reinitialized")
                
        except Exception as e:
            logger.warning("⚠️ Memory system reinitialization failed", error=str(e))

        # Calculate success rate
        successful_resets = sum(1 for system in reset_summary.values() if system.get("success", False))
        total_systems = len(reset_summary)
        
        overall_success = successful_resets == total_systems
        
        # Final status
        if overall_success:
            logger.warning("🎯 COMPLETE SYSTEM RESET SUCCESSFUL - AI will start fresh")
            status_message = f"✅ Successfully reset all {total_systems} memory systems"
        else:
            logger.error(f"⚠️ PARTIAL RESET - {successful_resets}/{total_systems} systems reset successfully")
            status_message = f"⚠️ Partial reset: {successful_resets}/{total_systems} systems"
        
        return {
            "success": overall_success,
            "message": status_message,
            "total_items_cleared": total_cleared,
            "systems_reset": successful_resets,
            "total_systems": total_systems,
            "reset_details": reset_summary,
            "timestamp": datetime.now().isoformat(),
            "warning": "All AI learning data has been permanently deleted. The system will start learning from scratch."
        }
        
    except Exception as e:
        logger.error("❌ COMPLETE SYSTEM RESET FAILED", error=str(e))
        raise HTTPException(status_code=500, detail=f"System reset failed: {str(e)}")

# Debug and development endpoints
@app.post("/api/v1/debug/test-gpt4-direct")
async def test_gpt4_direct(request: dict):
    """Test GPT-4 directly with a custom prompt"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
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
            "model": "gpt-3.5-turbo",
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
        "ai_analysis": {"confidence": 0.9, "analysis": "Mock analysis"},
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
        "ai_analysis": {"confidence": 0.9, "analysis": "Mock analysis"},
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

# DISABLED: kubectl Command Generation - Using YAML mode only
# @app.post("/api/v1/executor/generate-commands", response_model=CommandExecutionResponse)
async def generate_kubectl_commands_disabled(request: CommandExecutionRequest):
    """
    DISABLED: kubectl Command Generation - Using YAML mode only
    This endpoint is disabled to force YAML-only mode for better resource control
    """
    logger.warning("kubectl command generation disabled - system uses YAML mode only")
    raise HTTPException(
        status_code=503, 
        detail="kubectl command generation disabled - system uses YAML manifest mode only"
    )

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
    
    # Log executed commands if available
    executed_commands = request.execution_result.get('executed_commands', [])
    if executed_commands:
        logger.info("🔧 EXECUTED COMMANDS:")
        for i, cmd_info in enumerate(executed_commands, 1):
            cmd = cmd_info.get('command', 'Unknown command')
            status = '✅' if cmd_info.get('success', False) else '❌'
            duration = cmd_info.get('duration', 'N/A')
            logger.info(f"   {i}. {status} {cmd} (Duration: {duration})")
    
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

# Test Management Endpoints
class TestTriggerRequest(BaseModel):
    test_type: str = Field(..., description="Type of test: imagepull, crashloop, or oom")
    pod_name: Optional[str] = Field(None, description="Custom pod name (auto-generated if not provided)")
    namespace: str = Field(default="default", description="Kubernetes namespace")

class TestTriggerResponse(BaseModel):
    test_id: str
    test_type: str
    pod_name: str
    namespace: str
    status: str
    message: str
    yaml_applied: bool
    timestamp: str

@app.post("/api/v1/tests/trigger", response_model=TestTriggerResponse)
async def trigger_test(request: TestTriggerRequest):
    """Trigger a specific test scenario by deploying a test pod"""
    import subprocess
    import uuid
    from pathlib import Path
    
    try:
        # Generate unique test ID and pod name
        test_id = str(uuid.uuid4())[:8]
        
        # Map test types to YAML files
        yaml_files = {
            "imagepull": "test-imagepull-pod.yaml",
            "crashloop": "test-crashloop-pod.yaml", 
            "oom": "test-memory-limit.yaml"
        }
        
        if request.test_type not in yaml_files:
            raise HTTPException(status_code=400, detail=f"Invalid test type. Must be one of: {list(yaml_files.keys())}")
        
        yaml_file = yaml_files[request.test_type]
        yaml_path = Path(__file__).parent / yaml_file
        
        if not yaml_path.exists():
            raise HTTPException(status_code=404, detail=f"Test YAML file not found: {yaml_file}")
        
        # Generate pod name
        pod_name = request.pod_name or f"test-{request.test_type}-{test_id}"
        
        logger.info(f"🧪 Triggering {request.test_type} test", 
                   test_id=test_id, pod_name=pod_name, yaml_file=yaml_file)
        
        # Apply the YAML file using kubectl
        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", str(yaml_path), "-n", request.namespace],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                yaml_applied = True
                status = "deployed"
                message = f"Test pod {pod_name} deployed successfully"
                logger.info("✅ Test pod deployed", pod_name=pod_name, output=result.stdout.strip())
            else:
                yaml_applied = False
                status = "failed"
                message = f"Failed to deploy test pod: {result.stderr}"
                logger.error("❌ Test pod deployment failed", error=result.stderr)
                
        except subprocess.TimeoutExpired:
            yaml_applied = False
            status = "timeout" 
            message = "kubectl command timed out"
            logger.error("⏰ kubectl command timeout")
            
        except FileNotFoundError:
            yaml_applied = False
            status = "kubectl_not_found"
            message = "kubectl command not found. Please install kubectl."
            logger.error("❌ kubectl not found")
        
        return TestTriggerResponse(
            test_id=test_id,
            test_type=request.test_type,
            pod_name=pod_name,
            namespace=request.namespace,
            status=status,
            message=message,
            yaml_applied=yaml_applied,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error("Test trigger failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Test trigger failed: {str(e)}")

@app.get("/api/v1/tests/status/{test_type}")
async def get_test_status(test_type: str, namespace: str = "default"):
    """Get status of test pods for a specific test type"""
    import subprocess
    
    try:
        # Get pods with test labels
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-l", f"app={test_type}-test", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            import json as json_lib
            pods_data = json_lib.loads(result.stdout)
            
            pod_statuses = []
            for pod in pods_data.get("items", []):
                pod_status = {
                    "name": pod["metadata"]["name"],
                    "phase": pod["status"].get("phase", "Unknown"),
                    "created": pod["metadata"]["creationTimestamp"],
                    "ready": "0/0",
                    "restarts": 0
                }
                
                # Get container statuses
                if "containerStatuses" in pod["status"]:
                    for container in pod["status"]["containerStatuses"]:
                        pod_status["restarts"] += container.get("restartCount", 0)
                        if container.get("ready", False):
                            pod_status["ready"] = "1/1"
                
                pod_statuses.append(pod_status)
            
            return {
                "test_type": test_type,
                "namespace": namespace, 
                "pod_count": len(pod_statuses),
                "pods": pod_statuses,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "test_type": test_type,
                "namespace": namespace,
                "pod_count": 0,
                "pods": [],
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error("Failed to get test status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get test status: {str(e)}")

@app.delete("/api/v1/tests/cleanup/{test_type}")
async def cleanup_test_pods(test_type: str, namespace: str = "default"):
    """Clean up test pods for a specific test type"""
    import subprocess
    
    try:
        # Delete pods with test labels
        result = subprocess.run(
            ["kubectl", "delete", "pods", "-n", namespace, "-l", f"app={test_type}-test", "--force", "--grace-period=0"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        logger.info(f"🧹 Cleaning up {test_type} test pods", namespace=namespace)
        
        return {
            "test_type": test_type,
            "namespace": namespace,
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to cleanup test pods", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cleanup test pods: {str(e)}")

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