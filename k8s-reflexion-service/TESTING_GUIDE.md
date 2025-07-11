# K8s Reflexion Service - Comprehensive Testing Guide

Complete testing guide for the autonomous Kubernetes error resolution service with LangGraph + Reflexion integration.

## 🎯 Overview

This guide covers all testing scenarios from basic functionality to full integration with the Go service, enabling you to validate the autonomous learning capabilities of the Reflexion system.

## 📋 Testing Checklist

- [ ] Environment setup and dependencies
- [ ] Basic service health checks
- [ ] Reflection engine testing
- [ ] Knowledge base functionality
- [ ] Configuration management
- [ ] Go service integration
- [ ] Full workflow testing
- [ ] Performance and monitoring
- [ ] Error scenarios and edge cases

## 🚀 Quick Start Testing

### Prerequisites

```bash
# Required tools
- Python 3.11+
- curl or HTTPie
- jq (for JSON formatting)
- Docker & Docker Compose (optional)
- Go 1.24+ (for integration testing)

# Environment variables
export OPENAI_API_KEY="sk-your-actual-openai-key"
export GO_SERVICE_URL="http://localhost:8080"
export REFLECTION_DEPTH="medium"
```

### Fastest Test Route

```bash
# 1. Start the service
cd k8s-reflexion-service
pip install -r requirements.txt
python start.py

# 2. Quick health check
curl http://localhost:8000/health | jq

# 3. Interactive testing
open http://localhost:8000/api/docs
```

## 🧪 Test Categories

## 1. 🏥 **Health & Basic Functionality Tests**

### Test 1.1: Service Health Check
```bash
# Basic health check
curl http://localhost:8000/health | jq

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-07-10T14:30:22.123456",
  "openai_configured": true,
  "go_service_reachable": false
}
```

### Test 1.2: API Health Check
```bash
# API-specific health
curl http://localhost:8000/api/v1/health | jq

# Expected response:
{
  "status": "ok",
  "service": "k8s-reflexion",
  "timestamp": "2024-07-10T14:30:22.123456"
}
```

### Test 1.3: Service Configuration
```bash
# Get current configuration
curl http://localhost:8000/api/v1/config | jq

# Expected response:
{
  "reflection_depth": "medium",
  "go_service_url": "http://localhost:8080",
  "openai_model": "gpt-4-turbo-preview",
  "max_reflection_depth": 5,
  "strategy_confidence_threshold": 0.7
}
```

**✅ Success Criteria:**
- Health endpoints return 200 status
- OpenAI configuration detected
- Service starts without errors

## 2. 🧠 **Reflection Engine Tests**

### Test 2.1: Basic Reflection Simulation
```bash
# Test successful scenario reflection
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=ImagePullBackOff" \
     -d "success=true" \
     -d "resolution_time=45.0" | jq

# Expected response:
{
  "debug_reflection": true,
  "self_awareness_level": 0.7,
  "insights_generated": 3,
  "reflection_quality": 0.8,
  "timestamp": "2024-07-10T14:30:22.123456"
}
```

### Test 2.2: Failed Scenario Reflection
```bash
# Test failed scenario reflection
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=CrashLoopBackOff" \
     -d "success=false" \
     -d "resolution_time=120.0" | jq

# Expected response:
{
  "debug_reflection": true,
  "self_awareness_level": 0.5,
  "insights_generated": 4,
  "reflection_quality": 0.9,
  "timestamp": "2024-07-10T14:30:22.123456"
}
```

### Test 2.3: Different Error Types
```bash
# Test various error types
for error_type in "ImagePullBackOff" "CrashLoopBackOff" "OOMKilled" "InvalidImageName"; do
  echo "Testing $error_type..."
  curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
    -G -d "error_type=$error_type" -d "success=true" | jq .self_awareness_level
done
```

**✅ Success Criteria:**
- Reflection generates insights (2-5 insights expected)
- Self-awareness level between 0.0-1.0
- Quality scores > 0.5
- Different error types produce domain-specific reflections

## 3. 📚 **Knowledge Base Tests**

### Test 3.1: Strategy Database
```bash
# Get learned strategies
curl "http://localhost:8000/api/v1/reflexion/strategies" | jq

# Expected response:
{
  "strategies": [
    {
      "id": "temporal_1234",
      "type": "temporal_optimization",
      "confidence": 0.85,
      "usage_count": 5,
      "success_rate": 0.8,
      "description": "Timing-based optimization for CrashLoopBackOff"
    }
  ],
  "total_count": 2,
  "timestamp": "2024-07-10T14:30:22.123456"
}
```

