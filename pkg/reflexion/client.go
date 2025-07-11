package reflexion

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	v1 "k8s.io/api/core/v1"
)

// Client handles communication with the Python reflexion service
type Client struct {
	baseURL    string
	httpClient *http.Client
}

// NewClient creates a new reflexion client
func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second, // 30 seconds timeout
		},
	}
}

// RealK8sData represents the real Kubernetes data to send
type RealK8sData struct {
	PodSpec           *v1.Pod                `json:"pod_spec"`
	Events            []v1.Event             `json:"events"`
	Logs              []string               `json:"logs"`
	ContainerStatuses []v1.ContainerStatus  `json:"container_statuses,omitempty"`
}

// GoServiceErrorRequest is the request to send to Python reflexion service
type GoServiceErrorRequest struct {
	PodName     string      `json:"pod_name"`
	Namespace   string      `json:"namespace"`
	ErrorType   string      `json:"error_type"`
	RealK8sData RealK8sData `json:"real_k8s_data"`
}

// ReflexionResponse is the response from Python reflexion service
type ReflexionResponse struct {
	WorkflowID                string                 `json:"workflow_id"`
	Success                   bool                   `json:"success"`
	FinalStrategy             map[string]interface{} `json:"final_strategy"`
	ResolutionTime            float64                `json:"resolution_time"`
	RequiresHumanIntervention bool                   `json:"requires_human_intervention"`
	ReflexionSummary          map[string]interface{} `json:"reflexion_summary"`
}

// ProcessPodError sends a pod error to the reflexion service
func (c *Client) ProcessPodError(pod *v1.Pod, events []v1.Event, logs []string, errorType string) (*ReflexionResponse, error) {
	// Prepare the request
	request := GoServiceErrorRequest{
		PodName:   pod.Name,
		Namespace: pod.Namespace,
		ErrorType: errorType,
		RealK8sData: RealK8sData{
			PodSpec:           pod,
			Events:            events,
			Logs:              logs,
			ContainerStatuses: pod.Status.ContainerStatuses,
		},
	}

	// Convert to JSON
	jsonData, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Send request
	url := c.baseURL + "/api/v1/reflexion/process-with-k8s-data"
	resp, err := c.httpClient.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to send request to %s: %w", url, err)
	}
	defer resp.Body.Close()

	// Check response status
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("reflexion service returned status %d", resp.StatusCode)
	}

	// Parse response
	var reflexionResp ReflexionResponse
	if err := json.NewDecoder(resp.Body).Decode(&reflexionResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &reflexionResp, nil
}

// HealthCheck checks if the reflexion service is healthy
func (c *Client) HealthCheck() error {
	url := c.baseURL + "/health"
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return fmt.Errorf("failed to connect to reflexion service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("reflexion service health check failed with status %d", resp.StatusCode)
	}

	return nil
}