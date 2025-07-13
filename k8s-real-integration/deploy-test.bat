@echo off
echo 🚀 AI Test Senaryolarını Deploy Ediyorum...

REM Namespace oluştur ve test senaryolarını deploy et
kubectl apply -f test-scenarios.yaml

REM Deploy işleminin tamamlanması için bekle
echo Deploying... Please wait 10 seconds...
timeout /t 10 /nobreak > nul

echo.
echo 📊 Deploy Edilen Test Pod'ları:
kubectl get pods -n ai-test

echo.
echo 🔍 Hatalı Pod'lar:
kubectl get pods -n ai-test --field-selector=status.phase!=Running,status.phase!=Succeeded

echo.
echo 💡 AI Sistemi Başlatmak İçin:
echo python main.py

echo.
echo 🧹 Test'ten Sonra Temizlik İçin:
echo kubectl delete namespace ai-test

pause