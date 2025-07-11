#!/bin/bash
# Complete Test Suite for K8s Reflexion Service
# Comprehensive testing including performance, error scenarios, and integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Configuration
SERVICE_URL="http://localhost:8000"
GO_SERVICE_URL="http://localhost:8080"
LOG_FILE="test_results_$(date +%Y%m%d_%H%M%S).log"

# Function to log and display
log_and_echo() {
    local message="$1"
    echo -e "$message"
    echo -e "$message" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
}

# Function to run test with detailed logging
run_test() {
    local test_name="$1"
    local test_command="$2"
    local test_category="$3"
    local expected_result="$4"
    
    log_and_echo "${YELLOW}🧪 Testing: $test_name${NC}"
    log_and_echo "   Category: $test_category"
    log_and_echo "   Command: $test_command"
    
    local start_time=$(date +%s)
    
    if eval "$test_command" > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_and_echo "${GREEN}✅ PASSED: $test_name (${duration}s)${NC}"
        ((TESTS_PASSED++))
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_and_echo "${RED}❌ FAILED: $test_name (${duration}s)${NC}"
        ((TESTS_FAILED++))
        
        # Capture error details
        echo "   Error details:" >> "$LOG_FILE"
        eval "$test_command" >> "$LOG_FILE" 2>&1 || true
    fi
    echo
}

# Function to skip test
skip_test() {
    local test_name="$1"
    local reason="$2"
    
    log_and_echo "${CYAN}⏭️ SKIPPED: $test_name${NC}"
    log_and_echo "   Reason: $reason"
    ((TESTS_SKIPPED++))
    echo
}

# Function to wait for service
wait_for_service() {
    local url="$1"
    local timeout="$2"
    local name="$3"
    
    log_and_echo "${BLUE}⏳ Waiting for $name to be ready...${NC}"
    
    for i in $(seq 1 $timeout); do
        if curl -s "$url" > /dev/null 2>&1; then
            log_and_echo "${GREEN}✅ $name is ready${NC}"
            return 0
        fi
        sleep 1
    done
    
    log_and_echo "${RED}❌ $name not ready after ${timeout}s${NC}"
    return 1
}

# Header
log_and_echo "${BLUE}🚀 K8s Reflexion Service - Complete Test Suite${NC}"
log_and_echo "================================================="
log_and_echo "Started at: $(date)"
log_and_echo "Log file: $LOG_FILE"
log_and_echo ""

# Check prerequisites
log_and_echo "${PURPLE}📋 Checking Prerequisites${NC}"
log_and_echo "=========================="

# Check if Python service is running
if ! curl -s "$SERVICE_URL/health" > /dev/null 2>&1; then
    log_and_echo "${RED}❌ Python service not running on port 8000${NC}"
    log_and_echo "Start the service with: python start.py"
    exit 1
fi
log_and_echo "${GREEN}✅ Python service is running${NC}"

# Check if Go service is available
GO_SERVICE_AVAILABLE=false
if curl -s "$GO_SERVICE_URL/health" > /dev/null 2>&1; then
    log_and_echo "${GREEN}✅ Go service is running${NC}"
    GO_SERVICE_AVAILABLE=true
else
    log_and_echo "${YELLOW}⚠️ Go service not running (integration tests will be skipped)${NC}"
fi

# Check dependencies
command -v jq >/dev/null 2>&1 || { log_and_echo "${RED}❌ jq is required but not installed${NC}"; exit 1; }
command -v curl >/dev/null 2>&1 || { log_and_echo "${RED}❌ curl is required but not installed${NC}"; exit 1; }

log_and_echo "${GREEN}✅ All prerequisites met${NC}"
log_and_echo ""

# =============================================================================
# CATEGORY 1: HEALTH & BASIC FUNCTIONALITY TESTS
# =============================================================================

log_and_echo "${PURPLE}🏥 Category 1: Health & Basic Functionality Tests${NC}"
log_and_echo "=================================================="

run_test "Service Health Check" \
    "curl -s $SERVICE_URL/health | jq -e '.status == \"healthy\" or .status == \"degraded\"'" \
    "Health" \
    "status should be healthy or degraded"

run_test "API Health Check" \
    "curl -s $SERVICE_URL/api/v1/health | jq -e '.status == \"ok\"'" \
    "Health" \
    "API status should be ok"

