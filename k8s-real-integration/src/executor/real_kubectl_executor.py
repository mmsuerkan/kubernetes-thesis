"""
Real Kubectl Executor - Gerçek kubectl komutlarını çalıştıran sistem
"""
import asyncio
import subprocess
import platform
import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
import yaml

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Kubectl komut sonucu"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    command: str
    timestamp: datetime

@dataclass
class CommandValidationResult:
    """Komut güvenlik validasyon sonucu"""
    is_safe: bool
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    warnings: List[str]
    blocked_reason: Optional[str] = None

class KubectlSecurityValidator:
    """Kubectl komutları için güvenlik validatörü"""
    
    def __init__(self):
        # Tamamen yasaklı komutlar (CRITICAL RISK)
        self.forbidden_commands = {
            "delete namespace",
            "delete node", 
            "delete persistentvolume",
            "delete pv",
            "delete clusterrole",
            "delete clusterrolebinding",
            "delete customresourcedefinition",
            "delete crd"
        }
        
        # Yüksek riskli komutlar (dikkatli kullanım)
        self.high_risk_patterns = [
            r"delete\s+deployment",
            r"delete\s+service",
            r"delete\s+configmap",
            r"delete\s+secret",
            r"scale\s+.*--replicas=0",
            r"patch\s+.*security",
            r"exec\s+.*",
            r"port-forward\s+.*"
        ]
        
        # Orta riskli komutlar
        self.medium_risk_patterns = [
            r"delete\s+pod",
            r"rollout\s+restart",
            r"patch\s+.*",
            r"scale\s+.*",
            r"annotate\s+.*",
            r"label\s+.*"
        ]
        
        # İzin verilen güvenli komutlar
        self.safe_commands = {
            "get", "describe", "logs", "top", "version", 
            "cluster-info", "api-resources", "api-versions"
        }
    
    def validate_command(self, command: str) -> CommandValidationResult:
        """Komutun güvenliğini değerlendir"""
        command_lower = command.lower().strip()
        warnings = []
        
        # Boş komut kontrolü
        if not command_lower:
            return CommandValidationResult(
                is_safe=False,
                risk_level="critical",
                warnings=["Empty command not allowed"],
                blocked_reason="Empty command"
            )
        
        # Kubectl komutu mu kontrolü
        if not command_lower.startswith("kubectl"):
            return CommandValidationResult(
                is_safe=False,
                risk_level="critical", 
                warnings=["Only kubectl commands are allowed"],
                blocked_reason="Non-kubectl command"
            )
        
        # Forbidden komutlar kontrolü
        for forbidden in self.forbidden_commands:
            if forbidden in command_lower:
                return CommandValidationResult(
                    is_safe=False,
                    risk_level="critical",
                    warnings=[f"Forbidden command detected: {forbidden}"],
                    blocked_reason=f"Contains forbidden operation: {forbidden}"
                )
        
        # Shell injection kontrolü
        dangerous_chars = [';', '&&', '||', '|', '>', '<', '$', '`']
        for char in dangerous_chars:
            if char in command:
                warnings.append(f"Potentially dangerous character: {char}")
        
        # Risk level belirleme
        risk_level = "low"
        
        # High risk patterns
        for pattern in self.high_risk_patterns:
            if re.search(pattern, command_lower):
                risk_level = "high"
                warnings.append(f"High risk pattern detected: {pattern}")
        
        # Medium risk patterns  
        if risk_level == "low":
            for pattern in self.medium_risk_patterns:
                if re.search(pattern, command_lower):
                    risk_level = "medium"
                    warnings.append(f"Medium risk pattern detected: {pattern}")
        
        # Safe commands
        command_parts = command_lower.split()
        if len(command_parts) >= 2 and command_parts[1] in self.safe_commands:
            risk_level = "low"
        
        return CommandValidationResult(
            is_safe=True,  # Yasaklı değilse güvenli sayıyoruz
            risk_level=risk_level,
            warnings=warnings
        )

