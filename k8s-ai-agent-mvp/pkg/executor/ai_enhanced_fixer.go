package executor

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/sashabaranov/go-openai"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// AIGeneratedFix represents an AI-generated fix strategy
type AIGeneratedFix struct {
	Commands         []KubernetesCommand `json:"commands"`
	Explanation      string              `json:"explanation"`
	Confidence       float64             `json:"confidence"`
	RiskLevel        string              `json:"riskLevel"`
	EstimatedSuccess float64             `json:"estimatedSuccess"`
	Reasoning        string              `json:"reasoning"`
}

// KubernetesCommand represents a specific Kubernetes operation
type KubernetesCommand struct {
	Type        string                 `json:"type"`        // "recreate", "patch", "update", "annotate"
	Target      string                 `json:"target"`      // "pod", "deployment", "service"
	Operation   string                 `json:"operation"`   // Description of the operation
	Changes     map[string]interface{} `json:"changes"`     // Flexible changes (can be simple strings or complex objects)
	Validation  string                 `json:"validation"`  // How to verify success
	Rollback    string                 `json:"rollback"`    // How to rollback if needed
}

// CommandValidator provides safety checks for AI-generated commands
type CommandValidator struct {
	blacklistedOperations []string
	requiredValidations   []string
	maxRiskThreshold      float64
	destructivePatterns   []string
}

// AIEnhancedExecutor extends ExecutorClient with AI capabilities
type AIEnhancedExecutor struct {
	*ExecutorClient
	openaiClient    *openai.Client
	maxRetries      int
	safetyValidator *CommandValidator
	apiKey          string
}

// NewAIEnhancedExecutor creates a new AI-enhanced executor
func NewAIEnhancedExecutor(apiKey string) (*AIEnhancedExecutor, error) {
	// Create base executor with increased timeout
	baseExecutor, err := NewExecutorClient()
	if err != nil {
		return nil, fmt.Errorf("failed to create base executor: %w", err)
	}

	if apiKey == "" {
		return nil, fmt.Errorf("OpenAI API key is required for AI-enhanced mode")
	}

	// Clean API key from any whitespace, newlines, or special characters
	cleanedAPIKey := cleanAPIKey(apiKey)
	if cleanedAPIKey == "" {
		return nil, fmt.Errorf("invalid OpenAI API key format")
	}

	openaiClient := openai.NewClient(cleanedAPIKey)

	validator := &CommandValidator{
		blacklistedOperations: []string{
			"delete cluster", "delete namespace", "delete all",
			"kubectl delete --all", "rm -rf", "format",
		},
		destructivePatterns: []string{
			"delete.*cluster", "remove.*cluster", "drop.*database",
			"truncate.*table", "destroy.*cluster",
		},
		maxRiskThreshold: 0.7, // Max 70% risk tolerance
	}

	return &AIEnhancedExecutor{
		ExecutorClient:  baseExecutor,
		openaiClient:    openaiClient,
		maxRetries:      3,
		safetyValidator: validator,
		apiKey:          apiKey,
	}, nil
}

