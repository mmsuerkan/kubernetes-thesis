# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kubernetes AI-Powered Error Detection and Resolution thesis project that develops an automated system for detecting and resolving Kubernetes errors using AI. The project extends K8sGPT capabilities to create a fully automated remediation system called "K8s AI Auto-Fix Agent".

**Core Objective:** Automatically detect and fix Kubernetes errors using AI agents, moving beyond simple analysis to complete automated resolution.

## Project Architecture

### Current State
- **K8sGPT Integration**: Uses K8sGPT v0.4.21 for error detection and analysis
- **AI Provider**: OpenAI GPT-4o for intelligent diagnosis and solution recommendations
- **Testing Environment**: Minikube cluster with Docker driver
- **Binary Distribution**: Windows executable (k8sgpt.exe) for direct operation

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

The project follows a 12-week development schedule:
- **Weeks 1-2**: Backend development + K8sGPT integration
- **Weeks 3-4**: AI agent logic + OpenAI integration
- **Weeks 5-6**: Kubernetes operator development
- **Weeks 7-8**: Security implementation + test scenarios
- **Weeks 9-10**: Documentation + packaging
- **Weeks 11-12**: Community release + feedback integration

## System Requirements

- Windows 10/11 with Docker Desktop
- Kubernetes cluster (Minikube/Kind/Docker Desktop)
- PowerShell 5.1+
- Internet connectivity for OpenAI API access
- Valid OpenAI API key for GPT-4o access

## Project Context

This is an academic thesis project focused on advancing Kubernetes operations through AI automation. The current K8sGPT implementation provides excellent error detection but lacks automated remediation - this project bridges that gap with a production-ready automated fix system.

**Success Criteria**: Achieve 90%+ automatic resolution rate for common Kubernetes errors while maintaining production-level security standards and gaining community adoption.