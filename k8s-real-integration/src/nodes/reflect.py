"""
Reflection Node - Deep self-analysis for autonomous learning
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import json
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ReflexiveK8sState, ReflectionEntry, DEFAULT_REFLECTION_TEMPLATE

logger = structlog.get_logger()


class ReflectionEngine:
    """Advanced reflection engine for deep self-analysis"""
    
    def __init__(self, 
                 openai_api_key: str,
                 model: str = "gpt-3.5-turbo",
                 reflection_depth: str = "medium"):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model,
            temperature=0.1,  # Low temperature for analytical thinking
            max_tokens=2000
        )
        self.reflection_depth = reflection_depth
        self.template = DEFAULT_REFLECTION_TEMPLATE
        
    async def reflect_on_action_node(self, state: ReflexiveK8sState) -> ReflexiveK8sState:
        """
        Core reflection node - performs deep self-analysis of actions and outcomes
        """
        logger.info("Starting reflection process", 
                   pod_name=state["pod_name"],
                   reflection_depth=self.reflection_depth)
        
        try:
            # Generate reflection
            reflection = await self._generate_deep_reflection(state)
            
            # Process and integrate reflection
            processed_reflection = self._process_reflection_response(reflection, state)
            
            # Update state with reflection results
            state["current_reflection"] = processed_reflection
            state["reflection_history"].append(processed_reflection)
            state["reflection_depth"] = len(state["reflection_history"])
            
            # Update self-awareness metrics
            state["self_awareness_level"] = self._calculate_self_awareness_level(
                processed_reflection, state["reflection_history"]
            )
            
            # Update meta-learning metrics
            if "meta_learning" not in state:
                state["meta_learning"] = {
                    "total_reflections": 0,
                    "total_learning_cycles": 0,
                    "learning_success_rate": 0.0,
                    "reflection_quality_avg": 0.0
                }
            
            # Ensure meta_learning has all required fields
            if "total_reflections" not in state["meta_learning"]:
                state["meta_learning"]["total_reflections"] = 0
            if "reflection_quality_avg" not in state["meta_learning"]:
                state["meta_learning"]["reflection_quality_avg"] = 0.0
                
            state["meta_learning"]["total_reflections"] += 1
            state["meta_learning"]["reflection_quality_avg"] = self._calculate_avg_reflection_quality(
                state["reflection_history"]
            )
            
            logger.info("Reflection completed",
                       pod_name=state["pod_name"],
                       self_awareness_level=state["self_awareness_level"],
                       main_insights=len(processed_reflection.insights_gained))
            
            # Debug: Log the reflection text (first 500 chars)
            logger.debug("Reflection text preview", 
                        text_preview=reflection[:500] if reflection else "No text")
            
        except Exception as e:
            logger.error("Reflection failed", error=str(e))
            # Fallback reflection
            state["current_reflection"] = self._create_fallback_reflection(state)
            state["self_awareness_level"] = max(0.0, state.get("self_awareness_level", 0.5) - 0.1)
            
        return state
    
    async def _generate_deep_reflection(self, state: ReflexiveK8sState) -> str:
        """Generate deep reflection using LLM"""
        
        # Build reflection context
        reflection_context = self._build_reflection_context(state)
        
        # Create depth-appropriate prompt
        reflection_prompt = self._create_reflection_prompt(reflection_context, state)
        
        # System message for reflection guidance
        system_message = SystemMessage(content="""
You are an advanced AI system capable of deep self-reflection and meta-cognition. 
Your task is to analyze your own decision-making process in Kubernetes error resolution.

Key principles for reflection:
1. Be brutally honest about mistakes and limitations
2. Look for patterns and meta-patterns in your thinking
3. Consider alternative approaches you didn't try
4. Identify cognitive biases or blind spots
5. Focus on actionable insights for improvement
6. Maintain scientific skepticism about your own conclusions

