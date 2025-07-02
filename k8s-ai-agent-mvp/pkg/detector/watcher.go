package detector

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/fatih/color"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
	"path/filepath"
	
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/analyzer"
	"github.com/mmsuerkan/k8s-ai-agent-mvp/pkg/executor"
)

// PodError represents a detected pod error
type PodError struct {
	Pod       *corev1.Pod
	ErrorType string
	Timestamp time.Time
}

// PodTracker keeps track of already processed pods
type PodTracker struct {
	mu          sync.RWMutex
	processed   map[string]time.Time
	reCheckTime time.Duration
}

// WatcherConfig holds configuration for the watcher
type WatcherConfig struct {
	Namespace      string
	AllNamespaces  bool
	AutoFix        bool
	AnalyzeOnly    bool
	MaxConcurrent  int
	CheckInterval  time.Duration
}

// PodWatcher continuously monitors pods for errors
type PodWatcher struct {
	clientset     kubernetes.Interface
	config        WatcherConfig
	errorQueue    chan PodError
	fixInProgress sync.Map // Track pods being fixed
	podTracker    *PodTracker
	stopCh        chan struct{}
	wg            sync.WaitGroup
}

// NewPodWatcher creates a new pod watcher instance
func NewPodWatcher(config WatcherConfig) (*PodWatcher, error) {
	var k8sConfig *rest.Config
	var err error

	// Try in-cluster config first
	k8sConfig, err = rest.InClusterConfig()
	if err != nil {
		// Fall back to kubeconfig
		kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")
		k8sConfig, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to create kubernetes config: %w", err)
		}
	}

	clientset, err := kubernetes.NewForConfig(k8sConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create kubernetes client: %w", err)
	}

	// Set defaults
	if config.MaxConcurrent == 0 {
		config.MaxConcurrent = 3
	}
	if config.CheckInterval == 0 {
		config.CheckInterval = 5 * time.Second
	}

	return &PodWatcher{
		clientset:  clientset,
		config:     config,
		errorQueue: make(chan PodError, 100),
		podTracker: &PodTracker{
			processed:   make(map[string]time.Time),
			reCheckTime: 5 * time.Minute, // Re-check after 5 minutes
		},
		stopCh:     make(chan struct{}),
	}, nil
}

// Start begins watching for pod errors
func (pw *PodWatcher) Start(ctx context.Context) error {
	color.Green("👀 Starting pod watcher...")
	
	// Display configuration
	if pw.config.AllNamespaces {
		color.Yellow("📍 Watching all namespaces")
	} else {
		color.Yellow("📍 Watching namespace: %s", pw.config.Namespace)
	}
	
	if pw.config.AutoFix {
		color.Yellow("🔧 Auto-fix mode: ENABLED")
	} else if pw.config.AnalyzeOnly {
		color.Yellow("📊 Analyze-only mode: ENABLED")
	}

	// Start the error processor
	pw.wg.Add(1)
	go pw.processErrors(ctx)

	// Start watching pods
	pw.wg.Add(1)
	go pw.watchPods(ctx)
	
	// Start status reporter
	pw.wg.Add(1)
	go pw.statusReporter(ctx)

	// Wait for context cancellation
	<-ctx.Done()
	close(pw.stopCh)
	pw.wg.Wait()
	
	color.Yellow("👋 Pod watcher stopped")
	return nil
}

// watchPods monitors pod events
func (pw *PodWatcher) watchPods(ctx context.Context) {
	defer pw.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		case <-pw.stopCh:
			return
		default:
			// Create watch options
			watchOptions := metav1.ListOptions{
				Watch: true,
			}

			// Get the appropriate pod interface
			var podInterface watch.Interface
			var err error

			if pw.config.AllNamespaces {
				podInterface, err = pw.clientset.CoreV1().Pods("").Watch(ctx, watchOptions)
			} else {
				podInterface, err = pw.clientset.CoreV1().Pods(pw.config.Namespace).Watch(ctx, watchOptions)
			}

			if err != nil {
				color.Red("❌ Watch error: %v", err)
				time.Sleep(5 * time.Second)
				continue
			}

			pw.handlePodEvents(ctx, podInterface)
		}
	}
}

