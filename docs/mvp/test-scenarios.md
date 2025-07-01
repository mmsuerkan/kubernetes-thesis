# MVP Test Scenarios & Demo Procedures

**MVP Target:** K8s AI Auto-Fix Agent ImagePullBackOff Fix  
**Test Scope:** Manual & Automated Testing Procedures  
**Environment:** Local Kubernetes (Minikube/Docker Desktop)  

---

## 🎯 **Test Strategy Overview**

### **Test Pyramid**
```
    🔺 E2E Tests (1-2)           # Complete user journey
   🔻🔺 Integration Tests (5-8)   # Component interaction  
  🔻🔻🔺 Unit Tests (20+)         # Individual functions
```

### **Test Categories**
1. **Functionality Tests**: Core features working
2. **Error Handling Tests**: Graceful failure scenarios
3. **Integration Tests**: Component interaction
4. **User Experience Tests**: CLI usability
5. **Performance Tests**: Speed and reliability

---

## 🧪 **Manual Test Scenarios**

### **Scenario 1: Happy Path - ImagePullBackOff Fix**

#### **Setup**
```bash
# Ensure clean environment
kubectl delete pod demo-pod --ignore-not-found=true
minikube status  # Should be Running
./k8sgpt.exe version  # Should return version info
```

#### **Test Steps**
```bash
# Step 1: Create broken pod
kubectl run demo-pod --image=nginx:nonexistent-tag

# Step 2: Wait for error state
sleep 15
kubectl get pod demo-pod
# Expected: STATUS = ImagePullBackOff

# Step 3: Run MVP fix
./k8s-ai-agent fix-pod --pod=demo-pod --namespace=default

# Step 4: Verify fix
sleep 30
kubectl get pod demo-pod
# Expected: STATUS = Running
```

#### **Expected Output**
```
🔍 Checking pod status...
❌ Found ImagePullBackOff error
📦 Problematic image: nginx:nonexistent-tag
🤖 Running K8sGPT analysis...
💡 Analysis: Image 'nginx:nonexistent-tag' not found
🔧 Recommended fix: Replace non-existent image tag with latest stable version
📝 Action: Update image to 'nginx:latest'
🎯 Confidence: 80.0%
⏳ Applying fix...
✅ Image updated successfully
🔄 nginx:nonexistent-tag → nginx:latest
⏳ Waiting for pod recovery...
✅ Pod is now running! (took 23s)
```

#### **Success Criteria**
- ✅ Pod status changes from ImagePullBackOff to Running
- ✅ Tool completes in <60 seconds
- ✅ Clear, informative output messages
- ✅ No errors or crashes

---

### **Scenario 2: Dry-Run Mode**

#### **Test Steps**
```bash
# Step 1: Create broken pod
kubectl run dryrun-pod --image=nginx:nonexistent-tag

# Step 2: Wait for error state
sleep 15

# Step 3: Run dry-run
./k8s-ai-agent fix-pod --pod=dryrun-pod --namespace=default --dry-run

# Step 4: Verify no changes
kubectl get pod dryrun-pod
# Expected: Still ImagePullBackOff (no actual fix applied)
```

#### **Expected Output**
```
🔍 Checking pod status...
❌ Found ImagePullBackOff error
📦 Problematic image: nginx:nonexistent-tag
🤖 Running K8sGPT analysis...
💡 Analysis: Image 'nginx:nonexistent-tag' not found
🔧 Recommended fix: Replace non-existent image tag with latest stable version
📝 Action: Update image to 'nginx:latest'
🎯 Confidence: 80.0%
⏳ Applying fix...
✅ Dry run: Would update image successfully
🔄 nginx:nonexistent-tag → nginx:latest
🔍 Dry run completed successfully
```

#### **Success Criteria**
- ✅ Analysis and recommendation shown
- ✅ No actual changes made to pod
- ✅ Clear dry-run indication
- ✅ Pod remains in ImagePullBackOff state

---

### **Scenario 3: Healthy Pod (No Error)**

#### **Test Steps**
```bash
# Step 1: Create healthy pod
kubectl run healthy-pod --image=nginx:latest

# Step 2: Wait for running state
sleep 10
kubectl get pod healthy-pod
# Expected: STATUS = Running

# Step 3: Run fix on healthy pod
./k8s-ai-agent fix-pod --pod=healthy-pod --namespace=default
```