Provide structured, analytical reflection that demonstrates genuine self-awareness and learning.
""")
        
        human_message = HumanMessage(content=reflection_prompt)
        
        # Generate reflection
        response = await self.llm.ainvoke([system_message, human_message])
        
        return response.content
    
    def _build_reflection_context(self, state: ReflexiveK8sState) -> Dict[str, Any]:
        """Build comprehensive context for reflection"""
        
        # Extract key context elements
        context = {
            "current_situation": {
                "pod_name": state["pod_name"],
                "error_type": state["error_type"],
                "namespace": state["namespace"],
                "retry_count": state.get("retry_count", 0)
            },
            "action_taken": state.get("current_strategy", {}),
            "outcome_observed": state.get("detailed_observation", {}),
            "past_attempts": state.get("past_attempts", [])[-3:],  # Last 3 attempts
            "strategy_summary": self._summarize_strategy_database(state.get("strategy_database", {})),
            "performance_trend": self._extract_performance_trend(state),
            "context_factors": state.get("environment_context", {})
        }
        
        return context
    
    def _create_reflection_prompt(self, context: Dict[str, Any], state: ReflexiveK8sState) -> str:
        """Create depth-appropriate reflection prompt"""
        
        base_prompt = self.template.base_template.format(
            context=json.dumps(context["current_situation"], indent=2),
            action=json.dumps(context["action_taken"], indent=2),
            outcome=json.dumps(context["outcome_observed"], indent=2),
            past_attempts=json.dumps(context["past_attempts"], indent=2),
            strategy_summary=json.dumps(context["strategy_summary"], indent=2)
        )
        
        # Add depth-specific modifications
        depth_modifier = self.template.depth_modifiers.get(self.reflection_depth, "")
        
        # Add domain-specific questions based on error type
        domain_questions = self._get_domain_specific_questions(state["error_type"])
        
        enhanced_prompt = f"""
{base_prompt}

REFLECTION DEPTH: {self.reflection_depth.upper()}
{depth_modifier}

DOMAIN-SPECIFIC ANALYSIS:
{domain_questions}

HISTORICAL CONTEXT:
Performance Trend: {context['performance_trend']}
Environmental Factors: {json.dumps(context['context_factors'], indent=2)}

Please provide a thorough, honest self-reflection that will genuinely improve my future performance.

IMPORTANT: Format your key insights using one of these patterns:
- "I learned that..."
- "I realized that..."
- "The key insight is..."
- "In the future, I will..."

Include at least 3 specific insights from this experience.
"""
        
        return enhanced_prompt
    
    def _get_domain_specific_questions(self, error_type: str) -> str:
        """Get domain-specific reflection questions based on error type"""
        
        domain_questions = {
            "ImagePullBackOff": """
- How well did I assess image availability and registry accessibility?
- Did I consider alternative image sources or versions?
- What does this teach me about image tag management strategies?
- How might container registry performance patterns affect my decisions?
            """,
            "CrashLoopBackOff": """
- How effectively did I analyze the crash patterns and exit codes?
- Did I consider resource constraints, initialization timing, and dependencies?
- What insights about application lifecycle management can I extract?
- How might I better predict and prevent crash scenarios?
            """,
            "OOMKilled": """