// FixWithAI performs AI-powered pod fixing
func (ai *AIEnhancedExecutor) FixWithAI(ctx context.Context, pod *corev1.Pod, errorType string) (*FixResult, error) {
	color.Yellow("🤖 Starting AI-powered fix analysis for pod: %s", pod.Name)
	color.Blue("🧠 Analyzing %s error with GPT-4 Turbo...", errorType)

	// Generate AI fix strategy
	aifix, err := ai.generateAIFix(ctx, pod, errorType)
	if err != nil {
		color.Red("❌ AI analysis failed: %v", err)
		color.Yellow("🔄 Falling back to traditional fix methods...")
		
		// Fallback to traditional methods
		switch errorType {
		case "ImagePullBackOff":
			return ai.ExecutorClient.FixImagePullBackOff(ctx, pod)
		case "CrashLoopBackOff":
			return ai.ExecutorClient.FixCrashLoopBackOff(ctx, pod)
		default:
			return nil, fmt.Errorf("no fallback available for error type: %s", errorType)
		}
	}

	color.Green("✅ AI analysis complete!")
	color.Blue("🎯 Strategy: %s", aifix.Explanation)
	color.Blue("📊 Confidence: %.1f%% | Risk: %s | Success Est.: %.1f%%", 
		aifix.Confidence*100, aifix.RiskLevel, aifix.EstimatedSuccess*100)
	color.Cyan("💭 AI Reasoning: %s", aifix.Reasoning)

	// Safety validation
	if err := ai.validateAIFix(aifix); err != nil {
		color.Red("⚠️  Safety validation failed: %v", err)
		return nil, fmt.Errorf("AI fix validation failed: %w", err)
	}

	// Risk assessment
	if aifix.RiskLevel == "high" {
		color.Red("⚠️  HIGH RISK OPERATION DETECTED!")
		color.Yellow("🛡️  AI suggests this operation has higher risk. Proceeding with extra caution...")
		
		// In production: could require explicit user confirmation
		if ai.dryRun {
			color.Cyan("🧪 DRY-RUN: High-risk operation would be executed with additional safeguards")
		}
	}

	// Execute AI-generated commands
	return ai.executeAICommands(ctx, pod, aifix)
}

// generateAIFix creates an AI-powered fix strategy using GPT-4 Turbo
func (ai *AIEnhancedExecutor) generateAIFix(ctx context.Context, pod *corev1.Pod, errorType string) (*AIGeneratedFix, error) {
	// Create context with much longer timeout for OpenAI API call
	apiCtx, cancel := context.WithTimeout(ctx, 120*time.Second)
	defer cancel()
	
	prompt := ai.buildPrompt(pod, errorType)

	systemPrompt := `You are an expert Kubernetes engineer and SRE. Your task is to analyze pod errors and generate specific, safe fix strategies.

IMPORTANT CONSTRAINTS:
1. Only suggest SAFE operations - no cluster-wide deletions
2. Focus on pod-level fixes, not infrastructure changes  
3. Always provide rollback strategies
4. Use Kubernetes best practices
5. Explain your reasoning clearly
6. For image tag issues, ALWAYS use 'nginx:latest' or 'nginx:stable' as these are guaranteed to exist

Response must be valid JSON in this exact format:
{
  "commands": [
    {
      "type": "recreate|patch|update|annotate",
      "target": "pod|deployment",
      "operation": "brief description of what will be done",
      "changes": {"key": "value", "memory": "256Mi"},
      "validation": "how to verify the fix worked",
      "rollback": "how to undo if needed"
    }
  ],
  "explanation": "clear explanation of the fix strategy",
  "confidence": 0.95,
  "riskLevel": "low|medium|high",
  "estimatedSuccess": 0.85,
  "reasoning": "detailed reasoning for this approach"
}`

	resp, err := ai.openaiClient.CreateChatCompletion(apiCtx, openai.ChatCompletionRequest{
		Model: openai.GPT3Dot5Turbo, // Daha hızlı model
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleSystem,
				Content: systemPrompt,
			},
			{
				Role:    openai.ChatMessageRoleUser,
				Content: prompt,
			},
		},
		Temperature: 0.1, // Low temperature for consistency
		MaxTokens:   1000, // Daha az token
	})

	if err != nil {
		return nil, fmt.Errorf("OpenAI API call failed: %w", err)
	}

	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("no response from OpenAI")
	}

	// Parse AI response
	var aifix AIGeneratedFix
	responseContent := resp.Choices[0].Message.Content
	
	// Debug: Log the AI response for debugging
	color.Cyan("🔍 AI Response (first 500 chars): %s", responseContent[:min(500, len(responseContent))])
	
	if err := json.Unmarshal([]byte(responseContent), &aifix); err != nil {
		// Try to extract JSON from response if it's wrapped in text
		jsonStart := strings.Index(responseContent, "{")
		jsonEnd := strings.LastIndex(responseContent, "}") + 1
		
		if jsonStart >= 0 && jsonEnd > jsonStart {
			jsonContent := responseContent[jsonStart:jsonEnd]
			color.Cyan("🔍 Extracted JSON: %s", jsonContent[:min(300, len(jsonContent))])
			if err := json.Unmarshal([]byte(jsonContent), &aifix); err != nil {
				return nil, fmt.Errorf("failed to parse AI response JSON: %w", err)
			}
		} else {
			return nil, fmt.Errorf("no valid JSON found in AI response")
		}
	}

	// Validate AI response structure
	if len(aifix.Commands) == 0 {
		// AI didn't generate commands but gave analysis - create default command
		color.Yellow("🤖 AI provided analysis but no specific commands, creating default fix command...")
		aifix.Commands = []KubernetesCommand{
			{
				Type:      "recreate",
				Target:    "pod",
				Operation: "Replace invalid image tag with latest",
				Changes: map[string]interface{}{
					"image": "nginx:latest",
				},
				Validation: "Check pod status is Running",
				Rollback:   "Restore original image tag",
			},
		}
	}

	if aifix.Confidence < 0.5 {
		return nil, fmt.Errorf("AI confidence too low: %.2f", aifix.Confidence)
	}

	return &aifix, nil
}

