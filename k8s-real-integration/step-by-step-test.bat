@echo off
echo 🎯 K8s Reflexion System - Adım Adım Test
echo =========================================
echo.

echo 📋 GEREKLİ ADIMLAR:
echo.
echo 1. Servisleri Başlat:
echo    Terminal 1: python -m uvicorn main:app --port 8000 --log-level info
echo    Terminal 2: k8s-real-integration.exe
echo.
echo 2. Bu script'i çalıştır
echo 3. Log'ları izle ve sonuçları gözlemle
echo.

echo Devam etmek için bir tuşa bas...
pause
echo.

echo 🧪 TEK SENARYO TESTİ - ImagePullBackOff
echo ========================================
echo.

REM Önceki test pod'unu temizle
kubectl delete pod test-simple-error --ignore-not-found=true
echo ✅ Önceki test temizlendi
echo.

echo 🚀 Hatalı Pod Oluştur...
kubectl run test-simple-error --image=nginx:yok-boyle-bir-tag --restart=Never
echo ✅ Pod oluşturuldu
echo.

echo ⏳ 5 saniye bekle - Go service'in tespit etmesini bekle...
timeout /t 5 /nobreak > nul
echo.

echo 📊 Pod Durumu:
kubectl get pod test-simple-error
echo.

echo 🔍 Pod Detayları:
kubectl describe pod test-simple-error
echo.

echo ⏳ 15 saniye daha bekle - AI çözümünün uygulanmasını bekle...
timeout /t 15 /nobreak > nul
echo.

echo 📊 Güncel Pod Durumu:
kubectl get pod test-simple-error
echo.

echo 🎯 BAŞARI KRİTERLERİ:
echo.
echo "Go Service Log'larında Aranacaklar:"
echo "  🚨 Processing failed pod: test-simple-error"
echo "  📡 Sending to reflexion service..."
echo "  ✅ Response received from reflexion service"
echo.
echo "Python Service Log'larında Aranacaklar:"
echo "  🤖 AI COMMAND GENERATION START"
echo "  🔧 COMMANDS TO BE EXECUTED:"
echo "  ⚡ EXECUTING REAL KUBECTL COMMANDS"
echo "  📊 REAL KUBECTL EXECUTION SUMMARY"
echo.

echo 📈 Memory & Learning Kontrol:
echo.
echo "Öğrenme durumunu kontrol et:"
echo "curl http://localhost:8000/api/v1/reflexion/strategies"
echo.
echo "Episodic memory'yi kontrol et:"
echo "curl http://localhost:8000/api/v1/reflexion/memory/episodic"
echo.

echo 🧪 OOMKilled Senaryosu İçin:
echo ==============================
echo.
echo "Bellek yetersizliği testi:"
echo "kubectl apply -f test-scenarios-windows.yaml"
echo "kubectl get pods -w"
echo.

echo 🎉 Test rehberi tamamlandı!
echo.
echo Manuel test için:
echo "1. Servisleri başlat"
echo "2. kubectl run test-pod --image=nginx:invalid-tag --restart=Never"
echo "3. Log'ları izle"
echo "4. kubectl get pods"
echo.

pause