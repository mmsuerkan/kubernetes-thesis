# K8s Reflexion Service Integration Guide

Complete guide for integrating the Python Reflexion Service with the existing Go K8s AI Agent.

## 🔄 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Integration Flow                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    REST API     ┌─────────────────┐    OpenAI API         │
│  │  Go Service  │◄───────────────▶│ Python Service  │◄──────────────────────│
│  │              │                 │                 │                       │
│  │ • Detection  │   HTTP/JSON     │ • Reflexion     │   GPT-4 Turbo         │
│  │ • K8sGPT     │                 │ • Learning      │                       │
│  │ • Execution  │                 │ • Memory        │                       │
│  │ • Validation │                 │ • Evolution     │                       │
│  └──────────────┘                 └─────────────────┘                       │
│         │                                   │                               │
│         ▼                                   ▼                               │
│  ┌──────────────┐                 ┌─────────────────┐                       │
│  │  Kubernetes  │                 │ Knowledge Base  │                       │
│  │   Cluster    │                 │ (JSON/Database) │                       │
│  └──────────────┘                 └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📡 Required Go Service API Endpoints

The Python service requires the following REST endpoints from the Go service:

### 1. K8sGPT Analysis Endpoint

```go
// POST /api/v1/k8sgpt-analyze
type K8sGPTAnalyzeRequest struct {
    PodName   string `json:"pod_name"`
    Namespace string `json:"namespace"`
}

type K8sGPTAnalyzeResponse struct {
    Success     bool                   `json:"success"`
    Analysis    map[string]interface{} `json:"analysis"`
    Confidence  float64               `json:"confidence"`
    ErrorType   string                `json:"error_type"`
    Timestamp   string                `json:"timestamp"`
}
```

### 2. Fix Execution Endpoint

```go
// POST /api/v1/execute-fix
type ExecuteFixRequest struct {
    PodName   string                 `json:"pod_name"`
    Namespace string                 `json:"namespace"`
    Strategy  map[string]interface{} `json:"strategy"`
}

type ExecuteFixResponse struct {
    Success       bool                   `json:"success"`
    ExecutionID   string                 `json:"execution_id"`
    Result        map[string]interface{} `json:"result"`
    Error         string                 `json:"error,omitempty"`
    Timestamp     string                 `json:"timestamp"`
}
```

### 3. Pod Status Endpoint

```go
// GET /api/v1/pod-status/{podName}?namespace={namespace}
type PodStatusResponse struct {
    Status          string            `json:"status"`
    ContainersReady bool              `json:"containers_ready"`
    RestartCount    int               `json:"restart_count"`
    ReadyTime       string            `json:"ready_time,omitempty"`
    HealthChecks    map[string]string `json:"health_checks"`
    Timestamp       string            `json:"timestamp"`
}
```

### 4. Cluster Metrics Endpoint

```go
// GET /api/v1/cluster-metrics
type ClusterMetricsResponse struct {
    CPUUsage        float64 `json:"cpu_usage"`
    MemoryPressure  bool    `json:"memory_pressure"`
    ConcurrentOps   int     `json:"concurrent_ops"`
    NodeCount       int     `json:"node_count"`
    PodCount        int     `json:"pod_count"`
    Timestamp       string  `json:"timestamp"`
}
```

### 5. Recent Events Endpoint

```go
// GET /api/v1/recent-events
type RecentEventsResponse struct {
    Events []KubernetesEvent `json:"events"`
    Count  int               `json:"count"`
}

type KubernetesEvent struct {
    Type      string `json:"type"`
    Reason    string `json:"reason"`
    Message   string `json:"message"`
    Object    string `json:"object"`
    Timestamp string `json:"timestamp"`
}
```

### 6. Health Check Endpoint

```go
// GET /health
type HealthResponse struct {
    Status    string `json:"status"`
    Timestamp string `json:"timestamp"`
    Version   string `json:"version"`
}
```

## 🛠️ Go Service Implementation

Here's the implementation for the required endpoints in your Go service:

### API Router Setup

```go
// cmd/main.go - Add API router
func setupAPIRoutes(r *gin.Engine, client *k8s.Client, analyzer *analyzer.K8sGPT, fixer *executor.Fixer) {
    api := r.Group("/api/v1")
    
    // Reflexion service integration endpoints
    api.POST("/k8sgpt-analyze", handleK8sGPTAnalyze(analyzer))
    api.POST("/execute-fix", handleExecuteFix(fixer, client))
    api.GET("/pod-status/:podName", handlePodStatus(client))
    api.GET("/cluster-metrics", handleClusterMetrics(client))
    api.GET("/recent-events", handleRecentEvents(client))
    
    // Health check
    r.GET("/health", handleHealth())
}
```

### Handler Implementations

