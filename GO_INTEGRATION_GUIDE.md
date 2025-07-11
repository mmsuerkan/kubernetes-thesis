# Go Detector Integration Guide

## Overview

This guide explains how to integrate the Go-based k8s-ai-agent-mvp detector with the Python-based k8s-real-integration (reflexion) service.

## Architecture

```
┌─────────────────────┐         ┌────────────────────────┐
│   Go Service        │         │  Python Reflexion      │
│  (Detector)         │ ──────▶ │    Service             │
│                     │  HTTP   │                        │
│ • Real K8s Client   │         │ • LangGraph Workflow   │
│ • Error Detection   │         │ • AI Reflection        │
│ • Event Collection  │         │ • Strategy Learning    │
└─────────────────────┘         └────────────────────────┘
```

## Go Service Changes Required

### 1. Add HTTP Client to Detector

```go
// k8s-ai-agent-mvp/pkg/detector/watcher.go

import (
    "bytes"
    "encoding/json"
    "net/http"
    "time"
)

// Add to Watcher struct
type Watcher struct {
    // existing fields...
    reflexionURL string
    useReflexion bool
}

// Add reflexion integration
func (w *Watcher) sendToReflexion(pod *v1.Pod, errorType string) (*ReflexionResponse, error) {
    // Collect real K8s data
    events, err := w.k8sClient.GetPodEvents(pod.Name, pod.Namespace)
    if err != nil {
        return nil, err
    }
    
    logs, err := w.k8sClient.GetPodLogs(pod.Name, pod.Namespace)
    if err != nil {
        return nil, err
    }
    
    // Create request
    request := GoServiceErrorRequest{
        PodName:   pod.Name,
        Namespace: pod.Namespace,
        ErrorType: errorType,
        RealK8sData: RealK8sData{
            PodSpec: pod,
            Events:  events,
            Logs:    logs,
            ContainerStatuses: pod.Status.ContainerStatuses,
        },
    }
    
    // Send to reflexion service
    jsonData, err := json.Marshal(request)
    if err != nil {
        return nil, err
    }
    
    resp, err := http.Post(
        w.reflexionURL + "/api/v1/reflexion/process-with-k8s-data",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var reflexionResp ReflexionResponse
    if err := json.NewDecoder(resp.Body).Decode(&reflexionResp); err != nil {
        return nil, err
    }
    
    return &reflexionResp, nil
}
```

### 2. Add Models

```go
// k8s-ai-agent-mvp/pkg/detector/models.go

type RealK8sData struct {
    PodSpec          *v1.Pod                `json:"pod_spec"`
    Events           []v1.Event             `json:"events"`
    Logs             []string               `json:"logs"`
    ContainerStatuses []v1.ContainerStatus  `json:"container_statuses,omitempty"`
}

type GoServiceErrorRequest struct {
    PodName      string       `json:"pod_name"`
    Namespace    string       `json:"namespace"`
    ErrorType    string       `json:"error_type"`
    RealK8sData  RealK8sData  `json:"real_k8s_data"`
}

type ReflexionResponse struct {
    WorkflowID               string                 `json:"workflow_id"`
    Success                  bool                   `json:"success"`
    FinalStrategy           map[string]interface{} `json:"final_strategy"`
    ResolutionTime          float64                `json:"resolution_time"`
    RequiresHumanIntervention bool                  `json:"requires_human_intervention"`
    ReflexionSummary        map[string]interface{} `json:"reflexion_summary"`
}
```

### 3. Integrate with processPodError

```go
// k8s-ai-agent-mvp/pkg/detector/watcher.go

func (w *Watcher) processPodError(pod *v1.Pod, errorType string) {
    logger := w.logger.With("pod", pod.Name, "namespace", pod.Namespace)
    
    // Send to reflexion if enabled
    if w.useReflexion {
        reflexionResp, err := w.sendToReflexion(pod, errorType)
        if err != nil {
            logger.Error("Failed to send to reflexion service", "error", err)
            // Fallback to traditional processing
        } else {
            logger.Info("Received strategy from reflexion",
                "strategy", reflexionResp.FinalStrategy["type"],
                "confidence", reflexionResp.FinalStrategy["confidence"])
            
            // Execute the reflexion strategy
            if w.autoFix {
                w.executeReflexionStrategy(pod, reflexionResp.FinalStrategy)
                return
            }
        }
    }
    
    // Traditional processing (existing code)
    w.handleError(pod, errorType)
}
```

### 4. Configuration

```go
// k8s-ai-agent-mvp/internal/config/config.go

type Config struct {
    // existing fields...
    UseReflexion bool   `env:"USE_REFLEXION" default:"false"`
    ReflexionURL string `env:"REFLEXION_URL" default:"http://localhost:8000"`
}
```

## Python Service Setup

### 1. Start the Reflexion Service

```bash
# In k8s-real-integration directory
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Test the Integration

```bash
# Test with sample data
python test_go_integration.py
```

## API Endpoint

The Python service exposes a new endpoint for Go integration:

```
POST /api/v1/reflexion/process-with-k8s-data
```

Request body:
```json
{
    "pod_name": "test-pod",
    "namespace": "default",
    "error_type": "ImagePullBackOff",
    "real_k8s_data": {
        "pod_spec": { /* Full pod spec */ },
        "events": [ /* Pod events */ ],
        "logs": [ /* Pod logs */ ],
        "container_statuses": [ /* Container statuses */ ]
    }
}
```

Response:
```json
{
    "workflow_id": "go_integration_20250711_130000",
    "success": true,
    "pod_name": "test-pod",
    "final_strategy": {
        "id": "context_awareness_8433",
        "type": "fix_image_tag",
        "confidence": 0.95,
        "parameters": {
            "new_tag": "latest"
        }
    },
    "resolution_time": 45.2,
    "requires_human_intervention": false,
    "reflexion_summary": {
        "reflections_performed": 1,
        "strategies_learned": 2,
        "self_awareness_level": 0.75,
        "learning_velocity": 0.3,
        "used_real_k8s_data": true
    }
}
```

## Benefits

1. **Real K8s Data**: Go detector provides real pod data, events, and logs
2. **AI-Enhanced Analysis**: Reflexion provides intelligent strategy selection
3. **Learning System**: Strategies improve over time based on outcomes
4. **Minimal Changes**: Only detector needs modification, executor remains unchanged

## Testing

1. Start both services:
```bash
# Terminal 1: Python Reflexion Service
cd k8s-real-integration
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Go Detector (with reflexion enabled)
cd k8s-ai-agent-mvp
./k8s-ai-agent.exe watch --namespace=default --auto-fix
```

2. Environment variables for Go service:
```env
USE_REFLEXION=true
REFLEXION_URL=http://localhost:8000
```

## Next Steps

1. Implement the Go service changes
2. Test with real Kubernetes cluster
3. Monitor strategy effectiveness
4. Implement executor integration for real fix execution