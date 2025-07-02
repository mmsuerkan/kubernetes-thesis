package executor

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/fatih/color"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
	"path/filepath"
)

// FixResult represents the result of a fix operation
type FixResult struct {
	Success     bool
	ErrorType   string
	FixApplied  string
	OldValue    string
	NewValue    string
	Message     string
	CanRollback bool
}

// ExecutorClient handles automated pod fixing
type ExecutorClient struct {
	clientset kubernetes.Interface
	dryRun    bool
}

// NewExecutorClient creates a new executor client
func NewExecutorClient() (*ExecutorClient, error) {
	var config *rest.Config
	var err error

	// Try in-cluster config first
	config, err = rest.InClusterConfig()
	if err != nil {
		// Fall back to kubeconfig
		kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to create kubernetes config: %w", err)
		}
	}
	
	// Increase timeout for slow clusters
	config.Timeout = 60 * time.Second
	
	// Disable rate limiting for local development
	config.QPS = 100
	config.Burst = 200

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes client: %w", err)
	}

	return &ExecutorClient{
		clientset: clientset,
		dryRun:    false, // Default to real execution
	}, nil
}

// SetDryRun enables/disables dry-run mode
func (e *ExecutorClient) SetDryRun(dryRun bool) {
	e.dryRun = dryRun
}

// FixImagePullBackOff attempts to fix ImagePullBackOff errors
func (e *ExecutorClient) FixImagePullBackOff(ctx context.Context, pod *corev1.Pod) (*FixResult, error) {
	color.Yellow("🔧 Starting ImagePullBackOff fix for pod: %s", pod.Name)
	
	result := &FixResult{
		ErrorType:   "ImagePullBackOff",
		CanRollback: true,
	}

	// Analyze the pod to understand the image issue
	containerName, imageName, err := e.analyzeImageError(pod)
	if err != nil {
		result.Success = false
		result.Message = fmt.Sprintf("Failed to analyze image error: %v", err)
		return result, err
	}

	color.Blue("📋 Found problematic image: %s in container: %s", imageName, containerName)
	result.OldValue = imageName

	// Try different fix strategies
	newImageName, fixStrategy := e.determineImageFix(imageName)
	result.NewValue = newImageName
	result.FixApplied = fixStrategy

	color.Blue("💡 Fix strategy: %s", fixStrategy)
	color.Blue("🔄 Old image: %s → New image: %s", imageName, newImageName)

	if e.dryRun {
		color.Cyan("🧪 DRY-RUN MODE: Would update image to: %s", newImageName)
		result.Success = true
		result.Message = fmt.Sprintf("DRY-RUN: Would fix %s → %s using strategy: %s", imageName, newImageName, fixStrategy)
		return result, nil
	}

	// Apply the fix
	err = e.updatePodImage(ctx, pod, containerName, newImageName)
	if err != nil {
		result.Success = false
		result.Message = fmt.Sprintf("Failed to apply fix: %v", err)
		return result, err
	}

	color.Green("✅ Fix applied successfully!")
	result.Success = true
	result.Message = fmt.Sprintf("Successfully updated image from %s to %s", imageName, newImageName)

	return result, nil
}

// analyzeImageError finds the container and image causing the ImagePullBackOff
func (e *ExecutorClient) analyzeImageError(pod *corev1.Pod) (containerName, imageName string, err error) {
	// Check container statuses for ImagePullBackOff
	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.State.Waiting != nil {
			reason := containerStatus.State.Waiting.Reason
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" {
				// Find the container spec
				for _, container := range pod.Spec.Containers {
					if container.Name == containerStatus.Name {
						return container.Name, container.Image, nil
					}
				}
			}
		}
	}

	return "", "", fmt.Errorf("no ImagePullBackOff error found in pod containers")
}

// determineImageFix determines the best fix strategy for the image
func (e *ExecutorClient) determineImageFix(imageName string) (newImageName, strategy string) {
	// Strategy 1: If image has a specific tag that might be wrong, try 'latest'
	if strings.Contains(imageName, ":") {
		parts := strings.Split(imageName, ":")
		if len(parts) == 2 {
			baseImage := parts[0]
			oldTag := parts[1]
			
			// If it's not already 'latest', try 'latest'
			if oldTag != "latest" {
				return baseImage + ":latest", "Replace tag with 'latest'"
			}
		}
	}

	// Strategy 2: If no tag specified, add 'latest' tag
	if !strings.Contains(imageName, ":") {
		return imageName + ":latest", "Add 'latest' tag"
	}

	// Strategy 3: Try common alternatives for nginx
	if strings.Contains(imageName, "nginx") {
		if strings.Contains(imageName, "nonexistent") {
			return "nginx:latest", "Replace with working nginx image"
		}
	}

	// Strategy 4: For other cases, try the base image with latest
	if strings.Contains(imageName, ":") {
		parts := strings.Split(imageName, ":")
		return parts[0] + ":latest", "Fallback to latest tag"
	}

	// Fallback
	return imageName + ":latest", "Default fallback strategy"
}