#### **Expected Output**
```
🔍 Checking pod status...
✅ Pod healthy-pod is healthy, no ImagePullBackOff error
```

#### **Success Criteria**
- ✅ Tool detects pod is healthy
- ✅ No unnecessary analysis or fixes
- ✅ Clean exit with positive message
- ✅ Pod remains unchanged

---

### **Scenario 4: Non-Existent Pod**

#### **Test Steps**
```bash
# Step 1: Ensure pod doesn't exist
kubectl delete pod nonexistent-pod --ignore-not-found=true

# Step 2: Run fix on non-existent pod
./k8s-ai-agent fix-pod --pod=nonexistent-pod --namespace=default
```

#### **Expected Output**
```
🔍 Checking pod status...
❌ [Kubernetes] Failed to check pod: pod "nonexistent-pod" not found
  └─ Underlying cause: pods "nonexistent-pod" not found

💡 Troubleshooting hints:
  • Check if the pod exists: kubectl get pods
  • Verify the namespace is correct
```

#### **Success Criteria**
- ✅ Clear error message
- ✅ Helpful troubleshooting hints
- ✅ Tool exits gracefully with non-zero code
- ✅ No crash or panic

---

### **Scenario 5: Wrong Namespace**

#### **Test Steps**
```bash
# Step 1: Create pod in default namespace
kubectl run ns-test-pod --image=nginx:nonexistent-tag

# Step 2: Try to fix in wrong namespace
./k8s-ai-agent fix-pod --pod=ns-test-pod --namespace=kube-system
```

#### **Expected Output**
```
🔍 Checking pod status...
❌ [Kubernetes] Failed to check pod: pod "ns-test-pod" not found
  └─ Underlying cause: pods "ns-test-pod" not found

💡 Troubleshooting hints:
  • Check if the pod exists: kubectl get pods
  • Verify the namespace is correct
```

#### **Success Criteria**
- ✅ Namespace isolation working correctly
- ✅ Clear error message about pod not found
- ✅ No access to pods in other namespaces

---

### **Scenario 6: K8sGPT Binary Missing**

#### **Test Steps**
```bash
# Step 1: Rename k8sgpt binary
mv k8sgpt.exe k8sgpt.exe.backup

# Step 2: Create broken pod
kubectl run binary-test-pod --image=nginx:nonexistent-tag

# Step 3: Try to run fix
./k8s-ai-agent fix-pod --pod=binary-test-pod --namespace=default

# Step 4: Restore binary
mv k8sgpt.exe.backup k8sgpt.exe
```

#### **Expected Output**
```
🔍 Checking pod status...
❌ Found ImagePullBackOff error
📦 Problematic image: nginx:nonexistent-tag
🤖 Running K8sGPT analysis...
❌ [Analysis] K8sGPT execution failed: exec: "k8sgpt.exe": executable file not found in $PATH

💡 Troubleshooting hints:
  • Check if k8sgpt.exe is in the current directory
  • Verify k8sgpt is working: ./k8sgpt.exe version
```

#### **Success Criteria**
- ✅ Clear error about missing binary
- ✅ Helpful troubleshooting hints
- ✅ Tool fails gracefully

---

## 🤖 **Automated Test Suite**

### **Unit Tests**

#### **Pod Checker Tests**
```go
// pkg/detector/pod_checker_test.go
func TestPodChecker_CheckPod_ImagePullBackOff(t *testing.T) {
    // Mock Kubernetes client
    // Create mock pod with ImagePullBackOff
    // Verify detection works correctly
}

func TestPodChecker_CheckPod_HealthyPod(t *testing.T) {
    // Test healthy pod detection
}

func TestPodChecker_CheckPod_NonExistentPod(t *testing.T) {
    // Test error handling for non-existent pod
}
```

