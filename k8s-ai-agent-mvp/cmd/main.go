package main

import (
	"context"
	"os"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/k8s"
)

var (
	podName   string
	namespace string
)

var rootCmd = &cobra.Command{
	Use:   "k8s-ai-agent",
	Short: "Kubernetes AI-powered auto-fix agent",
	Long: `An intelligent agent that automatically detects and fixes Kubernetes pod errors using AI.
	
Currently supports:
- ImagePullBackOff error detection and fixing
- Pod health monitoring
- K8sGPT integration for analysis`,
}

var fixCmd = &cobra.Command{
	Use:   "fix-pod",
	Short: "Fix a specific pod with ImagePullBackOff error",
	Long: `Automatically detect and fix ImagePullBackOff errors in Kubernetes pods.

Example:
  k8s-ai-agent fix-pod --pod=broken-pod --namespace=default`,
	Run: func(cmd *cobra.Command, args []string) {
		color.Yellow("🔍 Connecting to Kubernetes cluster...")
		
		// Create Kubernetes client
		client, err := k8s.NewClient()
		if err != nil {
			color.Red("❌ Failed to connect to Kubernetes: %v", err)
			os.Exit(1)
		}
		
		// Test connection
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		
		if err := client.TestConnection(ctx); err != nil {
			color.Red("❌ Cannot reach Kubernetes cluster: %v", err)
			color.White("💡 Make sure kubectl is configured and cluster is running")
			os.Exit(1)
		}
		
		color.Green("✅ Connected to Kubernetes cluster!")
		
		// Get the pod
		color.Yellow("🔍 Looking for pod: %s in namespace: %s", podName, namespace)
		
		pod, err := client.GetPod(ctx, namespace, podName)
		if err != nil {
			color.Red("❌ Pod not found: %v", err)
			os.Exit(1)
		}
		
		color.Green("✅ Pod found: %s", pod.Name)
		
		// Check if pod has errors
		if client.IsPodFailed(pod) {
			reason := client.GetPodErrorReason(pod)
			color.Red("❌ Pod has error: %s", reason)
			
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" {
				color.Yellow("🎯 ImagePullBackOff detected - this is what MVP can fix!")
				color.Blue("📋 Next step: Add K8sGPT analysis")
			} else {
				color.Yellow("⚠️  Error type '%s' not supported in MVP", reason)
			}
		} else {
			color.Green("✅ Pod is healthy - no errors detected")
			color.White("Pod Status: %s", pod.Status.Phase)
		}
	},
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Show version information",
	Run: func(cmd *cobra.Command, args []string) {
		color.Cyan("k8s-ai-agent MVP v0.1.0")
		color.White("Built with Go " + "1.24.4")
	},
}

func init() {
	// Add flags to fix-pod command
	fixCmd.Flags().StringVarP(&podName, "pod", "p", "", "Pod name to fix (required)")
	fixCmd.Flags().StringVarP(&namespace, "namespace", "n", "default", "Namespace of the pod")
	fixCmd.MarkFlagRequired("pod")
	
	// Add commands to root
	rootCmd.AddCommand(fixCmd)
	rootCmd.AddCommand(versionCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		color.Red("❌ Error: %v", err)
		os.Exit(1)
	}
}