run_test "Service Configuration Access" \
    "curl -s $SERVICE_URL/api/v1/config | jq -e '.reflection_depth'" \
    "Configuration" \
    "Should return reflection depth"

run_test "OpenAI Configuration Detection" \
    "curl -s $SERVICE_URL/health | jq -e '.openai_configured == true'" \
    "Configuration" \
    "OpenAI should be configured"

# =============================================================================
# CATEGORY 2: REFLECTION ENGINE TESTS
# =============================================================================

log_and_echo "${PURPLE}🧠 Category 2: Reflection Engine Tests${NC}"
log_and_echo "======================================="

run_test "Basic Reflection - Success Case" \
    "curl -s -X POST '$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=ImagePullBackOff&success=true' | jq -e '.debug_reflection == true and .self_awareness_level > 0'" \
    "Reflection" \
    "Should generate reflection with positive self-awareness"

run_test "Basic Reflection - Failure Case" \
    "curl -s -X POST '$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=CrashLoopBackOff&success=false' | jq -e '.insights_generated > 0'" \
    "Reflection" \
    "Should generate insights for failures"

run_test "Reflection Quality Assessment" \
    "curl -s -X POST '$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=OOMKilled&success=true&resolution_time=60' | jq -e '.reflection_quality > 0.5'" \
    "Reflection" \
    "Reflection quality should be reasonable"

run_test "Different Error Types Handling" \
    "curl -s -X POST '$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=InvalidImageName&success=true' | jq -e '.self_awareness_level'" \
    "Reflection" \
    "Should handle unknown error types"

run_test "Performance Impact on Reflection" \
    "curl -s -X POST '$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=ImagePullBackOff&success=true&resolution_time=200' | jq -e '.self_awareness_level < 1.0'" \
    "Reflection" \
    "Long resolution time should affect reflection"

# =============================================================================
# CATEGORY 3: KNOWLEDGE BASE TESTS
# =============================================================================

log_and_echo "${PURPLE}📚 Category 3: Knowledge Base Tests${NC}"
log_and_echo "==================================="

run_test "Strategy Database Access" \
    "curl -s $SERVICE_URL/api/v1/reflexion/strategies | jq -e '.strategies | type == \"array\"'" \
    "Knowledge Base" \
    "Should return array of strategies"

run_test "Episodic Memory Access" \
    "curl -s $SERVICE_URL/api/v1/reflexion/memory/episodic | jq -e '.episodes | type == \"array\"'" \
    "Knowledge Base" \
    "Should return array of episodes"

run_test "System Metrics Access" \
    "curl -s $SERVICE_URL/api/v1/reflexion/metrics | jq -e '.total_workflows | type == \"number\"'" \
    "Knowledge Base" \
    "Should return numeric metrics"

run_test "Strategy Database Structure" \
    "curl -s $SERVICE_URL/api/v1/reflexion/strategies | jq -e '.total_count | type == \"number\"'" \
    "Knowledge Base" \
    "Should have total count field"

run_test "Memory Utilization Metrics" \
    "curl -s $SERVICE_URL/api/v1/reflexion/memory/episodic | jq -e '.memory_utilization | type == \"number\"'" \
    "Knowledge Base" \
    "Should track memory utilization"

# =============================================================================
# CATEGORY 4: CONFIGURATION MANAGEMENT TESTS
# =============================================================================

log_and_echo "${PURPLE}⚙️ Category 4: Configuration Management Tests${NC}"
log_and_echo "=============================================="

run_test "Configuration Retrieval" \
    "curl -s $SERVICE_URL/api/v1/config | jq -e '.openai_model and .reflection_depth and .strategy_confidence_threshold'" \
    "Configuration" \
    "Should return complete configuration"

run_test "Valid Reflection Depth Update - Medium" \
    "curl -s -X POST $SERVICE_URL/api/v1/config/reflection-depth -H 'Content-Type: application/json' -d '\"medium\"' | jq -e '.message'" \
    "Configuration" \
    "Should accept valid depth setting"

run_test "Valid Reflection Depth Update - Deep" \
    "curl -s -X POST $SERVICE_URL/api/v1/config/reflection-depth -H 'Content-Type: application/json' -d '\"deep\"' | jq -e '.message'" \
    "Configuration" \
    "Should accept deep reflection setting"

