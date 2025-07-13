package k8s

import (
	"context"
	"fmt"
	"log"
	"path/filepath"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

// Client wraps Kubernetes client functionality
type Client struct {
	clientset *kubernetes.Clientset
	config    *rest.Config
}

// NewClient creates a new Kubernetes client
func NewClient() (*Client, error) {
	// Try in-cluster config first
	config, err := rest.InClusterConfig()
	if err != nil {
		// Fall back to kubeconfig
		config, err = getKubeConfig()
		if err != nil {
			return nil, fmt.Errorf("failed to get kubeconfig: %w", err)
		}
	}

	// Create clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	return &Client{
		clientset: clientset,
		config:    config,
	}, nil
}

// getKubeConfig gets the kubeconfig from default locations
func getKubeConfig() (*rest.Config, error) {
	var kubeconfig string
	
	// Check if kubeconfig path is set
	if home := homedir.HomeDir(); home != "" {
		kubeconfig = filepath.Join(home, ".kube", "config")
	}

	// Build config from kubeconfig
	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return nil, fmt.Errorf("failed to build config from kubeconfig: %w", err)
	}

	return config, nil
}

// TestConnection tests the connection to Kubernetes cluster
func (c *Client) TestConnection() error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Try to get cluster info
	_, err := c.clientset.CoreV1().Namespaces().Get(ctx, "default", metav1.GetOptions{})
	if err != nil {
		return fmt.Errorf("failed to connect to cluster: %w", err)
	}

	log.Printf("✅ Successfully connected to Kubernetes cluster")
	return nil
}

// GetPod retrieves a pod by name and namespace
func (c *Client) GetPod(namespace, name string) (*v1.Pod, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	pod, err := c.clientset.CoreV1().Pods(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get pod %s/%s: %w", namespace, name, err)
	}

	return pod, nil
}

// ListPods lists all pods in a namespace
func (c *Client) ListPods(namespace string) (*v1.PodList, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	pods, err := c.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list pods in namespace %s: %w", namespace, err)
	}

	return pods, nil
}

// GetPodEvents retrieves events for a specific pod
func (c *Client) GetPodEvents(namespace, podName string) ([]v1.Event, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Get events related to the pod
	events, err := c.clientset.CoreV1().Events(namespace).List(ctx, metav1.ListOptions{
		FieldSelector: fmt.Sprintf("involvedObject.name=%s", podName),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get events for pod %s/%s: %w", namespace, podName, err)
	}

	return events.Items, nil
}

// GetPodLogs retrieves logs for a specific pod
func (c *Client) GetPodLogs(namespace, podName string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Get pod logs
	req := c.clientset.CoreV1().Pods(namespace).GetLogs(podName, &v1.PodLogOptions{
		TailLines: int64Ptr(50), // Get last 50 lines
	})

	logs, err := req.Stream(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get logs for pod %s/%s: %w", namespace, podName, err)
	}
	defer logs.Close()

	// Read logs (simplified - in production, use a proper log reader)
	logLines := []string{
		"Pod logs would be read here",
		"This is a placeholder for actual log reading",
	}

	return logLines, nil
}

// IsPodFailed checks if a pod has failed or is in problematic state
func (c *Client) IsPodFailed(pod *v1.Pod) bool {
	// Check pod phase
	if pod.Status.Phase == v1.PodFailed {
		return true
	}

	// Check if pod is stuck in Pending state (usually indicates problems)
	if pod.Status.Phase == v1.PodPending {
		// If pod has been pending for more than 60 seconds, consider it problematic
		if time.Since(pod.CreationTimestamp.Time) > 60*time.Second {
			return true
		}
	}

	// Check container states
	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.State.Waiting != nil {
			reason := containerStatus.State.Waiting.Reason
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" || reason == "CrashLoopBackOff" ||
			   reason == "InvalidImageName" || reason == "CreateContainerConfigError" ||
			   reason == "CreateContainerError" || reason == "ConfigError" {
				return true
			}
		}
		if containerStatus.State.Terminated != nil {
			if containerStatus.State.Terminated.ExitCode != 0 {
				return true
			}
		}
	}

	// Check init container states
	for _, initContainerStatus := range pod.Status.InitContainerStatuses {
		if initContainerStatus.State.Waiting != nil {
			reason := initContainerStatus.State.Waiting.Reason
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" || reason == "InvalidImageName" {
				return true
			}
		}
		if initContainerStatus.State.Terminated != nil {
			if initContainerStatus.State.Terminated.ExitCode != 0 {
				return true
			}
		}
	}

	return false
}

// GetPodErrorType determines the type of error for a failed pod
func (c *Client) GetPodErrorType(pod *v1.Pod) string {
	// Check if pod is stuck in Pending state
	if pod.Status.Phase == v1.PodPending {
		if time.Since(pod.CreationTimestamp.Time) > 60*time.Second {
			return "PodPending"
		}
	}

	// Check init container states first
	for _, initContainerStatus := range pod.Status.InitContainerStatuses {
		if initContainerStatus.State.Waiting != nil {
			reason := initContainerStatus.State.Waiting.Reason
			switch reason {
			case "ImagePullBackOff", "ErrImagePull":
				return "InitContainerImagePullBackOff"
			case "InvalidImageName":
				return "InitContainerInvalidImageName"
			}
		}
		if initContainerStatus.State.Terminated != nil {
			if initContainerStatus.State.Terminated.ExitCode != 0 {
				return "InitContainerFailed"
			}
		}
	}

	// Check container states for specific errors
	for _, containerStatus := range pod.Status.ContainerStatuses {
		// PRIORITY: Check Terminated state first for OOMKilled
		if containerStatus.State.Terminated != nil {
			// First check the Reason field - it's more reliable than exit code
			reason := containerStatus.State.Terminated.Reason
			if reason == "OOMKilled" {
				return "OOMKilled"
			}
			
			// Then check exit code as fallback
			exitCode := containerStatus.State.Terminated.ExitCode
			switch exitCode {
			case 1:
				return "CrashLoopBackOff"
			case 137:
				return "OOMKilled"
			case 139:
				return "Segfault"
			case 143:
				return "SIGTERM"
			default:
				if exitCode != 0 {
					return "CrashLoopBackOff"
				}
			}
		}
		
		if containerStatus.State.Waiting != nil {
			reason := containerStatus.State.Waiting.Reason
			switch reason {
			case "ImagePullBackOff", "ErrImagePull":
				return "ImagePullBackOff"
			case "CrashLoopBackOff":
				return "CrashLoopBackOff"
			case "InvalidImageName":
				return "InvalidImageName"
			case "CreateContainerConfigError":
				return "CreateContainerConfigError"
			case "CreateContainerError":
				return "CreateContainerError"
			case "ConfigError":
				return "ConfigError"
			}
		}
		}
	}

	// Check pod phase
	if pod.Status.Phase == v1.PodFailed {
		return "PodFailed"
	}

	return "Unknown"
}

// Helper function
func int64Ptr(i int64) *int64 {
	return &i
}