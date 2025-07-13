"""
YAML Manifest Generator - AI-Powered Kubernetes Manifest Generation
"""
import json
import yaml
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = structlog.get_logger()
logger.info("📄 YAML Manifest Generator module loaded - Full control over K8s resources")


class YAMLManifestGenerator:
    """AI-powered Kubernetes manifest generator using GPT-4"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model,
            temperature=0.3,
            timeout=60
        )
        
    async def generate_fix_manifest(self, 
                                   error_type: str,
                                   pod_name: str,
                                   namespace: str,
                                   strategy: Dict[str, Any],
                                   real_k8s_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete YAML manifest to fix Kubernetes errors
        
        Args:
            error_type: Type of Kubernetes error
            pod_name: Name of the failing pod
            namespace: Kubernetes namespace
            strategy: Selected strategy from reflexion
            real_k8s_data: Real Kubernetes data (pod spec, events, logs)
            
        Returns:
            Dictionary containing:
            - manifest: The YAML manifest as a string
            - apply_command: kubectl apply command
            - validation_commands: List of validation commands
        """
        logger.info("="*80)
        logger.info("📄 YAML MANIFEST GENERATION START")
        logger.info(f"   📱 Pod: {pod_name} (namespace: {namespace})")
        logger.info(f"   🚨 Error Type: {error_type}")
        logger.info(f"   🎯 Strategy: {strategy.get('type', 'unknown')}")
        logger.info("="*80)
        
        try:
            # Get current pod spec
            current_pod_spec = real_k8s_data.get("pod_spec", {})
            
            # Generate fixed manifest using AI
            fixed_manifest = await self._generate_manifest_with_ai(
                error_type, pod_name, namespace, strategy, current_pod_spec, real_k8s_data
            )
            
            # Save manifest to file
            manifest_filename = f"{pod_name}-fixed-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"
            
            return {
                "manifest": fixed_manifest,
                "manifest_filename": manifest_filename,
                "delete_command": f"kubectl delete pod {pod_name} -n {namespace} --ignore-not-found=true",
                "apply_command": f"kubectl apply -f {manifest_filename}",
                "validation_commands": [
                    f"kubectl get pod {pod_name} -n {namespace}",
                    f"kubectl describe pod {pod_name} -n {namespace}",
                    f"kubectl logs {pod_name} -n {namespace} --tail=50"
                ]
            }
            
        except Exception as e:
            logger.error("Failed to generate YAML manifest", error=str(e))
            return self._get_fallback_manifest(error_type, pod_name, namespace, real_k8s_data)
    
    async def _generate_manifest_with_ai(self, error_type: str, pod_name: str, 
                                       namespace: str, strategy: Dict[str, Any],
                                       current_pod_spec: Dict[str, Any],
                                       real_k8s_data: Dict[str, Any]) -> str:
        """Generate fixed manifest using AI"""
        
        system_prompt = """You are a Kubernetes expert specializing in manifest generation.
Generate complete, valid YAML manifests to fix Kubernetes pod errors.

ERROR-SPECIFIC FIX STRATEGIES:

1. ImagePullBackOff:
   - Change image to a valid one (nginx:latest, busybox:latest, alpine:latest)
   - Keep all other specifications intact
   - Preserve existing labels, annotations, volumes, etc.

2. OOMKilled:
   - Increase memory limits significantly (2x-5x original)
   - If no limits exist, add reasonable ones (memory: 256Mi, cpu: 200m)
   - Keep resource requests lower than limits
   - Preserve all other pod configurations

3. CrashLoopBackOff:
   - Fix command/args if they're causing crashes
   - Increase resource limits if needed
   - Add proper health checks
   - Consider changing restart policy if appropriate

4. CreateContainerConfigError:
   - Fix volume mounts (ensure paths exist)
   - Fix environment variables
   - Fix security contexts
   - Fix config/secret references

5. ErrImagePull:
   - Use public images that don't require authentication
   - Or add proper imagePullSecrets if needed

MANIFEST GENERATION RULES:
1. Generate COMPLETE pod manifests, not patches
2. Include apiVersion, kind, metadata, and spec
3. Preserve existing good configurations
4. Fix ONLY the problematic parts
5. Ensure all YAML is valid and properly indented
6. Add helpful comments explaining the fixes

OUTPUT FORMAT:
Return ONLY the YAML manifest without any additional text or markdown code blocks.
The output should be directly usable with kubectl apply -f."""

        # Check if deployment-managed
        is_deployment_pod = self._is_deployment_managed(pod_name)
        
        deployment_note = ""
        if is_deployment_pod:
            deployment_note = """
NOTE: This pod appears to be deployment-managed. Consider creating a Deployment manifest instead of a Pod manifest for better management."""
        
        # Extract current configuration
        current_config = {
            "containers": current_pod_spec.get("spec", {}).get("containers", []),
            "volumes": current_pod_spec.get("spec", {}).get("volumes", []),
            "labels": current_pod_spec.get("metadata", {}).get("labels", {}),
            "annotations": current_pod_spec.get("metadata", {}).get("annotations", {}),
        }
        
        # Get lessons learned
        lessons = real_k8s_data.get("lessons_learned", [])
        lessons_text = "\n".join([f"- {lesson}" for lesson in lessons]) if lessons else "None"
        
        human_prompt = f"""Generate a complete Kubernetes manifest to fix this error:

ERROR TYPE: {error_type}
POD NAME: {pod_name}
NAMESPACE: {namespace}
{deployment_note}

CURRENT POD CONFIGURATION:
{yaml.dump(current_config, default_flow_style=False)}

ERROR DETAILS:
- Error Messages: {json.dumps(real_k8s_data.get('events', []), indent=2)}
- Container Status: {json.dumps(real_k8s_data.get('container_statuses', []), indent=2)}

REFLEXION LESSONS LEARNED:
{lessons_text}

SELECTED STRATEGY: {strategy.get('type', 'unknown')} (confidence: {strategy.get('confidence', 0)})

Generate a complete, fixed pod manifest that resolves the {error_type} error."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Log the generated YAML for debugging
        logger.info("=" * 80)
        logger.info("📄 AI GENERATED YAML MANIFEST:")
        logger.info("=" * 80)
        logger.info(response.content)
        logger.info("=" * 80)
        
        # Validate the generated YAML
        try:
            yaml.safe_load(response.content)
            logger.info("✅ Generated valid YAML manifest")
            return response.content
        except yaml.YAMLError as e:
            logger.error("Generated invalid YAML", error=str(e))
            logger.error("Invalid YAML content:")
            logger.error(response.content)
            raise
    
    def _is_deployment_managed(self, pod_name: str) -> bool:
        """Check if pod is managed by a deployment"""
        return (
            '-' in pod_name and 
            len(pod_name.split('-')) >= 3 and
            any(len(part) >= 5 and part.replace('-', '').isalnum() 
                for part in pod_name.split('-')[-2:])
        )
    
    def _get_fallback_manifest(self, error_type: str, pod_name: str, 
                              namespace: str, real_k8s_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback manifest for common errors"""
        
        base_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": namespace,
                "labels": {
                    "app": pod_name,
                    "fixed-by": "reflexion-system",
                    "fix-timestamp": datetime.now().isoformat()
                }
            },
            "spec": {
                "containers": [{
                    "name": pod_name,
                    "image": "nginx:latest",
                    "resources": {
                        "limits": {
                            "memory": "256Mi",
                            "cpu": "200m"
                        },
                        "requests": {
                            "memory": "128Mi",
                            "cpu": "100m"
                        }
                    }
                }],
                "restartPolicy": "Always"
            }
        }
        
        # Customize based on error type
        if error_type == "OOMKilled":
            base_manifest["spec"]["containers"][0]["resources"]["limits"]["memory"] = "512Mi"
            base_manifest["spec"]["containers"][0]["resources"]["requests"]["memory"] = "256Mi"
        
        manifest_yaml = yaml.dump(base_manifest, default_flow_style=False)
        manifest_filename = f"{pod_name}-fallback-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"
        
        logger.warning("Using fallback manifest due to AI generation failure")
        
        return {
            "manifest": manifest_yaml,
            "manifest_filename": manifest_filename,
            "delete_command": f"kubectl delete pod {pod_name} -n {namespace} --ignore-not-found=true",
            "apply_command": f"kubectl apply -f {manifest_filename}",
            "validation_commands": [
                f"kubectl get pod {pod_name} -n {namespace}",
                f"kubectl describe pod {pod_name} -n {namespace}"
            ]
        }