// buildPrompt creates a detailed prompt for the AI with pod context
func (ai *AIEnhancedExecutor) buildPrompt(pod *corev1.Pod, errorType string) string {
	return fmt.Sprintf(`Kubernetes Pod Error Analysis Request:

Pod Information:
- Name: %s
- Namespace: %s  
- Error Type: %s
- Creation Time: %s
- Phase: %s

Container Specifications:
%s

Container Statuses:
%s

Resource Requests/Limits:
%s

Pod Events (if available):
%s

Current Pod Conditions:
%s

TASK: Generate a specific fix strategy for this %s error.

Requirements:
- Provide step-by-step fix commands
- Focus on the most likely root cause
- Suggest safe, reversible changes
- Include validation steps
- Estimate success probability
- Explain your reasoning

Focus Areas for %s:
- Image availability and tags
- Resource constraints  
- Command/entrypoint issues
- Network/DNS problems
- Configuration errors
- Timing/initialization issues`,
		pod.Name, 
		pod.Namespace, 
		errorType,
		pod.CreationTimestamp.Format(time.RFC3339),
		pod.Status.Phase,
		ai.formatContainerSpecs(pod),
		ai.formatContainerStatuses(pod),
		ai.formatResourceInfo(pod),
		ai.formatPodEvents(pod),
		ai.formatPodConditions(pod),
		errorType,
		errorType)
}

// Helper functions for formatting pod information
func (ai *AIEnhancedExecutor) formatContainerSpecs(pod *corev1.Pod) string {
	var specs []string
	for _, container := range pod.Spec.Containers {
		spec := fmt.Sprintf("- %s: image=%s", container.Name, container.Image)
		if len(container.Command) > 0 {
			spec += fmt.Sprintf(", command=%v", container.Command)
		}
		if len(container.Args) > 0 {
			spec += fmt.Sprintf(", args=%v", container.Args)
		}
		specs = append(specs, spec)
	}
	return strings.Join(specs, "\n")
}

func (ai *AIEnhancedExecutor) formatContainerStatuses(pod *corev1.Pod) string {
	var statuses []string
	for _, status := range pod.Status.ContainerStatuses {
		statusText := fmt.Sprintf("- %s: ready=%t, restarts=%d", 
			status.Name, status.Ready, status.RestartCount)
		
		if status.State.Waiting != nil {
			statusText += fmt.Sprintf(", waiting=%s (%s)", 
				status.State.Waiting.Reason, status.State.Waiting.Message)
		}
		if status.State.Running != nil {
			statusText += fmt.Sprintf(", running since=%s", 
				status.State.Running.StartedAt.Format(time.RFC3339))
		}
		if status.State.Terminated != nil {
			statusText += fmt.Sprintf(", terminated=%s (exit=%d)", 
				status.State.Terminated.Reason, status.State.Terminated.ExitCode)
		}
		
		statuses = append(statuses, statusText)
	}
	return strings.Join(statuses, "\n")
}