- How accurate was my resource requirement assessment?
- Did I consider memory usage patterns and peak demands?
- What can I learn about resource optimization strategies?
- How might I better balance performance and resource efficiency?
            """
        }
        
        return domain_questions.get(error_type, "Focus on general patterns and improvement opportunities.")
    
    def _process_reflection_response(self, reflection_text: str, state: ReflexiveK8sState) -> ReflectionEntry:
        """Process LLM reflection response into structured format"""
        
        try:
            # Try to extract JSON structure from reflection
            json_start = reflection_text.find('{')
            json_end = reflection_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = reflection_text[json_start:json_end]
                structured_data = json.loads(json_content)
            else:
                # No JSON found, create basic structure
                structured_data = {
                    "insights": [],
                    "strategy_modifications": {},
                    "overall_reflection_confidence": 0.7
                }
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.info(f"Reflection response is text-only (no JSON), proceeding with text analysis: {str(e)[:100]}")
            structured_data = {
                "insights": [],
                "strategy_modifications": {},
                "overall_reflection_confidence": 0.7
            }
        
        # Extract insights from text analysis
        insights = self._extract_insights_from_text(reflection_text)
        
        # Extract strategy modifications
        strategy_mods = structured_data.get("strategy_modifications", {})
        
        # Calculate reflection quality
        reflection_quality = self._assess_reflection_quality(reflection_text, structured_data)
        
        return ReflectionEntry(
            timestamp=datetime.now(),
            trigger_action=json.dumps(state.get("current_strategy", {})),
            outcome_observed=state.get("detailed_observation", {}),
            reflection_text=reflection_text,
            insights_gained=insights,
            strategy_modifications=strategy_mods,
            confidence_level=structured_data.get("overall_reflection_confidence", 0.7),
            meta_quality_score=reflection_quality
        )
    
    def _extract_insights_from_text(self, reflection_text: str) -> list[str]:
        """Extract key insights from reflection text"""
        
        insights = []
        
        # Look for insight indicators
        insight_markers = [
            "I learned that",
            "I realized that", 
            "The key insight is",
            "This reveals that",
            "I should have",
            "In the future, I will",
            "A better approach would be"
        ]
        
        lines = reflection_text.split('\n')
        for line in lines:
            line = line.strip()
            for marker in insight_markers:
                if marker.lower() in line.lower():
                    # Extract the insight
                    insight = line.split(marker, 1)[-1].strip()
                    if len(insight) > 10:  # Filter out too short insights
                        insights.append(insight)
                    break
        
        # If no insights found through markers, extract from structured sections
        if not insights:
            if "main_insights" in reflection_text:
                # Try to extract from main_insights section
                insights = ["General reflection completed - see full text for details"]
        
        return insights[:5]  # Limit to top 5 insights
    
    def _assess_reflection_quality(self, reflection_text: str, structured_data: Dict) -> float:
        """Assess the quality of the reflection"""
        
        quality_score = 0.0
        
        # Length and depth indicators
        if len(reflection_text) > 500:
            quality_score += 0.2
        if len(reflection_text) > 1000:
            quality_score += 0.1
            
        # Structured data completeness
        if structured_data.get("decision_quality_score") is not None:
            quality_score += 0.2
        if structured_data.get("main_insights"):
            quality_score += 0.2
        if structured_data.get("strategy_modifications"):
            quality_score += 0.2
            
        # Content quality indicators
        quality_indicators = [
            "because", "however", "alternatively", "in hindsight",
            "pattern", "insight", "improvement", "better approach"
        ]
        
        found_indicators = sum(1 for indicator in quality_indicators 
                             if indicator in reflection_text.lower())
        quality_score += min(0.3, found_indicators * 0.05)
        
        return min(1.0, quality_score)
    
    def _calculate_self_awareness_level(self, 
                                      current_reflection: ReflectionEntry,
                                      reflection_history: list[ReflectionEntry]) -> float:
        """Calculate overall self-awareness level"""
        
        if not reflection_history:
            return current_reflection.meta_quality_score
        
        # Recent reflection quality trend
        recent_quality = [r.meta_quality_score for r in reflection_history[-5:]]
        avg_recent_quality = sum(recent_quality) / len(recent_quality)
        
        # Insight depth trend  
        recent_insights = [len(r.insights_gained) for r in reflection_history[-5:]]
        avg_insight_count = sum(recent_insights) / len(recent_insights)
        insight_depth_score = min(1.0, avg_insight_count / 3.0)  # Normalize to 3 insights
        
        # Meta-cognition indicators
        meta_cognition_score = current_reflection.confidence_level
        
        # Combine factors
        self_awareness = (
            avg_recent_quality * 0.4 +
            insight_depth_score * 0.3 +
            meta_cognition_score * 0.3
        )
        
        return min(1.0, self_awareness)
    
    def _calculate_avg_reflection_quality(self, reflection_history: list[ReflectionEntry]) -> float:
        """Calculate average reflection quality over time"""
        if not reflection_history:
            return 0.0
        
        total_quality = sum(r.meta_quality_score for r in reflection_history)
        return total_quality / len(reflection_history)
    
    def _summarize_strategy_database(self, strategy_db: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize strategy database for context"""
        if not strategy_db:
            return {"status": "empty"}
        
        return {
            "total_strategies": len(strategy_db),
            "strategy_types": list(strategy_db.keys())[:5],  # Top 5 types
            "most_successful": "to_be_implemented",  # Placeholder
            "recent_additions": "to_be_implemented"   # Placeholder
        }
    
    def _extract_performance_trend(self, state: ReflexiveK8sState) -> str:
        """Extract performance trend from state"""
        trajectory = state.get("improvement_trajectory", [])
        
        if len(trajectory) < 2:
            return "insufficient_data"
        
        recent_trend = trajectory[-3:] if len(trajectory) >= 3 else trajectory
        
        if len(recent_trend) >= 2:
            if recent_trend[-1] > recent_trend[-2]:
                return "improving"
            elif recent_trend[-1] < recent_trend[-2]:
                return "declining" 
            else:
                return "stable"
        
        return "unknown"
    
    def _create_fallback_reflection(self, state: ReflexiveK8sState) -> ReflectionEntry:
        """Create basic fallback reflection when LLM reflection fails"""
        return ReflectionEntry(
            timestamp=datetime.now(),
            trigger_action=json.dumps(state.get("current_strategy", {})),
            outcome_observed=state.get("detailed_observation", {}),
            reflection_text="Fallback reflection: LLM analysis unavailable. Basic outcome recorded.",
            insights_gained=["Reflection system needs improvement", "Fallback mechanism activated"],
            strategy_modifications={},
            confidence_level=0.3,
            meta_quality_score=0.2
        )