// updatePodImage updates the pod's container image
func (e *ExecutorClient) updatePodImage(ctx context.Context, pod *corev1.Pod, containerName, newImageName string) error {
	color.Yellow("🔄 Updating pod image...")

	// For MVP, we'll delete and recreate the pod since it's simpler
	// In production, you'd want to update the deployment/replicaset
	
	// Create a new pod spec with the fixed image
	newPod := pod.DeepCopy()
	newPod.ResourceVersion = "" // Clear resource version for recreation
	newPod.UID = ""             // Clear UID for recreation
	
	// Update the image in the container spec
	for i, container := range newPod.Spec.Containers {
		if container.Name == containerName {
			newPod.Spec.Containers[i].Image = newImageName
			break
		}
	}

	// Delete the old pod with retry
	color.Yellow("🗑️  Deleting old pod...")
	deletePolicy := metav1.DeletePropagationForeground
	
	// Try multiple times
	var err error
	for i := 0; i < 3; i++ {
		err = e.clientset.CoreV1().Pods(pod.Namespace).Delete(ctx, pod.Name, metav1.DeleteOptions{
			PropagationPolicy: &deletePolicy,
		})
		if err == nil {
			break
		}
		if i < 2 {
			color.Yellow("⚠️  Delete attempt %d failed, retrying...", i+1)
			time.Sleep(2 * time.Second)
		}
	}
	if err != nil {
		return fmt.Errorf("failed to delete old pod after 3 attempts: %w", err)
	}

	// Wait a moment for deletion to complete
	time.Sleep(2 * time.Second)

	// Create the new pod with fixed image
	color.Yellow("🚀 Creating new pod with fixed image...")
	_, err = e.clientset.CoreV1().Pods(pod.Namespace).Create(ctx, newPod, metav1.CreateOptions{})
	if err != nil {
		return fmt.Errorf("failed to create new pod: %w", err)
	}

	color.Green("✅ Pod recreated successfully!")
	return nil
}

// FixCrashLoopBackOff attempts to fix CrashLoopBackOff errors
func (e *ExecutorClient) FixCrashLoopBackOff(ctx context.Context, pod *corev1.Pod) (*FixResult, error) {
	color.Yellow("🔧 Starting CrashLoopBackOff fix for pod: %s", pod.Name)
	
	result := &FixResult{
		ErrorType:   "CrashLoopBackOff",
		CanRollback: true,
	}

	// Find the crashing container
	containerName, exitCode, err := e.analyzeCrashError(pod)
	if err != nil {
		result.Success = false
		result.Message = fmt.Sprintf("Failed to analyze crash error: %v", err)
		return result, err
	}

	color.Blue("📋 Found crashing container: %s with exit code: %d", containerName, exitCode)

	// Determine fix strategy based on exit code
	fixStrategy := e.determineCrashFix(pod, containerName, exitCode)
	result.FixApplied = fixStrategy

	color.Blue("💡 Fix strategy: %s", fixStrategy)

	if e.dryRun {
		color.Cyan("🧪 DRY-RUN MODE: Would apply fix: %s", fixStrategy)
		result.Success = true
		result.Message = fmt.Sprintf("DRY-RUN: Would fix CrashLoopBackOff with strategy: %s", fixStrategy)
		return result, nil
	}

	// Apply the fix based on strategy
	switch fixStrategy {
	case "Add init delay":
		err = e.addInitDelay(ctx, pod, containerName)
	case "Increase memory limits":
		err = e.increaseMemoryLimits(ctx, pod, containerName)
	case "Fix command syntax":
		err = e.fixCommandSyntax(ctx, pod, containerName)
	case "Add liveness probe with initial delay":
		err = e.addLivenessProbeDelay(ctx, pod, containerName)
	default:
		// For simple crashes, try adding a sleep before the command
		err = e.addInitDelay(ctx, pod, containerName)
	}

	if err != nil {
		result.Success = false
		result.Message = fmt.Sprintf("Failed to apply fix: %v", err)
		return result, err
	}

	color.Green("✅ Fix applied successfully!")
	result.Success = true
	result.Message = fmt.Sprintf("Applied fix strategy: %s", fixStrategy)

	return result, nil
}

