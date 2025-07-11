# K8s Reflexion Service

Advanced Kubernetes error resolution service with **LangGraph + Reflexion** integration for autonomous learning and strategy evolution.

## 🚀 Overview

This service extends the K8s AI Agent with **true autonomous capabilities** through:

- **🧠 LangGraph Workflows**: State machine-based agent flows with conditional routing
- **🔄 Reflexion Learning**: Self-analysis and strategy evolution through reflection
- **📊 Multi-dimensional Observation**: Comprehensive outcome monitoring
- **💾 Episodic Memory**: Experience-based learning and pattern detection
- **⚡ Real-time Adaptation**: Dynamic strategy selection based on learned knowledge

## 📋 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Go Service    │───▶│  Python Service  │───▶│   OpenAI API    │
│  (Detection &   │    │  (Reflexion &    │    │  (Reflection)   │
│   Execution)    │    │   Learning)      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Knowledge Base  │
                    │  (Strategies &   │
                    │   Memory)        │
                    └──────────────────┘
```

### Core Components

1. **Observation Engine** (`src/nodes/observe.py`)
   - Multi-dimensional outcome monitoring
   - Performance metrics collection
   - Context and anomaly detection

2. **Reflection Engine** (`src/nodes/reflect.py`)
   - LLM-powered deep self-analysis
   - Insight extraction and quality assessment
   - Meta-cognition capabilities

3. **Learning Engine** (`src/nodes/learn.py`)
   - Strategy evolution and pattern detection
   - Episodic memory management
   - Knowledge base updates

4. **LangGraph Workflow** (`src/workflow.py`)
   - State machine-based agent flow
   - Conditional routing and retry logic
   - Human escalation handling

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- OpenAI API key
- Go K8s AI Agent running on port 8080

### Setup

```bash
# Clone and navigate
cd k8s-reflexion-service

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="sk-your-openai-api-key"
export GO_SERVICE_URL="http://localhost:8080"
export REFLECTION_DEPTH="medium"
```

### Docker Setup

```bash
# Build and run with docker-compose
docker-compose up --build

# Or run standalone
docker build -t k8s-reflexion-service .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="sk-your-key" \
  -e GO_SERVICE_URL="http://host.docker.internal:8080" \
  k8s-reflexion-service
```

## 🚀 Usage

### Quick Start

```bash
# Start the service
python start.py

# Or with custom configuration
python start.py --config custom-config.yaml --port 8001 --reload
```

### API Endpoints

#### Core Reflexion Workflow

```bash
# Process pod error through reflexive workflow
curl -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "failing-pod",
    "namespace": "default", 
    "error_type": "ImagePullBackOff",
    "thread_id": "session_001"
  }'
```

**Response:**
```json
{
  "workflow_id": "reflexive_20240710_143022_123",
  "success": true,
  "pod_name": "failing-pod",
  "final_strategy": {
    "type": "image_tag_replacement",
    "confidence": 0.95,
    "selection_reason": "highest_confidence_learned"
  },
  "resolution_time": 32.5,
  "requires_human_intervention": false,
  "reflexion_summary": {
    "reflections_performed": 2,
    "strategies_learned": 1,
    "self_awareness_level": 0.78,
    "learning_velocity": 0.15
  }
}
```

#### Async Processing

```bash
# Start async processing
curl -X POST "http://localhost:8000/api/v1/reflexion/process-async" \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "complex-pod",
    "error_type": "CrashLoopBackOff"
  }'

# Check workflow status
curl "http://localhost:8000/api/v1/reflexion/workflow/async_complex-pod_20240710_143022"
```

#### Knowledge Base Access

```bash
# Get learned strategies
curl "http://localhost:8000/api/v1/reflexion/strategies"

# Get episodic memory
curl "http://localhost:8000/api/v1/reflexion/memory/episodic"

# Get system metrics
curl "http://localhost:8000/api/v1/reflexion/metrics"
```

#### Health & Monitoring

```bash
# Health check
curl "http://localhost:8000/health"

