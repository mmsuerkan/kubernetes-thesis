package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"k8s-real-integration-go/pkg/k8s"
	"k8s-real-integration-go/pkg/reflexion"
	"k8s-real-integration-go/pkg/watcher"
)

func main() {
	fmt.Println("🚀 Starting K8s Real-Time Pod Monitoring System")
	fmt.Println("📡 Connecting to Kubernetes cluster and Python Reflexion Service")

	// Parse command line flags
	var (
		namespace      = flag.String("namespace", "default", "Namespace to monitor")
		reflexionURL   = flag.String("reflexion-url", "http://localhost:8000", "Reflexion service URL")
		testMode       = flag.Bool("test-mode", false, "Run in test mode (mock pod)")
	)
	flag.Parse()

	// Test mode - run the original mock test
	if *testMode {
		fmt.Println("🧪 Running in test mode with mock pod")
		runTestMode(*reflexionURL)
		return
	}

	// Real-time monitoring mode
	fmt.Printf("🔍 Starting real-time monitoring for namespace: %s\n", *namespace)
	fmt.Printf("📡 Reflexion service URL: %s\n", *reflexionURL)

	// Create Kubernetes client
	k8sClient, err := k8s.NewClient()
	if err != nil {
		log.Fatalf("❌ Failed to create Kubernetes client: %v", err)
	}

	// Create reflexion client
	reflexionClient := reflexion.NewClient(*reflexionURL)

	// Test reflexion service connection
	if err := reflexionClient.HealthCheck(); err != nil {
		log.Fatalf("❌ Reflexion service health check failed: %v", err)
	}
	fmt.Println("✅ Reflexion service connection verified")

	// Create pod watcher
	podWatcher := watcher.NewPodWatcher(k8sClient, reflexionClient, *namespace)

	// Start pod watcher
	if err := podWatcher.Start(); err != nil {
		log.Fatalf("❌ Failed to start pod watcher: %v", err)
	}

	// Setup signal handling for graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	fmt.Println("🎯 Pod monitoring started! Deploy a broken pod to test...")
	fmt.Println("📝 Example commands to create test pods:")
	fmt.Println("   kubectl run broken-nginx --image=nginx:nonexistent-tag")
	fmt.Println("   kubectl run broken-app --image=invalid-image:latest")
	fmt.Println("💡 Press Ctrl+C to stop monitoring")

	// Wait for signal
	<-sigCh
	fmt.Println("\n🛑 Received shutdown signal, stopping pod watcher...")

	// Stop pod watcher
	podWatcher.Stop()

	// Show processed pods
	processedPods := podWatcher.GetProcessedPods()
	if len(processedPods) > 0 {
		fmt.Printf("📊 Processed %d failed pods:\n", len(processedPods))
		for _, podKey := range processedPods {
			fmt.Printf("   - %s\n", podKey)
		}
	} else {
		fmt.Println("📊 No failed pods were detected during monitoring")
	}

	fmt.Println("👋 Pod monitoring stopped successfully")
}

// runTestMode runs the original mock test
func runTestMode(reflexionURL string) {
	fmt.Println("🧪 Running mock pod test...")
	
	// Import the old test code here
	testMockPod(reflexionURL)
}

