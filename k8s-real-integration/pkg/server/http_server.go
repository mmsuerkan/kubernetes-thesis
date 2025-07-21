package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"k8s-real-integration-go/pkg/executor"
)

// HTTPServer handles HTTP requests for kubectl command execution
type HTTPServer struct {
	port     int
	executor *executor.KubectlExecutor
}

// ExecuteCommandsRequest represents the request for executing kubectl commands
type ExecuteCommandsRequest struct {
	PodName   string              `json:"pod_name"`
	Namespace string              `json:"namespace"`
	ErrorType string              `json:"error_type"`
	Commands  map[string][]string `json:"commands"`
	DryRun    bool                `json:"dry_run"`
	Timeout   int                 `json:"timeout"` // seconds
}

// ExecuteCommandsResponse represents the response after executing kubectl commands
type ExecuteCommandsResponse struct {
	PodName       string                    `json:"pod_name"`
	Namespace     string                    `json:"namespace"`
	ErrorType     string                    `json:"error_type"`
	TotalCommands int                       `json:"total_commands"`
	SuccessCount  int                       `json:"success_count"`
	FailureCount  int                       `json:"failure_count"`
	Duration      string                    `json:"duration"`
	Status        string                    `json:"status"`
	Report        *executor.ExecutionReport `json:"report"`
	Commands      []executor.CommandResult  `json:"commands"`
	Message       string                    `json:"message"`
}

// NewHTTPServer creates a new HTTP server for kubectl command execution
func NewHTTPServer(port int, dryRun bool, timeout time.Duration) *HTTPServer {
	return &HTTPServer{
		port:     port,
		executor: executor.NewKubectlExecutor(dryRun, timeout),
	}
}

// Start starts the HTTP server
func (s *HTTPServer) Start() error {
	// Validate kubectl availability
	if !s.executor.IsKubectlAvailable() {
		return fmt.Errorf("kubectl is not available in system PATH")
	}

	// Validate Kubernetes connection
	if err := s.executor.ValidateKubernetesConnection(); err != nil {
		return fmt.Errorf("kubernetes connection validation failed: %v", err)
	}

	// Setup HTTP routes
	http.HandleFunc("/api/v1/execute-commands", s.handleExecuteCommands)
	http.HandleFunc("/api/v1/health", s.handleHealth)
	http.HandleFunc("/api/v1/kubectl-status", s.handleKubectlStatus)

	log.Printf("🚀 Starting HTTP server on port %d", s.port)
	return http.ListenAndServe(fmt.Sprintf(":%d", s.port), nil)
}

// handleExecuteCommands handles kubectl command execution requests
func (s *HTTPServer) handleExecuteCommands(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	log.Printf("📋 Received kubectl command execution request")

	// Parse request
	var req ExecuteCommandsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("❌ Failed to parse request: %v", err)
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	// Validate request
	if req.PodName == "" || req.ErrorType == "" {
		http.Error(w, "Missing required fields: pod_name, error_type", http.StatusBadRequest)
		return
	}

	// Set defaults
	if req.Namespace == "" {
		req.Namespace = "default"
	}
	if req.Timeout == 0 {
		req.Timeout = 60 // 60 seconds default
	}

	log.Printf("🔧 Executing kubectl commands for pod: %s (error: %s, dry-run: %v)",
		req.PodName, req.ErrorType, req.DryRun)

	// Execute commands in correct order: backup -> fix -> validation (skip rollback)
	var allCommands []string
	executionOrder := []string{"backup_commands", "fix_commands", "validation_commands"}

	for _, category := range executionOrder {
		if commands, exists := req.Commands[category]; exists {
			log.Printf("📂 Category: %s - %d commands", category, len(commands))
			allCommands = append(allCommands, commands...)
		}
	}

	// Execute commands with timeout
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(req.Timeout)*time.Second)
	defer cancel()

	report, err := s.executor.ExecuteCommands(ctx, allCommands, req.PodName, req.Namespace, req.ErrorType)
	if err != nil {
		log.Printf("❌ Command execution failed: %v", err)
		http.Error(w, fmt.Sprintf("Command execution failed: %v", err), http.StatusInternalServerError)
		return
	}

	// Prepare response
	response := ExecuteCommandsResponse{
		PodName:       req.PodName,
		Namespace:     req.Namespace,
		ErrorType:     req.ErrorType,
		TotalCommands: len(allCommands),
		SuccessCount:  report.SuccessCount,
		FailureCount:  report.FailureCount,
		Duration:      report.Duration,
		Status:        report.Status,
		Report:        report,
		Commands:      report.Commands,
		Message:       fmt.Sprintf("Executed %d commands for %s: %s", len(allCommands), req.ErrorType, report.Status),
	}

	// Set response headers
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	// Send response
	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("❌ Failed to encode response: %v", err)
	} else {
		log.Printf("✅ kubectl command execution completed: %s (%d/%d succeeded)",
			report.Status, report.SuccessCount, report.TotalCommands)
	}
}

// handleHealth handles health check requests
func (s *HTTPServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	health := map[string]interface{}{
		"status":            "healthy",
		"timestamp":         time.Now().Format(time.RFC3339),
		"service":           "kubectl-executor",
		"kubectl_available": s.executor.IsKubectlAvailable(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(health)
}

// handleKubectlStatus handles kubectl status requests
func (s *HTTPServer) handleKubectlStatus(w http.ResponseWriter, r *http.Request) {
	status := map[string]interface{}{
		"kubectl_available": s.executor.IsKubectlAvailable(),
		"timestamp":         time.Now().Format(time.RFC3339),
	}

	// Test Kubernetes connection
	if err := s.executor.ValidateKubernetesConnection(); err != nil {
		status["kubernetes_connection"] = false
		status["kubernetes_error"] = err.Error()
	} else {
		status["kubernetes_connection"] = true
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}
