"""
Reflexive K8s Agent State Definition
Enhanced LangGraph state with reflexion capabilities
"""
from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class ReflectionEntry(BaseModel):
    """Single reflection entry"""
    timestamp: datetime
    trigger_action: str
    outcome_observed: Dict[str, Any]
    reflection_text: str
    insights_gained: List[str]
    strategy_modifications: Dict[str, Any]
    confidence_level: float
    meta_quality_score: float


class StrategyEvolution(BaseModel):
    """Strategy evolution tracking"""
    strategy_id: str
    version: int
    trigger_event: str
    change_description: str
    expected_improvement: float
    actual_improvement: Optional[float] = None
    timestamp: datetime


class EpisodicMemory(BaseModel):
    """Episodic memory entry"""
    episode_id: str
    context: Dict[str, Any]
    action_taken: Dict[str, Any]
    outcome: Dict[str, Any]
    lessons_learned: List[str]
    timestamp: datetime


class ReflexiveK8sState(TypedDict):
    """Enhanced LangGraph state with reflexion capabilities"""
    
    # === Standard Workflow State ===
    workflow_id: str
    pod_name: str
    namespace: str
    error_type: str
    ai_analysis: Dict[str, Any]
    current_strategy: Dict[str, Any]
    execution_result: Dict[str, Any]
    success: bool
    retry_count: int
    
    # === Reflexion State ===
    # Observation data
    detailed_observation: Dict[str, Any]
    observation_timestamp: datetime
    
    # Reflection data
    current_reflection: Optional[ReflectionEntry]
    reflection_history: List[ReflectionEntry]
    reflection_depth: int  # How deep the current reflection is
    
    # Memory systems
    episodic_memory: List[EpisodicMemory]
    past_attempts: List[Dict[str, Any]]
    
    # Strategy evolution
    strategy_database: Dict[str, Any]
    strategy_evolution: List[StrategyEvolution]
    
    # Meta-learning tracking
    meta_learning: Dict[str, Any]
    self_awareness_level: float
    learning_velocity: float  # How fast agent is improving
    
    # Context awareness
    environment_context: Dict[str, Any]
    temporal_context: Dict[str, Any]
    
    # Performance tracking
    performance_metrics: Dict[str, float]
    improvement_trajectory: List[float]


class ObservationMetrics(BaseModel):
    """Structured observation metrics"""
    success_metrics: Dict[str, Any]
    performance_metrics: Dict[str, float] 
    context_factors: Dict[str, Any]
    comparative_analysis: Dict[str, Any]
    anomaly_detection: Dict[str, Any]


class ReflectionPromptTemplate(BaseModel):
    """Template for reflection prompts"""
    base_template: str
    context_variables: List[str]
    depth_modifiers: Dict[str, str]
    domain_specific_questions: List[str]


# Default reflection prompt template
DEFAULT_REFLECTION_TEMPLATE = ReflectionPromptTemplate(
    base_template="""
SELF-REFLECTION ON KUBERNETES FIX ATTEMPT

Context: {context}
Action Taken: {action}
Outcome: {outcome}
Past Similar Attempts: {past_attempts}
Current Strategy Database: {strategy_summary}

DEEP SELF-ANALYSIS:
1. Decision Quality Assessment:
   - Was my strategy selection optimal given the available context?
   - What contextual factors did I consider vs. miss?
   - How did my past experiences influence this decision?

2. Execution Analysis:
   - Was the timing of my action appropriate?
   - Did I adequately assess potential risks and side effects?
   - How could the execution have been improved?

3. Learning Integration:
   - How effectively did I apply lessons from past attempts?
   - What patterns am I starting to recognize?
   - Are there gaps in my knowledge that became apparent?

4. Outcome Evaluation:
   - Was the outcome aligned with my prediction?
   - What unexpected factors emerged?
   - How does this outcome fit into broader patterns?

5. Strategy Evolution:
   - What modifications should I make to my strategy database?
   - What new heuristics or rules should I develop?
   - How should I adjust my confidence levels?

6. Meta-Cognitive Assessment:
   - How is my reflection process itself evolving?
   - Am I asking the right questions?
   - What blind spots might I still have?

STRUCTURED REFLECTION OUTPUT:
{{
    "decision_quality_score": <0.0-1.0>,
    "execution_quality_score": <0.0-1.0>, 
    "learning_integration_score": <0.0-1.0>,
    "main_insights": [<list of key insights>],
    "strategy_modifications": {{<specific changes to make>}},
    "new_patterns_discovered": [<list of patterns>],
    "confidence_updates": {{<strategy_id: new_confidence>}},
    "knowledge_gaps_identified": [<list of gaps>],
    "meta_reflection_quality": <0.0-1.0>,
    "overall_reflection_confidence": <0.0-1.0>
}}
    """,
    context_variables=[
        "context", "action", "outcome", "past_attempts", "strategy_summary"
    ],
    depth_modifiers={
        "shallow": "Focus on immediate factors and obvious patterns.",
        "medium": "Include second-order effects and cross-domain analogies.",
        "deep": "Examine fundamental assumptions and paradigm-level insights."
    },
    domain_specific_questions=[
        "How does this relate to Kubernetes resource management patterns?",
        "What does this teach me about cluster behavior under stress?", 
        "How might this insight apply to other distributed systems?"
    ]
)