package executor

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/fatih/color"
	corev1 "k8s.io/api/core/v1"
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

	// Delete the old pod
	color.Yellow("🗑️  Deleting old pod...")
	deletePolicy := metav1.DeletePropagationForeground
	err := e.clientset.CoreV1().Pods(pod.Namespace).Delete(ctx, pod.Name, metav1.DeleteOptions{
		PropagationPolicy: &deletePolicy,
	})
	if err != nil {
		return fmt.Errorf("failed to delete old pod: %w", err)
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