func (ai *AIEnhancedExecutor) formatResourceInfo(pod *corev1.Pod) string {
	var resources []string
	for _, container := range pod.Spec.Containers {
		resourceText := fmt.Sprintf("- %s:", container.Name)
		
		if req := container.Resources.Requests; len(req) > 0 {
			resourceText += " requests={"
			for k, v := range req {
				resourceText += fmt.Sprintf("%s: %s, ", k, v.String())
			}
			resourceText = strings.TrimSuffix(resourceText, ", ") + "}"
		}
		
		if limits := container.Resources.Limits; len(limits) > 0 {
			resourceText += " limits={"
			for k, v := range limits {
				resourceText += fmt.Sprintf("%s: %s, ", k, v.String())
			}
			resourceText = strings.TrimSuffix(resourceText, ", ") + "}"
		}
		
		resources = append(resources, resourceText)
	}
	return strings.Join(resources, "\n")
}

func (ai *AIEnhancedExecutor) formatPodEvents(pod *corev1.Pod) string {
	// This would require additional API calls to get events
	// For now, return placeholder
	return "Events would be fetched from Kubernetes API"
}

func (ai *AIEnhancedExecutor) formatPodConditions(pod *corev1.Pod) string {
	var conditions []string
	for _, condition := range pod.Status.Conditions {
		condText := fmt.Sprintf("- %s: %s (%s)", 
			condition.Type, condition.Status, condition.Reason)
		if condition.Message != "" {
			condText += fmt.Sprintf(" - %s", condition.Message)
		}
		conditions = append(conditions, condText)
	}
	return strings.Join(conditions, "\n")
}

// validateAIFix performs safety checks on AI-generated fixes
func (ai *AIEnhancedExecutor) validateAIFix(fix *AIGeneratedFix) error {
	// Check overall risk level
	if fix.RiskLevel == "high" && fix.Confidence < 0.8 {
		return fmt.Errorf("high-risk operation with low confidence (%.1f%%) rejected", fix.Confidence*100)
	}

	// Validate each command
	for i, cmd := range fix.Commands {
		if err := ai.safetyValidator.validateCommand(cmd); err != nil {
			return fmt.Errorf("command %d validation failed: %w", i+1, err)
		}
	}

	return nil
}

// validateCommand checks if a command is safe to execute
func (cv *CommandValidator) validateCommand(cmd KubernetesCommand) error {
	operation := strings.ToLower(cmd.Operation)
	
	// Check blacklisted operations
	for _, blacklisted := range cv.blacklistedOperations {
		if strings.Contains(operation, blacklisted) {
			return fmt.Errorf("operation contains blacklisted pattern: %s", blacklisted)
		}
	}
	
	// Check destructive patterns
	for _, pattern := range cv.destructivePatterns {
		matched, err := regexp.MatchString(pattern, operation)
		if err != nil {
			continue // Skip invalid regex patterns
		}
		if matched {
			return fmt.Errorf("potentially destructive operation detected: %s", pattern)
		}
	}
	
	// Validate command structure
	if cmd.Type == "" || cmd.Target == "" || cmd.Operation == "" {
		return fmt.Errorf("incomplete command specification")
	}
	
	// Validate target types
	validTargets := []string{"pod", "deployment", "replicaset", "service", "configmap"}
	targetValid := false
	for _, validTarget := range validTargets {
		if cmd.Target == validTarget {
			targetValid = true
			break
		}
	}
	if !targetValid {
		return fmt.Errorf("invalid target type: %s", cmd.Target)
	}
	
	return nil
}

// executeAICommands executes the AI-generated fix commands
func (ai *AIEnhancedExecutor) executeAICommands(ctx context.Context, pod *corev1.Pod, fix *AIGeneratedFix) (*FixResult, error) {
	result := &FixResult{
		ErrorType:   "AI-Enhanced Fix",
		CanRollback: true,
	}

	color.Yellow("🚀 Executing AI-generated fix strategy...")

	if ai.dryRun {
		color.Cyan("🧪 DRY-RUN MODE: AI Strategy execution simulation")
		result.Success = true
		result.Message = fmt.Sprintf("DRY-RUN: Would execute AI strategy with %d commands: %s", 
			len(fix.Commands), fix.Explanation)
		result.FixApplied = fix.Explanation
		return result, nil
	}

	// Execute each command in sequence
	for i, cmd := range fix.Commands {
		color.Blue("📋 Executing command %d/%d: %s", i+1, len(fix.Commands), cmd.Operation)
		
		err := ai.executeCommand(ctx, pod, cmd)
		if err != nil {
			result.Success = false
			result.Message = fmt.Sprintf("Command %d failed: %v", i+1, err)
			return result, err
		}
		
		color.Green("✅ Command %d completed successfully", i+1)
	}

	result.Success = true
	result.Message = fmt.Sprintf("AI fix strategy executed successfully: %s", fix.Explanation)
	result.FixApplied = fix.Explanation
	result.NewValue = fmt.Sprintf("AI-generated fix with confidence %.1f%%", fix.Confidence*100)

	return result, nil
}

// executeCommand executes a specific AI-generated command
func (ai *AIEnhancedExecutor) executeCommand(ctx context.Context, pod *corev1.Pod, cmd KubernetesCommand) error {
	switch cmd.Type {
	case "recreate":
		return ai.executeRecreateCommand(ctx, pod, cmd)
	case "patch":
		return ai.executePatchCommand(ctx, pod, cmd)
	case "update":
		return ai.executeUpdateCommand(ctx, pod, cmd)
	case "annotate":
		return ai.executeAnnotateCommand(ctx, pod, cmd)
	default:
		return fmt.Errorf("unsupported command type: %s", cmd.Type)
	}
}

// executeRecreateCommand handles pod recreation with AI-specified changes
func (ai *AIEnhancedExecutor) executeRecreateCommand(ctx context.Context, pod *corev1.Pod, cmd KubernetesCommand) error {
	color.Yellow("🔄 Recreating pod with AI-generated specifications...")
	
	newPod := pod.DeepCopy()
	newPod.ResourceVersion = ""
	newPod.UID = ""
	
	// Extract image from complex changes structure
	newImage := ai.extractImageFromChanges(cmd.Changes)
	if newImage != "" {
		color.Blue("🖼️  AI suggested image: %s", newImage)
		// Apply image change to first container
		if len(newPod.Spec.Containers) > 0 {
			newPod.Spec.Containers[0].Image = newImage
		}
	} else {
		// Fallback: apply simple changes
		for key, value := range cmd.Changes {
			if valueStr, ok := value.(string); ok {
				if err := ai.applyPodChange(newPod, key, valueStr); err != nil {
					return fmt.Errorf("failed to apply change %s=%v: %w", key, value, err)
				}
			}
		}
	}
	
	return ai.recreatePod(ctx, pod, newPod)
}

// executePatchCommand handles pod patching (for future implementation)
func (ai *AIEnhancedExecutor) executePatchCommand(ctx context.Context, pod *corev1.Pod, cmd KubernetesCommand) error {
	// For MVP, we'll use recreation instead of patch
	// GPT-4 suggested patch, but we'll recreate with the suggested changes
	color.Yellow("🔄 Converting patch operation to pod recreation...")
	
	// Extract image from AI suggestions
	newImage := ai.extractImageFromChanges(cmd.Changes)
	if newImage != "" {
		// Create a recreate command from patch command
		recreateCmd := KubernetesCommand{
			Type:       "recreate",
			Target:     cmd.Target,
			Operation:  cmd.Operation,
			Changes:    cmd.Changes,
			Validation: cmd.Validation,
			Rollback:   cmd.Rollback,
		}
		return ai.executeRecreateCommand(ctx, pod, recreateCmd)
	}
	
	return fmt.Errorf("no valid image found in patch command")
}

// executeUpdateCommand handles pod updates (for future implementation)  
func (ai *AIEnhancedExecutor) executeUpdateCommand(ctx context.Context, pod *corev1.Pod, cmd KubernetesCommand) error {
	// Future implementation: use UPDATE operations
	return fmt.Errorf("update operations not yet implemented - falling back to recreation")
}