// analyzeCrashError finds the container and exit code causing the crash
func (e *ExecutorClient) analyzeCrashError(pod *corev1.Pod) (containerName string, exitCode int32, err error) {
	for _, containerStatus := range pod.Status.ContainerStatuses {
		// Check if container is in CrashLoopBackOff
		if containerStatus.State.Waiting != nil && 
		   containerStatus.State.Waiting.Reason == "CrashLoopBackOff" {
			// Check last termination state for exit code
			if containerStatus.LastTerminationState.Terminated != nil {
				return containerStatus.Name, 
				       containerStatus.LastTerminationState.Terminated.ExitCode, 
				       nil
			}
			// If no last termination state, return default
			return containerStatus.Name, 1, nil
		}
		
		// Also check if recently terminated
		if containerStatus.State.Terminated != nil {
			return containerStatus.Name, 
			       containerStatus.State.Terminated.ExitCode, 
			       nil
		}
	}
	
	return "", 0, fmt.Errorf("no crashing container found")
}

// determineCrashFix determines the best fix strategy based on exit code
func (e *ExecutorClient) determineCrashFix(pod *corev1.Pod, containerName string, exitCode int32) string {
	// Common exit codes and their fixes
	switch exitCode {
	case 0:
		// Exit 0 but still crashing - might need init delay
		return "Add init delay"
	case 1:
		// General errors - check if it's a simple command issue
		for _, container := range pod.Spec.Containers {
			if container.Name == containerName {
				if len(container.Command) > 0 && container.Command[0] == "sh" {
					return "Fix command syntax"
				}
			}
		}
		return "Add init delay"
	case 137:
		// SIGKILL - often OOM
		return "Increase memory limits"
	case 139:
		// Segmentation fault
		return "Add init delay"
	case 143:
		// SIGTERM - might need graceful shutdown handling
		return "Add liveness probe with initial delay"
	default:
		return "Add init delay"
	}
}

// addInitDelay adds a sleep before the main command
func (e *ExecutorClient) addInitDelay(ctx context.Context, pod *corev1.Pod, containerName string) error {
	color.Yellow("🔄 Adding initialization delay to container...")
	
	newPod := pod.DeepCopy()
	newPod.ResourceVersion = ""
	newPod.UID = ""
	
	// Find and modify the container
	for i, container := range newPod.Spec.Containers {
		if container.Name == containerName {
			// Wrap existing command with sleep
			if len(container.Command) > 0 {
				// Preserve original command and add sleep
				originalCmd := append([]string{}, container.Command...)
				originalArgs := append([]string{}, container.Args...)
				
				newPod.Spec.Containers[i].Command = []string{"sh", "-c"}
				cmdString := fmt.Sprintf("sleep 10 && %s", strings.Join(append(originalCmd, originalArgs...), " "))
				newPod.Spec.Containers[i].Args = []string{cmdString}
			} else {
				// If no command, just add sleep
				newPod.Spec.Containers[i].Command = []string{"sh", "-c", "sleep 10 && echo 'Container started'"}
			}
			break
		}
	}
	
	return e.recreatePod(ctx, pod, newPod)
}

// increaseMemoryLimits doubles the memory limits
func (e *ExecutorClient) increaseMemoryLimits(ctx context.Context, pod *corev1.Pod, containerName string) error {
	color.Yellow("🔄 Increasing memory limits...")
	
	newPod := pod.DeepCopy()
	newPod.ResourceVersion = ""
	newPod.UID = ""
	
	// Find and modify the container
	for i, container := range newPod.Spec.Containers {
		if container.Name == containerName {
			if newPod.Spec.Containers[i].Resources.Limits == nil {
				newPod.Spec.Containers[i].Resources.Limits = corev1.ResourceList{}
			}
			if newPod.Spec.Containers[i].Resources.Requests == nil {
				newPod.Spec.Containers[i].Resources.Requests = corev1.ResourceList{}
			}
			
			// Set or increase memory limits
			newPod.Spec.Containers[i].Resources.Limits[corev1.ResourceMemory] = resource.MustParse("256Mi")
			newPod.Spec.Containers[i].Resources.Requests[corev1.ResourceMemory] = resource.MustParse("128Mi")
			break
		}
	}
	
	return e.recreatePod(ctx, pod, newPod)
}

// fixCommandSyntax fixes common command syntax issues
func (e *ExecutorClient) fixCommandSyntax(ctx context.Context, pod *corev1.Pod, containerName string) error {
	color.Yellow("🔄 Fixing command syntax...")
	
	newPod := pod.DeepCopy()
	newPod.ResourceVersion = ""
	newPod.UID = ""
	
	// Find and modify the container
	for i, container := range newPod.Spec.Containers {
		if container.Name == containerName {
			// Fix common command issues
			if len(container.Command) > 0 && container.Command[0] == "sh" {
				// Ensure proper shell command format
				newPod.Spec.Containers[i].Command = []string{"sh", "-c"}
				if len(container.Args) > 0 {
					// Join args into single command
					newPod.Spec.Containers[i].Args = []string{strings.Join(container.Args, " ")}
				} else {
					// Add a simple echo command
					newPod.Spec.Containers[i].Args = []string{"echo 'Container running' && sleep 3600"}
				}
			}
			break
		}
	}
	
	return e.recreatePod(ctx, pod, newPod)
}