#### **K8sGPT Client Tests**
```go
// pkg/analyzer/k8sgpt_client_test.go
func TestK8sGPTClient_AnalyzePod_Success(t *testing.T) {
    // Mock k8sgpt binary execution
    // Test JSON parsing
    // Verify analysis result
}

func TestK8sGPTClient_AnalyzePod_BinaryNotFound(t *testing.T) {
    // Test missing binary handling
}

func TestK8sGPTClient_AnalyzePod_InvalidJSON(t *testing.T) {
    // Test malformed output handling
}
```

#### **Image Fixer Tests**
```go
// pkg/executor/image_fixer_test.go
func TestImageFixer_ApplyFix_Success(t *testing.T) {
    // Mock Kubernetes client
    // Test patch operation
    // Verify fix application
}

func TestImageFixer_DryRunFix(t *testing.T) {
    // Test dry-run mode
    // Verify no actual changes
}
```

### **Integration Tests**

#### **E2E Test Framework**
```go
// test/integration/e2e_test.go
func TestE2E_ImagePullBackOffFix(t *testing.T) {
    // Full end-to-end test
    // Requires running Kubernetes cluster
    // Creates broken pod, runs fix, validates result
}

func TestE2E_DryRunMode(t *testing.T) {
    // Test dry-run end-to-end
}

func TestE2E_HealthyPodHandling(t *testing.T) {
    // Test healthy pod handling
}
```

---

## 🎭 **Demo Procedures**

### **Demo Script 1: Basic Functionality**
```bash
#!/bin/bash
# scripts/demo-basic.sh

echo "🎬 K8s AI Auto-Fix Agent - Basic Demo"
echo "====================================="

# Setup
echo "🔧 Setting up demo environment..."
kubectl delete pod demo-basic --ignore-not-found=true

# Create broken pod
echo "📦 Creating pod with broken image..."
kubectl run demo-basic --image=nginx:this-tag-does-not-exist

echo "⏳ Waiting for ImagePullBackOff..."
sleep 20

# Show broken state
echo "📊 Current pod status:"
kubectl get pod demo-basic -o wide

# Run fix
echo "🤖 Running AI Auto-Fix Agent..."
./k8s-ai-agent fix-pod --pod=demo-basic --namespace=default

# Show result
echo "📊 Final pod status:"
kubectl get pod demo-basic -o wide

# Cleanup
echo "🧹 Cleaning up..."
kubectl delete pod demo-basic

echo "✅ Basic demo completed!"
```

### **Demo Script 2: Error Handling**
```bash
#!/bin/bash
# scripts/demo-errors.sh

echo "🎬 K8s AI Auto-Fix Agent - Error Handling Demo"
echo "=============================================="

# Test 1: Non-existent pod
echo "🧪 Test 1: Non-existent pod"
./k8s-ai-agent fix-pod --pod=does-not-exist --namespace=default
echo ""

# Test 2: Healthy pod
echo "🧪 Test 2: Healthy pod"
kubectl run healthy-demo --image=nginx:latest
sleep 10
./k8s-ai-agent fix-pod --pod=healthy-demo --namespace=default
kubectl delete pod healthy-demo
echo ""

# Test 3: Dry-run mode
echo "🧪 Test 3: Dry-run mode"
kubectl run dryrun-demo --image=nginx:nonexistent
sleep 15
./k8s-ai-agent fix-pod --pod=dryrun-demo --namespace=default --dry-run
kubectl delete pod dryrun-demo

echo "✅ Error handling demo completed!"
```

### **Demo Script 3: Performance Test**
```bash
#!/bin/bash
# scripts/demo-performance.sh

echo "🎬 K8s AI Auto-Fix Agent - Performance Demo"
echo "==========================================="

# Test multiple pods quickly
for i in {1..3}; do
    echo "🔄 Performance test $i/3"
    
    kubectl run perf-test-$i --image=nginx:nonexistent-tag
    sleep 15
    
    # Time the fix
    echo "⏱️  Timing fix operation..."
    time ./k8s-ai-agent fix-pod --pod=perf-test-$i --namespace=default
    
    kubectl delete pod perf-test-$i
    echo "---"
done

echo "✅ Performance demo completed!"
```

---

## 📊 **Test Execution & Validation**

### **Manual Test Execution Plan**

