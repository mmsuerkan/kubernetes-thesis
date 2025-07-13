"""
AI Command Generator - GPT-4 Powered kubectl Command Generation
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = structlog.get_logger()
logger.info("🤖 AI Command Generator module loaded - Enhanced logging enabled")


class AICommandGenerator:
    """AI-powered kubectl command generator using GPT-4"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model,
            temperature=0.3,  # Low temperature for consistent command generation
            timeout=60
        )
        
    async def generate_kubectl_commands(self, 
                                      error_type: str,
                                      pod_name: str,
                                      namespace: str,
                                      strategy: Dict[str, Any],
                                      real_k8s_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate kubectl commands using GPT-4 based on error analysis
        
        Args:
            error_type: Type of Kubernetes error
            pod_name: Name of the failing pod
            namespace: Kubernetes namespace
            strategy: Selected strategy from reflexion
            real_k8s_data: Real Kubernetes data (pod spec, events, logs)
            
        Returns:
            Dictionary containing backup, fix, validation, and rollback commands
        """
        logger.info("="*80)
        logger.info("🤖 AI COMMAND GENERATION START")
        logger.info(f"   📱 Pod: {pod_name} (namespace: {namespace})")
        logger.info(f"   🚨 Error Type: {error_type}")
        logger.info(f"   🎯 Strategy ID: {strategy.get('id', 'unknown')}")
        logger.info(f"   📊 Strategy Confidence: {strategy.get('confidence', 0):.2%}")
        logger.info(f"   💡 Selection Reason: {strategy.get('selection_reason', 'unknown')}")
        logger.info(f"   🔢 Usage Count: {strategy.get('usage_count', 0)}")
        logger.info(f"   📈 Success Rate: {strategy.get('success_rate', 0):.2%}")
        
        # Show if this is a learned strategy
        if strategy.get("selection_reason") == "high_confidence_persistent":
            logger.info("   🧠 USING LEARNED STRATEGY FROM DATABASE")
        elif strategy.get("selection_reason") == "default_fallback":
            logger.info("   🎯 USING DEFAULT FALLBACK STRATEGY")
        else:
            logger.info("   🔄 USING IN-MEMORY STRATEGY")
        logger.info("="*80)
        
        try:
            # Prepare context data
            context = self._prepare_context(error_type, pod_name, namespace, strategy, real_k8s_data)
            
            # Generate commands using GPT-4
            commands = await self._call_gpt4_for_commands(context)
            
            # Validate command structure
            validated_commands = self._validate_command_structure(commands)
            
            # Log the actual commands that will be executed
            total_commands = sum(len(cmds) for cmds in validated_commands.values())
            logger.info("="*80)
            logger.info("✅ AI COMMANDS GENERATED SUCCESSFULLY")
            logger.info(f"📊 Total Commands: {total_commands}")
            logger.info("🔧 COMMANDS TO BE EXECUTED:")
            
            for category, cmd_list in validated_commands.items():
                if cmd_list:
                    logger.info(f"   📋 {category.upper()}:")
                    for i, cmd in enumerate(cmd_list, 1):
                        logger.info(f"      {i}. {cmd}")
            
            logger.info("="*80)
            
            return validated_commands
            
        except Exception as e:
            logger.error("Failed to generate AI commands", error=str(e))
            return self._get_fallback_commands(error_type, pod_name, namespace)
    
    def _prepare_context(self, error_type: str, pod_name: str, namespace: str, 
                        strategy: Dict[str, Any], real_k8s_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for GPT-4 command generation"""
        
        # Extract relevant data
        pod_spec = real_k8s_data.get("pod", {})
        events = real_k8s_data.get("events", [])
        logs = real_k8s_data.get("logs", [])
        
        # Get container info
        containers = pod_spec.get("spec", {}).get("containers", [])
        container_info = []
        
        for container in containers:
            container_info.append({
                "name": container.get("name"),
                "image": container.get("image"),
                "resources": container.get("resources", {})
            })
        
        # Extract error details from events
        error_messages = []
        for event in events[-5:]:  # Last 5 events
            if event.get("type") == "Warning":
                error_messages.append(event.get("message", ""))
        
        # Extract log errors
        log_errors = []
        for log in logs[-10:]:  # Last 10 log lines
            if any(keyword in log.lower() for keyword in ["error", "failed", "exit"]):
                log_errors.append(log)
        
        return {
            "error_type": error_type,
            "pod_name": pod_name,
            "namespace": namespace,
            "strategy": strategy,
            "container_info": container_info,
            "error_messages": error_messages,
            "log_errors": log_errors,
            "pod_phase": pod_spec.get("status", {}).get("phase", "Unknown")
        }
    
    async def _call_gpt4_for_commands(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Call GPT-4 to generate kubectl commands"""
        
        system_prompt = """You are a Kubernetes expert specializing in error resolution.
Generate kubectl commands to fix pod errors safely and effectively.

CRITICAL RULES FOR WINDOWS COMPATIBILITY:
1. NEVER use pipe commands (|) - they fail on Windows kubectl execution
2. NEVER use shell redirections (>) - they fail on Windows kubectl execution  
3. Use only direct kubectl commands without shell operators

ERROR-SPECIFIC STRATEGIES:

For ImagePullBackOff:
- Root Cause: Invalid/nonexistent image tag
- NEVER use "kubectl set image" for pods with --restart=Never (they are immutable)
- ALWAYS use delete+recreate strategy
- Working Fix: ["kubectl delete pod {pod_name} -n {namespace}", "kubectl run {pod_name} --image=nginx:latest --restart=Never -n {namespace}"]

For CrashLoopBackOff:
- Root Cause: Container exits with error
- If pod is managed by Deployment: Use "kubectl patch deployment" or "kubectl scale" 
- For standalone pods: Use kubectl delete+recreate
- NEVER create new pods with same name as deployment-managed pods

WORKING COMMAND EXAMPLES:
✅ kubectl get pod podname -n namespace
✅ kubectl delete pod podname -n namespace  
✅ kubectl run newpodname --image=nginx:latest --restart=Never -n namespace
✅ kubectl scale deployment deploymentname --replicas=0 -n namespace
✅ kubectl scale deployment deploymentname --replicas=1 -n namespace
✅ kubectl describe pod podname -n namespace
❌ kubectl describe pod podname | grep "Image"  (pipe fails)
❌ kubectl get pod podname -o yaml > backup.yaml  (redirection fails)
❌ kubectl run existing-pod-name (pod already exists error)

Output format (use ONLY working commands):
{
    "backup_commands": ["kubectl get pod {pod_name} -n {namespace} -o yaml"],
    "fix_commands": ["simple_working_fix_command"],
    "validation_commands": ["kubectl get pod {pod_name} -n {namespace}", "kubectl describe pod {pod_name} -n {namespace}"],
    "rollback_commands": ["kubectl delete pod {pod_name} -n {namespace}"]
}"""

        # Check if this is a standalone pod or deployment-managed pod
        pod_name = context['pod_name']
        is_deployment_pod = '-' in pod_name and len(pod_name.split('-')) >= 3
        
        deployment_warning = ""
        if is_deployment_pod:
            deployment_warning = """
IMPORTANT: This pod appears to be managed by a Deployment (name contains hash suffix).
DO NOT create new pods with same name - they will conflict!
Use deployment-level fixes: kubectl scale, kubectl patch deployment, etc.
"""
        else:
            deployment_warning = """
IMPORTANT: This appears to be a standalone Pod (simple name without deployment hash).
Use pod-level fixes: kubectl delete pod, kubectl run, etc.
"""

        human_prompt = f"""Generate kubectl commands to fix this Kubernetes error:

ERROR TYPE: {context['error_type']}
POD NAME: {context['pod_name']}
NAMESPACE: {context['namespace']}
POD PHASE: {context['pod_phase']}

{deployment_warning}

STRATEGY: {context['strategy']['type']} (confidence: {context['strategy'].get('confidence', 0.0)})

CONTAINERS:
{json.dumps(context['container_info'], indent=2)}

ERROR MESSAGES:
{json.dumps(context['error_messages'], indent=2)}

LOG ERRORS:
{json.dumps(context['log_errors'], indent=2)}

Generate safe, effective kubectl commands following the specified JSON format."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Parse JSON response
        try:
            commands = json.loads(response.content)
            return commands
        except json.JSONDecodeError:
            logger.info("GPT-4 response contains JSON wrapper, extracting...")
            # Try to extract JSON from response
            return self._extract_json_from_response(response.content)
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, List[str]]:
        """Extract JSON from GPT-4 response text"""
        
        try:
            # Find JSON block in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        logger.warning("Could not extract JSON from GPT-4 response")
        return self._get_empty_command_structure()
    
    def _validate_command_structure(self, commands: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Validate and fix command structure"""
        
        required_keys = ["backup_commands", "fix_commands", "validation_commands", "rollback_commands"]
        
        # Ensure all required keys exist
        for key in required_keys:
            if key not in commands:
                commands[key] = []
        
        # Validate command format
        for key, command_list in commands.items():
            if not isinstance(command_list, list):
                logger.warning(f"Invalid command format for {key}, converting to list")
                commands[key] = [str(command_list)] if command_list else []
        
        return commands
    
    def _get_fallback_commands(self, error_type: str, pod_name: str, namespace: str) -> Dict[str, List[str]]:
        """Get fallback commands when AI generation fails"""
        
        logger.info("Using fallback commands", error_type=error_type)
        
        if error_type == "ImagePullBackOff":
            return {
                "backup_commands": [
                    f"kubectl get pod {pod_name} -n {namespace} -o yaml"
                ],
                "fix_commands": [
                    f"kubectl delete pod {pod_name} -n {namespace}",
                    f"kubectl run {pod_name} --image=nginx:latest --restart=Never -n {namespace}"
                ],
                "validation_commands": [
                    f"kubectl get pod {pod_name} -n {namespace}",
                    f"kubectl describe pod {pod_name} -n {namespace}"
                ],
                "rollback_commands": [
                    f"kubectl delete pod {pod_name} -n {namespace}"
                ]
            }
        
        elif error_type == "CrashLoopBackOff":
            return {
                "backup_commands": [
                    f"kubectl get pod {pod_name} -n {namespace} -o yaml > /tmp/{pod_name}-backup.yaml"
                ],
                "fix_commands": [
                    f"kubectl patch pod {pod_name} -n {namespace} -p '{{\"spec\":{{\"containers\":[{{\"name\":\"main\",\"resources\":{{\"limits\":{{\"memory\":\"512Mi\"}}}}}}]}}}}'",
                    f"kubectl delete pod {pod_name} -n {namespace}"
                ],
                "validation_commands": [
                    f"kubectl get pod {pod_name} -n {namespace}",
                    f"kubectl wait --for=condition=Ready pod/{pod_name} -n {namespace} --timeout=60s"
                ],
                "rollback_commands": [
                    f"kubectl apply -f /tmp/{pod_name}-backup.yaml"
                ]
            }
        
        return self._get_empty_command_structure()
    
    def _get_empty_command_structure(self) -> Dict[str, List[str]]:
        """Get empty command structure"""
        return {
            "backup_commands": [],
            "fix_commands": [],
            "validation_commands": [],
            "rollback_commands": []
        }
    
    async def test_command_generation(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test command generation with various scenarios"""
        
        logger.info("Testing AI command generation", test_cases=len(test_cases))
        
        results = []
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test case {i+1}/{len(test_cases)}")
            
            try:
                commands = await self.generate_kubectl_commands(
                    error_type=test_case["error_type"],
                    pod_name=test_case["pod_name"],
                    namespace=test_case["namespace"],
                    strategy=test_case["strategy"],
                    real_k8s_data=test_case["real_k8s_data"]
                )
                
                results.append({
                    "test_case": i + 1,
                    "success": True,
                    "commands": commands,
                    "total_commands": sum(len(cmds) for cmds in commands.values())
                })
                
            except Exception as e:
                results.append({
                    "test_case": i + 1,
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate success rate
        success_count = sum(1 for r in results if r["success"])
        success_rate = success_count / len(results) if results else 0
        
        return {
            "total_tests": len(test_cases),
            "successful_tests": success_count,
            "success_rate": success_rate,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }