package watcher

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	v1 "k8s.io/api/core/v1"

	"k8s-real-integration-go/pkg/k8s"
	"k8s-real-integration-go/pkg/reflexion"
)

// PodWatcher monitors Kubernetes pods for errors
type PodWatcher struct {
	k8sClient       *k8s.Client
	reflexionClient *reflexion.Client
	namespace       string
	processedPods   map[string]bool
	mutex           sync.RWMutex
	stopCh          chan struct{}
}

// NewPodWatcher creates a new pod watcher
func NewPodWatcher(k8sClient *k8s.Client, reflexionClient *reflexion.Client, namespace string) *PodWatcher {
	return &PodWatcher{
		k8sClient:       k8sClient,
		reflexionClient: reflexionClient,
		namespace:       namespace,
		processedPods:   make(map[string]bool),
		stopCh:          make(chan struct{}),
	}
}

// Start begins watching pods
func (pw *PodWatcher) Start() error {
	log.Printf("🔍 Starting pod watcher for namespace: %s", pw.namespace)

	// Test connection first
	if err := pw.k8sClient.TestConnection(); err != nil {
		return fmt.Errorf("failed to connect to Kubernetes: %w", err)
	}

	// Start the watch loop
	go pw.watchLoop()

	// Start periodic full scan
	go pw.periodicScan()

	log.Printf("✅ Pod watcher started successfully")
	return nil
}

// Stop stops the pod watcher
func (pw *PodWatcher) Stop() {
	log.Printf("🛑 Stopping pod watcher...")
	close(pw.stopCh)
}

// watchLoop continuously watches for pod changes
func (pw *PodWatcher) watchLoop() {
	for {
		select {
		case <-pw.stopCh:
			log.Printf("📴 Pod watcher stopped")
			return
		default:
			if err := pw.performWatch(); err != nil {
				log.Printf("❌ Watch error: %v", err)
				time.Sleep(5 * time.Second) // Wait before retry
			}
		}
	}
}

// performWatch performs the actual pod watching
func (pw *PodWatcher) performWatch() error {
	// Get clientset (this is a simplified approach)
	// In a real implementation, you'd use the proper watch API
	
	// For now, we'll use a polling approach
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-pw.stopCh:
			return nil
		case <-ticker.C:
			if err := pw.scanPods(); err != nil {
				log.Printf("❌ Scan error: %v", err)
			}
		}
	}
}

// scanPods scans all pods in the namespace
func (pw *PodWatcher) scanPods() error {
	pods, err := pw.k8sClient.ListPods(pw.namespace)
	if err != nil {
		return fmt.Errorf("failed to list pods: %w", err)
	}

	log.Printf("🔍 Scanning %d pods in namespace %s", len(pods.Items), pw.namespace)

	for _, pod := range pods.Items {
		if pw.shouldProcessPod(&pod) {
			pw.processPod(&pod)
		}
	}

	return nil
}

// shouldProcessPod determines if a pod should be processed
func (pw *PodWatcher) shouldProcessPod(pod *v1.Pod) bool {
	// Use UID for unique pod identification (handles recreated pods with same name)
	podKey := fmt.Sprintf("%s/%s/%s", pod.Namespace, pod.Name, pod.UID)

	// Debug: Log pod status
	log.Printf("🔍 DEBUG: Pod %s (UID: %s) - Phase: %s, ContainerStatuses: %d", 
		pod.Name, string(pod.UID)[:8], pod.Status.Phase, len(pod.Status.ContainerStatuses))
	
	for i, containerStatus := range pod.Status.ContainerStatuses {
		log.Printf("🔍 DEBUG: Container %d - Ready: %t, State: %+v", 
			i, containerStatus.Ready, containerStatus.State)
		if containerStatus.State.Waiting != nil {
			log.Printf("🔍 DEBUG: Waiting reason: %s, message: %s", 
				containerStatus.State.Waiting.Reason, containerStatus.State.Waiting.Message)
		}
	}

	// Check if pod has failed
	isFailed := pw.k8sClient.IsPodFailed(pod)
	log.Printf("🔍 DEBUG: Pod %s IsPodFailed result: %t", pod.Name, isFailed)
	
	if !isFailed {
		return false
	}

	// Check if we've already processed this specific pod instance (by UID)
	pw.mutex.RLock()
	processed := pw.processedPods[podKey]
	pw.mutex.RUnlock()

	log.Printf("🔍 DEBUG: Pod %s (UID: %s) already processed: %t", pod.Name, string(pod.UID)[:8], processed)
	return !processed
}

// processPod processes a failed pod
func (pw *PodWatcher) processPod(pod *v1.Pod) {
	// Use UID for unique identification (same as shouldProcessPod)
	podKey := fmt.Sprintf("%s/%s/%s", pod.Namespace, pod.Name, pod.UID)
	errorType := pw.k8sClient.GetPodErrorType(pod)

	log.Printf("🚨 Processing failed pod: %s/%s (UID: %s), Error: %s", 
		pod.Namespace, pod.Name, string(pod.UID)[:8], errorType)

	// Mark as processed (by UID)
	pw.mutex.Lock()
	pw.processedPods[podKey] = true
	pw.mutex.Unlock()

	// Get additional data
	events, err := pw.k8sClient.GetPodEvents(pod.Namespace, pod.Name)
	if err != nil {
		log.Printf("❌ Failed to get events for pod %s: %v", podKey, err)
		events = []v1.Event{}
	}

	logs, err := pw.k8sClient.GetPodLogs(pod.Namespace, pod.Name)
	if err != nil {
		log.Printf("❌ Failed to get logs for pod %s: %v", podKey, err)
		logs = []string{"Failed to retrieve logs"}
	}

	// Send to reflexion service
	log.Printf("📡 Sending to reflexion service...")
	response, err := pw.reflexionClient.ProcessPodError(pod, events, logs, errorType)
	if err != nil {
		log.Printf("❌ Failed to process pod with reflexion: %v", err)
		return
	}
	log.Printf("✅ Response received from reflexion service")

	// Log the response
	log.Printf("✅ Reflexion completed for pod %s:", podKey)
	log.Printf("   📋 Workflow ID: %s", response.WorkflowID)
	log.Printf("   🎯 Strategy: %v", response.FinalStrategy["type"])
	log.Printf("   📊 Confidence: %v", response.FinalStrategy["confidence"])
	log.Printf("   ⏱️  Resolution Time: %.2fs", response.ResolutionTime)
	log.Printf("   🔍 Used Real K8s Data: %v", response.ReflexionSummary["used_real_k8s_data"])

	if response.RequiresHumanIntervention {
		log.Printf("🚨 Human intervention required for pod %s", podKey)
	} else {
		log.Printf("🤖 AI strategy available for pod %s", podKey)
		log.Printf("📄 YAML Manifest mode active - Python service handles pod fixing automatically")
		
		// YAML mode: Python service already processed the pod with YAML manifests
		// No need for separate kubectl command generation
	}
}

// periodicScan performs periodic full scans
func (pw *PodWatcher) periodicScan() {
	ticker := time.NewTicker(60 * time.Second) // Full scan every minute
	defer ticker.Stop()

	for {
		select {
		case <-pw.stopCh:
			return
		case <-ticker.C:
			log.Printf("🔄 Performing periodic full scan...")
			if err := pw.scanPods(); err != nil {
				log.Printf("❌ Periodic scan error: %v", err)
			}
		}
	}
}

// GetProcessedPods returns the list of processed pods
func (pw *PodWatcher) GetProcessedPods() []string {
	pw.mutex.RLock()
	defer pw.mutex.RUnlock()

	var pods []string
	for podKey := range pw.processedPods {
		pods = append(pods, podKey)
	}
	return pods
}

// ResetProcessedPods clears the processed pods list
func (pw *PodWatcher) ResetProcessedPods() {
	pw.mutex.Lock()
	defer pw.mutex.Unlock()

	pw.processedPods = make(map[string]bool)
	log.Printf("🔄 Processed pods list reset")
}

// generateAndExecuteCommands generates kubectl commands using AI and executes them
func (pw *PodWatcher) generateAndExecuteCommands(pod *v1.Pod, response *reflexion.ProcessPodErrorResponse, errorType string) error {
	log.Printf("🔧 Generating kubectl commands for pod %s", pod.Name)
	
	// Step 1: Call Python service to generate commands
	commands, err := pw.generateCommands(pod, response, errorType)
	if err != nil {
		return fmt.Errorf("failed to generate commands: %v", err)
	}
	
	log.Printf("✅ Generated %d command categories", len(commands))
	
	// Step 2: Execute commands via local HTTP server
	executionResult, err := pw.executeCommands(pod, commands, errorType)
	if err != nil {
		return fmt.Errorf("failed to execute commands: %v", err)
	}
	
	log.Printf("📊 Execution result: %s (%d/%d commands succeeded)", 
		executionResult.Status, executionResult.SuccessCount, executionResult.TotalCommands)
	
	// Step 3: Send execution feedback to Python service for reflexion
	err = pw.sendExecutionFeedback(pod, response, executionResult, errorType)
	if err != nil {
		log.Printf("⚠️  Failed to send execution feedback: %v", err)
		// Continue anyway, don't fail the whole process
	}
	
	// Step 4: If pod was successfully fixed, remove from processed list
	// This allows re-processing if the same pod fails again
	if executionResult.Status == "success" {
		podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
		pw.mutex.Lock()
		delete(pw.processedPods, podKey)
		pw.mutex.Unlock()
		log.Printf("✅ Pod %s successfully fixed, removed from processed list", podKey)
	}
	
	return nil
}

