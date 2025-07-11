package executor

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"
)

// KubectlExecutor handles execution of kubectl commands
type KubectlExecutor struct {
	dryRun  bool
	timeout time.Duration
}

// CommandResult represents the result of a kubectl command execution
type CommandResult struct {
	Command    string `json:"command"`
	Success    bool   `json:"success"`
	Output     string `json:"output"`
	Error      string `json:"error,omitempty"`
	Duration   string `json:"duration"`
	ExecutedAt string `json:"executed_at"`
}

// ExecutionReport represents the complete execution report
type ExecutionReport struct {
	PodName       string          `json:"pod_name"`
	Namespace     string          `json:"namespace"`
	ErrorType     string          `json:"error_type"`
	TotalCommands int             `json:"total_commands"`
	SuccessCount  int             `json:"success_count"`
	FailureCount  int             `json:"failure_count"`
	Duration      string          `json:"duration"`
	Commands      []CommandResult `json:"commands"`
	Status        string          `json:"status"` // "success", "partial", "failed"
}

// NewKubectlExecutor creates a new kubectl executor
func NewKubectlExecutor(dryRun bool, timeout time.Duration) *KubectlExecutor {
	return &KubectlExecutor{
		dryRun:  dryRun,
		timeout: timeout,
	}
}

// ExecuteCommands executes a list of kubectl commands in sequence
func (e *KubectlExecutor) ExecuteCommands(ctx context.Context, commands []string, podName, namespace, errorType string) (*ExecutionReport, error) {
	startTime := time.Now()
	
	log.Printf("🔧 Starting kubectl command execution for pod: %s (dry-run: %v)", podName, e.dryRun)
	
	report := &ExecutionReport{
		PodName:       podName,
		Namespace:     namespace,
		ErrorType:     errorType,
		TotalCommands: len(commands),
		Commands:      make([]CommandResult, 0, len(commands)),
		Status:        "running",
	}
	
	// Execute each command
	for i, command := range commands {
		log.Printf("📋 Executing command %d/%d: %s", i+1, len(commands), command)
		
		result := e.executeCommand(ctx, command, podName, namespace)
		report.Commands = append(report.Commands, result)
		
		if result.Success {
			report.SuccessCount++
			log.Printf("✅ Command %d succeeded: %s", i+1, strings.Split(command, " ")[0])
		} else {
			report.FailureCount++
			log.Printf("❌ Command %d failed: %s - Error: %s", i+1, strings.Split(command, " ")[0], result.Error)
			
			// For critical commands (like backup), continue execution
			// For fix commands, we might want to stop on failure
			if strings.Contains(command, "kubectl delete") || strings.Contains(command, "kubectl apply") {
				log.Printf("⚠️  Critical command failed, continuing with caution...")
			}
		}
	}
	
	// Calculate final status
	if report.FailureCount == 0 {
		report.Status = "success"
	} else if report.SuccessCount > 0 {
		report.Status = "partial"
	} else {
		report.Status = "failed"
	}
	
	report.Duration = time.Since(startTime).String()
	
	log.Printf("📊 Execution completed for pod %s: %s (%d/%d commands succeeded)", 
		podName, report.Status, report.SuccessCount, report.TotalCommands)
	
	return report, nil
}

// executeCommand executes a single kubectl command
func (e *KubectlExecutor) executeCommand(ctx context.Context, command, podName, namespace string) CommandResult {
	startTime := time.Now()
	
	result := CommandResult{
		Command:    command,
		Success:    false,
		ExecutedAt: startTime.Format(time.RFC3339),
	}
	
	// Log command execution
	log.Printf("🔄 Executing: %s", command)
	
	// Handle dry-run mode
	if e.dryRun {
		result.Output = fmt.Sprintf("DRY-RUN: Would execute: %s", command)
		result.Success = true
		result.Duration = time.Since(startTime).String()
		log.Printf("🧪 DRY-RUN: %s", command)
		return result
	}
	
	// Create execution context with timeout
	execCtx, cancel := context.WithTimeout(ctx, e.timeout)
	defer cancel()
	
	// Parse command
	parts := strings.Fields(command)
	if len(parts) == 0 {
		result.Error = "Empty command"
		result.Duration = time.Since(startTime).String()
		return result
	}
	
	// Handle watch commands that can hang indefinitely
	if strings.Contains(command, "-w") || strings.Contains(command, "--watch") {
		// Remove watch flag and add timeout
		var filteredParts []string
		for _, part := range parts {
			if part != "-w" && part != "--watch" {
				filteredParts = append(filteredParts, part)
			}
		}
		parts = filteredParts
		log.Printf("🔧 Removed watch flag from command for timeout safety")
	}
	
	// Execute command
	cmd := exec.CommandContext(execCtx, parts[0], parts[1:]...)
	cmd.Env = os.Environ()
	
	output, err := cmd.CombinedOutput()
	result.Output = string(output)
	result.Duration = time.Since(startTime).String()
	
	if err != nil {
		result.Error = err.Error()
		result.Success = false
		log.Printf("❌ Command failed: %s | Error: %s", command, err.Error())
	} else {
		result.Success = true
		log.Printf("✅ Command succeeded: %s | Duration: %s", command, result.Duration)
		if len(result.Output) > 0 && len(result.Output) < 200 {
			log.Printf("📄 Output: %s", strings.TrimSpace(result.Output))
		}
	}
	
	return result
}

// IsKubectlAvailable checks if kubectl is available in the system
func (e *KubectlExecutor) IsKubectlAvailable() bool {
	cmd := exec.Command("kubectl", "version", "--client")
	err := cmd.Run()
	return err == nil
}

// ValidateKubernetesConnection validates connection to Kubernetes cluster
func (e *KubectlExecutor) ValidateKubernetesConnection() error {
	cmd := exec.Command("kubectl", "cluster-info")
	output, err := cmd.CombinedOutput()
	
	if err != nil {
		return fmt.Errorf("kubectl cluster connection failed: %v\nOutput: %s", err, string(output))
	}
	
	log.Printf("✅ kubectl cluster connection validated")
	return nil
}

// GetPodStatus gets the current status of a pod
func (e *KubectlExecutor) GetPodStatus(podName, namespace string) (string, error) {
	cmd := exec.Command("kubectl", "get", "pod", podName, "-n", namespace, "-o", "jsonpath={.status.phase}")
	output, err := cmd.CombinedOutput()
	
	if err != nil {
		return "", fmt.Errorf("failed to get pod status: %v", err)
	}
	
	return strings.TrimSpace(string(output)), nil
}

// WaitForPodReady waits for a pod to become ready or timeout
func (e *KubectlExecutor) WaitForPodReady(podName, namespace string, timeout time.Duration) error {
	log.Printf("⏳ Waiting for pod %s to become ready (timeout: %v)", podName, timeout)
	
	cmd := exec.Command("kubectl", "wait", "--for=condition=Ready", fmt.Sprintf("pod/%s", podName), "-n", namespace, 
		fmt.Sprintf("--timeout=%ds", int(timeout.Seconds())))
	
	output, err := cmd.CombinedOutput()
	
	if err != nil {
		return fmt.Errorf("pod did not become ready within timeout: %v\nOutput: %s", err, string(output))
	}
	
	log.Printf("✅ Pod %s is now ready", podName)
	return nil
}