```go
// pkg/api/handlers.go
package api

import (
    "net/http"
    "time"
    "github.com/gin-gonic/gin"
)

func handleK8sGPTAnalyze(analyzer *analyzer.K8sGPT) gin.HandlerFunc {
    return func(c *gin.Context) {
        var req K8sGPTAnalyzeRequest
        if err := c.ShouldBindJSON(&req); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        
        // Run K8sGPT analysis
        analysis, err := analyzer.AnalyzePod(req.PodName, req.Namespace)
        if err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        
        response := K8sGPTAnalyzeResponse{
            Success:    true,
            Analysis:   analysis.Problems,
            Confidence: analysis.Confidence,
            ErrorType:  analysis.ErrorType,
            Timestamp:  time.Now().Format(time.RFC3339),
        }
        
        c.JSON(http.StatusOK, response)
    }
}

func handleExecuteFix(fixer *executor.Fixer, client *k8s.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        var req ExecuteFixRequest
        if err := c.ShouldBindJSON(&req); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        
        // Execute fix strategy
        result, err := fixer.ExecuteStrategy(req.PodName, req.Namespace, req.Strategy)
        if err != nil {
            c.JSON(http.StatusOK, ExecuteFixResponse{
                Success:     false,
                ExecutionID: generateExecutionID(),
                Error:       err.Error(),
                Timestamp:   time.Now().Format(time.RFC3339),
            })
            return
        }
        
        c.JSON(http.StatusOK, ExecuteFixResponse{
            Success:     result.Success,
            ExecutionID: generateExecutionID(),
            Result:      result.Details,
            Timestamp:   time.Now().Format(time.RFC3339),
        })
    }
}

func handlePodStatus(client *k8s.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        podName := c.Param("podName")
        namespace := c.DefaultQuery("namespace", "default")
        
        pod, err := client.GetPod(podName, namespace)
        if err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "Pod not found"})
            return
        }
        
        response := PodStatusResponse{
            Status:          string(pod.Status.Phase),
            ContainersReady: isPodReady(pod),
            RestartCount:    getRestartCount(pod),
            ReadyTime:       getReadyTime(pod),
            HealthChecks:    getHealthChecks(pod),
            Timestamp:       time.Now().Format(time.RFC3339),
        }
        
        c.JSON(http.StatusOK, response)
    }
}

func handleClusterMetrics(client *k8s.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        metrics, err := client.GetClusterMetrics()
        if err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        
        c.JSON(http.StatusOK, metrics)
    }
}

func handleRecentEvents(client *k8s.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        events, err := client.GetRecentEvents(50) // Last 50 events
        if err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        
        response := RecentEventsResponse{
            Events: events,
            Count:  len(events),
        }
        
        c.JSON(http.StatusOK, response)
    }
}

func handleHealth() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.JSON(http.StatusOK, HealthResponse{
            Status:    "ok",
            Timestamp: time.Now().Format(time.RFC3339),
            Version:   "v0.3.0-ai-enhanced",
        })
    }
}
```

### Enhanced Executor for Strategy Execution

```go
// pkg/executor/strategy_executor.go
package executor

import (
    "encoding/json"
    "fmt"
)

type StrategyExecutor struct {
    client *k8s.Client
    fixer  *Fixer
}

func NewStrategyExecutor(client *k8s.Client, fixer *Fixer) *StrategyExecutor {
    return &StrategyExecutor{
        client: client,
        fixer:  fixer,
    }
}

func (se *StrategyExecutor) ExecuteStrategy(podName, namespace string, strategy map[string]interface{}) (*ExecutionResult, error) {
    strategyType, ok := strategy["type"].(string)
    if !ok {
        return nil, fmt.Errorf("invalid strategy type")
    }
    
    switch strategyType {
    case "image_tag_replacement":
        return se.executeImageTagReplacement(podName, namespace, strategy)
    case "resource_adjustment":
        return se.executeResourceAdjustment(podName, namespace, strategy)
    case "temporal_optimization":
        return se.executeTemporalOptimization(podName, namespace, strategy)
    case "context_adaptive":
        return se.executeContextAdaptive(podName, namespace, strategy)
    default:
        // Fallback to traditional fixer
        return se.fixer.FixPod(podName, namespace)
    }
}

type ExecutionResult struct {
    Success bool                   `json:"success"`
    Details map[string]interface{} `json:"details"`
    Message string                 `json:"message"`
}

func (se *StrategyExecutor) executeImageTagReplacement(podName, namespace string, strategy map[string]interface{}) (*ExecutionResult, error) {
    parameters, ok := strategy["parameters"].(map[string]interface{})
    if !ok {
        parameters = map[string]interface{}{}
    }
    
    newTag, ok := parameters["new_tag"].(string)
    if !ok {
        newTag = "latest"
    }
    
    // Execute image tag replacement
    result, err := se.fixer.FixImagePullBackOff(podName, namespace, newTag)
    if err != nil {
        return &ExecutionResult{
            Success: false,
            Details: map[string]interface{}{"error": err.Error()},
            Message: "Image tag replacement failed",
        }, nil
    }
    
    return &ExecutionResult{
        Success: result,
        Details: map[string]interface{}{
            "strategy": "image_tag_replacement",
            "new_tag":  newTag,
            "pod_name": podName,
        },
        Message: "Image tag replacement completed",
    }, nil
}
```

## 🔧 Integration Testing

### Test Script for Go Service API

