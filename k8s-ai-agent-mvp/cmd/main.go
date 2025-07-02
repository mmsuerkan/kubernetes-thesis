package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/k8s"
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/analyzer"
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/executor"
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/detector"
)

var (
	podName       string
	namespace     string
	dryRun        bool
	autoFix       bool
	allNamespaces bool
	analyzeOnly   bool
	maxConcurrent int
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
	Short: "Analyze and fix pods with ImagePullBackOff error",
	Long: `Analyze and automatically fix ImagePullBackOff errors in Kubernetes pods using AI.

Examples:
  k8s-ai-agent fix-pod --pod=broken-pod --namespace=default              # Analyze only
  k8s-ai-agent fix-pod --pod=broken-pod --auto-fix                       # Analyze and fix
  k8s-ai-agent fix-pod --pod=broken-pod --auto-fix --dry-run             # Show what would be fixed
  k8s-ai-agent fix-pod --pod=broken-pod --namespace=default --auto-fix   # Fix specific pod`,
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
				color.Yellow("🎯 ImagePullBackOff detected - running AI analysis...")
				
				// Create K8sGPT analyzer  
				k8sgptClient := analyzer.NewK8sGPTClient("../k8sgpt.exe")
				
				// Test K8sGPT binary
				if err := k8sgptClient.TestK8sGPT(ctx); err != nil {
					color.Red("❌ K8sGPT not available: %v", err)
					color.White("💡 Make sure k8sgpt.exe is in the parent directory")
					os.Exit(1)
				}
				
				// Run K8sGPT analysis
				analysis, err := k8sgptClient.AnalyzePod(ctx, pod)
				if err != nil {
					color.Red("❌ K8sGPT analysis failed: %v", err)
					// Continue with basic detection
					color.Yellow("🔧 Falling back to basic fix logic")
				} else {
					// Display AI analysis results
					color.Green("✅ AI Analysis completed!")
					color.White("📊 Error Type: %s", analysis.ErrorType)
					color.White("📝 Details: %s", analysis.ErrorDetails)
					color.White("💡 Recommendation: %s", analysis.Recommendation)
					color.White("🎯 Confidence: %.0f%%", analysis.Confidence*100)
					
					if analysis.CanAutoFix {
						color.Green("🚀 This error can be automatically fixed!")
						
						if autoFix {
							color.Blue("🔧 Starting automatic fix...")
							
							// Create executor client
							executorClient, err := executor.NewExecutorClient()
							if err != nil {
								color.Red("❌ Failed to create executor: %v", err)
								os.Exit(1)
							}
							
							// Set dry-run mode if specified
							executorClient.SetDryRun(dryRun)
							
							// Apply the fix
							fixResult, err := executorClient.FixImagePullBackOff(ctx, pod)
							if err != nil {
								color.Red("❌ Fix failed: %v", err)
								os.Exit(1)
							}
							
							// Display fix results
							if fixResult.Success {
								color.Green("✅ Fix applied successfully!")
								color.White("🔄 %s", fixResult.FixApplied)
								color.White("📝 %s", fixResult.Message)
								
								if !dryRun {
									// Validate the fix
									color.Yellow("⏳ Validating fix...")
									validationResult, err := executorClient.ValidateFix(ctx, namespace, podName, 180*time.Second)
									if err != nil {
										color.Red("❌ Fix validation failed: %v", err)
									} else if validationResult.Success {
										color.Green("✅ Fix validation successful!")
										color.White("📊 %s", validationResult.Message)
									} else {
										color.Yellow("⚠️  Fix validation failed: %s", validationResult.Message)
									}
								}
							} else {
								color.Red("❌ Fix failed: %s", fixResult.Message)
							}
						} else {
							color.Blue("📋 Use --auto-fix flag to apply automatic fix")
						}
					} else {
						color.Yellow("⚠️  This error requires manual intervention")
					}
				}
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
		color.Cyan("k8s-ai-agent MVP v0.2.0")
		color.White("Built with Go " + "1.24.4")
		color.White("Features: Watch Mode, Auto-Detection, Concurrent Fixing")
	},
}

var watchCmd = &cobra.Command{
	Use:   "watch",
	Short: "Continuously watch and fix pod errors",
	Long: `Continuously monitor Kubernetes pods for errors and optionally fix them automatically.

Examples:
  k8s-ai-agent watch --namespace=default                    # Watch specific namespace
  k8s-ai-agent watch --all-namespaces                      # Watch all namespaces
  k8s-ai-agent watch --namespace=default --auto-fix        # Watch and auto-fix
  k8s-ai-agent watch --analyze-only                        # Only analyze, no fixes
  k8s-ai-agent watch --auto-fix --max-concurrent=5         # Limit concurrent fixes`,
	Run: func(cmd *cobra.Command, args []string) {
		color.Green("🚀 Starting Kubernetes AI Auto-Fix Agent in Watch Mode")
		
		// Create watcher configuration
		config := detector.WatcherConfig{
			Namespace:     namespace,
			AllNamespaces: allNamespaces,
			AutoFix:       autoFix,
			AnalyzeOnly:   analyzeOnly,
			MaxConcurrent: maxConcurrent,
		}

		// Validate flags
		if allNamespaces && namespace != "default" {
			color.Red("❌ Cannot specify both --all-namespaces and --namespace")
			os.Exit(1)
		}

		if autoFix && analyzeOnly {
			color.Red("❌ Cannot specify both --auto-fix and --analyze-only")
			os.Exit(1)
		}

		// Create pod watcher
		watcher, err := detector.NewPodWatcher(config)
		if err != nil {
			color.Red("❌ Failed to create pod watcher: %v", err)
			os.Exit(1)
		}

		// Create context with cancellation
		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		// Setup signal handling for graceful shutdown
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

		go func() {
			<-sigChan
			color.Yellow("\n⚠️  Received shutdown signal...")
			cancel()
		}()

		// Start watching
		if err := watcher.Start(ctx); err != nil {
			color.Red("❌ Watcher error: %v", err)
			os.Exit(1)
		}

		color.Green("✅ Watch mode stopped gracefully")
	},
}

func init() {
	// Add flags to fix-pod command
	fixCmd.Flags().StringVarP(&podName, "pod", "p", "", "Pod name to fix (required)")
	fixCmd.Flags().StringVarP(&namespace, "namespace", "n", "default", "Namespace of the pod")
	fixCmd.Flags().BoolVar(&autoFix, "auto-fix", false, "Automatically apply fixes (default: analysis only)")
	fixCmd.Flags().BoolVar(&dryRun, "dry-run", false, "Show what would be fixed without applying changes")
	fixCmd.MarkFlagRequired("pod")
	
	// Add flags to watch command
	watchCmd.Flags().StringVarP(&namespace, "namespace", "n", "default", "Namespace to watch")
	watchCmd.Flags().BoolVar(&allNamespaces, "all-namespaces", false, "Watch all namespaces")
	watchCmd.Flags().BoolVar(&autoFix, "auto-fix", false, "Automatically apply fixes")
	watchCmd.Flags().BoolVar(&analyzeOnly, "analyze-only", false, "Only analyze errors, don't fix")
	watchCmd.Flags().IntVar(&maxConcurrent, "max-concurrent", 3, "Maximum concurrent fix operations")
	
	// Add commands to root
	rootCmd.AddCommand(fixCmd)
	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(watchCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		color.Red("❌ Error: %v", err)
		os.Exit(1)
	}
}