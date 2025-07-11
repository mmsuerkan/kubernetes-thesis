"""
Learning Node - Strategy evolution and knowledge integration
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog

from ..state import ReflexiveK8sState, StrategyEvolution, EpisodicMemory

logger = structlog.get_logger()


class LearningEngine:
    """Advanced learning engine for strategy evolution and knowledge integration"""
    
    def __init__(self, persistence_path: str = "./reflexion_memory.json"):
        self.persistence_path = persistence_path
        self.strategy_confidence_threshold = 0.7
        self.pattern_detection_threshold = 3  # Min occurrences to detect pattern
        
    async def learn_and_evolve_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """
        Core learning node - integrates reflection insights into knowledge base
        and evolves strategies
        """
        logger.info("Starting learning process", pod_name=state["pod_name"])
        
        try:
            # Extract learning from current reflection
            learning_results = await self._process_reflection_insights(state)
            
            # Update strategy database
            strategy_updates = await self._evolve_strategies(state, learning_results)
            
            # Update episodic memory
            episodic_entry = self._create_episodic_memory(state)
            state["episodic_memory"].append(episodic_entry)
            
            # Update meta-learning metrics
            meta_learning_updates = self._update_meta_learning(state, learning_results)
            
            # Detect new patterns
            new_patterns = await self._detect_emerging_patterns(state)
            
            # Calculate learning velocity
            learning_velocity = self._calculate_learning_velocity(state)
            
            # Update state with learning results
            state["strategy_database"] = strategy_updates["updated_strategies"]
            state["strategy_evolution"].extend(strategy_updates["evolution_records"])
            state["meta_learning"].update(meta_learning_updates)
            state["learning_velocity"] = learning_velocity
            
            # Persist learned knowledge
            await self._persist_knowledge(state)
            
            logger.info("Learning completed",
                       pod_name=state["pod_name"],
                       strategies_updated=len(strategy_updates["evolution_records"]),
                       patterns_detected=len(new_patterns),
                       learning_velocity=learning_velocity)
            
        except Exception as e:
            logger.error("Learning process failed", error=str(e))
            # Minimal learning fallback
            if "meta_learning" not in state:
                state["meta_learning"] = {
                    "total_reflections": 0,
                    "total_learning_cycles": 0,
                    "learning_success_rate": 0.0,
                    "reflection_quality_avg": 0.0
                }
            state["meta_learning"]["learning_failures"] = state["meta_learning"].get("learning_failures", 0) + 1
            
        return state
    
    async def _process_reflection_insights(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Extract actionable learning from reflection insights"""
        
        current_reflection = state.get("current_reflection")
        if not current_reflection:
            return {"insights_processed": 0}
        
        processed_insights = {
            "actionable_insights": [],
            "strategy_modifications": {},
            "pattern_discoveries": [],
            "confidence_adjustments": {},
            "knowledge_gaps": []
        }
        
        # Process each insight for actionability
        for insight in current_reflection.insights_gained:
            insight_analysis = self._analyze_insight_actionability(insight)
            if insight_analysis["actionable"]:
                processed_insights["actionable_insights"].append(insight_analysis)
        
        # Extract strategy modifications from reflection
        strategy_mods = current_reflection.strategy_modifications
        processed_insights["strategy_modifications"] = self._validate_strategy_modifications(strategy_mods)
        
        # Identify new patterns mentioned in reflection
        patterns = self._extract_pattern_references(current_reflection.reflection_text)
        processed_insights["pattern_discoveries"] = patterns
        
        # Extract confidence adjustments
        confidence_adjustments = self._extract_confidence_adjustments(current_reflection)
        processed_insights["confidence_adjustments"] = confidence_adjustments
        
        return processed_insights
    
    def _analyze_insight_actionability(self, insight: str) -> Dict[str, Any]:
        """Analyze if an insight can be converted to actionable strategy updates"""
        
        # Actionability indicators
        actionable_patterns = [
            "should", "need to", "must", "will", "better to",
            "instead of", "rather than", "improve by", "optimize"
        ]
        
        # Strategy modification indicators
        strategy_indicators = [
            "strategy", "approach", "method", "technique", "algorithm",
            "timeout", "retry", "threshold", "parameter"
        ]
        
        # Context awareness indicators
        context_indicators = [
            "when", "if", "during", "in case of", "depends on",
            "environment", "namespace", "cluster", "time"
        ]
        
        insight_lower = insight.lower()
        
        actionability_score = 0.0
        if any(pattern in insight_lower for pattern in actionable_patterns):
            actionability_score += 0.4
        if any(indicator in insight_lower for indicator in strategy_indicators):
            actionability_score += 0.3
        if any(indicator in insight_lower for indicator in context_indicators):
            actionability_score += 0.3
        
        return {
            "insight": insight,
            "actionable": actionability_score > 0.5,
            "actionability_score": actionability_score,
            "insight_type": self._classify_insight_type(insight),
            "implementation_priority": "high" if actionability_score > 0.8 else "medium" if actionability_score > 0.5 else "low"
        }
    
    def _classify_insight_type(self, insight: str) -> str:
        """Classify the type of insight for appropriate handling"""
        insight_lower = insight.lower()
        
        if any(word in insight_lower for word in ["timing", "time", "delay", "duration"]):
            return "temporal"
        elif any(word in insight_lower for word in ["resource", "memory", "cpu", "limit"]):
            return "resource_management"
        elif any(word in insight_lower for word in ["context", "environment", "namespace", "cluster"]):
            return "context_awareness"
        elif any(word in insight_lower for word in ["strategy", "approach", "algorithm"]):
            return "strategy_optimization"
        elif any(word in insight_lower for word in ["pattern", "correlation", "relationship"]):
            return "pattern_recognition"
        else:
            return "general"
    
    async def _evolve_strategies(self, state: ReflexiveK8sState, learning_results: Dict[str, Any]) -> Dict[str, Any]:
        """Evolve strategies based on learning results"""
        
        current_strategies = state.get("strategy_database", {})
        evolution_records = []
        
        # Process strategy modifications from reflection
        strategy_mods = learning_results.get("strategy_modifications", {})
        
        for strategy_id, modifications in strategy_mods.items():
            if strategy_id in current_strategies:
                # Evolve existing strategy
                evolved_strategy, evolution_record = self._evolve_existing_strategy(
                    strategy_id, current_strategies[strategy_id], modifications, state
                )
                current_strategies[strategy_id] = evolved_strategy
                evolution_records.append(evolution_record)
            else:
                # Create new strategy
                new_strategy, evolution_record = self._create_new_strategy(
                    strategy_id, modifications, state
                )
                current_strategies[strategy_id] = new_strategy
                evolution_records.append(evolution_record)
        
        # Process actionable insights for strategy creation/modification
        for insight_analysis in learning_results.get("actionable_insights", []):
            if insight_analysis["actionable"] and insight_analysis["implementation_priority"] in ["high", "medium"]:
                strategy_update = self._convert_insight_to_strategy_update(insight_analysis, state)
                if strategy_update:
                    strategy_id = strategy_update["strategy_id"]
                    current_strategies[strategy_id] = strategy_update["strategy"]
                    evolution_records.append(strategy_update["evolution_record"])
        
        # Update confidence levels based on recent performance
        self._update_strategy_confidence_levels(current_strategies, state)
        
        return {
            "updated_strategies": current_strategies,
            "evolution_records": evolution_records
        }
    
    def _evolve_existing_strategy(self, strategy_id: str, current_strategy: Dict, 
                                modifications: Dict, state: ReflexiveK8sState) -> tuple[Dict, StrategyEvolution]:
        """Evolve an existing strategy based on modifications"""
        
        evolved_strategy = current_strategy.copy()
        
        # Apply modifications
        for key, value in modifications.items():
            if key in ["timeout", "retry_count", "confidence_threshold"]:
                # Numeric parameter updates
                evolved_strategy[key] = value
            elif key == "conditions":
                # Conditional logic updates
                evolved_strategy.setdefault("conditions", []).extend(value if isinstance(value, list) else [value])
            elif key == "parameters":
                # Parameter updates
                evolved_strategy.setdefault("parameters", {}).update(value)
        
        # Increment version
        evolved_strategy["version"] = current_strategy.get("version", 1) + 1
        evolved_strategy["last_updated"] = datetime.now().isoformat()
        
        # Create evolution record
        evolution_record = StrategyEvolution(
            strategy_id=strategy_id,
            version=evolved_strategy["version"],
            trigger_event=f"reflection_insight_{state['workflow_id']}",
            change_description=f"Applied modifications: {list(modifications.keys())}",
            expected_improvement=0.1,  # Default expected improvement
            timestamp=datetime.now()
        )
        
        return evolved_strategy, evolution_record
    
    def _create_new_strategy(self, strategy_id: str, modifications: Dict, 
                           state: ReflexiveK8sState) -> tuple[Dict, StrategyEvolution]:
        """Create a new strategy from modifications"""
        
        new_strategy = {
            "id": strategy_id,
            "type": modifications.get("type", "generic"),
            "version": 1,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "confidence": 0.5,  # Start with medium confidence
            "usage_count": 0,
            "success_rate": 0.0,
            "parameters": modifications.get("parameters", {}),
            "conditions": modifications.get("conditions", []),
            "description": modifications.get("description", f"Strategy created from reflection insights")
        }
        
        evolution_record = StrategyEvolution(
            strategy_id=strategy_id,
            version=1,
            trigger_event=f"new_strategy_creation_{state['workflow_id']}",
            change_description="New strategy created from reflection insights",
            expected_improvement=0.05,  # Conservative estimate for new strategies
            timestamp=datetime.now()
        )
        
        return new_strategy, evolution_record
    
    def _convert_insight_to_strategy_update(self, insight_analysis: Dict, 
                                          state: ReflexiveK8sState) -> Optional[Dict]:
        """Convert an actionable insight into a concrete strategy update"""
        
        insight = insight_analysis["insight"]
        insight_type = insight_analysis["insight_type"]
        
        # Generate strategy ID based on insight content
        strategy_id = f"{insight_type}_{hash(insight) % 10000}"
        
        strategy_update = None
        
        if insight_type == "temporal":
            # Timing-related strategies
            strategy_update = self._create_temporal_strategy(insight, strategy_id, state)
        elif insight_type == "resource_management":
            # Resource-related strategies
            strategy_update = self._create_resource_strategy(insight, strategy_id, state)
        elif insight_type == "context_awareness":
            # Context-aware strategies
            strategy_update = self._create_context_strategy(insight, strategy_id, state)
        elif insight_type == "strategy_optimization":
            # Strategy optimization
            strategy_update = self._create_optimization_strategy(insight, strategy_id, state)
        
        return strategy_update
    
    def _create_temporal_strategy(self, insight: str, strategy_id: str, state: ReflexiveK8sState) -> Dict:
        """Create timing-related strategy from insight"""
        return {
            "strategy_id": strategy_id,
            "strategy": {
                "id": strategy_id,
                "type": "temporal_optimization",
                "version": 1,
                "parameters": {
                    "timing_consideration": insight,
                    "context_dependent": True
                },
                "conditions": [f"error_type == '{state['error_type']}'"],
                "confidence": 0.6
            },
            "evolution_record": StrategyEvolution(
                strategy_id=strategy_id,
                version=1,
                trigger_event=f"temporal_insight_{state['workflow_id']}",
                change_description=f"Temporal strategy from insight: {insight[:50]}...",
                expected_improvement=0.15,
                timestamp=datetime.now()
            )
        }
    
    def _create_resource_strategy(self, insight: str, strategy_id: str, state: ReflexiveK8sState) -> Dict:
        """Create resource management strategy from insight"""
        return {
            "strategy_id": strategy_id,
            "strategy": {
                "id": strategy_id,
                "type": "resource_optimization",
                "version": 1,
                "parameters": {
                    "resource_consideration": insight,
                    "adaptive_sizing": True
                },
                "conditions": [f"namespace == '{state['namespace']}'"],
                "confidence": 0.7
            },
            "evolution_record": StrategyEvolution(
                strategy_id=strategy_id,
                version=1,
                trigger_event=f"resource_insight_{state['workflow_id']}",
                change_description=f"Resource strategy from insight: {insight[:50]}...",
                expected_improvement=0.2,
                timestamp=datetime.now()
            )
        }
    
    def _create_context_strategy(self, insight: str, strategy_id: str, state: ReflexiveK8sState) -> Dict:
        """Create context-aware strategy from insight"""
        return {
            "strategy_id": strategy_id,
            "strategy": {
                "id": strategy_id,
                "type": "context_adaptive",
                "version": 1,
                "parameters": {
                    "context_insight": insight,
                    "environment_sensitive": True
                },
                "conditions": ["requires_context_evaluation"],
                "confidence": 0.65
            },
            "evolution_record": StrategyEvolution(
                strategy_id=strategy_id,
                version=1,
                trigger_event=f"context_insight_{state['workflow_id']}",
                change_description=f"Context strategy from insight: {insight[:50]}...",
                expected_improvement=0.18,
                timestamp=datetime.now()
            )
        }
    
    def _create_optimization_strategy(self, insight: str, strategy_id: str, state: ReflexiveK8sState) -> Dict:
        """Create strategy optimization from insight"""
        return {
            "strategy_id": strategy_id,
            "strategy": {
                "id": strategy_id,
                "type": "strategy_optimization",
                "version": 1,
                "parameters": {
                    "optimization_insight": insight,
                    "adaptive_learning": True
                },
                "conditions": ["general_optimization"],
                "confidence": 0.5
            },
            "evolution_record": StrategyEvolution(
                strategy_id=strategy_id,
                version=1,
                trigger_event=f"optimization_insight_{state['workflow_id']}",
                change_description=f"Strategy optimization from insight: {insight[:50]}...",
                expected_improvement=0.1,
                timestamp=datetime.now()
            )
        }
    
    def _update_strategy_confidence_levels(self, strategies: Dict[str, Any], state: ReflexiveK8sState):
        """Update strategy confidence levels based on recent performance"""
        
        recent_attempts = state.get("past_attempts", [])[-10:]  # Last 10 attempts
        
        for strategy_id, strategy in strategies.items():
            # Find attempts that used this strategy
            strategy_attempts = [
                attempt for attempt in recent_attempts
                if attempt.get("strategy", {}).get("id") == strategy_id
            ]
            
            if strategy_attempts:
                # Calculate success rate
                success_count = sum(1 for attempt in strategy_attempts if attempt.get("success", False))
                success_rate = success_count / len(strategy_attempts)
                
                # Update confidence based on success rate and sample size
                sample_weight = min(1.0, len(strategy_attempts) / 5.0)  # Full weight at 5+ samples
                new_confidence = (strategy.get("confidence", 0.5) * 0.7) + (success_rate * sample_weight * 0.3)
                
                strategy["confidence"] = round(new_confidence, 3)
                strategy["success_rate"] = round(success_rate, 3)
                strategy["usage_count"] = strategy.get("usage_count", 0) + len(strategy_attempts)
    
    def _create_episodic_memory(self, state: ReflexiveK8sState) -> EpisodicMemory:
        """Create episodic memory entry for current experience"""
        
        lessons_learned = []
        if state.get("current_reflection"):
            lessons_learned = state["current_reflection"].insights_gained[:3]  # Top 3 insights
        
        return EpisodicMemory(
            episode_id=f"{state['workflow_id']}_{state['pod_name']}",
            context={
                "pod_name": state["pod_name"],
                "namespace": state["namespace"],
                "error_type": state["error_type"],
                "environment_context": state.get("environment_context", {}),
                "retry_count": state.get("retry_count", 0)
            },
            action_taken=state.get("current_strategy", {}),
            outcome={
                "success": state.get("success", False),
                "detailed_observation": state.get("detailed_observation", {}),
                "resolution_time": state.get("resolution_time", 0)
            },
            lessons_learned=lessons_learned,
            timestamp=datetime.now()
        )
    
    def _update_meta_learning(self, state: ReflexiveK8sState, learning_results: Dict[str, Any]) -> Dict[str, Any]:
        """Update meta-learning metrics"""
        
        current_meta = state.get("meta_learning", {})
        
        # Update counters
        current_meta["total_learning_cycles"] = current_meta.get("total_learning_cycles", 0) + 1
        current_meta["insights_processed"] = current_meta.get("insights_processed", 0) + len(learning_results.get("actionable_insights", []))
        current_meta["strategies_evolved"] = current_meta.get("strategies_evolved", 0) + len(learning_results.get("strategy_modifications", {}))
        
        # Update learning effectiveness metrics
        if state.get("success", False):
            current_meta["successful_learning_cycles"] = current_meta.get("successful_learning_cycles", 0) + 1
        
        current_meta["learning_success_rate"] = (
            current_meta.get("successful_learning_cycles", 0) / 
            max(1, current_meta.get("total_learning_cycles", 1))
        )
        
        # Update knowledge base size
        current_meta["total_strategies"] = len(state.get("strategy_database", {}))
        current_meta["total_episodes"] = len(state.get("episodic_memory", []))
        
        return current_meta
    
    async def _detect_emerging_patterns(self, state: ReflexiveK8sState) -> List[Dict[str, Any]]:
        """Detect emerging patterns in episodic memory"""
        
        episodic_memory = state.get("episodic_memory", [])
        
        if len(episodic_memory) < self.pattern_detection_threshold:
            return []
        
        patterns = []
        
        # Pattern 1: Error type + namespace correlations
        error_namespace_pattern = self._detect_error_namespace_patterns(episodic_memory)
        if error_namespace_pattern:
            patterns.append(error_namespace_pattern)
        
        # Pattern 2: Temporal patterns
        temporal_pattern = self._detect_temporal_patterns(episodic_memory)
        if temporal_pattern:
            patterns.append(temporal_pattern)
        
        # Pattern 3: Strategy effectiveness patterns
        strategy_pattern = self._detect_strategy_effectiveness_patterns(episodic_memory)
        if strategy_pattern:
            patterns.append(strategy_pattern)
        
        return patterns
    
    def _detect_error_namespace_patterns(self, episodes: List[EpisodicMemory]) -> Optional[Dict[str, Any]]:
        """Detect patterns between error types and namespaces"""
        
        error_namespace_freq = {}
        
        for episode in episodes[-20:]:  # Last 20 episodes
            error_type = episode.context.get("error_type")
            namespace = episode.context.get("namespace") 
            
            if error_type and namespace:
                key = f"{error_type}:{namespace}"
                error_namespace_freq[key] = error_namespace_freq.get(key, 0) + 1
        
        # Find frequent combinations
        frequent_patterns = {k: v for k, v in error_namespace_freq.items() if v >= self.pattern_detection_threshold}
        
        if frequent_patterns:
            return {
                "pattern_type": "error_namespace_correlation",
                "patterns": frequent_patterns,
                "confidence": 0.7,
                "actionable": True
            }
        
        return None
    
    def _detect_temporal_patterns(self, episodes: List[EpisodicMemory]) -> Optional[Dict[str, Any]]:
        """Detect temporal patterns in error occurrences"""
        
        if len(episodes) < 5:
            return None
        
        # Analyze timing patterns
        timestamps = [episode.timestamp for episode in episodes[-10:]]
        hours = [ts.hour for ts in timestamps]
        
        # Simple frequency analysis
        hour_freq = {}
        for hour in hours:
            hour_freq[hour] = hour_freq.get(hour, 0) + 1
        
        # Find peak hours
        peak_hours = [hour for hour, freq in hour_freq.items() if freq >= 2]
        
        if peak_hours:
            return {
                "pattern_type": "temporal_clustering",
                "peak_hours": peak_hours,
                "confidence": 0.6,
                "actionable": False  # Informational for now
            }
        
        return None
    
    def _detect_strategy_effectiveness_patterns(self, episodes: List[EpisodicMemory]) -> Optional[Dict[str, Any]]:
        """Detect patterns in strategy effectiveness"""
        
        strategy_outcomes = {}
        
        for episode in episodes[-15:]:  # Last 15 episodes
            strategy_type = episode.action_taken.get("type")
            success = episode.outcome.get("success", False)
            
            if strategy_type:
                if strategy_type not in strategy_outcomes:
                    strategy_outcomes[strategy_type] = {"success": 0, "total": 0}
                
                strategy_outcomes[strategy_type]["total"] += 1
                if success:
                    strategy_outcomes[strategy_type]["success"] += 1
        
        # Calculate success rates
        strategy_rates = {}
        for strategy, outcomes in strategy_outcomes.items():
            if outcomes["total"] >= 3:  # Minimum sample size
                success_rate = outcomes["success"] / outcomes["total"]
                strategy_rates[strategy] = success_rate
        
        if strategy_rates:
            return {
                "pattern_type": "strategy_effectiveness",
                "strategy_success_rates": strategy_rates,
                "confidence": 0.8,
                "actionable": True
            }
        
        return None
    
    def _calculate_learning_velocity(self, state: ReflexiveK8sState) -> float:
        """Calculate how fast the agent is learning/improving"""
        
        improvement_trajectory = state.get("improvement_trajectory", [])
        
        if len(improvement_trajectory) < 3:
            return 0.0
        
        # Calculate trend over last few data points
        recent_trajectory = improvement_trajectory[-5:]
        
        if len(recent_trajectory) < 2:
            return 0.0
        
        # Simple linear trend calculation
        x_values = list(range(len(recent_trajectory)))
        y_values = recent_trajectory
        
        # Calculate slope (learning velocity)
        n = len(recent_trajectory)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize slope to 0-1 range
        normalized_velocity = max(0.0, min(1.0, slope + 0.5))
        
        return round(normalized_velocity, 3)
    
    def _validate_strategy_modifications(self, strategy_mods: Dict) -> Dict:
        """Validate and sanitize strategy modifications"""
        
        validated_mods = {}
        
        for strategy_id, modifications in strategy_mods.items():
            if isinstance(modifications, dict):
                # Validate modification keys
                valid_keys = ["timeout", "retry_count", "confidence_threshold", "parameters", "conditions", "type", "description"]
                validated_modifications = {
                    k: v for k, v in modifications.items() 
                    if k in valid_keys and v is not None
                }
                
                if validated_modifications:
                    validated_mods[strategy_id] = validated_modifications
        
        return validated_mods
    
    def _extract_pattern_references(self, reflection_text: str) -> List[Dict[str, Any]]:
        """Extract pattern references from reflection text"""
        
        patterns = []
        pattern_keywords = ["pattern", "correlation", "relationship", "trend", "consistency"]
        
        lines = reflection_text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in pattern_keywords):
                patterns.append({
                    "text": line.strip(),
                    "type": "textual_pattern",
                    "confidence": 0.5
                })
        
        return patterns[:3]  # Limit to top 3 patterns
    
    def _extract_confidence_adjustments(self, reflection: 'ReflectionEntry') -> Dict[str, float]:
        """Extract confidence adjustments from reflection"""
        
        # This would be more sophisticated in production
        # For now, return basic confidence adjustment based on reflection quality
        
        base_adjustment = 0.0
        
        if reflection.meta_quality_score > 0.8:
            base_adjustment = 0.05  # Slight confidence boost for high-quality reflection
        elif reflection.meta_quality_score < 0.4:
            base_adjustment = -0.05  # Slight confidence decrease for poor reflection
        
        return {"general_confidence_adjustment": base_adjustment}
    
    async def _persist_knowledge(self, state: ReflexiveK8sState):
        """Persist learned knowledge to storage"""
        
        try:
            # Prepare data for persistence
            knowledge_snapshot = {
                "timestamp": datetime.now().isoformat(),
                "strategy_database": state.get("strategy_database", {}),
                "meta_learning": state.get("meta_learning", {}),
                "learning_velocity": state.get("learning_velocity", 0.0),
                "episodic_memory_count": len(state.get("episodic_memory", [])),
                "reflection_history_count": len(state.get("reflection_history", []))
            }
            
            # In production, this would use a proper database
            # For now, append to JSON file
            with open(self.persistence_path, "a") as f:
                f.write(json.dumps(knowledge_snapshot) + "\n")
                
        except Exception as e:
            logger.error("Failed to persist knowledge", error=str(e))