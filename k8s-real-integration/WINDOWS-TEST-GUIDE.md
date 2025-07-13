# 🧪 Windows Test Guide - K8s Reflexion System

## 📋 Hazırlık Adımları

### 1. Servisleri Başlat

**Terminal 1 (Python Service):**
```cmd
cd kubernetes-thesis\k8s-real-integration
python -m uvicorn main:app --port 8000 --log-level info
```

**Terminal 2 (Go Service):**
```cmd
cd kubernetes-thesis\k8s-real-integration
k8s-real-integration.exe
```

### 2. Kubernetes Cluster Kontrolü
```cmd
kubectl cluster-info
kubectl get nodes
```

## 🧪 Test Senaryoları

### ⚡ Hızlı Test (Önerilen)
```cmd
step-by-step-test.bat
```

### 🔄 Tam Test Suite  
```cmd
run-tests-windows.bat
```

### 💾 Memory Test (OOMKilled)
```cmd
memory-test-specific.bat
```

## 📊 Test Senaryoları Detayı

### 1. **ImagePullBackOff Test**
```cmd
kubectl run test-error --image=nginx:invalid-tag --restart=Never
```
**Beklenen Sonuç:**
- Go service hatayı tespit eder
- AI `nginx:latest` ile düzeltir
- Pod Running state'e geçer

### 2. **OOMKilled Test**  
```cmd
kubectl run test-oom --image=polinux/stress --limits="memory=30Mi" --restart=Never -- stress --vm 1 --vm-bytes 50M
```
**Beklenen Sonuç:**
- Exit code 137 (OOMKilled) tespit edilir
- AI memory limitini 200Mi'ya çıkarır
- Pod başarıyla çalışır

### 3. **CrashLoopBackOff Test**
```cmd
kubectl apply -f test-scenarios-windows.yaml
```
**Beklenen Sonuç:**
- Exit code 1 tespit edilir
- AI restart policy veya image düzenler
- Pod stabilize olur

## 🔍 Log'larda Aranacak Anahtar Kelimeler

### Go Service Logs:
```
🚨 Processing failed pod: [pod-name]
📡 Sending to reflexion service...
✅ Response received from reflexion service
🔧 Generating kubectl commands for pod [pod-name]
```

### Python Service Logs:
```
🤖 AI COMMAND GENERATION START
🔧 COMMANDS TO BE EXECUTED:
⚡ EXECUTING REAL KUBECTL COMMANDS
📊 REAL KUBECTL EXECUTION SUMMARY:
🧠 REFLEXION: Found X lessons from Y similar episodes
```

## 📈 Başarı Kriterleri

### ✅ Sistem Çalışıyor:
1. **Error Detection**: Pod hatası 2-5 saniye içinde tespit edilir
2. **AI Command Generation**: Uygun kubectl komutları üretilir  
3. **Real Execution**: Komutlar gerçekten çalıştırılır
4. **Learning**: Episodic memory'ye kaydedilir

### ✅ Memory Management:
```cmd
# Strategies kontrolü
curl http://localhost:8000/api/v1/reflexion/strategies

# Episodic memory kontrolü  
curl http://localhost:8000/api/v1/reflexion/memory/episodic

# System health
curl http://localhost:8000/health
```

## 🐛 Troubleshooting

### Problem: Go service pod'ları görmüyor
**Çözüm:**
```cmd
kubectl get pods
# Eğer boş ise
kubectl config get-contexts
kubectl config use-context docker-desktop
```

### Problem: Python service bağlantı hatası
**Çözüm:**
```cmd
netstat -an | findstr :8000
# Port 8000 açık olmalı
```

### Problem: Memory temizliği gerekiyor
**Çözüm:**
```cmd
curl -X DELETE http://localhost:8000/api/v1/memory/clear
```

## 🎯 Beklenen Sonuçlar

### Test Başarı Örnekleri:

**ImagePullBackOff → Running:**
```
test-error    0/1     ImagePullBackOff   0          30s
               ↓
test-error    1/1     Running            0          45s
```

**OOMKilled → Running with increased memory:**
```
test-oom      0/1     OOMKilled         0          15s
               ↓  
test-oom      1/1     Running           0          30s
```

### Learning Metrics:
```json
{
  "learning_velocity": 0.581,  // Artış bekleniyor
  "strategies_learned": 3,     // Yeni strategy'ler
  "success_rate": "100%"       // Yüksek başarı
}
```

## 🆕 YAML Manifest Mode Test

### YAML Test Senaryosu:
```cmd
# OOMKilled test with YAML generation
kubectl apply -f test-yaml-mode.yaml

# Sistem otomatik olarak şunu yapacak:
# 1. OOMKilled tespit edecek (Go service)
# 2. AI ile yeni YAML manifest üretecek (memory: 256Mi)
# 3. Temporary file oluşturup kubectl apply -f ile uygulayacak
# 4. Validation komutları çalıştıracak
# 5. Temporary file'ı temizleyecek
```

### YAML Mode Avantajları (Artık Default):
- ✅ workingDir set edilebilir (kubectl run ile mümkün değil)
- ✅ securityContext ayarlanabilir  
- ✅ Complex volume mounts
- ✅ initContainers eklenebilir
- ✅ Full pod spec kontrolü
- ✅ Affinity/Toleration rules
- ✅ Resource quotas and limits
- ✅ Environment variables from ConfigMaps/Secrets

## 🚀 İleri Seviye Test

### Reflexion Learning Test:
```cmd
# Aynı hatayı 2 kez oluştur
kubectl run test1 --image=nginx:invalid --restart=Never
# AI çözene kadar bekle
kubectl delete pod test1
kubectl run test2 --image=nginx:invalid --restart=Never  
# 2. sefer daha hızlı çözmeli (learned strategy)
```

### Performance Test:
```cmd
# Çoklu pod testi
kubectl apply -f test-scenarios-windows.yaml
# Sistem 5 pod'u paralel işlemeli
```

---

## 📞 Destek

Test sırasında sorun yaşarsan:
1. **Go service log'larını** kontrol et
2. **Python service log'larını** kontrol et  
3. **kubectl get pods** ile durumu gör
4. **curl health endpoint'lerini** kontrol et

**Test başarı raporu bekleniyor!** 🎉