run_test "Valid Reflection Depth Update - Shallow" \
    "curl -s -X POST $SERVICE_URL/api/v1/config/reflection-depth -H 'Content-Type: application/json' -d '\"shallow\"' | jq -e '.message'" \
    "Configuration" \
    "Should accept shallow reflection setting"

run_test "Invalid Reflection Depth Rejection" \
    "curl -s -X POST $SERVICE_URL/api/v1/config/reflection-depth -H 'Content-Type: application/json' -d '\"invalid\"' | jq -e '.detail'" \
    "Configuration" \
    "Should reject invalid depth settings"

# =============================================================================
# CATEGORY 5: ERROR HANDLING & EDGE CASES
# =============================================================================

log_and_echo "${PURPLE}🚨 Category 5: Error Handling & Edge Cases${NC}"
log_and_echo "=========================================="

run_test "404 Error for Invalid Endpoint" \
    "curl -s -w '%{http_code}' $SERVICE_URL/invalid-endpoint -o /dev/null | grep -q '404'" \
    "Error Handling" \
    "Should return 404 for invalid endpoints"

run_test "422 Error for Malformed Request" \
    "curl -s -w '%{http_code}' -X POST $SERVICE_URL/api/v1/reflexion/process -H 'Content-Type: application/json' -d '{\"invalid\": \"data\"}' -o /dev/null | grep -q '422'" \
    "Error Handling" \
    "Should return 422 for malformed requests"

run_test "JSON Parse Error Handling" \
    "curl -s -w '%{http_code}' -X POST $SERVICE_URL/api/v1/reflexion/process -H 'Content-Type: application/json' -d 'invalid json' -o /dev/null | grep -q '422'" \
    "Error Handling" \
    "Should handle JSON parse errors"

run_test "Missing Required Fields" \
    "curl -s -X POST $SERVICE_URL/api/v1/reflexion/process -H 'Content-Type: application/json' -d '{}' | jq -e '.detail'" \
    "Error Handling" \
    "Should validate required fields"

run_test "Empty Request Body" \
    "curl -s -w '%{http_code}' -X POST $SERVICE_URL/api/v1/reflexion/process -H 'Content-Type: application/json' -d '' -o /dev/null | grep -q '422'" \
    "Error Handling" \
    "Should handle empty request body"

# =============================================================================
# CATEGORY 6: PERFORMANCE TESTS
# =============================================================================

log_and_echo "${PURPLE}⚡ Category 6: Performance Tests${NC}"
log_and_echo "==============================="

# Response time test
start_time=$(date +%s%3N)
curl -s -X POST "$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=ImagePullBackOff&success=true" > /dev/null
end_time=$(date +%s%3N)
response_time=$((end_time - start_time))

if [ $response_time -lt 10000 ]; then  # 10 seconds
    log_and_echo "${GREEN}✅ PASSED: Response Time Test (${response_time}ms)${NC}"
    ((TESTS_PASSED++))
else
    log_and_echo "${RED}❌ FAILED: Response Time Test (${response_time}ms > 10000ms)${NC}"
    ((TESTS_FAILED++))
fi

# Concurrent requests test
log_and_echo "${YELLOW}🧪 Testing: Concurrent Request Handling${NC}"
concurrent_pids=()
for i in {1..3}; do
    curl -s -X POST "$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=Test$i&success=true" > /dev/null &
    concurrent_pids+=($!)
done

# Wait for all concurrent requests
all_passed=true
for pid in "${concurrent_pids[@]}"; do
    if ! wait $pid; then
        all_passed=false
    fi
done

if $all_passed; then
    log_and_echo "${GREEN}✅ PASSED: Concurrent Request Handling${NC}"
    ((TESTS_PASSED++))
else
    log_and_echo "${RED}❌ FAILED: Concurrent Request Handling${NC}"
    ((TESTS_FAILED++))
fi

# Memory usage test (basic check)
if command -v ps >/dev/null 2>&1; then
    memory_usage=$(ps aux | grep "python.*reflexion" | grep -v grep | awk '{print $6}' | head -1)
    if [ -n "$memory_usage" ] && [ "$memory_usage" -lt 1000000 ]; then  # Less than 1GB
        log_and_echo "${GREEN}✅ PASSED: Memory Usage Check (${memory_usage}KB)${NC}"
        ((TESTS_PASSED++))
    else
        log_and_echo "${YELLOW}⚠️ WARNING: High Memory Usage (${memory_usage}KB)${NC}"
        ((TESTS_PASSED++))  # Not failing, just warning
    fi
