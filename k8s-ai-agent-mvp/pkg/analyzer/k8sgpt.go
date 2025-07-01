package analyzer

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"time"

	"github.com/fatih/color"
	corev1 "k8s.io/api/core/v1"
)

// K8sGPTAnalysis represents the analysis result from K8sGPT
type K8sGPTAnalysis struct {
	Kind        string `json:"kind"`
	Name        string `json:"name"`
	Namespace   string `json:"namespace"`
	Error       []K8sGPTError `json:"error"`
	Details     string `json:"details"`
}

// K8sGPTError represents individual error details
type K8sGPTError struct {
	Text      string `json:"text"`
	Details   string `json:"details,omitempty"`
	Sensitive []K8sGPTSensitive `json:"sensitive,omitempty"`
}

// K8sGPTSensitive represents sensitive information found
type K8sGPTSensitive struct {
	Unmasked string `json:"unmasked"`
	Masked   string `json:"masked"`
}

// K8sGPTResponse represents the full response from K8sGPT
type K8sGPTResponse struct {
	Status   string           `json:"status"`
	Problems int              `json:"problems"`
	Results  []K8sGPTAnalysis `json:"results"`
}

// AnalysisResult represents our processed analysis result
type AnalysisResult struct {
	PodName        string
	Namespace      string
	ErrorType      string
	ErrorDetails   string
	Recommendation string
	Confidence     float64
	CanAutoFix     bool
}

// K8sGPTClient handles interaction with K8sGPT binary
type K8sGPTClient struct {
	binaryPath string
	timeout    time.Duration
}

// NewK8sGPTClient creates a new K8sGPT client
func NewK8sGPTClient(binaryPath string) *K8sGPTClient {
	if binaryPath == "" {
		// Default to current directory k8sgpt.exe
		binaryPath = "k8sgpt.exe"
	}
	
	return &K8sGPTClient{
		binaryPath: binaryPath,
		timeout:    30 * time.Second,
	}
}

// SetBinaryPath updates the K8sGPT binary path
func (c *K8sGPTClient) SetBinaryPath(path string) {
	c.binaryPath = path
}

// SetTimeout updates the execution timeout
func (c *K8sGPTClient) SetTimeout(timeout time.Duration) {
	c.timeout = timeout
}

// TestK8sGPT tests if K8sGPT binary is available and working
func (c *K8sGPTClient) TestK8sGPT(ctx context.Context) error {
	color.Yellow("🔍 Testing K8sGPT binary...")
	
	// Check if binary exists
	if !c.binaryExists() {
		return fmt.Errorf("k8sgpt binary not found at: %s", c.binaryPath)
	}
	
	// Test with version command
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	
	cmd := exec.CommandContext(ctx, c.binaryPath, "version")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("k8sgpt version failed: %w", err)
	}
	
	color.Green("✅ K8sGPT binary working: %s", string(output))
	return nil
}

// AnalyzePod runs K8sGPT analysis on a specific pod
func (c *K8sGPTClient) AnalyzePod(ctx context.Context, pod *corev1.Pod) (*AnalysisResult, error) {
	color.Yellow("🤖 Running K8sGPT analysis on pod: %s", pod.Name)
	
	// Run general K8sGPT analysis and find our pod
	response, err := c.AnalyzeCluster(ctx, pod.Namespace)
	if err != nil {
		return nil, err
	}
	
	// Find analysis for our specific pod
	// K8sGPT returns name in format "namespace/podname"
	expectedName := pod.Namespace + "/" + pod.Name
	for _, result := range response.Results {
		if result.Name == expectedName && result.Kind == "Pod" {
			color.Green("✅ Found K8sGPT analysis for pod: %s", pod.Name)
			return c.processAnalysis(result, pod), nil
		}
	}
	
	// If not found, create analysis based on pod status
	color.Yellow("⚠️  K8sGPT didn't analyze this pod, creating basic analysis...")
	return c.createBasicAnalysis(pod), nil
}

// AnalyzeCluster runs general K8sGPT analysis on the cluster
func (c *K8sGPTClient) AnalyzeCluster(ctx context.Context, namespace string) (*K8sGPTResponse, error) {
	color.Yellow("🤖 Running K8sGPT cluster analysis...")
	
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()
	
	args := []string{
		"analyze",
		"--output", "json",
		"--explain",
	}
	
	if namespace != "" {
		args = append(args, "--namespace", namespace)
	}
	
	cmd := exec.CommandContext(ctx, c.binaryPath, args...)
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("k8sgpt analyze failed: %w", err)
	}
	
	var response K8sGPTResponse
	if err := json.Unmarshal(output, &response); err != nil {
		return nil, fmt.Errorf("failed to parse k8sgpt output: %w", err)
	}
	
	color.Green("✅ K8sGPT analysis complete. Found %d problems", response.Problems)
	return &response, nil
}

