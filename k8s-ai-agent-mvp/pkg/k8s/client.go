package k8s

import (
	"context"
	"fmt"
	"path/filepath"
	
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// Client wraps the Kubernetes clientset with helper methods
type Client struct {
	clientset kubernetes.Interface
}

// NewClient creates a new Kubernetes client
// It tries in-cluster config first, then falls back to kubeconfig
func NewClient() (*Client, error) {
	var config *rest.Config
	var err error

	// Try in-cluster config first (when running inside K8s pod)
	config, err = rest.InClusterConfig()
	if err != nil {
		// Fall back to kubeconfig (local development)
		kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to create kubernetes config: %w", err)
		}
	}

	// Create the clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes client: %w", err)
	}

	return &Client{clientset: clientset}, nil
}

// GetPod retrieves a specific pod by name and namespace
func (c *Client) GetPod(ctx context.Context, namespace, name string) (*corev1.Pod, error) {
	pod, err := c.clientset.CoreV1().Pods(namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get pod %s/%s: %w", namespace, name, err)
	}
	return pod, nil
}

// ListPods lists all pods in a namespace
func (c *Client) ListPods(ctx context.Context, namespace string) (*corev1.PodList, error) {
	pods, err := c.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to list pods in namespace %s: %w", namespace, err)
	}
	return pods, nil
}

// IsPodFailed checks if a pod is in a failed state
func (c *Client) IsPodFailed(pod *corev1.Pod) bool {
	// Check pod phase
	if pod.Status.Phase == corev1.PodFailed {
		return true
	}

	// Check container statuses for ImagePullBackOff
	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.State.Waiting != nil {
			reason := containerStatus.State.Waiting.Reason
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" {
				return true
			}
		}
	}

	return false
}

// GetPodErrorReason returns the specific error reason for a failed pod
func (c *Client) GetPodErrorReason(pod *corev1.Pod) string {
	// Check container statuses
	for _, containerStatus := range pod.Status.ContainerStatuses {
		if containerStatus.State.Waiting != nil {
			return containerStatus.State.Waiting.Reason
		}
	}

	// Return pod phase if no container-specific error
	return string(pod.Status.Phase)
}

// TestConnection tests if the Kubernetes client can connect to the cluster
func (c *Client) TestConnection(ctx context.Context) error {
	// Try to get server version as a connection test
	_, err := c.clientset.Discovery().ServerVersion()
	if err != nil {
		return fmt.Errorf("failed to connect to kubernetes cluster: %w", err)
	}
	return nil
}