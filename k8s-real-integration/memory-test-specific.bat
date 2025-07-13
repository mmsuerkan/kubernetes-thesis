@echo off
echo 💾 OOMKilled Memory Test - Spesifik Senaryo
echo ===========================================
echo.

echo 📋 Bu test özellikle OOMKilled senaryosunu test eder
echo AI'ın memory limitlerini nasıl artırdığını gösterir
echo.

echo 🧹 Önceki test'leri temizle...
kubectl delete pod test-memory-stress --ignore-not-found=true
kubectl delete pod memory-stress-test --ignore-not-found=true
echo.

echo 🧪 Memory Stress Pod Oluştur...
echo Bu pod memory limiti aşacak ve OOMKilled olacak
echo.

kubectl run test-memory-stress ^
  --image=polinux/stress ^
  --limits="memory=30Mi,cpu=0.1" ^
  --requests="memory=10Mi,cpu=0.05" ^
  --restart=Never ^
  -- stress --vm 1 --vm-bytes 50M --timeout 30s

echo ✅ Memory stress pod oluşturuldu
echo.

echo ⏳ 10 saniye bekle - Pod'un OOMKilled olmasını bekle...
timeout /t 10 /nobreak > nul
echo.

echo 📊 Pod Durumu (OOMKilled bekleniyor):
kubectl get pod test-memory-stress
echo.

echo 🔍 Exit Code Kontrolü (137 = OOMKilled):
kubectl describe pod test-memory-stress | findstr "Exit Code"
echo.

echo ⏳ 20 saniye daha bekle - AI'ın tespit ve çözmesini bekle...
echo Go service log'larında "OOMKilled" kelimesini ara
echo Python service log'larında "memory=200Mi" artışını ara
timeout /t 20 /nobreak > nul
echo.

echo 📊 Güncel Pod Durumu:
kubectl get pod test-memory-stress
echo.

echo 🧠 AI'ın Memory Çözümü Kontrol:
echo.
echo "AI şunları yapmış olmalı:"
echo "  1. Exit code 137'yi tespit etti (OOMKilled)"
echo "  2. Memory limitini 30Mi'dan 200Mi'ya çıkardı"
echo "  3. Pod'u yeniden oluşturdu"
echo "  4. Başarılı çözümü episodic memory'ye kaydetti"
echo.

echo 🔍 Detaylı Analiz:
echo.
echo "Go Service Log'larında Aranacaklar:"
echo "  🔍 DEBUG: Pod test-memory-stress IsPodFailed result: true"
echo "  🚨 Processing failed pod: test-memory-stress, Error: OOMKilled"
echo.
echo "Python Service Log'larında Aranacaklar:"
echo "  🚨 Error Type: OOMKilled"
echo "  🔧 COMMANDS TO BE EXECUTED:"
echo "  kubectl run test-memory-stress --limits='memory=200Mi,cpu=0.2'"
echo.

echo 📈 Learning Verification:
echo.
echo "Öğrenme başarısını kontrol et:"
echo "curl http://localhost:8000/api/v1/reflexion/strategies | jq"
echo.

echo 💡 Başarı Göstergeleri:
echo "  ✅ Pod Running state'e geçti"
echo "  ✅ Memory limiti 200Mi'ya çıktı"
echo "  ✅ OOMKilled stratejisi oluşturuldu"
echo "  ✅ Learning velocity arttı"
echo.

echo 🧪 Manuel Verification:
echo "kubectl describe pod test-memory-stress | findstr -i memory"
echo.

echo 🎯 Test tamamlandı!
pause