### Test 3.2: Episodic Memory
```bash
# Get episodic memory entries
curl "http://localhost:8000/api/v1/reflexion/memory/episodic" | jq

# Expected response:
{
  "episodes": [
    {
      "episode_id": "ep_001",
      "context": {"pod_name": "test-pod", "error_type": "ImagePullBackOff"},
      "action_taken": {"type": "image_tag_replacement"},
      "outcome": {"success": true, "resolution_time": 30},
      "lessons_learned": ["Image tag validation is crucial"],
      "timestamp": "2024-07-10T10:30:00"
    }
  ],
  "total_episodes": 15,
  "memory_utilization": 0.3
}
```

### Test 3.3: System Metrics
```bash
# Get overall system metrics
curl "http://localhost:8000/api/v1/reflexion/metrics" | jq

# Expected response:
{
  "total_workflows": 42,
  "success_rate": 0.85,
  "average_resolution_time": 45.2,
  "total_strategies_learned": 15,
  "average_self_awareness": 0.72,
  "learning_velocity": 0.15,
  "timestamp": "2024-07-10T14:30:22.123456"
}
```

**✅ Success Criteria:**
- Strategy database returns structured data
- Episodic memory shows learning history
- Metrics show reasonable values
- All endpoints return valid JSON

## 4. ⚙️ **Configuration Tests**

### Test 4.1: Update Reflection Depth
```bash
# Test valid depth changes
for depth in "shallow" "medium" "deep"; do
  echo "Testing depth: $depth"
  curl -X POST "http://localhost:8000/api/v1/config/reflection-depth" \
    -H "Content-Type: application/json" \
    -d "\"$depth\"" | jq
done

# Expected response:
{
  "message": "Reflection depth updated to deep",
  "timestamp": "2024-07-10T14:30:22.123456"
}
```

### Test 4.2: Invalid Configuration
```bash
# Test invalid depth (should fail)
curl -X POST "http://localhost:8000/api/v1/config/reflection-depth" \
  -H "Content-Type: application/json" \
  -d '"invalid"' | jq

# Expected response (400 error):
{
  "detail": "Invalid depth. Must be one of: ['shallow', 'medium', 'deep']"
}
```

**✅ Success Criteria:**
- Valid configurations accepted
- Invalid configurations rejected with proper error messages
- Configuration changes take effect

## 5. 🔗 **Go Service Integration Tests**

### Prerequisites: Go Service Setup

First, add these endpoints to your Go service:

```go
// Add to cmd/main.go
func setupAPIRoutes(r *gin.Engine) {
    api := r.Group("/api/v1")
    
    // K8sGPT Analysis endpoint
    api.POST("/k8sgpt-analyze", func(c *gin.Context) {
        c.JSON(200, gin.H{
            "success": true,
            "analysis": map[string]interface{}{
                "problems": []string{"ImagePullBackOff detected"},
                "confidence": 0.95,
            },
            "error_type": "ImagePullBackOff",
            "timestamp": time.Now().Format(time.RFC3339),
        })
    })
    
    // Execute fix endpoint
    api.POST("/execute-fix", func(c *gin.Context) {
        c.JSON(200, gin.H{
            "success": true,
            "execution_id": "test_123",
            "result": map[string]interface{}{
                "pod_recreated": true,
                "new_image": "nginx:latest",
            },
            "timestamp": time.Now().Format(time.RFC3339),
        })
    })
    
    // Pod status endpoint
    api.GET("/pod-status/:podName", func(c *gin.Context) {
        c.JSON(200, gin.H{
            "status": "Running",
            "containers_ready": true,
            "restart_count": 0,
            "ready_time": time.Now().Format(time.RFC3339),
            "health_checks": map[string]string{"liveness": "ok"},
            "timestamp": time.Now().Format(time.RFC3339),
        })
    })
}

// Add to main function
func main() {
    r := gin.Default()
    setupAPIRoutes(r)
    r.Run(":8080")
}
```

### Test 5.1: Go Service Connectivity
```bash
# Start Go service with new endpoints
cd ../k8s-ai-agent-mvp
go run cmd/main.go &

# Test Go service endpoints
curl -X POST "http://localhost:8080/api/v1/k8sgpt-analyze" \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "test-pod", "namespace": "default"}' | jq

curl "http://localhost:8080/api/v1/pod-status/test-pod?namespace=default" | jq
```