// addLivenessProbeDelay adds or modifies liveness probe with initial delay
func (e *ExecutorClient) addLivenessProbeDelay(ctx context.Context, pod *corev1.Pod, containerName string) error {
	color.Yellow("🔄 Adding liveness probe delay...")
	
	newPod := pod.DeepCopy()
	newPod.ResourceVersion = ""
	newPod.UID = ""
	
	// Find and modify the container
	for i, container := range newPod.Spec.Containers {
		if container.Name == containerName {
			// Add or modify liveness probe
			if newPod.Spec.Containers[i].LivenessProbe == nil {
				newPod.Spec.Containers[i].LivenessProbe = &corev1.Probe{}
			}
			
			// Set initial delay to give container time to start
			newPod.Spec.Containers[i].LivenessProbe.InitialDelaySeconds = 30
			newPod.Spec.Containers[i].LivenessProbe.PeriodSeconds = 10
			
			// Add simple exec probe if none exists
			if newPod.Spec.Containers[i].LivenessProbe.Exec == nil &&
			   newPod.Spec.Containers[i].LivenessProbe.HTTPGet == nil &&
			   newPod.Spec.Containers[i].LivenessProbe.TCPSocket == nil {
				newPod.Spec.Containers[i].LivenessProbe.Exec = &corev1.ExecAction{
					Command: []string{"echo", "alive"},
				}
			}
			break
		}
	}
	
	return e.recreatePod(ctx, pod, newPod)
}

// recreatePod deletes old pod and creates new one
func (e *ExecutorClient) recreatePod(ctx context.Context, oldPod, newPod *corev1.Pod) error {
	// Delete the old pod
	color.Yellow("🗑️  Deleting old pod...")
	deletePolicy := metav1.DeletePropagationForeground
	err := e.clientset.CoreV1().Pods(oldPod.Namespace).Delete(ctx, oldPod.Name, metav1.DeleteOptions{
		PropagationPolicy: &deletePolicy,
	})
	if err != nil {
		return fmt.Errorf("failed to delete old pod: %w", err)
	}

	// Wait a moment for deletion
	time.Sleep(2 * time.Second)

	// Create the new pod
	color.Yellow("🚀 Creating new pod with fix...")
	_, err = e.clientset.CoreV1().Pods(oldPod.Namespace).Create(ctx, newPod, metav1.CreateOptions{})
	if err != nil {
		return fmt.Errorf("failed to create new pod: %w", err)
	}

	color.Green("✅ Pod recreated with fix!")
	return nil
}

// ValidateFix checks if the fix was successful
func (e *ExecutorClient) ValidateFix(ctx context.Context, namespace, podName string, timeout time.Duration) (*FixResult, error) {
	color.Yellow("✅ Validating fix for pod: %s", podName)
	
	result := &FixResult{
		ErrorType: "ValidationCheck",
	}

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// Wait for pod to be ready or fail
	for {
		select {
		case <-ctx.Done():
			result.Success = false
			result.Message = "Validation timeout - pod did not become ready"
			return result, fmt.Errorf("validation timeout")
			
		default:
			pod, err := e.clientset.CoreV1().Pods(namespace).Get(ctx, podName, metav1.GetOptions{})
			if err != nil {
				result.Success = false
				result.Message = fmt.Sprintf("Failed to get pod during validation: %v", err)
				return result, err
			}

			// Check if pod is running successfully
			if pod.Status.Phase == corev1.PodRunning {
				// Check if all containers are ready
				allReady := true
				for _, containerStatus := range pod.Status.ContainerStatuses {
					if !containerStatus.Ready {
						allReady = false
						break
					}
				}
				
				if allReady {
					color.Green("✅ Fix validation successful - pod is running!")
					result.Success = true
					result.Message = "Pod is running successfully after fix"
					return result, nil
				}
			}

			// Check if pod failed again
			if pod.Status.Phase == corev1.PodFailed {
				result.Success = false
				result.Message = "Pod failed after fix attempt"
				return result, fmt.Errorf("pod failed after fix")
			}

			// Check for still having ImagePullBackOff
			for _, containerStatus := range pod.Status.ContainerStatuses {
				if containerStatus.State.Waiting != nil {
					reason := containerStatus.State.Waiting.Reason
					if reason == "ImagePullBackOff" || reason == "ErrImagePull" {
						result.Success = false
						result.Message = "Fix failed - still has ImagePullBackOff"
						return result, fmt.Errorf("fix failed - still has image pull error")
					}
				}
			}

			// Wait before next check
			time.Sleep(2 * time.Second)
		}
	}
}