# API health
curl "http://localhost:8000/api/v1/health"
```

## 🧠 Reflexion Workflow

The service implements a sophisticated autonomous learning cycle:

### 1. **Analyze Error**
- K8sGPT integration for error analysis
- Context gathering and initialization

### 2. **Strategy Selection**
- Intelligent selection from learned strategies
- Confidence-based ranking
- Fallback to default strategies

### 3. **Execute Fix**
- Strategy execution via Go service
- Timeout and error handling
- Result validation

### 4. **Observe Outcome**
- Multi-dimensional observation
- Performance metrics collection
- Context and anomaly detection

### 5. **Reflect on Action**
- LLM-powered deep reflection
- Insight extraction and quality assessment
- Strategy modification suggestions

### 6. **Learn and Evolve**
- Strategy database updates
- Pattern detection and learning
- Episodic memory creation

### Conditional Routing

The workflow includes intelligent routing based on:
- **Success**: End workflow or continue learning
- **Retry**: Based on strategy confidence and retry count
- **Meta-reflection**: When reflection quality is low
- **Human escalation**: When automated resolution fails
- **Deep analysis**: For unknown error types

## 📊 Learning Capabilities

### Strategy Evolution
- **Automatic improvement** based on success rates
- **Context-aware** strategy selection
- **Confidence scoring** and threshold management
- **Version tracking** and rollback capability

### Pattern Detection
- **Error-namespace correlations**
- **Temporal clustering** analysis  
- **Strategy effectiveness** patterns
- **Anomaly detection** for unexpected behaviors

### Self-Awareness Metrics
- **Reflection quality** trending
- **Learning velocity** calculation
- **Strategy confidence** evolution
- **Meta-learning** performance tracking

## ⚙️ Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# Optional
GO_SERVICE_URL=http://localhost:8080           # Go service endpoint
REFLECTION_DEPTH=medium                        # shallow|medium|deep
PYTHONUNBUFFERED=1                            # Python output buffering
```

### Configuration File (`config.yaml`)

```yaml
# Service settings
service:
  port: 8000
  debug: true

# OpenAI settings  
openai:
  model: "gpt-4-turbo-preview"
  temperature: 0.1
  max_tokens: 2000

# Reflexion settings
reflexion:
  reflection_depth: "medium"
  strategy_confidence_threshold: 0.7
  max_reflection_cycles: 5

# Workflow settings
workflow:
  max_retry_count: 3
  execution_timeout: 120
  checkpointing_enabled: true
```

## 🧪 Development & Testing

### Debug Endpoints

```bash
# Simulate reflection process
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=ImagePullBackOff" \
     -d "success=true" \
     -d "resolution_time=45.0"
```

### Development Mode

```bash
# Start with auto-reload
python start.py --reload --log-level debug

# Use mock Go service
docker-compose --profile mock up
```

### Testing Scenarios

1. **ImagePullBackOff**: Test image tag replacement strategies
2. **CrashLoopBackOff**: Test resource and timing strategies  
3. **OOMKilled**: Test memory optimization strategies
4. **Complex scenarios**: Multi-retry with meta-reflection

## 📈 Monitoring

### Key Metrics

- **Success Rate**: Overall resolution success percentage
- **Learning Velocity**: How fast the agent improves
- **Self-Awareness Level**: Reflection quality and meta-cognition
- **Strategy Confidence**: Average confidence in learned strategies
- **Resolution Time**: Average time to fix errors

### Logs and Debugging

```bash
# View logs
tail -f logs/reflexion.log

# Check memory usage
ls -la reflexion_memory.json

# Monitor Docker logs
docker-compose logs -f k8s-reflexion-service
```

## 🔄 Integration with Go Service

The Python service communicates with the Go K8s AI Agent via REST API:

### Required Go Endpoints

```go
// K8sGPT analysis
POST /api/v1/k8sgpt-analyze
{
  "pod_name": "failing-pod",
  "namespace": "default"
}

// Execute fix strategy  
POST /api/v1/execute-fix
{
  "pod_name": "failing-pod", 
  "namespace": "default",
  "strategy": {...}
}

// Pod status check
GET /api/v1/pod-status/{pod_name}?namespace=default

// Health check
GET /health
```

## 🚀 Deployment

### Production Deployment

```bash
# Build production image
docker build -t k8s-reflexion-service:latest .

# Run with production config
docker run -d \
  --name k8s-reflexion \
  -p 8000:8000 \
  -e OPENAI_API_KEY="sk-prod-key" \
  -e GO_SERVICE_URL="http://k8s-ai-agent:8080" \
  -v $(pwd)/prod-config.yaml:/app/config.yaml \
  -v reflexion-data:/app/reflexion_memory.json \
  k8s-reflexion-service:latest
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-reflexion-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: k8s-reflexion-service
  template:
    metadata:
      labels:
        app: k8s-reflexion-service
    spec:
      containers:
      - name: reflexion-service
        image: k8s-reflexion-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        - name: GO_SERVICE_URL
          value: "http://k8s-ai-agent-service:8080"
```

## 📚 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
- Check the logs: `tail -f logs/reflexion.log`
- Review configuration: `cat config.yaml`
- Test health endpoints: `curl localhost:8000/health`
- Enable debug mode: `python start.py --log-level debug`

---

**K8s Reflexion Service** - Autonomous Kubernetes error resolution with true learning capabilities! 🚀🧠