// handlePodEvents processes incoming pod events
func (pw *PodWatcher) handlePodEvents(ctx context.Context, watcher watch.Interface) {
	defer watcher.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-pw.stopCh:
			return
		case event, ok := <-watcher.ResultChan():
			if !ok {
				// Channel closed, restart watch
				return
			}

			pod, ok := event.Object.(*corev1.Pod)
			if !ok {
				continue
			}

			// Only process ADDED and MODIFIED events
			if event.Type != watch.Added && event.Type != watch.Modified {
				continue
			}

			// Check if pod has errors
			if errorType := pw.checkPodForErrors(pod); errorType != "" {
				podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
				
				// Check if we're already fixing this pod
				if _, exists := pw.fixInProgress.Load(podKey); exists {
					continue
				}
				
				// Check if we've recently processed this pod
				if pw.shouldSkipPod(podKey) {
					continue
				}

				color.Red("❌ Error detected in pod %s/%s: %s", pod.Namespace, pod.Name, errorType)
				
				// Mark as processed
				pw.markPodProcessed(podKey)
				
				// Add to error queue
				pw.errorQueue <- PodError{
					Pod:       pod,
					ErrorType: errorType,
					Timestamp: time.Now(),
				}
			}
		}
	}
}

// checkPodForErrors examines a pod for known error conditions
func (pw *PodWatcher) checkPodForErrors(pod *corev1.Pod) string {
	// Skip if pod is being deleted
	if pod.DeletionTimestamp != nil {
		return ""
	}

	// Check container statuses
	for _, containerStatus := range pod.Status.ContainerStatuses {
		// Check for ImagePullBackOff or ErrImagePull
		if containerStatus.State.Waiting != nil {
			reason := containerStatus.State.Waiting.Reason
			if reason == "ImagePullBackOff" || reason == "ErrImagePull" {
				return "ImagePullBackOff"
			}
			if reason == "CrashLoopBackOff" {
				return "CrashLoopBackOff"
			}
		}

		// Check for OOMKilled
		if containerStatus.State.Terminated != nil {
			if containerStatus.State.Terminated.Reason == "OOMKilled" {
				return "OOMKilled"
			}
		}

		// Check LastTerminationState for OOMKilled
		if containerStatus.LastTerminationState.Terminated != nil {
			if containerStatus.LastTerminationState.Terminated.Reason == "OOMKilled" {
				return "OOMKilled"
			}
		}
	}

	return ""
}

// processErrors handles errors from the queue
func (pw *PodWatcher) processErrors(ctx context.Context) {
	defer pw.wg.Done()

	// Create a semaphore for concurrent processing
	sem := make(chan struct{}, pw.config.MaxConcurrent)

	for {
		select {
		case <-ctx.Done():
			return
		case <-pw.stopCh:
			return
		case podError := <-pw.errorQueue:
			// Acquire semaphore
			sem <- struct{}{}

			// Process error in goroutine
			go func(pe PodError) {
				defer func() { <-sem }() // Release semaphore

				// Mark pod as being fixed
				podKey := fmt.Sprintf("%s/%s", pe.Pod.Namespace, pe.Pod.Name)
				pw.fixInProgress.Store(podKey, true)
				defer pw.fixInProgress.Delete(podKey)

				// Process the error
				pw.handlePodError(ctx, pe)
			}(podError)
		}
	}
}