### Test 5.2: Full Integration Test
```bash
# Start both services
cd ../k8s-ai-agent-mvp && go run cmd/main.go &
cd ../k8s-reflexion-service && python start.py &

# Test full reflexion workflow
curl -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "test-pod",
    "namespace": "default",
    "error_type": "ImagePullBackOff",
    "thread_id": "test_session_001"
  }' | jq

# Expected response:
{
  "workflow_id": "reflexive_20240710_143022_123",
  "success": true,
  "pod_name": "test-pod",
  "final_strategy": {
    "type": "image_tag_replacement",
    "confidence": 0.95,
    "selection_reason": "default_fallback"
  },
  "resolution_time": 32.5,
  "requires_human_intervention": false,
  "reflexion_summary": {
    "reflections_performed": 1,
    "strategies_learned": 0,
    "self_awareness_level": 0.7,
    "learning_velocity": 0.0
  }
}
```

### Test 5.3: Async Processing
```bash
# Test async workflow
curl -X POST "http://localhost:8000/api/v1/reflexion/process-async" \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "complex-pod",
    "namespace": "default",
    "error_type": "CrashLoopBackOff"
  }' | jq

# Check workflow status
WORKFLOW_ID=$(curl -s -X POST "http://localhost:8000/api/v1/reflexion/process-async" \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "status-test", "error_type": "ImagePullBackOff"}' | jq -r .workflow_id)

curl "http://localhost:8000/api/v1/reflexion/workflow/$WORKFLOW_ID" | jq
```

**✅ Success Criteria:**
- Both services communicate successfully
- Full workflow completes without errors
- Async processing returns workflow ID
- Status tracking works

## 6. 🐳 **Docker Integration Tests**

### Test 6.1: Docker Compose Setup
```bash
# Build and start with docker-compose
docker-compose up --build -d

# Wait for services to be ready
sleep 30

# Test health endpoints
curl http://localhost:8000/health | jq
curl http://localhost:8080/health | jq
```

### Test 6.2: Docker Network Testing
```bash
# Test inter-service communication
docker exec k8s-reflexion-service curl http://k8s-ai-agent:8080/health

# Test full workflow in Docker
curl -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "docker-test-pod",
    "error_type": "ImagePullBackOff"
  }' | jq
```

### Test 6.3: Docker Logs and Monitoring
```bash
# Check logs
docker-compose logs k8s-reflexion-service
docker-compose logs k8s-ai-agent

# Monitor resource usage
docker stats
```

**✅ Success Criteria:**
- Both containers start successfully
- Network communication works
- No critical errors in logs
- Resource usage reasonable

## 7. 📊 **Performance & Load Tests**

### Test 7.1: Concurrent Requests
```bash
# Test multiple concurrent reflections
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
    -G -d "error_type=ImagePullBackOff" -d "success=true" &
done
wait

echo "All concurrent tests completed"
```

### Test 7.2: Memory Usage Monitoring
```bash
# Monitor memory during testing
ps aux | grep python | grep reflexion
htop -p $(pgrep -f "python.*reflexion")
```

### Test 7.3: Response Time Testing
```bash
# Measure response times
time curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=CrashLoopBackOff" -d "success=false" > /dev/null

# Expected: < 10 seconds for reflection
```

**✅ Success Criteria:**
- Handles 5+ concurrent requests
- Memory usage < 500MB
- Response times < 10 seconds
- No memory leaks over time

## 8. 🚨 **Error Scenarios & Edge Cases**

### Test 8.1: Invalid OpenAI Key
```bash
# Test with invalid API key
OPENAI_API_KEY="invalid-key" python start.py

# Expected: Service starts but reflection fails gracefully
```

### Test 8.2: Go Service Unavailable
```bash
# Stop Go service and test
pkill -f "go run"

# Test reflexion (should handle gracefully)
curl -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "test", "error_type": "ImagePullBackOff"}' | jq
```

### Test 8.3: Malformed Requests
```bash
# Test various malformed requests
curl -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}' | jq

curl -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d 'invalid json' | jq
```

### Test 8.4: Rate Limiting & Timeouts
```bash
# Test rapid requests (should handle gracefully)
for i in {1..20}; do
  curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
    -G -d "error_type=Test$i" &
done
```

**✅ Success Criteria:**
- Service handles errors gracefully
- Proper error messages returned
- No service crashes
- Fallback mechanisms work

## 9. 🔍 **Monitoring & Debug Tests**

### Test 9.1: Log Analysis
```bash
# Check log files
tail -f logs/reflexion.log | grep ERROR
tail -f logs/reflexion.log | grep WARN

# Check for memory persistence
cat reflexion_memory.json | jq .timestamp
```

### Test 9.2: Health Check Monitoring
```bash
# Continuous health monitoring
while true; do
  status=$(curl -s http://localhost:8000/health | jq -r .status)
  echo "$(date): Health status: $status"
  sleep 30
done
```

### Test 9.3: Memory File Integrity
```bash
# Validate memory file structure
cat reflexion_memory.json | jq . > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Check file size growth
ls -la reflexion_memory.json
```

