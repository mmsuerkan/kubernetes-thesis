"""
Observation Node - Enhanced outcome monitoring for reflexion
"""
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, List
import structlog

from ..state import ReflexiveK8sState, ObservationMetrics

logger = structlog.get_logger()


class ObservationEngine:
    """Advanced observation engine for reflexive learning"""
    
    def __init__(self, go_service_url: str = ""):
        # No Go service needed - using mock data
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def observe_outcome_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """
        Enhanced observation node that captures multi-dimensional outcome data
        for reflexive learning
        """
        logger.info("Starting enhanced observation", pod_name=state["pod_name"])
        
        try:
            # Multi-dimensional observation
            observation = await self._collect_comprehensive_observation(state)
            
            # Update state with detailed observation
            state["detailed_observation"] = observation.model_dump()
            state["observation_timestamp"] = datetime.now()
            
            # Calculate observation quality score
            observation_quality = self._assess_observation_quality(observation)
            if "meta_learning" not in state:
                state["meta_learning"] = {
                    "total_reflections": 0,
                    "total_learning_cycles": 0,
                    "learning_success_rate": 0.0,
                    "reflection_quality_avg": 0.0
                }
            state["meta_learning"]["observation_quality"] = observation_quality
            
            logger.info(
                "Observation complete", 
                pod_name=state["pod_name"],
                observation_quality=observation_quality
            )
            
        except Exception as e:
            logger.error("Observation failed", error=str(e))
            # Fallback to basic observation
            state["detailed_observation"] = await self._basic_observation_fallback(state)
            if "meta_learning" not in state:
                state["meta_learning"] = {
                    "total_reflections": 0,
                    "total_learning_cycles": 0,
                    "learning_success_rate": 0.0,
                    "reflection_quality_avg": 0.0
                }
            state["meta_learning"]["observation_quality"] = 0.3
        
        return state
    
    async def _collect_comprehensive_observation(self, state: ReflexiveK8sState) -> ObservationMetrics:
        """Collect multi-layered observation data"""
        
        # Parallel data collection for efficiency
        tasks = [
            self._collect_success_metrics(state),
            self._collect_performance_metrics(state),
            self._collect_context_factors(state),
            self._collect_comparative_analysis(state),
            self._detect_anomalies(state)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return ObservationMetrics(
            success_metrics=results[0] if not isinstance(results[0], Exception) else {},
            performance_metrics=results[1] if not isinstance(results[1], Exception) else {},
            context_factors=results[2] if not isinstance(results[2], Exception) else {},
            comparative_analysis=results[3] if not isinstance(results[3], Exception) else {},
            anomaly_detection=results[4] if not isinstance(results[4], Exception) else {}
        )
    
    async def _collect_success_metrics(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Collect detailed success/failure metrics"""
        try:
            # Use mock pod status since we're standalone
            pod_status = {
                "status": "Running" if state.get("success", False) else "Failed",
                "containers_ready": state.get("success", False),
                "restart_count": 0 if state.get("success", False) else 3,
                "ready_time": "2024-07-11T06:30:00Z" if state.get("success", False) else None
            }
            
            return {
                "pod_status": pod_status["status"],
                "container_ready": pod_status.get("containers_ready", False),
                "restart_count": pod_status.get("restart_count", 0),
                "ready_time": pod_status.get("ready_time"),
                "error_resolution": pod_status["status"] == "Running",
                "stability_score": self._calculate_stability_score(pod_status),
                "health_check_status": pod_status.get("health_checks", {})
            }
                
        except Exception as e:
            return {"error": f"Success metrics collection failed: {str(e)}"}
    
    async def _collect_performance_metrics(self, state: ReflexiveK8sState) -> Dict[str, float]:
        """Collect performance-related metrics"""
        try:
            # Time-based metrics
            execution_start = state.get("execution_start_time")
            current_time = datetime.now()
            
            if execution_start:
                resolution_time = (current_time - execution_start).total_seconds()
            else:
                resolution_time = 0.0
            
            # Resource impact assessment
            resource_impact = await self._assess_resource_impact(state)
            
            return {
                "time_to_resolution": resolution_time,
                "resource_cpu_impact": resource_impact.get("cpu", 0.0),
                "resource_memory_impact": resource_impact.get("memory", 0.0),
                "network_impact": resource_impact.get("network", 0.0),
                "efficiency_score": self._calculate_efficiency_score(resolution_time, resource_impact)
            }
            
        except Exception as e:
            logger.error("Performance metrics collection failed", error=str(e))
            return {}
    
    async def _collect_context_factors(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Collect environmental and contextual factors"""
        try:
            current_time = datetime.now()
            
            # Cluster context
            cluster_metrics = await self._get_cluster_metrics()
            
            return {
                "timestamp": current_time.isoformat(),
                "time_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "cluster_load": cluster_metrics.get("cpu_usage", 0.0),
                "cluster_memory_pressure": cluster_metrics.get("memory_pressure", False),
                "namespace_criticality": self._assess_namespace_criticality(state["namespace"]),
                "concurrent_operations": cluster_metrics.get("concurrent_ops", 0),
                "recent_cluster_events": await self._get_recent_cluster_events()
            }
            
        except Exception as e:
            return {"context_collection_error": str(e)}
    
    async def _collect_comparative_analysis(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Compare current attempt with historical data"""
        try:
            # Compare with past attempts
            past_attempts = state.get("past_attempts", [])
            similar_cases = self._find_similar_historical_cases(state, past_attempts)
            
            comparative_data = {
                "vs_previous_attempts": self._compare_with_previous(state, past_attempts),
                "vs_similar_cases": self._compare_with_similar(state, similar_cases),
                "improvement_trajectory": self._calculate_improvement_trajectory(past_attempts),
                "pattern_consistency": self._assess_pattern_consistency(state, similar_cases)
            }
            
            return comparative_data
            
        except Exception as e:
            return {"comparative_analysis_error": str(e)}
    
    async def _detect_anomalies(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Detect anomalous patterns or unexpected behaviors"""
        try:
            anomalies = {
                "unexpected_success": self._detect_unexpected_success(state),
                "unusual_timing": self._detect_timing_anomalies(state),
                "resource_anomalies": self._detect_resource_anomalies(state),
                "pattern_violations": self._detect_pattern_violations(state)
            }
            
            return {
                "anomalies_detected": anomalies,
                "anomaly_score": self._calculate_anomaly_score(anomalies),
                "investigation_needed": any(anomalies.values())
            }
            
        except Exception as e:
            return {"anomaly_detection_error": str(e)}
    
    def _calculate_stability_score(self, pod_status: Dict[str, Any]) -> float:
        """Calculate pod stability score based on status"""
        if pod_status["status"] == "Running":
            restart_count = pod_status.get("restart_count", 0)
            # Lower restart count = higher stability
            return max(0.0, 1.0 - (restart_count * 0.1))
        return 0.0
    
    async def _assess_resource_impact(self, state: ReflexiveK8sState) -> Dict[str, float]:
        """Assess the resource impact of the fix operation"""
        try:
            # This would integrate with cluster monitoring
            # For now, return mock data
            return {
                "cpu": 0.1,  # 10% CPU impact
                "memory": 0.05,  # 5% memory impact  
                "network": 0.02  # 2% network impact
            }
        except:
            return {}
    
    def _calculate_efficiency_score(self, resolution_time: float, resource_impact: Dict[str, float]) -> float:
        """Calculate overall efficiency score"""
        time_efficiency = max(0.0, 1.0 - (resolution_time / 300.0))  # 5 min baseline
        resource_efficiency = 1.0 - sum(resource_impact.values())
        return (time_efficiency + resource_efficiency) / 2.0
    
    async def _get_cluster_metrics(self) -> Dict[str, Any]:
        """Get current cluster metrics"""
        try:
            # Mock cluster metrics since we're standalone
            return {
                "total_pods": 50,
                "failed_pods": 2,
                "resource_pressure": "low",
                "node_health": "healthy"
            }
        except:
            return {}
    
    def _assess_namespace_criticality(self, namespace: str) -> str:
        """Assess criticality level of namespace"""
        critical_namespaces = {"production", "prod", "live"}
        if namespace in critical_namespaces:
            return "critical"
        elif namespace in {"staging", "stage"}:
            return "medium"
        return "low"
    
    async def _get_recent_cluster_events(self) -> List[Dict[str, Any]]:
        """Get recent cluster events for context"""
        try:
            # Mock recent events since we're standalone
            return [
                {"type": "Warning", "reason": "ImagePullBackOff", "message": "Mock event for testing"},
                {"type": "Normal", "reason": "Started", "message": "Container started"}
            ]
        except:
            return []
    
    def _find_similar_historical_cases(self, state: ReflexiveK8sState, past_attempts: List[Dict]) -> List[Dict]:
        """Find similar cases from history"""
        current_error = state["error_type"]
        similar = [
            attempt for attempt in past_attempts
            if attempt.get("error_type") == current_error
        ]
        return similar[-5:]  # Last 5 similar cases
    
    def _compare_with_previous(self, state: ReflexiveK8sState, past_attempts: List[Dict]) -> Dict[str, Any]:
        """Compare with previous attempts"""
        if not past_attempts:
            return {"comparison": "no_previous_attempts"}
        
        last_attempt = past_attempts[-1]
        return {
            "strategy_similarity": self._calculate_strategy_similarity(
                state["current_strategy"], 
                last_attempt.get("strategy", {})
            ),
            "context_similarity": self._calculate_context_similarity(state, last_attempt),
            "outcome_comparison": "improved" if state.get("success") and not last_attempt.get("success") else "similar"
        }
    
    def _compare_with_similar(self, state: ReflexiveK8sState, similar_cases: List[Dict]) -> Dict[str, Any]:
        """Compare with similar historical cases"""
        if not similar_cases:
            return {"comparison": "no_similar_cases"}
        
        success_rate = sum(1 for case in similar_cases if case.get("success", False)) / len(similar_cases)
        avg_resolution_time = sum(case.get("resolution_time", 0) for case in similar_cases) / len(similar_cases)
        
        return {
            "historical_success_rate": success_rate,
            "avg_historical_resolution_time": avg_resolution_time,
            "performance_vs_historical": "better" if state.get("resolution_time", 0) < avg_resolution_time else "worse"
        }
    
    def _calculate_improvement_trajectory(self, past_attempts: List[Dict]) -> List[float]:
        """Calculate improvement trajectory over time"""
        if len(past_attempts) < 2:
            return []
        
        success_rates = []
        window_size = 5
        
        for i in range(len(past_attempts) - window_size + 1):
            window = past_attempts[i:i + window_size]
            success_rate = sum(1 for attempt in window if attempt.get("success", False)) / window_size
            success_rates.append(success_rate)
        
        return success_rates
    
    def _assess_pattern_consistency(self, state: ReflexiveK8sState, similar_cases: List[Dict]) -> float:
        """Assess how consistent current outcome is with patterns"""
        if not similar_cases:
            return 0.5  # Neutral when no data
        
        # Simple pattern consistency based on success correlation with strategy type
        current_strategy_type = state["current_strategy"].get("type", "unknown")
        strategy_success_rate = sum(
            1 for case in similar_cases 
            if case.get("strategy", {}).get("type") == current_strategy_type and case.get("success", False)
        ) / max(1, len([case for case in similar_cases if case.get("strategy", {}).get("type") == current_strategy_type]))
        
        return strategy_success_rate
    
    def _detect_unexpected_success(self, state: ReflexiveK8sState) -> bool:
        """Detect if success was unexpected based on context"""
        # This would use more sophisticated logic in production
        return state.get("success", False) and state.get("retry_count", 0) > 2
    
    def _detect_timing_anomalies(self, state: ReflexiveK8sState) -> bool:
        """Detect unusual timing patterns"""
        resolution_time = state.get("resolution_time", 0)
        return resolution_time < 5 or resolution_time > 300  # Too fast or too slow
    
    def _detect_resource_anomalies(self, state: ReflexiveK8sState) -> bool:
        """Detect unusual resource usage patterns"""
        # Placeholder for resource anomaly detection
        return False
    
    def _detect_pattern_violations(self, state: ReflexiveK8sState) -> bool:
        """Detect violations of expected patterns"""
        # Placeholder for pattern violation detection
        return False
    
    def _calculate_anomaly_score(self, anomalies: Dict[str, bool]) -> float:
        """Calculate overall anomaly score"""
        anomaly_count = sum(1 for detected in anomalies.values() if detected)
        return anomaly_count / len(anomalies)
    
    def _calculate_strategy_similarity(self, strategy1: Dict, strategy2: Dict) -> float:
        """Calculate similarity between two strategies"""
        # Simple similarity based on strategy type
        if strategy1.get("type") == strategy2.get("type"):
            return 0.8
        return 0.2
    
    def _calculate_context_similarity(self, state: ReflexiveK8sState, past_attempt: Dict) -> float:
        """Calculate context similarity with past attempt"""
        # Simple context similarity
        same_namespace = state["namespace"] == past_attempt.get("namespace")
        same_error_type = state["error_type"] == past_attempt.get("error_type")
        
        similarity = 0.0
        if same_namespace:
            similarity += 0.3
        if same_error_type:
            similarity += 0.7
            
        return similarity
    
    def _assess_observation_quality(self, observation: ObservationMetrics) -> float:
        """Assess the quality/completeness of observation data"""
        completeness_score = 0.0
        
        # Check completeness of each observation dimension
        if observation.success_metrics:
            completeness_score += 0.3
        if observation.performance_metrics:
            completeness_score += 0.2
        if observation.context_factors:
            completeness_score += 0.2
        if observation.comparative_analysis:
            completeness_score += 0.2
        if observation.anomaly_detection:
            completeness_score += 0.1
            
        return completeness_score
    
    async def _basic_observation_fallback(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Fallback to basic observation if comprehensive observation fails"""
        return {
            "basic_success_check": state.get("success", False),
            "error_type": state["error_type"],
            "timestamp": datetime.now().isoformat(),
            "fallback_used": True
        }