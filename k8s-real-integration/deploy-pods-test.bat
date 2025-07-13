@echo off
echo 🚀 AI Test Pod'larını Deploy Ediyorum (Default Namespace)...

REM Test pod'larını deploy et
kubectl apply -f test-pods-only.yaml

REM Deploy işleminin tamamlanması için bekle
echo Deploying... Please wait 10 seconds...
timeout /t 10 /nobreak > nul

echo.
echo 📊 Deploy Edilen Test Pod'ları:
kubectl get pods -l test-type

echo.
echo 🔍 Hatalı Pod'lar:
kubectl get pods --field-selector=status.phase!=Running,status.phase!=Succeeded

echo.
echo 💡 AI Sistemi Başlatmak İçin:
echo python -m uvicorn main:app --port 8000
echo go run main.go

echo.
echo 🧹 Test'ten Sonra Temizlik İçin:
echo kubectl delete -f test-pods-only.yaml

pause