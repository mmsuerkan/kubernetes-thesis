"""
Reflexive LangGraph Workflow - Enhanced K8s error resolution with self-learning
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Literal
import structlog
from langgraph.graph import StateGraph, END

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
    
    async def _analyze_error_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Enhanced error analysis with reflexive capabilities"""
        logger.info("Starting reflexive error analysis", pod_name=state["pod_name"])
        
        try:
            # Use mock analysis since we're running standalone
            state["k8sgpt_analysis"] = {
                "confidence": 0.9,
                "analysis": f"Mock analysis for {state['error_type']} error",
                "recommendations": ["Check image repository", "Verify network connectivity"],
                "error_details": f"Pod {state['pod_name']} experiencing {state['error_type']}"
            }
        
        except Exception as e:
            logger.error("Error analysis failed", error=str(e))
            state["k8sgpt_analysis"] = {"error": str(e)}
        
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
    
    async def _intelligent_strategy_selection_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """Intelligent strategy selection based on learned knowledge"""
        logger.info("Performing intelligent strategy selection", pod_name=state["pod_name"])
        
        strategy_database = state.get("strategy_database", {})
        error_type = state["error_type"]
        
        # Find relevant strategies from learned knowledge (both persistent and in-memory)
        relevant_strategies = self._find_relevant_strategies(error_type, state, strategy_database)
        
        # Always try to use persistent strategies first
        persistent_strategies = self.strategy_db.get_strategies_for_error(error_type)
        
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
            use_persistent = random.random() < 0.8  # 80% chance
            
            logger.info(f"Found {len(persistent_strategies)} persistent strategies, best: {best_persistent.id} (confidence: {best_persistent.confidence:.2f})")
            
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
                logger.info("Selected high-confidence persistent strategy", 
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
            # Fallback to simulated time if no start_time
            state["resolution_time"] = execution_time
            logger.warning("No execution_start_time found, using simulated time")
        
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
            "k8sgpt_analysis": {},
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
                config = {"configurable": {"thread_id": thread_id or f"thread_{pod_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}}
                result = await self.compiled_workflow.ainvoke(initial_state, config=config)
            else:
                result = await self.compiled_workflow.ainvoke(initial_state)
            
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