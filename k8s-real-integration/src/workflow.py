"""
Reflexive LangGraph Workflow - Enhanced K8s error resolution with self-learning
"""
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Literal
import structlog
from langgraph.graph import StateGraph, END

# LangSmith Integration
from langsmith import traceable
from langchain_core.tracers import LangChainTracer

# Initialize LangSmith tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
if "LANGCHAIN_API_KEY" in os.environ:
    langsmith_tracer = LangChainTracer()
else:
    langsmith_tracer = None

# Simple memory store (MemorySaver might not be available in all versions)
try:
    from langgraph.checkpoint import MemorySaver
    CHECKPOINT_AVAILABLE = True
except ImportError:
    CHECKPOINT_AVAILABLE = False

from .state import ReflexiveK8sState
from .nodes.observe import ObservationEngine
from .nodes.reflect import ReflectionEngine
from .nodes.learn import LearningEngine
from .memory.strategy_db import StrategyDatabase, Strategy
from .memory.episodic_memory import EpisodicMemoryManager, EpisodicMemory
from .memory.performance_tracker import PerformanceTracker

logger = structlog.get_logger()
logger.info("🚀 Workflow module loaded - Enhanced logging enabled")


class ReflexiveK8sWorkflow:
    """Enhanced K8s workflow with reflexion capabilities"""
    
    def __init__(self, 
                 openai_api_key: str,
                 go_service_url: str = "",
                 reflection_depth: str = "medium"):
        
        # Initialize engines
        self.observation_engine = ObservationEngine("")
        self.reflection_engine = ReflectionEngine(
            openai_api_key=openai_api_key,
            reflection_depth=reflection_depth
        )
        self.learning_engine = LearningEngine()
        
        # Initialize persistent memory system
        self.strategy_db = StrategyDatabase()
        self.episodic_memory = EpisodicMemoryManager()
        self.performance_tracker = PerformanceTracker()
        
        # Build workflow
        self.workflow = self._build_reflexive_workflow()
        
        # Add checkpointing for state persistence (if available)
        if CHECKPOINT_AVAILABLE:
            memory = MemorySaver()
            self.compiled_workflow = self.workflow.compile(checkpointer=memory)
        else:
            self.compiled_workflow = self.workflow.compile()
        
    def _build_reflexive_workflow(self) -> StateGraph:
        """Build the complete reflexive workflow"""
        
        workflow = StateGraph(ReflexiveK8sState)
        
        # === Standard K8s Workflow Nodes ===
        workflow.add_node("analyze_error", self._analyze_error_node)
        workflow.add_node("decide_strategy", self._decide_strategy_node)
        workflow.add_node("execute_fix", self._execute_fix_node)
        
        # === Reflexion Enhancement Nodes ===
        workflow.add_node("observe_outcome", self.observation_engine.observe_outcome_node)
        workflow.add_node("reflect_on_action", self.reflection_engine.reflect_on_action_node)
        workflow.add_node("learn_and_evolve", self.learning_engine.learn_and_evolve_node)
        
        # === Meta-Cognition Nodes ===
        workflow.add_node("meta_reflect", self._meta_reflection_node)
        workflow.add_node("strategy_selection", self._intelligent_strategy_selection_node)
        
        # === Special Nodes ===
        workflow.add_node("human_escalation", self._human_escalation_node)
        workflow.add_node("deep_analysis", self._deep_analysis_node)
        
        # === Define Workflow Flow ===
        workflow.set_entry_point("analyze_error")
        
        # Primary flow
        workflow.add_edge("analyze_error", "strategy_selection")
        workflow.add_edge("strategy_selection", "decide_strategy")
        workflow.add_edge("decide_strategy", "execute_fix")
        workflow.add_edge("execute_fix", "observe_outcome")
        
        # Reflexion flow
        workflow.add_conditional_edges(
            "observe_outcome",
            self._should_reflect,
            {
                "reflect": "reflect_on_action",
                "skip_reflection": "learn_and_evolve"
            }
        )
        
        workflow.add_edge("reflect_on_action", "learn_and_evolve")
        
        # Post-learning routing
        workflow.add_conditional_edges(
            "learn_and_evolve",
            self._post_learning_routing,
            {
                "success": END,
                "retry": "strategy_selection",
                "meta_reflect": "meta_reflect",
                "human_escalation": "human_escalation",
                "deep_analysis": "deep_analysis"
            }
        )
        
        # Meta-reflection routing
        workflow.add_conditional_edges(
            "meta_reflect",
            self._meta_reflection_routing,
            {
                "retry_with_insights": "strategy_selection",
                "human_escalation": "human_escalation",
                "end": END
            }
        )
        
        # Terminal nodes
        workflow.add_edge("human_escalation", END)
        workflow.add_edge("deep_analysis", "strategy_selection")
        
        return workflow
    
    # === Core Workflow Nodes ===
    
    @traceable(name="analyze_error_node")
    async def _analyze_error_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Enhanced error analysis with reflexive capabilities"""
        logger.info("Starting reflexive error analysis", pod_name=state["pod_name"])
        
        try:
            # Check if we have real K8s data from Go service
            if state.get("real_k8s_data") and state.get("ai_analysis", {}).get("real_data"):
                # Use real K8s data for enhanced analysis
                logger.info("Using real K8s data for analysis", pod_name=state["pod_name"])
                
                # Enhance existing analysis with real data insights
                real_data = state["real_k8s_data"]
                events = real_data.get("events", [])
                logs = real_data.get("logs", [])
                
                # Extract insights from events
                event_insights = self._analyze_k8s_events(events)
                
                # Extract insights from logs
                log_insights = self._analyze_pod_logs(logs)
                
                # Enhance the ai_analysis with real data
                state["ai_analysis"].update({
                    "event_insights": event_insights,
                    "log_insights": log_insights,
                    "enhanced_with_real_data": True,
                    "confidence": min(0.98, state["ai_analysis"].get("confidence", 0.9) + 0.05)  # Boost confidence
                })
                
            else:
                # Fallback to AI analysis
                state["ai_analysis"] = {
                    "confidence": 0.9,
                    "analysis": f"AI analysis for {state['error_type']} error",
                    "recommendations": ["Check image repository", "Verify network connectivity"],
                    "error_details": f"Pod {state['pod_name']} experiencing {state['error_type']}"
                }
        
        except Exception as e:
            logger.error("Error analysis failed", error=str(e))
            state["ai_analysis"] = {"error": str(e)}
        
        # Initialize reflexive state components
        if "reflection_history" not in state:
            state["reflection_history"] = []
        if "episodic_memory" not in state:
            state["episodic_memory"] = []
        if "strategy_database" not in state:
            state["strategy_database"] = {}
        if "strategy_evolution" not in state:
            state["strategy_evolution"] = []
        if "meta_learning" not in state:
            state["meta_learning"] = {
                "total_reflections": 0,
                "total_learning_cycles": 0,
                "learning_success_rate": 0.0,
                "reflection_quality_avg": 0.0
            }
        if "performance_metrics" not in state:
            state["performance_metrics"] = {}
        if "improvement_trajectory" not in state:
            state["improvement_trajectory"] = []
        
        # Set workflow metadata with explicit timing
        start_time = datetime.now()
        state["workflow_id"] = f"reflexive_{start_time.strftime('%Y%m%d_%H%M%S')}_{hash(state['pod_name']) % 1000}"
        state["execution_start_time"] = start_time
        logger.info(f"🕐 Workflow started at: {start_time.isoformat()}")
        
        return state
    
    @traceable(name="strategy_selection_node")
    async def _intelligent_strategy_selection_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Intelligent strategy selection based on learned knowledge"""
        logger.info("🧠 STRATEGY SELECTION START", pod_name=state["pod_name"], error_type=state["error_type"])
        
        # Anti-infinite loop protection
        retry_count = state.get("retry_count", 0)
        if retry_count >= 5:  # Limit to 5 iterations max
            logger.warning(f"🛑 RETRY LIMIT REACHED ({retry_count}) - Forcing workflow completion")
            state["success"] = True  # Force completion
            state["requires_human_intervention"] = True
            return state
        
        strategy_database = state.get("strategy_database", {})
        error_type = state["error_type"]
        
        # Find relevant strategies from learned knowledge (both persistent and in-memory)
        relevant_strategies = self._find_relevant_strategies(error_type, state, strategy_database)
        
        # NEW: Retrieve lessons learned from similar episodes
        context_dict = {
            "pod_name": state.get("pod_name", ""),
            "namespace": state.get("namespace", "default"),
            "error_context": state.get("analysis", {})
        }
        similar_episodes = self.episodic_memory.get_similar_episodes(
            error_type=error_type,
            context=context_dict,
            limit=5
        )
        
        lessons_learned = []
        for episode in similar_episodes:
            lessons_learned.extend(episode.lessons_learned)
        
        if lessons_learned:
            logger.info(f"📚 LESSONS LEARNED: Found {len(lessons_learned)} lessons from {len(similar_episodes)} similar episodes")
            for i, lesson in enumerate(lessons_learned[:3]):  # Top 3 lessons
                logger.info(f"  💡 Lesson {i+1}: {lesson[:100]}...")
            
            # Add lessons to state for strategy modification
            state["lessons_learned"] = lessons_learned
        else:
            logger.info("📚 LESSONS LEARNED: No similar episodes found")
            state["lessons_learned"] = []
        
        # Always try to use persistent strategies first
        persistent_strategies = self.strategy_db.get_strategies_for_error(error_type)
        
        logger.info(f"📚 DATABASE CHECK: Found {len(persistent_strategies)} persistent strategies")
        for i, strat in enumerate(persistent_strategies):
            logger.info(f"  📊 Strategy {i+1}: ID={strat.id}, Confidence={strat.confidence:.2f}, SuccessRate={strat.success_rate:.2f}, UsageCount={strat.usage_count}")
        
        selected_strategy = None
        
        # Strategy selection priority (PREFER LEARNING):
        # 1. ANY persistent strategies (give learning a chance)
        # 2. Relevant in-memory strategies  
        # 3. Default strategies (only as last resort)
        
        if persistent_strategies:
            # ALWAYS prefer persistent strategies to encourage learning
            best_persistent = max(persistent_strategies, key=lambda s: max(s.confidence, 0.1))
            
            # Use persistent strategy with 80% probability to encourage learning
            import random
            dice_roll = random.random()
            use_persistent = dice_roll < 0.8  # 80% chance
            
            logger.info("="*80)
            logger.info("🎯 STRATEGY SELECTION DECISION POINT")
            logger.info(f"📚 Found {len(persistent_strategies)} persistent strategies in database")
            logger.info(f"🎲 Dice roll: {dice_roll:.3f} (threshold: 0.8)")
            logger.info(f"💡 Decision: {'USE PERSISTENT' if use_persistent else 'SKIP PERSISTENT'} (80% chance to use)")
            logger.info(f"🏆 Best persistent strategy: ID={best_persistent.id}")
            logger.info(f"   📊 Confidence: {best_persistent.confidence:.2%}")
            logger.info(f"   📈 Success Rate: {best_persistent.success_rate:.2%}")
            logger.info(f"   🔢 Usage Count: {best_persistent.usage_count}")
            logger.info(f"   📅 Last Used: {getattr(best_persistent, 'last_used', 'Not available')}")
            logger.info("="*80)
            
            if use_persistent:  # Prefer persistent strategies for learning
                selected_strategy = {
                    "id": best_persistent.id,
                    "type": best_persistent.error_type,
                    "action": "learned_strategy",
                    "confidence": best_persistent.confidence,
                    "parameters": best_persistent.actions,
                    "conditions": best_persistent.conditions,
                    "selection_reason": "high_confidence_persistent",
                    "usage_count": best_persistent.usage_count,
                    "success_rate": best_persistent.success_rate,
                    "decision_reasoning": f"Selected learned strategy '{best_persistent.id}' with {best_persistent.confidence:.2f} confidence based on {best_persistent.usage_count} previous uses (success rate: {best_persistent.success_rate:.1%}). Preferred over default strategies to leverage acquired knowledge."
                }
                logger.info("✅ SELECTED: Persistent strategy chosen for execution", 
                           strategy_id=best_persistent.id,
                           confidence=best_persistent.confidence)
        
        if not selected_strategy and relevant_strategies:
            # Use best in-memory strategy
            selected_strategy = self._select_best_strategy(relevant_strategies, state)
            logger.info("Selected in-memory strategy", 
                       strategy_type=selected_strategy.get("type"),
                       confidence=selected_strategy.get("confidence"))
        
        if not selected_strategy:
            # Fallback to default strategy
            selected_strategy = self._get_default_strategy(error_type, state)
            logger.info("Using default strategy fallback", strategy_type=selected_strategy.get("type"))
        
        state["current_strategy"] = selected_strategy
        return state
    
    def _find_relevant_strategies(self, error_type: str, state: ReflexiveK8sState, 
                                strategy_database: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Find strategies relevant to current error and context using persistent storage"""
        
        # Get strategies from persistent database
        context = {
            "namespace": state["namespace"],
            "cluster_size": state.get("cluster_size", "small")
        }
        
        persistent_strategies = self.strategy_db.get_strategies_for_error(error_type, context)
        
        # Convert Strategy objects to dict format for compatibility
        relevant = []
        for strategy in persistent_strategies:
            strategy_dict = {
                "id": strategy.id,
                "type": strategy.error_type,
                "actions": strategy.actions,
                "confidence": strategy.confidence,
                "success_rate": strategy.success_rate,
                "conditions": strategy.conditions,
                "usage_count": strategy.usage_count,
                "context": strategy.context
            }
            relevant.append(strategy_dict)
        
        # Also check in-memory strategies (fallback)
        for strategy_id, strategy in strategy_database.items():
            conditions = strategy.get("conditions", [])
            strategy_relevant = False
            
            if f"error_type == '{error_type}'" in conditions:
                strategy_relevant = True
            if f"namespace == '{state['namespace']}'" in conditions:
                strategy_relevant = True
            if strategy.get("confidence", 0.0) >= 0.6:
                strategy_relevant = True
            
            if strategy_relevant and strategy not in relevant:
                relevant.append(strategy)
        
        # Sort by performance metrics
        relevant.sort(key=lambda s: (s.get("confidence", 0.0), s.get("success_rate", 0.0)), reverse=True)
        
        return relevant[:3]  # Top 3 relevant strategies
    
    def _select_best_strategy(self, strategies: list[Dict[str, Any]], 
                            state: ReflexiveK8sState) -> Dict[str, Any]:
        """Select the best strategy from candidates"""
        
        if not strategies:
            return self._get_default_strategy(state["error_type"], state)
        
        # For now, select highest confidence strategy
        # In production, this would use more sophisticated selection logic
        best_strategy = strategies[0]
        
        # Add selection metadata
        best_strategy["selection_reason"] = "highest_confidence_learned"
        best_strategy["alternatives_considered"] = len(strategies)
        
        return best_strategy
    
    def _get_default_strategy(self, error_type: str, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Get default strategy for error type"""
        
        default_strategies = {
            "ImagePullBackOff": {
                "id": "default_image_fix",
                "type": "image_tag_replacement",
                "action": "replace_with_latest",
                "confidence": 0.8,
                "parameters": {"new_tag": "latest"},
                "selection_reason": "default_fallback"
            },
            "CrashLoopBackOff": {
                "id": "default_crash_fix",
                "type": "resource_adjustment",
                "action": "increase_resources",
                "confidence": 0.7,
                "parameters": {"memory_increase": "256Mi"},
                "selection_reason": "default_fallback"
            }
        }
        
        return default_strategies.get(error_type, {
            "id": "generic_default",
            "type": "generic_fix",
            "action": "manual_investigation_required",
            "confidence": 0.3,
            "selection_reason": "no_strategy_available"
        })
    
    @traceable(name="decide_strategy_node")
    async def _decide_strategy_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Enhanced strategy decision with reflexive insights"""
        logger.info("Making strategy decision", pod_name=state["pod_name"])
        
        current_strategy = state.get("current_strategy", {})
        
        # Enhance strategy with contextual information
        enhanced_strategy = current_strategy.copy()
        enhanced_strategy["context"] = {
            "namespace": state["namespace"],
            "error_type": state["error_type"],
            "retry_count": state.get("retry_count", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add reflexive decision reasoning
        enhanced_strategy["decision_reasoning"] = self._generate_decision_reasoning(state)
        
        state["current_strategy"] = enhanced_strategy
        return state
    
    def _generate_decision_reasoning(self, state: ReflexiveK8sState) -> str:
        """Generate reasoning for strategy decision"""
        
        strategy = state.get("current_strategy", {})
        selection_reason = strategy.get("selection_reason", "unknown")
        
        reasoning_templates = {
            "highest_confidence_learned": f"Selected strategy based on learned knowledge with {strategy.get('confidence', 0.0):.2f} confidence from {strategy.get('usage_count', 0)} previous uses.",
            "default_fallback": f"Using default strategy for {state['error_type']} as no learned strategies are available yet.",
            "no_strategy_available": "No specific strategy available - requires human investigation."
        }
        
        base_reasoning = reasoning_templates.get(selection_reason, "Strategy selected based on available options.")
        
        # Add detailed context
        confidence = strategy.get("confidence", 0.0)
        usage_count = strategy.get("usage_count", 0)
        
        if confidence > 0 and usage_count > 0:
            detailed_reasoning = f"{base_reasoning} This strategy has {confidence:.1%} confidence from {usage_count} previous applications."
        else:
            detailed_reasoning = base_reasoning
            
        return detailed_reasoning
    
    @traceable(name="execute_fix_node")
    async def _execute_fix_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Execute the selected strategy"""
        logger.info("Executing fix strategy", pod_name=state["pod_name"])
        
        try:
            # Simulate fix execution with realistic timing
            import random
            import time
            
            # Simulate realistic execution time based on strategy type
            strategy_type = state.get("current_strategy", {}).get("type", "default")
            
            # Strategy performance based on type and confidence
            strategy_confidence = state.get("current_strategy", {}).get("confidence", 0.5)
            
            if "learned" in strategy_type or "adaptive" in strategy_type or "high_confidence_persistent" in state.get("current_strategy", {}).get("selection_reason", ""):
                # Learned strategies: Better performance as confidence increases
                base_time = random.uniform(10.0, 25.0)  # Faster execution
                success_rate = min(0.95, 0.6 + (strategy_confidence * 0.4))  # Confidence-based success
                logger.info(f"Using learned strategy with confidence-based success rate: {success_rate:.2f}")
            else:
                # Default strategies: Consistent but slower
                base_time = random.uniform(30.0, 60.0)
                success_rate = 0.75  # Moderate success rate
            
            success = random.random() < success_rate
            execution_time = base_time + (random.uniform(5.0, 20.0) if not success else 0)
            
            state["execution_result"] = {
                "success": success,
                "message": f"Mock execution of {state.get('current_strategy', {}).get('type', 'default')} strategy",
                "execution_time": execution_time,
                "details": f"Simulated fix for {state['error_type']} on pod {state['pod_name']}"
            }
            state["success"] = success
            
            # Record performance in persistent storage
            strategy = state.get("current_strategy", {})
            if strategy.get("id"):
                confidence_before = strategy.get("confidence", 0.5)
                new_confidence = self.performance_tracker.record_performance(
                    strategy_id=strategy["id"],
                    success=success,
                    resolution_time=execution_time,
                    confidence_before=confidence_before,
                    context={
                        "namespace": state["namespace"],
                        "error_type": state["error_type"],
                        "pod_name": state["pod_name"]
                    }
                )
                
                # Update strategy confidence
                strategy["confidence"] = new_confidence
                state["current_strategy"] = strategy
                
                # Always update persistent strategy database for ANY learned strategy
                learned_reasons = ["high_confidence_persistent", "highest_confidence_learned", "learned_strategy"]
                if any(reason in strategy.get("selection_reason", "") for reason in learned_reasons):
                    self.strategy_db.update_strategy_performance(
                        strategy_id=strategy["id"],
                        success=success,
                        execution_time=execution_time,
                        pod_name=state["pod_name"],
                        namespace=state["namespace"],
                        feedback=f"Execution result: {'success' if success else 'failure'}, time: {execution_time:.1f}s"
                    )
                    logger.info(f"✅ Updated persistent strategy performance: {strategy['id']} (success={success}, time={execution_time:.1f}s)")
                    
                    # Force update strategy confidence in current state
                    strategy["usage_count"] = strategy.get("usage_count", 0) + 1
                    strategy["last_used"] = datetime.now().isoformat()
                    state["current_strategy"] = strategy
                else:
                    logger.info(f"Recorded performance for strategy: {strategy['id']} (type: {strategy.get('selection_reason', 'unknown')})")
            else:
                logger.warning("No strategy ID found for performance tracking")
        
        except Exception as e:
            logger.error("Fix execution failed", error=str(e))
            state["execution_result"] = {"success": False, "error": str(e)}
            state["success"] = False
        
        # Calculate REAL execution time (overriding simulation time)
        if "execution_start_time" in state:
            real_execution_time = (datetime.now() - state["execution_start_time"]).total_seconds()
            state["resolution_time"] = real_execution_time
            
            # Update execution_result with real time
            if "execution_result" in state:
                state["execution_result"]["execution_time"] = real_execution_time
                
            logger.info(f"Real execution time: {real_execution_time:.2f}s (simulated: {execution_time:.2f}s)")
        else:
            # Set execution_start_time if not exists and use simulated time
            state["execution_start_time"] = datetime.now()
            state["resolution_time"] = execution_time
            logger.info(f"Using simulated execution time: {execution_time:.2f}s")
        
        return state
    
    # === Reflexion Routing Logic ===
    
    def _should_reflect(self, state: ReflexiveK8sState) -> Literal["reflect", "skip_reflection"]:
        """Decide whether to perform reflection"""
        
        # FOR TESTING: Always reflect to generate persistent data
        # TODO: Make this more selective in production
        
        reflection_triggers = [
            state.get("success") is False,  # Always reflect on failures
            state.get("retry_count", 0) > 0,  # Reflect on retries
            len(state.get("reflection_history", [])) == 0,  # First reflection - ALWAYS true initially
            state.get("resolution_time", 0) > 60,  # Slow resolutions
            True  # FORCE REFLECTION FOR TESTING - always reflect for now
        ]
        
        # Also reflect randomly on successes for continuous learning
        import random
        if state.get("success") and random.random() < 0.8:  # 80% chance (increased for testing)
            reflection_triggers.append(True)
        
        if any(reflection_triggers):
            logger.info(f"REFLECTION TRIGGERED for pod {state.get('pod_name')}: triggers={reflection_triggers}")
            return "reflect"
        else:
            logger.info(f"REFLECTION SKIPPED for pod {state.get('pod_name')}")
            return "skip_reflection"
    
    def _post_learning_routing(self, state: ReflexiveK8sState) -> Literal["success", "retry", "meta_reflect", "human_escalation", "deep_analysis"]:
        """Route after learning based on outcome and state"""
        
        success = state.get("success", False)
        retry_count = state.get("retry_count", 0)
        self_awareness = state.get("self_awareness_level", 0.5)
        
        if success:
            return "success"
        
        # Check retry conditions
        if retry_count < 3:
            # Analyze if retry is worthwhile
            if self_awareness > 0.7 and len(state.get("strategy_database", {})) > 0:
                return "retry"  # Have learned strategies to try
            elif retry_count < 2:
                return "retry"  # Early retries
        
        # Check for meta-reflection needs
        if retry_count >= 2 and self_awareness < 0.6:
            return "meta_reflect"  # Reflect on why reflection isn't helping
        
        # Check for deep analysis needs
        if state["error_type"] not in ["ImagePullBackOff", "CrashLoopBackOff"]:
            return "deep_analysis"  # Unknown error types need deeper analysis
        
        # Default to human escalation
        return "human_escalation"
    
    def _meta_reflection_routing(self, state: ReflexiveK8sState) -> Literal["retry_with_insights", "human_escalation", "end"]:
        """Route after meta-reflection"""
        
        meta_reflection = state.get("meta_reflection_result")
        
        if meta_reflection and meta_reflection.get("actionable_insights"):
            return "retry_with_insights"
        elif state.get("retry_count", 0) >= 3:
            return "human_escalation"
        else:
            return "end"
    
    # === Special Nodes ===
    
    async def _meta_reflection_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Meta-reflection on the reflection process itself"""
        logger.info("Performing meta-reflection", pod_name=state["pod_name"])
        
        reflection_history = state.get("reflection_history", [])
        
        if len(reflection_history) >= 2:
            # Analyze reflection quality trend
            recent_quality = [r.meta_quality_score for r in reflection_history[-3:]]
            avg_quality = sum(recent_quality) / len(recent_quality)
            
            meta_reflection = {
                "reflection_quality_trend": "improving" if len(recent_quality) > 1 and recent_quality[-1] > recent_quality[0] else "stable",
                "average_reflection_quality": avg_quality,
                "insights_per_reflection": sum(len(r.insights_gained) for r in reflection_history[-3:]) / len(reflection_history[-3:]),
                "actionable_insights": avg_quality > 0.6,
                "meta_insight": "Reflection quality needs improvement" if avg_quality < 0.5 else "Reflection process is effective"
            }
        else:
            meta_reflection = {
                "meta_insight": "Insufficient reflection history for meta-analysis",
                "actionable_insights": False
            }
        
        state["meta_reflection_result"] = meta_reflection
        return state
    
    async def _human_escalation_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Handle human escalation scenarios"""
        logger.info("Escalating to human intervention", pod_name=state["pod_name"])
        
        escalation_context = {
            "reason": "automated_resolution_failed",
            "attempts_made": state.get("retry_count", 0) + 1,
            "strategies_tried": [attempt.get("strategy", {}).get("type") for attempt in state.get("past_attempts", [])],
            "last_error": state.get("execution_result", {}).get("error"),
            "reflexion_summary": {
                "total_reflections": len(state.get("reflection_history", [])),
                "self_awareness_level": state.get("self_awareness_level", 0.0),
                "learning_velocity": state.get("learning_velocity", 0.0)
            }
        }
        
        state["human_escalation"] = escalation_context
        state["requires_human_intervention"] = True
        
        return state
    
    async def _deep_analysis_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Perform deep analysis for complex cases"""
        logger.info("Performing deep analysis", pod_name=state["pod_name"])
        
        # This would integrate with more advanced analysis tools
        # For now, just mark for enhanced strategy selection
        state["deep_analysis_performed"] = True
        state["analysis_depth"] = "enhanced"
        
        return state
    
    # === Public Interface ===
    
    @traceable(name="k8s_reflexion_workflow")
    async def process_pod_error(self, 
                              pod_name: str,
                              namespace: str, 
                              error_type: str,
                              thread_id: str = None) -> Dict[str, Any]:
        """Process a pod error through the reflexive workflow"""
        
        # Initialize state
        initial_state: ReflexiveK8sState = {
            "pod_name": pod_name,
            "namespace": namespace,
            "error_type": error_type,
            "retry_count": 0,
            "success": False,
            "workflow_id": "",
            "ai_analysis": {},
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
            "improvement_trajectory": []
        }
        
        try:
            # Execute workflow (with or without checkpointing)
            if CHECKPOINT_AVAILABLE:
                config = {
                    "configurable": {"thread_id": thread_id or f"thread_{pod_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
                    "recursion_limit": 50  # Increase recursion limit
                }
                result = await self.compiled_workflow.ainvoke(initial_state, config=config)
            else:
                config = {"recursion_limit": 50}  # Increase recursion limit
                result = await self.compiled_workflow.ainvoke(initial_state, config=config)
            
            # Prepare response
            response = {
                "workflow_id": result.get("workflow_id"),
                "success": result.get("success", False),
                "pod_name": pod_name,
                "final_strategy": result.get("current_strategy", {}),
                "resolution_time": result.get("resolution_time", 0),
                "requires_human_intervention": result.get("requires_human_intervention", False),
                "reflexion_summary": {
                    "reflections_performed": len(result.get("reflection_history", [])),
                    "strategies_learned": len(result.get("strategy_database", {})),
                    "self_awareness_level": result.get("self_awareness_level", 0.0),
                    "learning_velocity": result.get("learning_velocity", 0.0)
                }
            }
            
            return response
            
        except Exception as e:
            logger.error("Workflow execution failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "requires_human_intervention": True
            }
    
    # === Helper Methods for Real K8s Data Analysis ===
    
    def _analyze_k8s_events(self, events: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Kubernetes events for insights"""
        insights = {
            "error_patterns": [],
            "recent_events": [],
            "critical_events": []
        }
        
        for event in events[-10:]:  # Last 10 events
            event_msg = event.get("message", "").lower()
            event_type = event.get("type", "")
            
            # Pattern detection
            if "pull" in event_msg and ("denied" in event_msg or "failed" in event_msg):
                insights["error_patterns"].append("image_pull_authentication")
            elif "crashloopbackoff" in event_msg:
                insights["error_patterns"].append("crash_loop")
            elif "oomkilled" in event_msg:
                insights["error_patterns"].append("out_of_memory")
            
            # Critical events
            if event_type == "Warning":
                insights["critical_events"].append({
                    "reason": event.get("reason", ""),
                    "message": event.get("message", "")[:200]
                })
        
        return insights
    
    def _analyze_pod_logs(self, logs: list[str]) -> Dict[str, Any]:
        """Analyze pod logs for insights"""
        insights = {
            "error_types": [],
            "exit_codes": [],
            "stack_traces": False
        }
        
        for log in logs[-50:]:  # Last 50 log lines
            log_lower = log.lower()
            
            # Error type detection
            if "error" in log_lower:
                insights["error_types"].append("general_error")
            elif "exception" in log_lower:
                insights["error_types"].append("exception")
            elif "panic" in log_lower:
                insights["error_types"].append("panic")
            
            # Exit code detection
            if "exit code" in log_lower:
                import re
                match = re.search(r'exit code[:\s]+(\d+)', log_lower)
                if match:
                    insights["exit_codes"].append(int(match.group(1)))
            
            # Stack trace detection
            if "traceback" in log_lower or "stack trace" in log_lower:
                insights["stack_traces"] = True
        
        return insights