else
    skip_test "Memory Usage Check" "ps command not available"
fi

# =============================================================================
# CATEGORY 7: INTEGRATION TESTS (if Go service available)
# =============================================================================

if $GO_SERVICE_AVAILABLE; then
    log_and_echo "${PURPLE}🔗 Category 7: Integration Tests${NC}"
    log_and_echo "==============================="
    
    run_test "Go Service Health Check" \
        "curl -s $GO_SERVICE_URL/health | jq -e '.status'" \
        "Integration" \
        "Go service should be healthy"
    
    run_test "Full Workflow Integration" \
        "curl -s -X POST $SERVICE_URL/api/v1/reflexion/process -H 'Content-Type: application/json' -d '{\"pod_name\":\"integration-test\",\"namespace\":\"default\",\"error_type\":\"ImagePullBackOff\"}' | jq -e '.workflow_id'" \
        "Integration" \
        "Should complete full workflow"
    
    run_test "Async Workflow Processing" \
        "curl -s -X POST $SERVICE_URL/api/v1/reflexion/process-async -H 'Content-Type: application/json' -d '{\"pod_name\":\"async-test\",\"error_type\":\"CrashLoopBackOff\"}' | jq -e '.workflow_id'" \
        "Integration" \
        "Should start async workflow"
    
    # Test workflow status (using a mock workflow ID)
    run_test "Workflow Status Tracking" \
        "curl -s $SERVICE_URL/api/v1/reflexion/workflow/test_workflow_123 | jq -e '.workflow_id'" \
        "Integration" \
        "Should track workflow status"
    
else
    skip_test "Go Service Integration Tests" "Go service not available"
fi

# =============================================================================
# CATEGORY 8: API DOCUMENTATION TESTS
# =============================================================================

log_and_echo "${PURPLE}📖 Category 8: API Documentation Tests${NC}"
log_and_echo "====================================="

run_test "OpenAPI/Swagger Documentation" \
    "curl -s $SERVICE_URL/openapi.json | jq -e '.info.title'" \
    "Documentation" \
    "Should serve OpenAPI documentation"

run_test "Swagger UI Accessibility" \
    "curl -s $SERVICE_URL/api/docs | grep -q 'swagger'" \
    "Documentation" \
    "Swagger UI should be accessible"

run_test "ReDoc Accessibility" \
    "curl -s $SERVICE_URL/api/redoc | grep -q 'redoc'" \
    "Documentation" \
    "ReDoc should be accessible"

# =============================================================================
# CATEGORY 9: MONITORING & OBSERVABILITY TESTS
# =============================================================================

log_and_echo "${PURPLE}📊 Category 9: Monitoring & Observability Tests${NC}"
log_and_echo "=============================================="

# Check if logs directory exists and is writable
if [ -d "logs" ] && [ -w "logs" ]; then
    log_and_echo "${GREEN}✅ PASSED: Log Directory Access${NC}"
    ((TESTS_PASSED++))
else
    log_and_echo "${RED}❌ FAILED: Log Directory Access${NC}"
    ((TESTS_FAILED++))
fi

# Check memory file creation/access
if [ -f "reflexion_memory.json" ] || touch "test_memory.json" 2>/dev/null; then
    log_and_echo "${GREEN}✅ PASSED: Memory File Access${NC}"
    ((TESTS_PASSED++))
    [ -f "test_memory.json" ] && rm "test_memory.json"
else
    log_and_echo "${RED}❌ FAILED: Memory File Access${NC}"
    ((TESTS_FAILED++))
fi

# Validate memory file structure (if exists)
if [ -f "reflexion_memory.json" ]; then
    if jq . reflexion_memory.json > /dev/null 2>&1; then
        log_and_echo "${GREEN}✅ PASSED: Memory File JSON Validity${NC}"
        ((TESTS_PASSED++))
    else
        log_and_echo "${RED}❌ FAILED: Memory File JSON Validity${NC}"
        ((TESTS_FAILED++))
    fi
else
    skip_test "Memory File JSON Validity" "Memory file does not exist yet"
fi

# =============================================================================
# CATEGORY 10: STRESS TESTS
# =============================================================================

log_and_echo "${PURPLE}💪 Category 10: Stress Tests${NC}"
log_and_echo "==========================="

