package watcher

import (
	"fmt"
	"log"
	"sync"
	"time"

	v1 "k8s.io/api/core/v1"

	"k8s-real-integration-go/pkg/k8s"
	"k8s-real-integration-go/pkg/reflexion"
)

// PodWatcher monitors Kubernetes pods for errors
type PodWatcher struct {
	k8sClient       *k8s.Client
	reflexionClient *reflexion.Client
	namespace       string
	processedPods   map[string]bool
	mutex           sync.RWMutex
	stopCh          chan struct{}
}

// NewPodWatcher creates a new pod watcher
func NewPodWatcher(k8sClient *k8s.Client, reflexionClient *reflexion.Client, namespace string) *PodWatcher {
	return &PodWatcher{
		k8sClient:       k8sClient,
		reflexionClient: reflexionClient,
		namespace:       namespace,
		processedPods:   make(map[string]bool),
		stopCh:          make(chan struct{}),
	}
}

// Start begins watching pods
func (pw *PodWatcher) Start() error {
	log.Printf("🔍 Starting pod watcher for namespace: %s", pw.namespace)

	// Test connection first
	if err := pw.k8sClient.TestConnection(); err != nil {
		return fmt.Errorf("failed to connect to Kubernetes: %w", err)
	}

	// Start the watch loop
	go pw.watchLoop()

	// Start periodic full scan
	go pw.periodicScan()

	log.Printf("✅ Pod watcher started successfully")
	return nil
}

// Stop stops the pod watcher
func (pw *PodWatcher) Stop() {
	log.Printf("🛑 Stopping pod watcher...")
	close(pw.stopCh)
}

// watchLoop continuously watches for pod changes
func (pw *PodWatcher) watchLoop() {
	for {
		select {
		case <-pw.stopCh:
			log.Printf("📴 Pod watcher stopped")
			return
		default:
			if err := pw.performWatch(); err != nil {
				log.Printf("❌ Watch error: %v", err)
				time.Sleep(5 * time.Second) // Wait before retry
			}
		}
	}
}

// performWatch performs the actual pod watching
func (pw *PodWatcher) performWatch() error {
	// Get clientset (this is a simplified approach)
	// In a real implementation, you'd use the proper watch API
	
	// For now, we'll use a polling approach
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-pw.stopCh:
			return nil
		case <-ticker.C:
			if err := pw.scanPods(); err != nil {
				log.Printf("❌ Scan error: %v", err)
			}
		}
	}
}

// scanPods scans all pods in the namespace
func (pw *PodWatcher) scanPods() error {
	pods, err := pw.k8sClient.ListPods(pw.namespace)
	if err != nil {
		return fmt.Errorf("failed to list pods: %w", err)
	}

	log.Printf("🔍 Scanning %d pods in namespace %s", len(pods.Items), pw.namespace)

	for _, pod := range pods.Items {
		if pw.shouldProcessPod(&pod) {
			pw.processPod(&pod)
		}
	}

	return nil
}

// shouldProcessPod determines if a pod should be processed
func (pw *PodWatcher) shouldProcessPod(pod *v1.Pod) bool {
	podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

	// Check if pod has failed
	if !pw.k8sClient.IsPodFailed(pod) {
		return false
	}

	// Check if we've already processed this pod
	pw.mutex.RLock()
	processed := pw.processedPods[podKey]
	pw.mutex.RUnlock()

	return !processed
}

// processPod processes a failed pod
func (pw *PodWatcher) processPod(pod *v1.Pod) {
	podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
	errorType := pw.k8sClient.GetPodErrorType(pod)

	log.Printf("🚨 Processing failed pod: %s, Error: %s", podKey, errorType)

	// Mark as processed
	pw.mutex.Lock()
	pw.processedPods[podKey] = true
	pw.mutex.Unlock()

	// Get additional data
	events, err := pw.k8sClient.GetPodEvents(pod.Namespace, pod.Name)
	if err != nil {
		log.Printf("❌ Failed to get events for pod %s: %v", podKey, err)
		events = []v1.Event{}
	}

	logs, err := pw.k8sClient.GetPodLogs(pod.Namespace, pod.Name)
	if err != nil {
		log.Printf("❌ Failed to get logs for pod %s: %v", podKey, err)
		logs = []string{"Failed to retrieve logs"}
	}

	// Send to reflexion service
	log.Printf("📡 Sending to reflexion service...")
	response, err := pw.reflexionClient.ProcessPodError(pod, events, logs, errorType)
	if err != nil {
		log.Printf("❌ Failed to process pod with reflexion: %v", err)
		return
	}
	log.Printf("✅ Response received from reflexion service")

	// Log the response
	log.Printf("✅ Reflexion completed for pod %s:", podKey)
	log.Printf("   📋 Workflow ID: %s", response.WorkflowID)
	log.Printf("   🎯 Strategy: %v", response.FinalStrategy["type"])
	log.Printf("   📊 Confidence: %v", response.FinalStrategy["confidence"])
	log.Printf("   ⏱️  Resolution Time: %.2fs", response.ResolutionTime)
	log.Printf("   🔍 Used Real K8s Data: %v", response.ReflexionSummary["used_real_k8s_data"])

	if response.RequiresHumanIntervention {
		log.Printf("🚨 Human intervention required for pod %s", podKey)
	} else {
		log.Printf("🤖 AI strategy available for pod %s", podKey)
	}
}

// periodicScan performs periodic full scans
func (pw *PodWatcher) periodicScan() {
	ticker := time.NewTicker(60 * time.Second) // Full scan every minute
	defer ticker.Stop()

	for {
		select {
		case <-pw.stopCh:
			return
		case <-ticker.C:
			log.Printf("🔄 Performing periodic full scan...")
			if err := pw.scanPods(); err != nil {
				log.Printf("❌ Periodic scan error: %v", err)
			}
		}
	}
}

// GetProcessedPods returns the list of processed pods
func (pw *PodWatcher) GetProcessedPods() []string {
	pw.mutex.RLock()
	defer pw.mutex.RUnlock()

	var pods []string
	for podKey := range pw.processedPods {
		pods = append(pods, podKey)
	}
	return pods
}

// ResetProcessedPods clears the processed pods list
func (pw *PodWatcher) ResetProcessedPods() {
	pw.mutex.Lock()
	defer pw.mutex.Unlock()

	pw.processedPods = make(map[string]bool)
	log.Printf("🔄 Processed pods list reset")
}