**✅ Success Criteria:**
- Logs show appropriate detail level
- Memory file maintains valid JSON
- Health checks remain stable
- No memory corruption

## 🎯 **Complete Test Suite Script**

Create this comprehensive test script:

```bash
#!/bin/bash
# complete_test_suite.sh

set -e

echo "🚀 Starting K8s Reflexion Service Test Suite..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        ((TESTS_FAILED++))
    fi
    echo
}

# Ensure services are running
echo "📋 Checking prerequisites..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Python service not running. Start with: python start.py"
    exit 1
fi

echo "✅ Python service is running"

# Run test suite
echo "🧪 Running test suite..."

# Health tests
run_test "Service Health Check" "curl -s http://localhost:8000/health | jq -e '.status == \"healthy\" or .status == \"degraded\"'"
run_test "API Health Check" "curl -s http://localhost:8000/api/v1/health | jq -e '.status == \"ok\"'"

# Reflection tests
run_test "Basic Reflection Simulation" "curl -s -X POST 'http://localhost:8000/api/v1/debug/simulate-reflection?error_type=ImagePullBackOff&success=true' | jq -e '.debug_reflection == true'"
run_test "Failed Scenario Reflection" "curl -s -X POST 'http://localhost:8000/api/v1/debug/simulate-reflection?error_type=CrashLoopBackOff&success=false' | jq -e '.self_awareness_level > 0'"

# Knowledge base tests
run_test "Strategy Database Access" "curl -s http://localhost:8000/api/v1/reflexion/strategies | jq -e '.strategies | type == \"array\"'"
run_test "Episodic Memory Access" "curl -s http://localhost:8000/api/v1/reflexion/memory/episodic | jq -e '.episodes | type == \"array\"'"
run_test "System Metrics Access" "curl -s http://localhost:8000/api/v1/reflexion/metrics | jq -e '.total_workflows | type == \"number\"'"

# Configuration tests
run_test "Configuration Access" "curl -s http://localhost:8000/api/v1/config | jq -e '.reflection_depth'"
run_test "Valid Config Update" "curl -s -X POST http://localhost:8000/api/v1/config/reflection-depth -H 'Content-Type: application/json' -d '\"medium\"' | jq -e '.message'"

# Error handling tests
run_test "Invalid Config Update" "curl -s -X POST http://localhost:8000/api/v1/config/reflection-depth -H 'Content-Type: application/json' -d '\"invalid\"' | jq -e '.detail'"

# Integration tests (if Go service is available)
if curl -s http://localhost:8080/health > /dev/null; then
    echo "🔗 Go service detected, running integration tests..."
    run_test "Go Service Integration" "curl -s -X POST http://localhost:8000/api/v1/reflexion/process -H 'Content-Type: application/json' -d '{\"pod_name\":\"test\",\"error_type\":\"ImagePullBackOff\"}' | jq -e '.workflow_id'"
else
    echo "⚠️ Go service not running, skipping integration tests"
fi

# Summary
echo "📊 Test Results Summary:"
echo -e "✅ Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "❌ Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "📈 Success Rate: $(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))%"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️ Some tests failed. Check the output above.${NC}"
    exit 1
fi
```

### Run Complete Test Suite:
```bash
chmod +x complete_test_suite.sh
./complete_test_suite.sh
```

## 📋 **Test Documentation Template**

Use this template to document your test runs:

```markdown
## Test Run Report - [Date]

### Environment
- Python Service: ✅ Running on port 8000
- Go Service: ✅/❌ Running on port 8080  
- OpenAI API: ✅ Configured
- Docker: ✅/❌ Available

### Test Results
| Test Category | Passed | Failed | Notes |
|---------------|--------|---------|-------|
| Health Checks | 2/2 | 0/2 | All services responding |
| Reflection Engine | 3/3 | 0/3 | GPT-4 integration working |
| Knowledge Base | 3/3 | 0/3 | Data persistence working |
| Configuration | 2/2 | 0/2 | Config updates successful |
| Integration | 1/1 | 0/1 | Go service communication OK |
| Error Handling | 2/3 | 1/3 | One timeout issue |

### Issues Found
- [ ] Timeout on large reflection requests
- [ ] Memory file growing larger than expected

### Recommendations
- Increase timeout for reflection endpoint
- Implement memory cleanup routine
```

## 🎯 **Next Steps After Testing**

1. **✅ All Basic Tests Pass**: Ready for Go service integration
2. **✅ Integration Tests Pass**: Ready for production deployment  
3. **✅ Performance Tests Pass**: Ready for load testing
4. **✅ Error Handling Works**: Ready for operational deployment

**Happy Testing! 🚀🧪**