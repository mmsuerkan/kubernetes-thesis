@echo off
echo 🧪 K8s Reflexion System - Windows Test Suite
echo ==============================================
echo.

REM Sistem durumunu kontrol et
echo 📋 Sistem Kontrolü...
kubectl cluster-info
if %errorlevel% neq 0 (
    echo ❌ Kubernetes cluster'a bağlanılamıyor!
    echo Minikube veya Docker Desktop başlatılmış mı?
    pause
    exit /b 1
)

echo ✅ Kubernetes cluster bağlantısı başarılı
echo.

REM Servislerin çalışıp çalışmadığını kontrol et
echo 🔍 Servisleri Kontrol Et...
echo Python Service: http://localhost:8000/health
echo Go Service: Background'da çalışıyor olmalı
echo.

REM Mevcut pod'ları temizle
echo 🧹 Test ortamını temizle...
kubectl delete pod test-image-error --ignore-not-found=true
kubectl delete pod test-oom-killer --ignore-not-found=true  
kubectl delete pod test-crash-loop --ignore-not-found=true
kubectl delete pod test-invalid-image --ignore-not-found=true
kubectl delete pod test-resource-conflict --ignore-not-found=true
echo ✅ Eski test pod'ları temizlendi
echo.

echo 🚀 Test Senaryolarını Başlat...
echo.

REM Test 1: ImagePullBackOff
echo ========================
echo 🧪 Test 1: ImagePullBackOff
echo ========================
echo Hatalı image tag kullanarak ImagePullBackOff hatası oluştur
kubectl apply -f test-scenarios-windows.yaml
echo.
echo ⏳ Pod'ların oluşmasını bekle (10 saniye)...
timeout /t 10 /nobreak > nul
echo.

echo 📊 Pod Durumları:
kubectl get pods -l test-type
echo.

echo 🔍 Detaylı Pod Bilgileri:
echo.
echo --- ImagePullBackOff Pod ---
kubectl describe pod test-image-error
echo.
echo --- OOMKilled Pod ---  
kubectl describe pod test-oom-killer
echo.
echo --- CrashLoop Pod ---
kubectl describe pod test-crash-loop
echo.

echo ⏳ Go service'in hataları tespit etmesini bekle (30 saniye)...
echo "Bu süre içinde Go service log'larını kontrol et"
timeout /t 30 /nobreak > nul
echo.

echo 📈 Sonuçları Kontrol Et:
echo.
echo "1. Go service log'larında şu mesajları ara:"
echo "   🚨 Processing failed pod"
echo "   📡 Sending to reflexion service"
echo.
echo "2. Python service log'larında şu mesajları ara:"
echo "   🤖 AI COMMAND GENERATION START"
echo "   ✅ AI COMMANDS GENERATED SUCCESSFULLY"
echo "   🚀 REAL KUBECTL EXECUTION START"
echo.
echo "3. Pod durumlarını tekrar kontrol et:"
kubectl get pods -l test-type
echo.

echo 🎯 Başarı Kriterleri:
echo ✅ Go service hataları tespit etti
echo ✅ Python service AI komutları üretti  
echo ✅ kubectl komutları çalıştırıldı
echo ✅ Pod'lar düzeltildi veya yeniden oluşturuldu
echo ✅ Learning velocity arttı
echo.

echo 📊 Memory Management Test:
echo "curl http://localhost:8000/api/v1/reflexion/strategies"
echo "curl http://localhost:8000/api/v1/reflexion/memory/episodic"
echo.

echo 🔄 Test tamamlandı! Sonuçları analiz et.
echo.

REM Test temizliği (isteğe bağlı)
echo 🧹 Test pod'larını temizlemek istiyor musun? (Y/N)
set /p cleanup=
if /i "%cleanup%"=="Y" (
    kubectl delete pod test-image-error --ignore-not-found=true
    kubectl delete pod test-oom-killer --ignore-not-found=true
    kubectl delete pod test-crash-loop --ignore-not-found=true
    kubectl delete pod test-invalid-image --ignore-not-found=true
    kubectl delete pod test-resource-conflict --ignore-not-found=true
    echo ✅ Test pod'ları temizlendi
)

echo.
echo 🎉 Test suite tamamlandı!
pause