// handlePodError processes a single pod error
func (pw *PodWatcher) handlePodError(ctx context.Context, podError PodError) {
	pod := podError.Pod
	
	color.Yellow("🔍 Processing error for pod %s/%s", pod.Namespace, pod.Name)
	color.White("📊 Error Type: %s", podError.ErrorType)
	color.White("⏰ Detected at: %s", podError.Timestamp.Format("15:04:05"))

	// Run K8sGPT analysis
	color.Yellow("🎯 Running AI analysis...")
	k8sgptClient := analyzer.NewK8sGPTClient("../k8sgpt.exe")
	
	// Test K8sGPT binary
	if err := k8sgptClient.TestK8sGPT(ctx); err != nil {
		color.Red("❌ K8sGPT not available: %v", err)
		return
	}
	
	// Run K8sGPT analysis
	analysis, err := k8sgptClient.AnalyzePod(ctx, pod)
	if err != nil {
		color.Red("❌ K8sGPT analysis failed: %v", err)
		return
	}
	
	// Display AI analysis results
	color.Green("✅ AI Analysis completed!")
	color.White("📊 Error Type: %s", analysis.ErrorType)
	color.White("📝 Details: %s", analysis.ErrorDetails)
	color.White("💡 Recommendation: %s", analysis.Recommendation)
	color.White("🎯 Confidence: %.0f%%", analysis.Confidence*100)

	// In analyze-only mode, just report
	if pw.config.AnalyzeOnly {
		color.Blue("📋 Analysis-only mode - no fixes will be applied")
		return
	}

	// If auto-fix is enabled and AI says it can be fixed
	if pw.config.AutoFix && analysis.CanAutoFix {
		color.Green("🔧 Auto-fix enabled - applying fix...")
		
		// Create executor client
		executorClient, err := executor.NewExecutorClient()
		if err != nil {
			color.Red("❌ Failed to create executor: %v", err)
			return
		}
		
		// Apply the fix based on error type
		var fixResult *executor.FixResult
		switch podError.ErrorType {
		case "ImagePullBackOff":
			fixResult, err = executorClient.FixImagePullBackOff(ctx, pod)
		case "CrashLoopBackOff":
			fixResult, err = executorClient.FixCrashLoopBackOff(ctx, pod)
		case "OOMKilled":
			color.Yellow("⚠️  OOMKilled fix not yet implemented")
			return
		default:
			color.Yellow("⚠️  Unknown error type: %s", podError.ErrorType)
			return
		}
		
		if err != nil {
			color.Red("❌ Fix failed: %v", err)
			return
		}
		
		// Display fix results
		if fixResult.Success {
			color.Green("✅ Fix applied successfully!")
			color.White("🔄 %s", fixResult.FixApplied)
			color.White("📝 %s", fixResult.Message)
			
			// Validate the fix
			color.Yellow("⏳ Validating fix...")
			validationResult, err := executorClient.ValidateFix(ctx, pod.Namespace, pod.Name, 60*time.Second)
			if err != nil {
				color.Red("❌ Fix validation failed: %v", err)
			} else if validationResult.Success {
				color.Green("✅ Fix validation successful!")
				color.White("📊 %s", validationResult.Message)
			} else {
				color.Yellow("⚠️  Fix validation failed: %s", validationResult.Message)
			}
		} else {
			color.Red("❌ Fix failed: %s", fixResult.Message)
		}
	} else if pw.config.AutoFix && !analysis.CanAutoFix {
		color.Yellow("⚠️  This error requires manual intervention")
	}
}

// Stop gracefully stops the watcher
func (pw *PodWatcher) Stop() {
	color.Yellow("🛑 Stopping pod watcher...")
	close(pw.stopCh)
}

// GetStats returns current watcher statistics
func (pw *PodWatcher) GetStats() (queueSize int, inProgress int) {
	queueSize = len(pw.errorQueue)
	
	inProgress = 0
	pw.fixInProgress.Range(func(key, value interface{}) bool {
		inProgress++
		return true
	})
	
	return queueSize, inProgress
}

// shouldSkipPod checks if we should skip processing this pod
func (pw *PodWatcher) shouldSkipPod(podKey string) bool {
	pw.podTracker.mu.RLock()
	defer pw.podTracker.mu.RUnlock()
	
	if lastProcessed, exists := pw.podTracker.processed[podKey]; exists {
		// Skip if we processed this pod recently
		if time.Since(lastProcessed) < pw.podTracker.reCheckTime {
			return true
		}
	}
	return false
}

// markPodProcessed marks a pod as processed
func (pw *PodWatcher) markPodProcessed(podKey string) {
	pw.podTracker.mu.Lock()
	defer pw.podTracker.mu.Unlock()
	
	pw.podTracker.processed[podKey] = time.Now()
	
	// Clean up old entries (older than 1 hour)
	for key, timestamp := range pw.podTracker.processed {
		if time.Since(timestamp) > time.Hour {
			delete(pw.podTracker.processed, key)
		}
	}
}

// statusReporter periodically reports watcher status
func (pw *PodWatcher) statusReporter(ctx context.Context) {
	defer pw.wg.Done()
	
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	for {
		select {
		case <-ctx.Done():
			return
		case <-pw.stopCh:
			return
		case <-ticker.C:
			queueSize, inProgress := pw.GetStats()
			
			// Count processed pods
			pw.podTracker.mu.RLock()
			processedCount := len(pw.podTracker.processed)
			pw.podTracker.mu.RUnlock()
			
			color.Cyan("📊 Status: Queue=%d, Processing=%d, Recently Processed=%d | %s",
				queueSize, inProgress, processedCount, time.Now().Format("15:04:05"))
		}
	}
}