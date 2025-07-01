# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kubernetes AI-Powered Error Detection and Resolution thesis project that develops an automated system for detecting and resolving Kubernetes errors using AI. The project extends K8sGPT capabilities to create a fully automated remediation system called "K8s AI Auto-Fix Agent".

**Core Objective:** Automatically detect and fix Kubernetes errors using AI agents, moving beyond simple analysis to complete automated resolution.

## Project Architecture

### Current State (Updated: 1 Temmuz 2025)
- **MVP Status**: ✅ Gün 1-2 tamamlandı - Kubernetes entegrasyonu başarılı!
- **Working MVP**: Go-based CLI application with Kubernetes pod detection
- **K8sGPT Integration**: Uses K8sGPT v0.4.21 for error detection and analysis  
- **AI Provider**: OpenAI GPT-4o for intelligent diagnosis and solution recommendations
- **Testing Environment**: Minikube cluster with Docker driver (v1.28.3)
- **Binary Distribution**: Windows executable (k8sgpt.exe) + MVP binary (k8s-ai-agent.exe)

### Planned System Architecture (K8s AI Auto-Fix Agent)
The thesis contributes a 4-layer automated remediation system:

1. **K8sGPT Layer**: Kubernetes error detection and analysis
2. **AI Agent Layer**: Solution generation and decision-making using LangChain + OpenAI
3. **Executor Layer**: Automated solution application via Kubernetes operators
4. **Validator Layer**: Success verification and rollback capability

### Technology Stack
- **Backend**: Go (recommended) or Python for Kubernetes ecosystem compatibility
- **AI Framework**: LangChain + OpenAI for solution generation, CrewAI for multi-agent orchestration
- **Kubernetes Integration**: Operator Pattern with Custom Resource Definitions, client-go for API access
- **Security**: Dry-run mode, rollback capability, human approval gates, audit logging

## MVP Commands (Current Working Implementation)

### K8s AI Agent MVP
```powershell
# Build MVP
cd k8s-ai-agent-mvp
go build -o k8s-ai-agent.exe ./cmd

# Version check
./k8s-ai-agent.exe version

# Pod detection and error analysis  
./k8s-ai-agent.exe fix-pod --pod=broken-pod --namespace=default

# Help
./k8s-ai-agent.exe --help
```

### MVP Test Results
```powershell
# Successfully tested with real ImagePullBackOff pod:
PS C:\> ./k8s-ai-agent.exe fix-pod --pod=broken-pod --namespace=default
🔍 Connecting to Kubernetes cluster...
✅ Connected to Kubernetes cluster!
🔍 Looking for pod: broken-pod in namespace: default
✅ Pod found: broken-pod
❌ Pod has error: ImagePullBackOff
🎯 ImagePullBackOff detected - this is what MVP can fix!
📋 Next step: Add K8sGPT analysis
```

## Key Commands

### K8sGPT Operations
```powershell
# Basic cluster analysis
.\k8sgpt.exe analyze

# AI-powered analysis with explanations
.\k8sgpt.exe analyze --explain

# Check authentication status
.\k8sgpt.exe auth list

# Version information
.\k8sgpt.exe version
```

### Environment Setup
```powershell
# Start Minikube cluster
minikube start --driver=docker

# Verify cluster status
kubectl cluster-info
kubectl get nodes

# Create test scenarios
kubectl run broken-pod --image=nginx:nonexistent-tag
kubectl get pods
```

### OpenAI Integration
```powershell
# Configure OpenAI provider
.\k8sgpt.exe auth add openai
# Enter API key when prompted
```

## Development Guidelines

### Error Detection Categories
The system handles these Kubernetes error types:
- **Image Pull Errors**: Nonexistent tags, registry authentication issues
- **Resource Issues**: Memory/CPU limit violations
- **Configuration Errors**: Invalid ConfigMap/Secret references
- **Network Problems**: Service/Ingress misconfigurations
- **Storage Issues**: PVC capacity and binding problems

### Security Requirements
All automated fixes must implement:
- **Dry-run mode**: Risk-free testing before application
- **Rollback capability**: Automatic reversion on failure
- **Human approval**: Critical operations require confirmation
- **Circuit breaker**: Stop execution on repeated failures
- **Audit logging**: Complete operation tracking

### Performance Targets
- **Detection Speed**: 2-37 iterations/second (complexity-dependent)
- **Success Rate**: 90%+ automatic resolution for common errors
- **AI Response**: Sub-10 second analysis with GPT-4o

## Development Timeline

### MVP Progress (2-Week Sprint)
**Status**: 15% Complete - Gün 1-2 ✅ Tamamlandı

- **✅ Gün 1**: Go project setup, CLI skeleton, dependencies
- **✅ Gün 2**: Kubernetes client integration, pod detection working  
- **🟡 Gün 3-4**: K8sGPT integration + JSON parsing (In Progress)
- **⏳ Gün 5-6**: Fix logic + image tag replacement
- **⏳ Gün 7-8**: CLI refinement + end-to-end testing
- **⏳ Gün 9-10**: Integration testing + error handling
- **⏳ Gün 11-12**: Documentation + demo preparation
- **⏳ Gün 13-14**: Final testing + MVP release

### Full System Timeline (12-Week Schedule)
- **✅ Weeks 1-2**: Backend development + K8sGPT integration (MVP Complete)
- **⏳ Weeks 3-4**: AI agent logic + OpenAI integration
- **⏳ Weeks 5-6**: Kubernetes operator development
- **⏳ Weeks 7-8**: Security implementation + test scenarios
- **⏳ Weeks 9-10**: Documentation + packaging
- **⏳ Weeks 11-12**: Community release + feedback integration

## System Requirements

- Windows 10/11 with Docker Desktop
- Kubernetes cluster (Minikube/Kind/Docker Desktop)
- PowerShell 5.1+
- Internet connectivity for OpenAI API access
- Valid OpenAI API key for GPT-4o access

## Project Context

This is an academic thesis project focused on advancing Kubernetes operations through AI automation. The current K8sGPT implementation provides excellent error detection but lacks automated remediation - this project bridges that gap with a production-ready automated fix system.

**Success Criteria**: Achieve 90%+ automatic resolution rate for common Kubernetes errors while maintaining production-level security standards and gaining community adoption.