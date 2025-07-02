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
	aiMode        bool
	openaiAPIKey  string
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
	Short: "Analyze and fix pods with various Kubernetes errors",
	Long: `Analyze and automatically fix Kubernetes pod errors using AI-powered strategies.

Supported error types:
  - ImagePullBackOff (Traditional + AI mode)
  - CrashLoopBackOff (Traditional + AI mode)
  - OOMKilled, Evicted, etc. (AI mode only)

Examples:
  k8s-ai-agent fix-pod --pod=broken-pod --namespace=default              # Analyze only
  k8s-ai-agent fix-pod --pod=broken-pod --auto-fix                       # Traditional fix
  k8s-ai-agent fix-pod --pod=broken-pod --auto-fix --ai-mode             # AI-enhanced fix
  k8s-ai-agent fix-pod --pod=broken-pod --auto-fix --dry-run             # Preview changes
  k8s-ai-agent fix-pod --pod=broken-pod --ai-mode --openai-key=sk-...    # AI with custom key`,
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
			
			// Handle different error types based on mode
			supportedInTraditional := reason == "ImagePullBackOff" || reason == "ErrImagePull" || reason == "CrashLoopBackOff"
			
			if supportedInTraditional || aiMode {
				color.Yellow("🎯 %s detected - running analysis...", reason)
				
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
							
							// Declare variables for fix result and executor
							var fixResult *executor.FixResult
							var executorClient *executor.ExecutorClient
							
							// Create executor client (AI-enhanced or standard)
							if aiMode {
								color.Blue("🤖 Using AI-Enhanced mode with GPT-4 Turbo")
								
								// Get OpenAI API key
								apiKey := openaiAPIKey
								if apiKey == "" {
									apiKey = os.Getenv("OPENAI_API_KEY")
								}
								if apiKey == "" {
									color.Red("❌ OpenAI API key required for AI mode")
									color.White("💡 Set OPENAI_API_KEY environment variable or use --openai-key flag")
									os.Exit(1)
								}
								
								// Create AI-enhanced executor
								aiExecutor, err := executor.NewAIEnhancedExecutor(apiKey)
								if err != nil {
									color.Red("❌ Failed to create AI-enhanced executor: %v", err)
									os.Exit(1)
								}
								
								// Set dry-run mode if specified
								aiExecutor.SetDryRun(dryRun)
								
								// Apply AI-powered fix
								fixResult, err = aiExecutor.FixWithAI(ctx, pod, reason)
							} else {
								// Standard executor
								var err error
								executorClient, err = executor.NewExecutorClient()
								if err != nil {
									color.Red("❌ Failed to create executor: %v", err)
									os.Exit(1)
								}
								
								// Set dry-run mode if specified
								executorClient.SetDryRun(dryRun)
								
								// Apply the traditional fix based on error type
								switch reason {
								case "ImagePullBackOff", "ErrImagePull":
									fixResult, err = executorClient.FixImagePullBackOff(ctx, pod)
								case "CrashLoopBackOff":
									fixResult, err = executorClient.FixCrashLoopBackOff(ctx, pod)
								default:
									color.Red("❌ Error type '%s' not supported in traditional mode", reason)
									color.White("💡 Try using --ai-mode for advanced error handling")
									os.Exit(1)
								}
							}
							if err != nil {
								color.Red("❌ Fix failed: %v", err)
								os.Exit(1)
							}
							
							// Display fix results
							if fixResult != nil && fixResult.Success {
								color.Green("✅ Fix applied successfully!")
								color.White("🔄 %s", fixResult.FixApplied)
								color.White("📝 %s", fixResult.Message)
								
								if !dryRun {
									// Validate the fix (use appropriate executor)
									color.Yellow("⏳ Validating fix...")
									var validationResult *executor.FixResult
									var err error
									
									if aiMode {
										// For AI mode, we still need a basic executor for validation
										if executorClient == nil {
											executorClient, _ = executor.NewExecutorClient()
										}
									}
									
									validationResult, err = executorClient.ValidateFix(ctx, namespace, podName, 300*time.Second)
									if err != nil {
										color.Red("❌ Fix validation failed: %v", err)
									} else if validationResult.Success {
										color.Green("✅ Fix validation successful!")
										color.White("📊 %s", validationResult.Message)
									} else {
										color.Yellow("⚠️  Fix validation failed: %s", validationResult.Message)
									}
								}
							} else if fixResult != nil {
								color.Red("❌ Fix failed: %s", fixResult.Message)
							} else {
								color.Red("❌ Fix failed: No result returned")
							}
						} else {
							color.Blue("📋 Use --auto-fix flag to apply automatic fix")
						}
					} else {
						color.Yellow("⚠️  This error requires manual intervention")
					}
				}
			} else {
				color.Yellow("⚠️  Error type '%s' not supported in traditional mode", reason)
				color.White("💡 Try using --ai-mode for advanced error handling with GPT-4 Turbo")
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
		color.Cyan("k8s-ai-agent MVP v0.3.0-ai-enhanced")
		color.White("Built with Go " + "1.24.4")
		color.White("Features: Watch Mode, Auto-Detection, Concurrent Fixing")
		color.Green("🤖 NEW: AI-Enhanced Mode with GPT-4 Turbo")
		color.White("AI Features: Dynamic command generation, advanced error handling")
	},
}

var watchCmd = &cobra.Command{
	Use:   "watch",
	Short: "Continuously watch and fix pod errors",
	Long: `Continuously monitor Kubernetes pods for errors and optionally fix them automatically.

AI Mode Support:
  - Traditional mode: ImagePullBackOff, CrashLoopBackOff
  - AI-enhanced mode: All error types with GPT-4 Turbo

Examples:
  k8s-ai-agent watch --namespace=default                    # Watch specific namespace
  k8s-ai-agent watch --all-namespaces                      # Watch all namespaces
  k8s-ai-agent watch --namespace=default --auto-fix        # Watch and auto-fix
  k8s-ai-agent watch --auto-fix --ai-mode                  # AI-enhanced fixing
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
	fixCmd.Flags().BoolVar(&aiMode, "ai-mode", false, "Use AI-enhanced fixing with GPT-4 Turbo")
	fixCmd.Flags().StringVar(&openaiAPIKey, "openai-key", "", "OpenAI API key (can also use OPENAI_API_KEY env var)")
	fixCmd.MarkFlagRequired("pod")
	
	// Add flags to watch command
	watchCmd.Flags().StringVarP(&namespace, "namespace", "n", "default", "Namespace to watch")
	watchCmd.Flags().BoolVar(&allNamespaces, "all-namespaces", false, "Watch all namespaces")
	watchCmd.Flags().BoolVar(&autoFix, "auto-fix", false, "Automatically apply fixes")
	watchCmd.Flags().BoolVar(&analyzeOnly, "analyze-only", false, "Only analyze errors, don't fix")
	watchCmd.Flags().IntVar(&maxConcurrent, "max-concurrent", 3, "Maximum concurrent fix operations")
	watchCmd.Flags().BoolVar(&aiMode, "ai-mode", false, "Use AI-enhanced fixing with GPT-4 Turbo")
	watchCmd.Flags().StringVar(&openaiAPIKey, "openai-key", "", "OpenAI API key (can also use OPENAI_API_KEY env var)")
	
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