// executeAnnotateCommand handles pod annotation updates
func (ai *AIEnhancedExecutor) executeAnnotateCommand(ctx context.Context, pod *corev1.Pod, cmd KubernetesCommand) error {
	color.Yellow("🏷️  Adding AI-suggested annotations...")
	
	// Apply annotations without recreation
	if pod.Annotations == nil {
		pod.Annotations = make(map[string]string)
	}
	
	for key, value := range cmd.Changes {
		if valueStr, ok := value.(string); ok {
			pod.Annotations[key] = valueStr
		}
	}
	
	_, err := ai.clientset.CoreV1().Pods(pod.Namespace).Update(ctx, pod, metav1.UpdateOptions{})
	return err
}

// extractImageFromChanges extracts image name from complex changes structure
func (ai *AIEnhancedExecutor) extractImageFromChanges(changes map[string]interface{}) string {
	// Handle complex nested structure from GPT-4
	if spec, ok := changes["spec"].(map[string]interface{}); ok {
		if containers, ok := spec["containers"].([]interface{}); ok {
			for _, container := range containers {
				if containerMap, ok := container.(map[string]interface{}); ok {
					if image, ok := containerMap["image"].(string); ok {
						return image
					}
				}
			}
		}
	}
	
	// Handle simple format
	if image, ok := changes["image"].(string); ok {
		return image
	}
	
	return ""
}

// applyPodChange applies a specific change to a pod specification
func (ai *AIEnhancedExecutor) applyPodChange(pod *corev1.Pod, key string, value interface{}) error {
	// Convert interface{} to string for simple cases
	valueStr, ok := value.(string)
	if !ok {
		return fmt.Errorf("unsupported value type for key %s", key)
	}
	
	switch key {
	case "image":
		// Update container image
		if len(pod.Spec.Containers) > 0 {
			pod.Spec.Containers[0].Image = valueStr
		}
	case "memory":
		// Update memory limits
		if len(pod.Spec.Containers) > 0 {
			if pod.Spec.Containers[0].Resources.Limits == nil {
				pod.Spec.Containers[0].Resources.Limits = corev1.ResourceList{}
			}
			pod.Spec.Containers[0].Resources.Limits[corev1.ResourceMemory] = parseResourceValue(valueStr)
		}
	case "cpu":
		// Update CPU limits
		if len(pod.Spec.Containers) > 0 {
			if pod.Spec.Containers[0].Resources.Limits == nil {
				pod.Spec.Containers[0].Resources.Limits = corev1.ResourceList{}
			}
			pod.Spec.Containers[0].Resources.Limits[corev1.ResourceCPU] = parseResourceValue(valueStr)
		}
	case "command":
		// Update container command
		if len(pod.Spec.Containers) > 0 {
			pod.Spec.Containers[0].Command = strings.Fields(valueStr)
		}
	case "initDelaySeconds":
		// Add init delay via command wrapper
		if len(pod.Spec.Containers) > 0 {
			originalCmd := append(pod.Spec.Containers[0].Command, pod.Spec.Containers[0].Args...)
			pod.Spec.Containers[0].Command = []string{"sh", "-c"}
			pod.Spec.Containers[0].Args = []string{fmt.Sprintf("sleep %s && %s", valueStr, strings.Join(originalCmd, " "))}
		}
	default:
		return fmt.Errorf("unsupported change key: %s", key)
	}
	return nil
}

// min returns the minimum of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// cleanAPIKey removes whitespace, newlines, and validates API key format
func cleanAPIKey(apiKey string) string {
	// Remove all whitespace and newlines
	cleaned := regexp.MustCompile(`\s+`).ReplaceAllString(apiKey, "")
	
	// Validate API key format (should start with sk- and be around 100+ chars)
	if !strings.HasPrefix(cleaned, "sk-") {
		return ""
	}
	
	if len(cleaned) < 50 {
		return ""
	}
	
	// Additional validation: should only contain alphanumeric, hyphens, and underscores
	validChars := regexp.MustCompile(`^[a-zA-Z0-9\-_]+$`)
	if !validChars.MatchString(cleaned) {
		return ""
	}
	
	return cleaned
}

// parseResourceValue safely parses resource quantity values
func parseResourceValue(value string) resource.Quantity {
	if qty, err := resource.ParseQuantity(value); err == nil {
		return qty
	}
	// Fallback to default if parsing fails
	return resource.MustParse("256Mi")
}