```bash
#!/bin/bash
# test_integration.sh

GO_SERVICE="http://localhost:8080"
PYTHON_SERVICE="http://localhost:8000"

echo "Testing Go Service API Integration..."

# Test 1: K8sGPT Analysis
echo "1. Testing K8sGPT Analysis endpoint..."
curl -X POST "$GO_SERVICE/api/v1/k8sgpt-analyze" \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "test-pod", "namespace": "default"}' \
  | jq .

# Test 2: Pod Status
echo "2. Testing Pod Status endpoint..."
curl "$GO_SERVICE/api/v1/pod-status/test-pod?namespace=default" | jq .

# Test 3: Health Check
echo "3. Testing Health endpoint..."
curl "$GO_SERVICE/health" | jq .

# Test 4: Python Service Integration
echo "4. Testing Python Service integration..."
curl -X POST "$PYTHON_SERVICE/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "test-pod",
    "namespace": "default",
    "error_type": "ImagePullBackOff"
  }' | jq .

echo "Integration tests completed!"
```

## 🚀 Deployment Configuration

### Docker Compose for Full Stack

```yaml
# docker-compose.integration.yml
version: '3.8'

services:
  k8s-ai-agent:
    build: 
      context: ../k8s-ai-agent-mvp
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - KUBECONFIG=/root/.kube/config
    volumes:
      - ~/.kube:/root/.kube:ro
    networks:
      - k8s-ai-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  k8s-reflexion-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GO_SERVICE_URL=http://k8s-ai-agent:8080
      - REFLECTION_DEPTH=medium
    depends_on:
      k8s-ai-agent:
        condition: service_healthy
    networks:
      - k8s-ai-network
    volumes:
      - ./logs:/app/logs
      - reflexion-data:/app/reflexion_memory.json

networks:
  k8s-ai-network:
    driver: bridge

volumes:
  reflexion-data:
```

### Environment Configuration

```bash
# .env.integration
OPENAI_API_KEY=sk-your-openai-api-key
GO_SERVICE_URL=http://k8s-ai-agent:8080
REFLECTION_DEPTH=medium
KUBECONFIG=/path/to/your/kubeconfig
```

## 📊 Monitoring Integration

### Shared Metrics Dashboard

```yaml
# monitoring/docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:
```

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'k8s-ai-agent'
    static_configs:
      - targets: ['k8s-ai-agent:8080']
    metrics_path: '/metrics'

  - job_name: 'k8s-reflexion-service'
    static_configs:
      - targets: ['k8s-reflexion-service:8000']
    metrics_path: '/metrics'
```

## 🔍 Troubleshooting

### Common Integration Issues

1. **Connection Refused**
   ```bash
   # Check if Go service is running
   curl http://localhost:8080/health
   
   # Check Docker network connectivity
   docker network ls
   docker network inspect k8s-ai-network
   ```

2. **API Endpoint Not Found**
   ```bash
   # Verify Go service has new endpoints
   curl http://localhost:8080/api/v1/k8sgpt-analyze
   
   # Check Go service logs
   docker logs k8s-ai-agent
   ```

3. **OpenAI API Errors**
   ```bash
   # Verify API key is set
   echo $OPENAI_API_KEY
   
   # Check Python service logs
   docker logs k8s-reflexion-service
   ```

### Debug Commands

```bash
# Check service connectivity
curl http://localhost:8080/health && echo "Go service OK"
curl http://localhost:8000/health && echo "Python service OK"

# Test full integration
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=ImagePullBackOff" -d "success=true"

# Monitor logs
docker-compose logs -f

# Check network connectivity
docker exec k8s-reflexion-service curl http://k8s-ai-agent:8080/health
```

## 🎯 Performance Optimization

### Go Service Optimizations

```go
// Add connection pooling for HTTP client
var httpClient = &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:       10,
        IdleConnTimeout:    30 * time.Second,
        DisableCompression: true,
    },
}

// Add request validation middleware
func validateRequest() gin.HandlerFunc {
    return gin.CustomRecovery(func(c *gin.Context, recovered interface{}) {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
    })
}
```

### Python Service Optimizations

```python
# Add connection pooling in observation engine
import httpx

class ObservationEngine:
    def __init__(self, go_service_url: str):
        self.go_service_url = go_service_url
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
```

## 📋 Integration Checklist

- [ ] Go service API endpoints implemented
- [ ] HTTP client configured in Python service
- [ ] Error handling added for network failures
- [ ] Authentication/authorization configured (if needed)
- [ ] Logging integrated between services
- [ ] Health checks implemented
- [ ] Monitoring and metrics configured
- [ ] Integration tests written and passing
- [ ] Docker compose configuration working
- [ ] Documentation updated

## 🚀 Next Steps

1. **Implement the required Go API endpoints**
2. **Test integration with curl/Postman**
3. **Deploy both services with docker-compose**
4. **Create monitoring dashboard**
5. **Add comprehensive integration tests**
6. **Document operational procedures**

This integration enables the autonomous learning capabilities of the Reflexion service while leveraging the existing Go service's Kubernetes integration and execution capabilities.