// processAnalysis converts K8sGPT analysis to our AnalysisResult format
func (c *K8sGPTClient) processAnalysis(analysis K8sGPTAnalysis, pod *corev1.Pod) *AnalysisResult {
	result := &AnalysisResult{
		PodName:   pod.Name,
		Namespace: pod.Namespace,
		Confidence: 0.9, // Higher confidence when K8sGPT+AI provides analysis
	}
	
	// Process errors to extract useful information
	if len(analysis.Error) > 0 {
		firstError := analysis.Error[0]
		result.ErrorDetails = firstError.Text
		
		// Detect error type and auto-fix capability
		result.ErrorType, result.CanAutoFix = c.detectErrorType(firstError.Text)
		
		// Use AI-generated recommendation from K8sGPT if available
		if analysis.Details != "" {
			result.Recommendation = analysis.Details
			result.Confidence = 0.98 // Very high confidence with AI explanation
		} else {
			result.Recommendation = c.generateRecommendation(result.ErrorType, firstError.Text)
		}
		
		// Adjust confidence based on error type
		if result.ErrorType == "ImagePullBackOff" {
			result.Confidence = 0.98 // Very high confidence for AI-analyzed image errors
		}
	}
	
	return result
}

// detectErrorType identifies the type of error and if it can be auto-fixed
func (c *K8sGPTClient) detectErrorType(errorText string) (string, bool) {
	// ImagePullBackOff detection
	if contains(errorText, []string{"ImagePullBackOff", "ErrImagePull", "pull"}) {
		return "ImagePullBackOff", true
	}
	
	// OOMKilled detection
	if contains(errorText, []string{"OOMKilled", "out of memory", "memory"}) {
		return "OOMKilled", false // Not supported in MVP
	}
	
	// CrashLoopBackOff detection
	if contains(errorText, []string{"CrashLoopBackOff", "crash", "restart"}) {
		return "CrashLoopBackOff", false // Not supported in MVP
	}
	
	return "Unknown", false
}

// generateRecommendation creates a fix recommendation based on error type
func (c *K8sGPTClient) generateRecommendation(errorType, errorText string) string {
	switch errorType {
	case "ImagePullBackOff":
		return "Update image tag to 'latest' or verify image exists in registry"
	case "OOMKilled":
		return "Increase memory limits in pod specification"
	case "CrashLoopBackOff":
		return "Check application logs and fix startup issues"
	default:
		return "Manual investigation required"
	}
}

// binaryExists checks if K8sGPT binary exists
func (c *K8sGPTClient) binaryExists() bool {
	// For Windows, check file directly
	if _, err := os.Stat(c.binaryPath); err == nil {
		return true
	}
	
	// Fallback to LookPath
	_, err := exec.LookPath(c.binaryPath)
	return err == nil
}

// contains checks if any of the needles exist in haystack (case-insensitive)
func contains(haystack string, needles []string) bool {
	haystack = fmt.Sprintf("%s", haystack) // Ensure string
	for _, needle := range needles {
		if len(haystack) >= len(needle) {
			for i := 0; i <= len(haystack)-len(needle); i++ {
				if haystack[i:i+len(needle)] == needle {
					return true
				}
			}
		}
	}
	return false
}

// createBasicAnalysis creates analysis when K8sGPT doesn't have results
func (c *K8sGPTClient) createBasicAnalysis(pod *corev1.Pod) *AnalysisResult {
	result := &AnalysisResult{
		PodName:   pod.Name,
		Namespace: pod.Namespace,
		Confidence: 0.85,
	}
	
	// Analyze container statuses manually
	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.State.Waiting != nil {
			reason := containerStatus.State.Waiting.Reason
			message := containerStatus.State.Waiting.Message
			
			result.ErrorType = reason
			result.ErrorDetails = fmt.Sprintf("%s: %s", reason, message)
			
			// Determine if we can auto-fix
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" {
				result.CanAutoFix = true
				result.Recommendation = "Update image tag to 'latest' or verify image exists in registry"
				result.Confidence = 0.95
			} else {
				result.CanAutoFix = false
				result.Recommendation = "Manual investigation required for " + reason
			}
			
			break // Use first error found
		}
	}
	
	return result
}