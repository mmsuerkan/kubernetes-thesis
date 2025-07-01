# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kubernetes AI-Powered Error Detection and Resolution thesis project that develops an automated system for detecting and resolving Kubernetes errors using AI. The project extends K8sGPT capabilities to create a fully automated remediation system called "K8s AI Auto-Fix Agent".

**Core Objective:** Automatically detect and fix Kubernetes errors using AI agents, moving beyond simple analysis to complete automated resolution.

## Current MVP Implementation

### MVP Status: 40% Complete (Day 5 of 14)
- **✅ Gün 1-2**: Go project setup + Kubernetes client integration  
- **✅ Gün 3-4**: K8sGPT+AI analysis integration (98% confidence)
- **🟡 Gün 5-6**: Fix Logic (Executor Agent) - In Progress
- **⏳ Gün 7+**: Integration testing, CLI refinement, deployment

### Working Components

#### **1. Kubernetes Client (pkg/k8s/client.go)**
```go
// Fully functional Kubernetes integration
✅ NewClient() - Minikube cluster connection
✅ GetPod() - Pod information retrieval  
✅ IsPodFailed() - Error detection (ImagePullBackOff)
✅ GetPodErrorReason() - Specific error identification
✅ TestConnection() - Cluster health verification
```

#### **2. K8sGPT Analyzer (pkg/analyzer/k8sgpt.go)**
```go
// AI-powered error analysis with GPT-4 integration
✅ K8sGPT binary wrapper with JSON parsing
✅ AI analysis via --explain flag (98% confidence)
✅ Multi-pod support (nginx, redis tested)
✅ Fallback mechanism for edge cases
✅ Error type detection and auto-fix capability assessment
```

#### **3. CLI Application (cmd/main.go)**
```go
// User-friendly command-line interface
✅ Cobra framework with colored output
✅ fix-pod command with pod/namespace targeting
✅ Kubernetes cluster connectivity
✅ K8sGPT integration with AI recommendations
✅ Error handling and user feedback
```

### Current Architecture (MVP)

```
User Input → Pod Validator → K8sGPT+AI Analyzer → [Future: Executor Agent]
```

**Note**: Current "detector" is actually a **pod validator** - user provides pod name, system validates if it has errors. True autonomous detection will be implemented in full system.

### Test Results
```powershell
# Successfully tested scenarios:
✅ broken-pod (nginx:nonexistent-tag) → 98% confidence AI solution
✅ test-broken (redis:nonexistent-version) → Different AI solution  
✅ Multi-error analysis → ConfigMaps + ImagePullBackOff detection
✅ K8sGPT+AI integration → Real GPT-4 recommendations
```

## MVP Commands (Current Working Implementation)

### Build and Execute
```powershell
# Build MVP
cd k8s-ai-agent-mvp
go build -o k8s-ai-agent.exe ./cmd

# Version check
.\k8s-ai-agent.exe version

# Pod error analysis and AI recommendations
.\k8s-ai-agent.exe fix-pod --pod=broken-pod --namespace=default

# Help
.\k8s-ai-agent.exe --help
```

### Expected Output
```powershell
🔍 Connecting to Kubernetes cluster...
✅ Connected to Kubernetes cluster!
✅ Pod found: broken-pod
❌ Pod has error: ImagePullBackOff
🎯 ImagePullBackOff detected - running AI analysis...
✅ K8sGPT analysis complete. Found 2 problems
✅ Found K8sGPT analysis for pod: broken-pod
✅ AI Analysis completed!
📊 Error Type: ImagePullBackOff
💡 Recommendation: [GPT-4 AI Solution with step-by-step fix]
🎯 Confidence: 98%
🚀 This error can be automatically fixed!
```

## Planned System Architecture (Full System)

### 4-Layer Automated Remediation System:
1. **Detector Agent**: Real-time Kubernetes event monitoring
2. **Analyzer Agent**: K8sGPT+GPT-4 powered diagnosis  
3. **Executor Agent**: Automated solution application
4. **Validator Agent**: Success verification and rollback capability

### Technology Stack
- **Backend**: Go for Kubernetes ecosystem compatibility
- **AI Framework**: K8sGPT + OpenAI GPT-4 for solution generation
- **Kubernetes Integration**: client-go for API access, Operator Pattern
- **Security**: Dry-run mode, rollback capability, human approval gates, audit logging

## Development Guidelines

### Current MVP Focus Areas
1. **ImagePullBackOff Errors**: Primary target for automated fixing
2. **Single Pod Operations**: Manual pod specification (not autonomous detection yet)
3. **AI-Powered Analysis**: K8sGPT+GPT-4 integration for intelligent recommendations  
4. **Safety First**: Validation before any automatic operations

### Next Implementation Steps (Gün 5-6)
1. **Executor Agent**: Implement automatic image tag fixing logic
2. **Pod Recreation**: Safe pod deletion and recreation with corrected image
3. **Validation Logic**: Verify fix success and pod health recovery
4. **Error Handling**: Robust rollback mechanisms

### Performance Targets
- **Detection Speed**: <5 seconds for pod error identification
- **AI Analysis**: <10 seconds for GPT-4 solution generation  
- **Success Rate**: 90%+ automatic resolution for ImagePullBackOff errors
- **Recovery Time**: <30 seconds total pod fix cycle

## File Organization

```
k8s-ai-agent-mvp/
├── cmd/
│   └── main.go              # CLI application entry point
├── pkg/
│   ├── k8s/
│   │   └── client.go        # Kubernetes client wrapper
│   ├── analyzer/
│   │   └── k8sgpt.go        # K8sGPT+AI integration
│   └── executor/            # [Future] Automated fix logic
└── go.mod                   # Go dependencies
```

## Key Implementation Notes

1. **K8sGPT Integration**: Uses binary execution with JSON parsing for AI-powered analysis
2. **Error Detection**: Currently validates user-specified pods (not autonomous detection)
3. **AI Solutions**: Real GPT-4 recommendations via K8sGPT --explain flag
4. **Multi-pod Support**: Successfully handles different image errors (nginx, redis)
5. **Fallback Mechanism**: Basic analysis when K8sGPT doesn't analyze specific pods

## Development Standards

- **Go Conventions**: Standard Go project structure with package organization
- **Error Handling**: Comprehensive error checking and user feedback
- **Security First**: Validation before any Kubernetes API operations
- **User Experience**: Colored CLI output with clear progress indicators
- **Testing**: Real cluster testing with Minikube and broken pod scenarios

## Success Metrics (Current Achievement)

- ✅ **98% Confidence**: AI analysis for ImagePullBackOff errors
- ✅ **Multi-pod Support**: nginx and redis image errors tested successfully  
- ✅ **<10 Second Analysis**: Fast AI-powered diagnosis
- ✅ **Real Cluster Testing**: Minikube integration working perfectly
- ✅ **User-Friendly CLI**: Intuitive command structure and output

## Documentation Structure

- **[README.md](README.md)**: Quick start guide and basic usage
- **[docs/FULL_DOCUMENTATION.md](docs/FULL_DOCUMENTATION.md)**: Complete system architecture and specifications
- **[docs/mvp/progress.md](docs/mvp/progress.md)**: Detailed development progress tracking

## Version Information

- **MVP Version**: 0.1.0 (40% complete)
- **Go Version**: 1.24.4
- **K8sGPT Version**: 0.4.21
- **Target Completion**: 14-day sprint (Day 5 current)
- **Architecture**: Template-based MVP with production-ready foundation