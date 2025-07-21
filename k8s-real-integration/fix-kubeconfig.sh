#!/bin/sh
# Fix kubeconfig for Docker container environment

echo "🔧 Fixing kubeconfig paths for container..."

# Get minikube IP from host
MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "192.168.49.2")

# Create container-compatible kubeconfig
mkdir -p /home/appuser/.kube

# Replace Windows paths with container-mounted paths
sed 's|C:\\Users\\mmert\\\.minikube|/home/appuser/.minikube|g' /home/appuser/.kube/config > /tmp/config-temp
sed 's|\\|/|g' /tmp/config-temp > /tmp/config-fixed

# Replace localhost/127.0.0.1 with minikube IP and preserve the port
sed "s|127\.0\.0\.1|${MINIKUBE_IP}|g" /tmp/config-fixed > /home/appuser/.kube/config-fixed

echo "✅ Kubeconfig fixed for container environment"
echo "📍 Using Kubernetes cluster at: ${MINIKUBE_IP}:8443"

# Use the fixed config
export KUBECONFIG=/home/appuser/.kube/config-fixed
exec "$@"