#### **Pre-Release Testing (Day 13)**
```bash
# Test Matrix Execution
Scenario 1: Happy Path          [PASS/FAIL] ___
Scenario 2: Dry-Run Mode        [PASS/FAIL] ___
Scenario 3: Healthy Pod         [PASS/FAIL] ___
Scenario 4: Non-Existent Pod    [PASS/FAIL] ___
Scenario 5: Wrong Namespace     [PASS/FAIL] ___
Scenario 6: K8sGPT Missing      [PASS/FAIL] ___

Performance Requirements:
- Fix completion time: <60 seconds [PASS/FAIL] ___
- Tool startup time: <5 seconds   [PASS/FAIL] ___
- Memory usage: <50MB             [PASS/FAIL] ___

User Experience:
- Clear error messages            [PASS/FAIL] ___
- Helpful troubleshooting hints   [PASS/FAIL] ___
- Colored output working          [PASS/FAIL] ___
- Help text comprehensive         [PASS/FAIL] ___
```

#### **Automated Test Execution**
```bash
# Run full test suite
make test

# Run integration tests (requires K8s cluster)
make test-integration

# Run E2E tests
make test-e2e

# Performance benchmarks
make benchmark
```

### **Test Data Collection**

#### **Performance Metrics**
```bash
# Execution time measurement
$ time ./k8s-ai-agent fix-pod --pod=test-pod
real    0m23.456s
user    0m0.123s
sys     0m0.045s

# Memory usage measurement
$ /usr/bin/time -v ./k8s-ai-agent fix-pod --pod=test-pod
Maximum resident set size (kbytes): 32768

# Success rate measurement (10 runs)
Success Rate: 10/10 (100%)
Average Execution Time: 24.3s
```

#### **Error Rate Analysis**
```bash
# Error categories tracking
Network Errors:          0/50 (0%)
Permission Errors:       0/50 (0%)
K8sGPT Errors:          1/50 (2%)
Timeout Errors:          0/50 (0%)
Unknown Errors:          0/50 (0%)
```

---

## 🏆 **Acceptance Criteria**

### **MVP Release Criteria**

#### **Functional Requirements**
- ✅ **ImagePullBackOff Detection**: 100% accuracy
- ✅ **K8sGPT Integration**: Successful analysis parsing
- ✅ **Image Fix**: Successful patch application
- ✅ **Status Validation**: Pod recovery verification
- ✅ **CLI Interface**: User-friendly commands

#### **Performance Requirements**
- ✅ **Execution Time**: <60 seconds end-to-end
- ✅ **Success Rate**: >95% for supported scenarios
- ✅ **Memory Usage**: <100MB peak usage
- ✅ **CPU Usage**: <1 core during execution

#### **Quality Requirements**
- ✅ **Error Handling**: Graceful failure in all error cases
- ✅ **User Experience**: Clear, helpful messages
- ✅ **Documentation**: Complete usage instructions
- ✅ **Testing**: >80% test coverage

#### **Reliability Requirements**
- ✅ **Crash Rate**: 0% (no panics or crashes)
- ✅ **Data Safety**: No accidental data deletion
- ✅ **Rollback**: Dry-run mode available
- ✅ **Audit Trail**: Clear logging of all actions

---

## 🎯 **Test Sign-Off**

### **Final Test Execution (Day 14)**
```bash
# Executive Summary Test Report
Date: _______________
Tester: _____________
Environment: ________

Test Results Summary:
- Manual Test Scenarios:     ___/6 PASSED
- Automated Unit Tests:      ___/20+ PASSED  
- Integration Tests:         ___/5 PASSED
- Performance Tests:         ___/3 PASSED
- Demo Scripts:              ___/3 PASSED

Overall Status: [PASS/FAIL] ________

Sign-off: ___________________
```

### **Production Readiness Checklist**
- [ ] All test scenarios passing
- [ ] Performance requirements met
- [ ] Error handling comprehensive
- [ ] Documentation complete
- [ ] Demo scripts working
- [ ] Build process clean
- [ ] No critical bugs

**MVP Ready for Release: [YES/NO] ________**

---

**Bu test planını takip ederek MVP'nin quality ve reliability'sini garantileyebiliriz!**

---

**Test Plan Sahibi:** QA Team  
**Son Güncelleme:** 30 Haziran 2025  
**Versiyon:** 1.0