class RealKubectlExecutor:
    """Gerçek kubectl komutlarını çalıştıran sınıf"""
    
    def __init__(self, 
                 dry_run: bool = False,
                 timeout: int = 120,
                 max_retries: int = 3):
        self.dry_run = dry_run
        self.timeout = timeout
        self.max_retries = max_retries
        self.security_validator = KubectlSecurityValidator()
        self.platform = platform.system().lower()
        
        # kubectl binary path detection
        self.kubectl_path = self._detect_kubectl_path()
        
        logger.info(f"🔧 RealKubectlExecutor initialized")
        logger.info(f"   Platform: {self.platform}")
        logger.info(f"   Kubectl path: {self.kubectl_path}")
        logger.info(f"   Dry run mode: {self.dry_run}")
        logger.info(f"   Timeout: {self.timeout}s")
    
    def _detect_kubectl_path(self) -> str:
        """kubectl binary path'ini tespit et"""
        try:
            if self.platform == "windows":
                result = subprocess.run(["where", "kubectl"], 
                                      capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run(["which", "kubectl"], 
                                      capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                kubectl_path = result.stdout.strip().split('\n')[0]
                logger.info(f"✅ kubectl found at: {kubectl_path}")
                return kubectl_path
            else:
                logger.warning("⚠️ kubectl not found in PATH, using 'kubectl'")
                return "kubectl"
                
        except Exception as e:
            logger.warning(f"⚠️ kubectl detection failed: {e}, using 'kubectl'")
            return "kubectl"
    
    async def execute_command(self, command: str, 
                            retry_on_failure: bool = True) -> ExecutionResult:
        """Tek kubectl komutunu çalıştır"""
        
        logger.info(f"🚀 EXECUTING KUBECTL COMMAND: {command}")
        
        # Güvenlik validasyonu
        validation = self.security_validator.validate_command(command)
        
        if not validation.is_safe:
            logger.error(f"🚫 COMMAND BLOCKED: {validation.blocked_reason}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Command blocked: {validation.blocked_reason}",
                exit_code=-1,
                execution_time=0,
                command=command,
                timestamp=datetime.now()
            )
        
        # Risk seviyesi logla
        if validation.risk_level == "high":
            logger.warning(f"⚠️ HIGH RISK COMMAND: {command}")
            for warning in validation.warnings:
                logger.warning(f"   - {warning}")
        elif validation.risk_level == "medium":
            logger.info(f"⚡ MEDIUM RISK COMMAND: {command}")
        
        # Dry run mode
        if self.dry_run:
            logger.info(f"🧪 DRY RUN MODE: Would execute: {command}")
            return ExecutionResult(
                success=True,
                stdout=f"[DRY RUN] Would execute: {command}",
                stderr="",
                exit_code=0,
                execution_time=0.1,
                command=command,
                timestamp=datetime.now()
            )
        
        # Gerçek execution
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                start_time = datetime.now()
                
                # Command'ı parçalara ayır
                cmd_parts = command.split()
                
                # subprocess ile çalıştır
                process = await asyncio.create_subprocess_exec(
                    *cmd_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=1024*1024  # 1MB limit
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=self.timeout
                    )
                    
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    stdout_str = stdout.decode('utf-8', errors='replace')
                    stderr_str = stderr.decode('utf-8', errors='replace')
                    
                    result = ExecutionResult(
                        success=process.returncode == 0,
                        stdout=stdout_str,
                        stderr=stderr_str,
                        exit_code=process.returncode,
                        execution_time=execution_time,
                        command=command,
                        timestamp=start_time
                    )
                    
                    if result.success:
                        logger.info(f"✅ COMMAND SUCCESS: {command}")
                        logger.info(f"   Execution time: {execution_time:.2f}s")
                        if stdout_str:
                            logger.info(f"   Output: {stdout_str[:200]}...")
                    else:
                        logger.error(f"❌ COMMAND FAILED: {command}")
                        logger.error(f"   Exit code: {process.returncode}")
                        logger.error(f"   Error: {stderr_str}")
                        
                        # Retry logic
                        if retry_on_failure and retry_count < self.max_retries:
                            retry_count += 1
                            logger.info(f"🔄 RETRYING ({retry_count}/{self.max_retries}): {command}")
                            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                            continue
                    
                    return result
                    
                except asyncio.TimeoutError:
                    logger.error(f"⏰ COMMAND TIMEOUT ({self.timeout}s): {command}")
                    process.kill()
                    await process.wait()
                    
                    return ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"Command timed out after {self.timeout} seconds",
                        exit_code=-2,
                        execution_time=self.timeout,
                        command=command,
                        timestamp=start_time
                    )
                    
            except Exception as e:
                logger.error(f"💥 COMMAND EXECUTION ERROR: {command}")
                logger.error(f"   Error: {str(e)}")
                
                if retry_on_failure and retry_count < self.max_retries:
                    retry_count += 1
                    logger.info(f"🔄 RETRYING ({retry_count}/{self.max_retries}): {command}")
                    await asyncio.sleep(2 ** retry_count)
                    continue
                
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution error: {str(e)}",
                    exit_code=-3,
                    execution_time=0,
                    command=command,
                    timestamp=datetime.now()
                )
        
        # Max retry'a ulaşıldı
        logger.error(f"🚫 MAX RETRIES EXCEEDED: {command}")
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Max retries ({self.max_retries}) exceeded",
            exit_code=-4,
            execution_time=0,
            command=command,
            timestamp=datetime.now()
        )
    
    async def execute_yaml_manifest(self,
                                  manifest_content: str,
                                  manifest_filename: str,
                                  delete_command: str,
                                  validation_commands: List[str]) -> Dict[str, Any]:
        """
        Execute a YAML manifest file
        
        Args:
            manifest_content: YAML content as string
            manifest_filename: Filename for the manifest
            delete_command: Command to delete existing pod
            validation_commands: Commands to validate after apply
            
        Returns:
            Dict with execution results
        """
        results = {
            "manifest_applied": False,
            "manifest_path": None,
            "delete_result": None,
            "apply_result": None,
            "validation_results": [],
            "cleanup_result": None
        }
        
        temp_dir = None
        try:
            # Create temporary directory for manifest
            temp_dir = tempfile.mkdtemp(prefix="k8s-manifest-")
            manifest_path = os.path.join(temp_dir, manifest_filename)
            
            # Write manifest to file
            with open(manifest_path, 'w') as f:
                f.write(manifest_content)
            
            logger.info(f"📄 Created manifest file: {manifest_path}")
            logger.info("📄 MANIFEST FILE CONTENT:")
            logger.info("=" * 60)
            logger.info(manifest_content)
            logger.info("=" * 60)
            results["manifest_path"] = manifest_path
            
            # First delete the existing pod
            logger.info("🗑️ Deleting existing pod...")
            delete_result = await self.execute_command(delete_command)
            results["delete_result"] = delete_result
            
            if delete_result.success:
                logger.info("✅ Pod deleted successfully")
                # Wait a moment for pod to be fully deleted
                await asyncio.sleep(2)
            else:
                logger.warning("⚠️ Pod deletion failed, continuing with apply...")
            
            # Apply the manifest
            apply_command = f"kubectl apply -f {manifest_path}"
            apply_result = await self.execute_command(apply_command)
            results["apply_result"] = apply_result
            
            if apply_result.success:
                logger.info("✅ Manifest applied successfully")
                results["manifest_applied"] = True
                
                # Run validation commands
                logger.info("🔍 Running validation commands...")
                for cmd in validation_commands:
                    val_result = await self.execute_command(cmd)
                    results["validation_results"].append(val_result)
            else:
                logger.error("❌ Failed to apply manifest")
                
        except Exception as e:
            logger.error(f"Error executing manifest: {str(e)}")
            results["error"] = str(e)
            
        finally:
            # Cleanup temporary file
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.info("🧹 Cleaned up temporary manifest file")
                    results["cleanup_result"] = "success"
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir: {str(e)}")
                    results["cleanup_result"] = f"failed: {str(e)}"
                    
        return results
    
    async def execute_command_sequence(self, 
                                     commands: List[str],
                                     stop_on_failure: bool = True) -> List[ExecutionResult]:
        """Komut dizisini sırayla çalıştır"""
        
        logger.info(f"🔗 EXECUTING COMMAND SEQUENCE: {len(commands)} commands")
        
        results = []
        
        for i, command in enumerate(commands, 1):
            logger.info(f"📋 Command {i}/{len(commands)}: {command}")
            
            result = await self.execute_command(command)
            results.append(result)
            
            if not result.success and stop_on_failure:
                logger.error(f"🛑 SEQUENCE STOPPED: Command {i} failed")
                break
            
            # Small delay between commands
            if i < len(commands):
                await asyncio.sleep(0.5)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"📊 SEQUENCE COMPLETE: {success_count}/{len(results)} successful")
        
        return results
    
    async def execute_kubectl_commands_dict(self, 
                                          commands_dict: Dict[str, List[str]]) -> Dict[str, List[ExecutionResult]]:
        """AI'dan gelen komut dictionary'sini çalıştır"""
        
        logger.info("🎯 EXECUTING AI GENERATED COMMANDS")
        logger.info(f"   Categories: {list(commands_dict.keys())}")
        
        all_results = {}
        
        # Execution order: backup -> fix -> validation -> rollback (if needed)
        execution_order = ["backup_commands", "fix_commands", "validation_commands", "rollback_commands"]
        
        for category in execution_order:
            if category in commands_dict and commands_dict[category]:
                logger.info(f"🔧 Executing {category}: {len(commands_dict[category])} commands")
                
                results = await self.execute_command_sequence(
                    commands_dict[category],
                    stop_on_failure=(category in ["backup_commands", "fix_commands"])
                )
                
                all_results[category] = results
                
                # Fix commands başarısızsa rollback yap
                if category == "fix_commands":
                    fix_success = all(r.success for r in results)
                    if not fix_success and "rollback_commands" in commands_dict:
                        logger.warning("🔄 FIX FAILED, EXECUTING ROLLBACK")
                        rollback_results = await self.execute_command_sequence(
                            commands_dict["rollback_commands"],
                            stop_on_failure=False
                        )
                        all_results["rollback_commands"] = rollback_results
                        break  # Rollback'ten sonra validation'a geçme
        
        return all_results
    
    def analyze_execution_results(self, 
                                results: Dict[str, List[ExecutionResult]]) -> Dict[str, Any]:
        """Execution sonuçlarını analiz et"""
        
        total_commands = sum(len(cmd_list) for cmd_list in results.values())
        successful_commands = sum(
            sum(1 for r in cmd_list if r.success) 
            for cmd_list in results.values()
        )
        
        total_time = sum(
            sum(r.execution_time for r in cmd_list)
            for cmd_list in results.values()
        )
        
        # Critical success: fix commands başarılı mı?
        fix_success = True
        if "fix_commands" in results:
            fix_success = all(r.success for r in results["fix_commands"])
        
        # Validation success: validation commands başarılı mı?
        validation_success = True
        if "validation_commands" in results:
            validation_success = all(r.success for r in results["validation_commands"])
        
        overall_success = fix_success and validation_success
        
        analysis = {
            "overall_success": overall_success,
            "fix_success": fix_success,
            "validation_success": validation_success,
            "total_commands": total_commands,
            "successful_commands": successful_commands,
            "success_rate": successful_commands / total_commands if total_commands > 0 else 0,
            "total_execution_time": total_time,
            "average_command_time": total_time / total_commands if total_commands > 0 else 0,
            "categories_executed": list(results.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
        # Error summary
        errors = []
        for category, cmd_results in results.items():
            for result in cmd_results:
                if not result.success:
                    errors.append({
                        "category": category,
                        "command": result.command,
                        "error": result.stderr,
                        "exit_code": result.exit_code
                    })
        
        analysis["errors"] = errors
        
        logger.info("📊 EXECUTION ANALYSIS:")
        logger.info(f"   Overall success: {overall_success}")
        logger.info(f"   Commands: {successful_commands}/{total_commands}")
        logger.info(f"   Total time: {total_time:.2f}s")
        logger.info(f"   Errors: {len(errors)}")
        
        return analysis