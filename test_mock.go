package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// testMockPod runs the original mock pod test
func testMockPod(reflexionURL string) {
	fmt.Println("🧪 Creating mock pod with ImagePullBackOff error...")

	// Create a test pod with ImagePullBackOff error
	pod := &v1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-nginx-pod",
			Namespace: "default",
		},
		Spec: v1.PodSpec{
			Containers: []v1.Container{
				{
					Name:  "nginx",
					Image: "nginx:nonexistent-tag",
				},
			},
		},
		Status: v1.PodStatus{
			Phase: v1.PodPending,
			ContainerStatuses: []v1.ContainerStatus{
				{
					Name:  "nginx",
					Ready: false,
					State: v1.ContainerState{
						Waiting: &v1.ContainerStateWaiting{
							Reason:  "ImagePullBackOff",
							Message: "Back-off pulling image \"nginx:nonexistent-tag\"",
						},
					},
				},
			},
		},
	}

	// Create mock events and logs
	events := []v1.Event{
		{
			Type:    "Warning",
			Reason:  "Failed",
			Message: "Failed to pull image \"nginx:nonexistent-tag\": rpc error: code = Unknown desc = Error response from daemon: manifest for nginx:nonexistent-tag not found",
		},
		{
			Type:    "Warning",
			Reason:  "Failed",
			Message: "Error: ImagePullBackOff",
		},
	}

	logs := []string{
		"Error: image nginx:nonexistent-tag not found",
		"Failed to pull image",
		"Back-off pulling image \"nginx:nonexistent-tag\"",
	}

	// Send to reflexion service
	log.Printf("🔄 Sending ImagePullBackOff error to reflexion service for pod %s", pod.Name)

	response, err := sendMockToReflexion(reflexionURL, pod, events, logs, "ImagePullBackOff")
	if err != nil {
		log.Printf("❌ Failed to get reflexion strategy: %v", err)
		return
	}

	// Process the response
	log.Printf("✅ Received strategy from reflexion service:")
	log.Printf("   📋 Workflow ID: %s", response.WorkflowID)
	log.Printf("   🎯 Strategy Type: %v", response.FinalStrategy["type"])
	log.Printf("   📊 Confidence: %v", response.FinalStrategy["confidence"])
	log.Printf("   ✅ Success: %v", response.Success)
	log.Printf("   ⏱️  Resolution Time: %.2fs", response.ResolutionTime)

	// Check reflexion summary
	if summary, ok := response.ReflexionSummary["used_real_k8s_data"]; ok {
		log.Printf("   🔍 Used Real K8s Data: %v", summary)
	}
	if reflections, ok := response.ReflexionSummary["reflections_performed"]; ok {
		log.Printf("   🤔 Reflections Performed: %v", reflections)
	}
	if learning, ok := response.ReflexionSummary["learning_velocity"]; ok {
		log.Printf("   📈 Learning Velocity: %v", learning)
	}

	if response.RequiresHumanIntervention {
		log.Printf("🚨 Human intervention required for pod %s", pod.Name)
	} else {
		log.Printf("🤖 AI can handle this automatically")
	}
}

// Mock request/response types
type MockRealK8sData struct {
	PodSpec           *v1.Pod                `json:"pod_spec"`
	Events            []v1.Event             `json:"events"`
	Logs              []string               `json:"logs"`
	ContainerStatuses []v1.ContainerStatus  `json:"container_statuses,omitempty"`
}

type MockGoServiceErrorRequest struct {
	PodName     string          `json:"pod_name"`
	Namespace   string          `json:"namespace"`
	ErrorType   string          `json:"error_type"`
	RealK8sData MockRealK8sData `json:"real_k8s_data"`
}

type MockReflexionResponse struct {
	WorkflowID                string                 `json:"workflow_id"`
	Success                   bool                   `json:"success"`
	FinalStrategy             map[string]interface{} `json:"final_strategy"`
	ResolutionTime            float64                `json:"resolution_time"`
	RequiresHumanIntervention bool                   `json:"requires_human_intervention"`
	ReflexionSummary          map[string]interface{} `json:"reflexion_summary"`
}

func sendMockToReflexion(reflexionURL string, pod *v1.Pod, events []v1.Event, logs []string, errorType string) (*MockReflexionResponse, error) {
	// Prepare the request
	request := MockGoServiceErrorRequest{
		PodName:   pod.Name,
		Namespace: pod.Namespace,
		ErrorType: errorType,
		RealK8sData: MockRealK8sData{
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

	// Create HTTP client with timeout
	client := &http.Client{
		Timeout: 120 * time.Second,
	}

	// Send to reflexion service
	resp, err := client.Post(
		reflexionURL+"/api/v1/reflexion/process-with-k8s-data",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	// Check response status
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("reflexion service returned status %d", resp.StatusCode)
	}

	// Parse response
	var reflexionResp MockReflexionResponse
	if err := json.NewDecoder(resp.Body).Decode(&reflexionResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &reflexionResp, nil
}