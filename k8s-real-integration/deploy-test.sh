#!/bin/bash

echo "🚀 AI Test Senaryolarını Deploy Ediyorum..."

# Namespace oluştur
kubectl apply -f test-scenarios.yaml

# Her deployment için bekleme süresi
sleep 10

echo ""
echo "📊 Deploy Edilen Test Pod'ları:"
kubectl get pods -n ai-test

echo ""
echo "🔍 Hatalı Pod'lar:"
kubectl get pods -n ai-test --field-selector=status.phase!=Running,status.phase!=Succeeded

echo ""
echo "💡 AI Sistemi Başlatmak İçin:"
echo "cd /mnt/c/Users/mmert/kubernetes-thesis/k8s-real-integration"
echo "python main.py"

echo ""
echo "🧹 Test'ten Sonra Temizlik İçin:"
echo "kubectl delete namespace ai-test"