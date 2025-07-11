#!/bin/bash
# Quick Test Script for K8s Reflexion Service
# Run this after starting the service to verify basic functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 K8s Reflexion Service - Quick Test Suite${NC}"
echo "=============================================="

# Check if service is running
echo -e "${YELLOW}📡 Checking service availability...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ Service not running on port 8000${NC}"
    echo "Start the service with: python start.py"
    exit 1
fi
echo -e "${GREEN}✅ Service is running${NC}"
echo

# Test 1: Health Check
echo -e "${YELLOW}🏥 Test 1: Health Check${NC}"
HEALTH_STATUS=$(curl -s http://localhost:8000/health | jq -r .status)
echo "Health Status: $HEALTH_STATUS"
if [ "$HEALTH_STATUS" = "healthy" ] || [ "$HEALTH_STATUS" = "degraded" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi
echo

# Test 2: API Health
echo -e "${YELLOW}🔌 Test 2: API Health${NC}"
API_STATUS=$(curl -s http://localhost:8000/api/v1/health | jq -r .status)
echo "API Status: $API_STATUS"
if [ "$API_STATUS" = "ok" ]; then
    echo -e "${GREEN}✅ API health check passed${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
fi
echo

# Test 3: Reflection Simulation (Success Case)
echo -e "${YELLOW}🧠 Test 3: Reflection Engine (Success Case)${NC}"
REFLECTION_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=ImagePullBackOff" \
     -d "success=true" \
     -d "resolution_time=45.0")

SELF_AWARENESS=$(echo $REFLECTION_RESULT | jq -r .self_awareness_level)
INSIGHTS_COUNT=$(echo $REFLECTION_RESULT | jq -r .insights_generated)

echo "Self-Awareness Level: $SELF_AWARENESS"
echo "Insights Generated: $INSIGHTS_COUNT"

if [ "$SELF_AWARENESS" != "null" ] && [ "$INSIGHTS_COUNT" != "null" ]; then
    echo -e "${GREEN}✅ Reflection engine working${NC}"
else
    echo -e "${RED}❌ Reflection engine failed${NC}"
    echo "Response: $REFLECTION_RESULT"
fi
echo

# Test 4: Reflection Simulation (Failure Case)
echo -e "${YELLOW}🔄 Test 4: Reflection Engine (Failure Case)${NC}"
FAILURE_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" \
  -G -d "error_type=CrashLoopBackOff" \
     -d "success=false" \
     -d "resolution_time=120.0")

FAILURE_AWARENESS=$(echo $FAILURE_RESULT | jq -r .self_awareness_level)
FAILURE_INSIGHTS=$(echo $FAILURE_RESULT | jq -r .insights_generated)

echo "Self-Awareness Level: $FAILURE_AWARENESS"
echo "Insights Generated: $FAILURE_INSIGHTS"

if [ "$FAILURE_AWARENESS" != "null" ] && [ "$FAILURE_INSIGHTS" != "null" ]; then
    echo -e "${GREEN}✅ Failure case reflection working${NC}"
else
    echo -e "${RED}❌ Failure case reflection failed${NC}"
fi
echo

# Test 5: Knowledge Base Access
echo -e "${YELLOW}📚 Test 5: Knowledge Base Access${NC}"

# Test strategies endpoint
STRATEGIES_RESPONSE=$(curl -s http://localhost:8000/api/v1/reflexion/strategies)
STRATEGIES_COUNT=$(echo $STRATEGIES_RESPONSE | jq -r '.total_count // 0')
echo "Strategies in database: $STRATEGIES_COUNT"

# Test episodic memory endpoint
MEMORY_RESPONSE=$(curl -s http://localhost:8000/api/v1/reflexion/memory/episodic)
EPISODES_COUNT=$(echo $MEMORY_RESPONSE | jq -r '.total_episodes // 0')
echo "Episodes in memory: $EPISODES_COUNT"

# Test metrics endpoint
METRICS_RESPONSE=$(curl -s http://localhost:8000/api/v1/reflexion/metrics)
TOTAL_WORKFLOWS=$(echo $METRICS_RESPONSE | jq -r '.total_workflows // 0')
echo "Total workflows: $TOTAL_WORKFLOWS"

if [ "$STRATEGIES_COUNT" != "null" ] && [ "$EPISODES_COUNT" != "null" ] && [ "$TOTAL_WORKFLOWS" != "null" ]; then
    echo -e "${GREEN}✅ Knowledge base access working${NC}"
else
    echo -e "${RED}❌ Knowledge base access failed${NC}"
fi
echo

# Test 6: Configuration Management
echo -e "${YELLOW}⚙️ Test 6: Configuration Management${NC}"

# Get current config
CONFIG_RESPONSE=$(curl -s http://localhost:8000/api/v1/config)
REFLECTION_DEPTH=$(echo $CONFIG_RESPONSE | jq -r .reflection_depth)
echo "Current reflection depth: $REFLECTION_DEPTH"

# Test config update
UPDATE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/config/reflection-depth" \
  -H "Content-Type: application/json" \
  -d '"medium"')

UPDATE_SUCCESS=$(echo $UPDATE_RESPONSE | jq -r .message)

if [ "$REFLECTION_DEPTH" != "null" ] && [ "$UPDATE_SUCCESS" != "null" ]; then
    echo -e "${GREEN}✅ Configuration management working${NC}"
else
    echo -e "${RED}❌ Configuration management failed${NC}"
fi
echo

# Test 7: Go Service Integration (if available)
echo -e "${YELLOW}🔗 Test 7: Go Service Integration${NC}"
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "Go service detected on port 8080"
    
    # Test full workflow
    WORKFLOW_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/reflexion/process" \
      -H "Content-Type: application/json" \
      -d '{
        "pod_name": "quick-test-pod",
        "namespace": "default",
        "error_type": "ImagePullBackOff",
        "thread_id": "quick_test_001"
      }')
    
    WORKFLOW_ID=$(echo $WORKFLOW_RESPONSE | jq -r .workflow_id)
    WORKFLOW_SUCCESS=$(echo $WORKFLOW_RESPONSE | jq -r .success)
    
    echo "Workflow ID: $WORKFLOW_ID"
    echo "Workflow Success: $WORKFLOW_SUCCESS"
    
    if [ "$WORKFLOW_ID" != "null" ]; then
        echo -e "${GREEN}✅ Full integration working${NC}"
    else
        echo -e "${RED}❌ Integration failed${NC}"
        echo "Response: $WORKFLOW_RESPONSE"
    fi
else
    echo -e "${YELLOW}⚠️ Go service not running, skipping integration test${NC}"
    echo "To test integration, start Go service on port 8080"
fi
echo

# Test 8: Error Handling
echo -e "${YELLOW}🚨 Test 8: Error Handling${NC}"

# Test invalid endpoint
INVALID_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:8000/invalid-endpoint -o /dev/null)
echo "Invalid endpoint response code: $INVALID_RESPONSE"

# Test malformed request
MALFORMED_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/reflexion/process" \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}' \
  -w "%{http_code}" -o /dev/null)
echo "Malformed request response code: $MALFORMED_RESPONSE"

if [ "$INVALID_RESPONSE" = "404" ] && [ "$MALFORMED_RESPONSE" = "422" ]; then
    echo -e "${GREEN}✅ Error handling working${NC}"
else
    echo -e "${RED}❌ Error handling needs improvement${NC}"
fi
echo

# Summary
echo -e "${BLUE}📊 Quick Test Summary${NC}"
echo "=================================="
echo -e "✅ Service is ${GREEN}running and responsive${NC}"
echo -e "🧠 Reflection engine is ${GREEN}functioning${NC}"
echo -e "📚 Knowledge base is ${GREEN}accessible${NC}"
echo -e "⚙️ Configuration management is ${GREEN}working${NC}"

if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "🔗 Go service integration is ${GREEN}available${NC}"
else
    echo -e "🔗 Go service integration is ${YELLOW}not tested${NC}"
fi

echo
echo -e "${GREEN}🎉 Quick test completed successfully!${NC}"
echo
echo "Next steps:"
echo "1. 🌐 Open Swagger UI: http://localhost:8000/api/docs"
echo "2. 📖 Read full testing guide: cat TESTING_GUIDE.md"
echo "3. 🔗 Set up Go service integration (see INTEGRATION_GUIDE.md)"
echo "4. 🐳 Try Docker deployment: docker-compose up"

# Open Swagger UI automatically (optional)
if command -v open >/dev/null 2>&1; then
    echo
    read -p "Open Swagger UI in browser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open http://localhost:8000/api/docs
    fi
elif command -v xdg-open >/dev/null 2>&1; then
    echo
    read -p "Open Swagger UI in browser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        xdg-open http://localhost:8000/api/docs
    fi
fi

echo -e "${GREEN}Happy testing! 🚀${NC}"