// generateCommands calls Python service to generate kubectl commands
func (pw *PodWatcher) generateCommands(pod *v1.Pod, response *reflexion.ProcessPodErrorResponse, errorType string) (map[string][]string, error) {
	// Prepare request for Python service
	requestData := map[string]interface{}{
		"pod_name":   pod.Name,
		"namespace":  pod.Namespace,
		"error_type": errorType,
		"strategy":   response.FinalStrategy,
		"real_k8s_data": map[string]interface{}{
			"pod_spec": map[string]interface{}{
				"containers": []map[string]interface{}{
					{
						"name":  pod.Spec.Containers[0].Name,
						"image": pod.Spec.Containers[0].Image,
					},
				},
			},
			"events": []map[string]interface{}{
				{
					"type":    "Warning",
					"message": fmt.Sprintf("Pod %s has %s error", pod.Name, errorType),
				},
			},
			"logs": []string{"Failed to retrieve logs"},
		},
		"dry_run": false,
	}
	
	// Convert to JSON
	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}
	
	// Make HTTP request to Python service
	pythonURL := "http://localhost:8000/api/v1/executor/generate-commands"
	resp, err := http.Post(pythonURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call Python service: %v", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Python service returned status %d", resp.StatusCode)
	}
	
	// Parse response
	var commandResponse struct {
		Commands map[string][]string `json:"commands"`
	}
	
	if err := json.NewDecoder(resp.Body).Decode(&commandResponse); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}
	
	return commandResponse.Commands, nil
}

// executeCommands calls Go HTTP server to execute kubectl commands
func (pw *PodWatcher) executeCommands(pod *v1.Pod, commands map[string][]string, errorType string) (*ExecutionResult, error) {
	// Prepare request for Go HTTP server
	requestData := map[string]interface{}{
		"pod_name":   pod.Name,
		"namespace":  pod.Namespace,
		"error_type": errorType,
		"commands":   commands,
		"dry_run":    false,
		"timeout":    120,
	}
	
	// Convert to JSON
	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}
	
	// Make HTTP request to local Go server
	goURL := "http://localhost:8080/api/v1/execute-commands"
	resp, err := http.Post(goURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to call Go HTTP server: %v", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Go HTTP server returned status %d", resp.StatusCode)
	}
	
	// Parse response
	var executionResult ExecutionResult
	if err := json.NewDecoder(resp.Body).Decode(&executionResult); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}
	
	return &executionResult, nil
}

// ExecutionResult represents the result of command execution
type ExecutionResult struct {
	PodName          string                   `json:"pod_name"`
	Namespace        string                   `json:"namespace"`
	ErrorType        string                   `json:"error_type"`
	TotalCommands    int                      `json:"total_commands"`
	SuccessCount     int                      `json:"success_count"`
	FailureCount     int                      `json:"failure_count"`
	Status           string                   `json:"status"`
	Message          string                   `json:"message"`
	Commands         []CommandResult          `json:"commands,omitempty"`
	ExecutedCommands []map[string]interface{} `json:"executed_commands,omitempty"`
}

// CommandResult represents individual command execution result
type CommandResult struct {
	Command    string `json:"command"`
	Success    bool   `json:"success"`
	Output     string `json:"output"`
	Error      string `json:"error"`
	Duration   string `json:"duration"`
	ExecutedAt string `json:"executed_at"`
}

// sendExecutionFeedback sends execution results back to Python service for reflexion
func (pw *PodWatcher) sendExecutionFeedback(pod *v1.Pod, response *reflexion.ProcessPodErrorResponse, executionResult *ExecutionResult, errorType string) error {
	log.Printf("🔄 Sending execution feedback for reflexion learning...")
	
	// Prepare feedback data
	feedbackData := map[string]interface{}{
		"workflow_id":     response.WorkflowID,
		"pod_name":        pod.Name,
		"namespace":       pod.Namespace,
		"error_type":      errorType,
		"strategy_used":   response.FinalStrategy,
		"execution_result": map[string]interface{}{
			"success":           executionResult.Status == "success",
			"partial_success":   executionResult.Status == "partial",
			"total_commands":    executionResult.TotalCommands,
			"success_count":     executionResult.SuccessCount,
			"failure_count":     executionResult.FailureCount,
			"status":            executionResult.Status,
			"commands":          executionResult.Commands,
			"executed_commands": executionResult.Commands, // For backward compatibility
		},
		"timestamp": time.Now().Format(time.RFC3339),
	}
	
	// Convert to JSON
	jsonData, err := json.Marshal(feedbackData)
	if err != nil {
		return fmt.Errorf("failed to marshal feedback: %v", err)
	}
	
	// Send to Python service reflexion endpoint
	pythonURL := "http://localhost:8000/api/v1/reflexion/execution-feedback"
	resp, err := http.Post(pythonURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to send feedback to Python service: %v", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Python service returned status %d for feedback", resp.StatusCode)
	}
	
	log.Printf("✅ Execution feedback sent for reflexion learning")
	return nil
}