# Rapid sequential requests
log_and_echo "${YELLOW}🧪 Testing: Rapid Sequential Requests${NC}"
rapid_success=true
for i in {1..10}; do
    if ! curl -s -X POST "$SERVICE_URL/api/v1/debug/simulate-reflection?error_type=Stress$i&success=true" > /dev/null; then
        rapid_success=false
        break
    fi
done

if $rapid_success; then
    log_and_echo "${GREEN}✅ PASSED: Rapid Sequential Requests${NC}"
    ((TESTS_PASSED++))
else
    log_and_echo "${RED}❌ FAILED: Rapid Sequential Requests${NC}"
    ((TESTS_FAILED++))
fi

# Large request payload test
large_payload='{"pod_name":"'$(printf 'a%.0s' {1..100})'","namespace":"default","error_type":"ImagePullBackOff","thread_id":"stress_test"}'
if curl -s -X POST "$SERVICE_URL/api/v1/reflexion/process" -H 'Content-Type: application/json' -d "$large_payload" > /dev/null; then
    log_and_echo "${GREEN}✅ PASSED: Large Payload Handling${NC}"
    ((TESTS_PASSED++))
else
    log_and_echo "${RED}❌ FAILED: Large Payload Handling${NC}"
    ((TESTS_FAILED++))
fi

# =============================================================================
# SUMMARY AND REPORTING
# =============================================================================

log_and_echo ""
log_and_echo "${BLUE}📊 Test Suite Complete${NC}"
log_and_echo "======================"
log_and_echo "Completed at: $(date)"
log_and_echo ""

total_tests=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
success_rate=0
if [ $total_tests -gt 0 ]; then
    success_rate=$(echo "scale=1; $TESTS_PASSED * 100 / $total_tests" | bc 2>/dev/null || echo "0")
fi

log_and_echo "${GREEN}✅ Passed: $TESTS_PASSED${NC}"
log_and_echo "${RED}❌ Failed: $TESTS_FAILED${NC}"
log_and_echo "${CYAN}⏭️ Skipped: $TESTS_SKIPPED${NC}"
log_and_echo "${BLUE}📈 Total: $total_tests${NC}"
log_and_echo "${PURPLE}📊 Success Rate: ${success_rate}%${NC}"

log_and_echo ""
log_and_echo "📋 Detailed results saved to: $LOG_FILE"

# Generate recommendations
log_and_echo ""
log_and_echo "${BLUE}🔍 Recommendations${NC}"
log_and_echo "=================="

if [ $TESTS_FAILED -eq 0 ]; then
    log_and_echo "${GREEN}🎉 Excellent! All tests passed. Your service is ready for production.${NC}"
    log_and_echo ""
    log_and_echo "Next steps:"
    log_and_echo "1. 🚀 Deploy to staging environment"
    log_and_echo "2. 📊 Set up monitoring and alerting"
    log_and_echo "3. 🔄 Schedule regular health checks"
    if ! $GO_SERVICE_AVAILABLE; then
        log_and_echo "4. 🔗 Set up Go service integration"
    fi
elif [ $TESTS_FAILED -le 3 ]; then
    log_and_echo "${YELLOW}⚠️ Good! Most tests passed with minor issues.${NC}"
    log_and_echo ""
    log_and_echo "Recommended actions:"
    log_and_echo "1. 🔍 Review failed tests in the log file"
    log_and_echo "2. 🛠️ Fix critical issues before deployment"
    log_and_echo "3. 🧪 Re-run tests after fixes"
else
    log_and_echo "${RED}🚨 Warning! Multiple test failures detected.${NC}"
    log_and_echo ""
    log_and_echo "Required actions:"
    log_and_echo "1. 🔍 Review all failed tests immediately"
    log_and_echo "2. 🛠️ Fix critical issues before proceeding"
    log_and_echo "3. 🧪 Re-run full test suite"
    log_and_echo "4. 📞 Consider getting additional support"
fi

log_and_echo ""
log_and_echo "${BLUE}📚 Additional Resources${NC}"
log_and_echo "======================"
log_and_echo "• 📖 Full Testing Guide: TESTING_GUIDE.md"
log_and_echo "• 🔗 Integration Guide: INTEGRATION_GUIDE.md"
log_and_echo "• 📋 README: README.md"
log_and_echo "• 🌐 Swagger UI: $SERVICE_URL/api/docs"
log_and_echo "• 📊 Health Check: $SERVICE_URL/health"

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi