# Kubernetes AI-Powered Error Detection and Resolution

Bu tez projesi, Kubernetes ortamlarındaki hataları AI kullanarak otomatik tespit etme ve çözüm önerisi sunma konusunu ele almaktadır.

## Proje Genel Bakış

**Tez Konusu:** Kubernetes ortamındaki hataları AI kullanarak otomatik şekilde düzeltmek

**Kullanılan Teknolojiler:**
- Kubernetes (Minikube)
- K8sGPT (AI-powered Kubernetes diagnostic tool)
- OpenAI GPT-4o
- Docker
- PowerShell/Bash

## Ortam Kurulumu

### 1. Kubernetes Cluster Kurulumu

**Minikube Kurulumu:**
```powershell
# Minikube başlat
minikube start --driver=docker

# Cluster durumunu kontrol et
kubectl cluster-info
kubectl get nodes
```

### 2. K8sGPT Kurulumu

**Windows Binary İndirme:**
1. GitHub releases sayfasından Windows binary indir:
   - https://github.com/k8sgpt-ai/k8sgpt/releases/latest
   - `k8sgpt_Windows_x86_64.zip` dosyasını indir

2. Projeye çıkart:
```powershell
unzip k8sgpt_Windows_x86_64.zip
```

**Version Kontrolü:**
```powershell
.\k8sgpt.exe version
# Output: k8sgpt: 0.4.21 (392c79d), built at: unknown
```

### 3. OpenAI Entegrasyonu

**API Key Kurulumu:**
1. https://platform.openai.com/api-keys adresinden API key al
2. K8sGPT'ye OpenAI provider'ını ekle:

```powershell
.\k8sgpt.exe auth add openai
# OpenAI API key'ini gir
```

**Kurulumu Doğrulama:**
```powershell
.\k8sgpt.exe auth list
```

## Temel Kullanım

### 1. Cluster Analizi

**Basit Analiz:**
```powershell
.\k8sgpt.exe analyze
```

**AI Açıklaması ile Analiz:**
```powershell
.\k8sgpt.exe analyze --explain
```

### 2. Test Hataları Oluşturma

**Hatalı Pod Oluşturma:**
```powershell
# Var olmayan image tag'i ile pod oluştur
kubectl run broken-pod --image=nginx:nonexistent-tag

# Pod durumunu kontrol et
kubectl get pods

# K8sGPT ile analiz et
.\k8sgpt.exe analyze --explain
```

## İlk Test Sonuçları

### Başarılı Tespit Edilen Hatalar

1. **Image Pull Error:**
   - **Hata:** `nginx:nonexistent-tag` manifest bulunamadı
   - **AI Tanısı:** "Docker image tag does not exist"
   - **Önerilen Çözüm:** 
     - Tag adını doğrula
     - Geçerli image tag'i kullan
     - Pod'u yeniden deploy et

2. **Kullanılmayan ConfigMap'ler:**
   - 9 adet ConfigMap tespit edildi
   - AI her biri için temizlik önerileri sundu

### K8sGPT Performansı

- **Analiz Hızı:** 2-37 it/s (complexity'ye bağlı)
- **AI Provider:** OpenAI GPT-4o
- **Başarı Oranı:** %100 (test edilen senaryolarda)

## Tespit Edilen Sınırlamalar

1. **Sadece Analiz:** K8sGPT otomatik düzeltme yapmıyor
2. **Manuel Müdahale:** Çözüm önerileri manuel uygulanmalı
3. **Cost:** OpenAI API kullanımı ücretli

# Kubernetes AI Auto-Fix Agent: Sistem Mimarisi

## 📋 Proje Hedefi

Kubernetes cluster'larında meydana gelen hataları **tamamen otomatik** olarak tespit edip düzelten akıllı bir sistem geliştirmek. Bu sistem, yöneticilerin manuel müdahalesine gerek kalmadan sorunları çözer.

---

## 🏗️ Sistem Mimarisi Overview

Sistem 4 ana bileşenden oluşur ve her biri belirli bir görevi yerine getirir:

```
🔍 Detector Agent  →  🤖 Analyzer Agent  →  ⚡ Executor Agent  →  ✅ Validator Agent
(Event Detection)   (AI Analysis)        (Auto Remediation)   (Verification)
```

### 1. **🔍 Detector Agent**
- **Function:** Kubernetes event'lerini sürekli monitor eder ve anomali tespit eder
- **Implementation:** client-go ile Watch API kullanarak real-time event streaming
- **Technology Stack:**
  - **Go + client-go:** Kubernetes API client library
  - **Kubernetes Watch API:** Real-time event streaming
  - **Redis Go Client:** Message queue integration
  - **Gin/Echo Framework:** REST API endpoints
- **Output:** Structured error events → Message Queue

### 2. **🤖 Analyzer Agent (K8sGPT + AI)**  
- **Function:** Error events'i alır, AI-powered root cause analysis yapar
- **Implementation:** K8sGPT + GPT-4 integration ile intelligent diagnosis
- **Technology Stack:**
  - **K8sGPT Binary:** Kubernetes diagnostic tool integration
  - **OpenAI SDK (Go/Python):** GPT-4 API client
  - **LangChain:** Prompt engineering ve chain management
  - **JSON/YAML Parser:** Structured output processing
- **Output:** Diagnostic report + remediation recommendations → Message Queue

### 3. **⚡ Executor Agent**
- **Function:** AI recommendations'ı alır ve otomatik remediation uygular
- **Implementation:** Kubernetes API calls + GPT-4 Turbo (command validation)
- **AI Model:** GPT-4 Turbo - Risk assessment ve command safety validation
- **Technology Stack:**
  - **Kubernetes Go Client:** API server interaction
  - **OpenAI API (GPT-4 Turbo):** Command safety validation
  - **kubectl Wrapper:** Command execution interface
  - **Retry Logic Library:** Failed operation handling
- **Output:** Applied fixes + execution status → Message Queue

### 4. **✅ Validator Agent**
- **Function:** Remediation sonuçlarını verify eder ve success/failure determine eder
- **Implementation:** Post-fix monitoring + GPT-4 Turbo (success evaluation)
- **AI Model:** GPT-4 Turbo - System state analysis ve rollback decision making
- **Technology Stack:**
  - **Kubernetes Informers:** Resource state monitoring
  - **OpenAI API (GPT-4 Turbo):** Success evaluation logic
  - **PostgreSQL Driver:** Audit log storage
  - **Prometheus Client:** Metrics collection
- **Output:** Validation results + audit logs → System

---

## 🔧 Teknoloji Seçenekleri

### **Backend (Sistemin Kalbi)**
- **🟢 Go (Tavsiye Edilen):** Kubernetes'in kendi diliyle uyumlu, hızlı ve güvenli
- **🟡 Python:** AI kütüphaneleri çok, ama Kubernetes için biraz yavaş

### **AI Framework (Intelligent Layer)**

#### **Model Assignment Strategy:**
| **Agent** | **AI Model** | **Use Case** | **Reasoning** |
|-----------|--------------|--------------|---------------|
| **Detector** | ❌ No AI Model | Rule-based event filtering | Deterministic logic sufficient |
| **Analyzer** | **GPT-4** | Complex diagnosis & solution design | Comprehensive analysis capability |
| **Executor** | **GPT-4 Turbo** | Command safety validation | Fast risk assessment needed |
| **Validator** | **GPT-4 Turbo** | Success evaluation & rollback | Quick decision making required |

#### **Framework Integration:**
- **LangChain:** Agent communication ve prompt engineering
- **CrewAI:** Multi-agent workflow orchestration  
- **OpenAI API:** All GPT model access centralized

### **Kubernetes Entegrasyonu (Sinir Sistemi)**
- **Operator Pattern:** Kubernetes'e doğal entegrasyon
- **Controller Manager:** 7/24 sürekli izleme
- **client-go:** Kubernetes ile direkt konuşma kütüphanesi

---

## 🚀 Kubernetes-Native Sistem Nasıl Çalışır?

### **1️⃣ Sistem Kurulumu**

```
📋 Policy Tanımla → 🏗️ Infrastructure Kur → 🤖 Controller Deploy Et
```

**Ne Yapılır:**
- **AutoFixPolicy:** Hangi hata türlerinin otomatik düzeltileceği kuralları yazılır
- **CRD (Custom Resource Definition):** Kubernetes'e yeni kaynak tipi öğretilir
- **Controller:** Sürekli çalışan monitoring ve automation sistemi kurulur

**Örnek Kural:**
```yaml
# "default" bölümünde ImagePullBackOff hatalarını otomatik düzelt
namespace: default
auto-fix-enabled: 
  - ImagePullBackOff: true
  - OutOfMemory: false  # Bu hataya dokunma
```

### **2️⃣ Real-Time Monitoring**

```
👀 Event Watch → 📊 Data Collection → 🔄 Continuous Check → 📋 Logging
```

**Süreç:**
- **client-go:** Kubernetes API'yi sürekli dinler (saniyede 100+ kontrol)
- **Watch Events:** Sistem değişikliklerini anında yakalar
- **Reconcile Loop:** Her event için "Aksiyon gerekli mi?" kontrolü yapar
- **Policy Check:** Tanımlı kurallara göre karar verir

**Örnek Event Timeline:**
```
11:30:25 - Pod "web-app" oluşturuldu ✅
11:30:27 - Pod "web-app" ImagePullBackOff durumuna düştü ❌
11:30:28 - Controller: Event yakalandı, analiz başlatılıyor
```

### **3️⃣ Error Detection & Decision Making**

```
🚨 Alert → 🔍 Analysis → 📋 Policy Check → ⚖️ Decision
```

**Adım Adım Süreç:**
1. **Event Detection:** Pod ImagePullBackOff durumuna düştü
2. **Error Analysis:** Hatanın root cause analizi yapılır
3. **Policy Validation:** AutoFixPolicy kuralları kontrol edilir
4. **Decision:** Otomatik düzeltme için go/no-go kararı

**Örnek Scenario:**
```
❌ Pod Status: ImagePullBackOff
🔍 Root Cause: "nginx:nonexistent-tag" image bulunamıyor
📋 Policy Check: "ImagePullBackOff → Auto-fix: ENABLED"
⚖️ Decision: "Otomatik düzeltme başlatılsın"
```

### **4️⃣ Automated Remediation**

```
🎯 Target Identification → 🤖 AI Analysis → 💊 Solution Apply → ✅ Result Check
```

**İşlem Adımları:**
1. **K8sGPT Integration:** AI-powered error analysis ve solution generation
2. **Solution Generation:** GPT-4: "Image tag'ini 'latest' olarak değiştir"
3. **Command Execution:** Otomatik `kubectl patch` komutu üretimi
4. **API Application:** Kubernetes API üzerinden düzeltme uygulama

**Gerçek Düzeltme Örneği:**
```bash
# AI'ın önerdiği çözüm:
kubectl patch deployment web-app -p '{"spec":{"template":{"spec":{"containers":[{"name":"web","image":"nginx:latest"}]}}}}'
```

### **5️⃣ Validation & Monitoring**

```
⏱️ Wait → 🔍 Verify → 📊 Assessment → 📝 Report
```

**Validation Process:**
1. **Grace Period:** Düzeltme sonrası 30 saniye bekleme
2. **Status Check:** Pod durumunun "Running" olması kontrol edilir
3. **Success Assessment:** Düzeltmenin başarı durumu değerlendirilir
4. **Audit Logging:** Tüm işlemler audit trail'e kaydedilir

**Başarı Senaryosu:**
```
✅ Pod Status: Running
✅ Duration: 45 seconds
✅ Fix Applied: Image tag updated to 'latest'
✅ Audit Log: Operation completed successfully
```

---

## 📡 Message Queue Infrastructure

### **Communication Architecture**

Sistem bileşenleri arasındaki iletişim **asynchronous message queue** üzerinden gerçekleşir:

```
Detector Agent → Redis Stream → Analyzer Agent → Redis Stream → 
Executor Agent → Redis Stream → Validator Agent
```

### **Technology Stack**

#### **1. Message Queue Options**
| **Teknoloji** | **Avantaj** | **Kullanım Durumu** |
|---------------|-------------|---------------------|
| **🟢 Redis Streams** | Kubernetes-native, hızlı, basit | Önerilen çözüm |
| **🟡 RabbitMQ** | Enterprise features, routing | Complex workflow'lar |
| **🟠 Apache Kafka** | High-throughput, distributed | Büyük scale sistemler |

#### **2. Queue Topics & Message Flow**

```yaml
# Message Queue Channels
crash-events:
  - source: Detector Agent
  - target: Analyzer Agent
  - payload: {"namespace": "default", "pod": "web-app", "error": "ImagePullBackOff"}

analysis-results:
  - source: Analyzer Agent  
  - target: Executor Agent
  - payload: {"analysis": "Image not found", "solution": "update-image-tag", "confidence": 0.95}

execution-results:
  - source: Executor Agent
  - target: Validator Agent
  - payload: {"command": "kubectl patch...", "timestamp": "2024-01-01T10:30:00Z", "applied": true}

validation-results:
  - source: Validator Agent
  - target: System Logs
  - payload: {"status": "success", "duration": "45s", "pod_status": "Running"}
```

#### **3. Deployment Configuration**

**Redis StatefulSet (Kubernetes):**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-message-queue
spec:
  serviceName: redis-service
  replicas: 1
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      resources:
        requests:
          storage: 10Gi
```

#### **4. Message Persistence & Reliability**

- **Durability:** Redis AOF persistence enabled
- **Retry Mechanism:** Failed message'lar için 3x retry policy
- **Dead Letter Queue:** Sürekli başarısız olan message'lar için separate queue
- **Monitoring:** Queue depth ve processing time metrikleri

#### **5. Performance Specifications**

| **Metric** | **Target** | **Monitoring** |
|------------|------------|----------------|
| **Message Latency** | < 100ms | Redis latency monitoring |
| **Queue Throughput** | 1000+ msg/sec | Custom Prometheus metrics |
| **Memory Usage** | < 2GB | Kubernetes resource monitoring |
| **Persistence** | 99.9% durability | AOF sync verification |

---

## 🎯 Sistem Avantajları

| **Özellik** | **Açıklama** | **Faydası** |
|-------------|--------------|-------------|
| ⚡ **Native Performance** | kubectl yerine direkt API kullanır | 10x daha hızlı işlem |
| 🔄 **Event-Driven** | Sorun olduğu anda müdahale eder | Anında tepki |
| 🎛️ **Policy-Based** | Namespace bazında kontrol | Güvenli ve kontrollü |
| 🔒 **Secure** | RBAC ile yetkilendirme | Enterprise güvenlik |
| 📈 **Scalable** | Cluster büyüdükçe otomatik büyür | Sınırsız büyüme |

---

## 🔄 Tam Süreç Özeti

```
1. 🏥 Sistem Kurulu → 2. 👀 Sürekli İzleme → 3. 🚨 Hata Tespiti → 
4. 🤖 AI Analizi → 5. ⚡ Otomatik Düzeltme → 6. ✅ Doğrulama → 
7. 📝 Raporlama → 2. 👀 Sürekli İzleme (Döngü devam eder)
```

**Sonuç:** İnsan müdahalesi olmadan, 7/24 çalışan, akıllı Kubernetes yönetim sistemi! 🎉

### 3. Otomatik Çözüm Kategorileri
- **Image Pull Errors:** Tag düzeltme, registry auth
- **Resource Issues:** Memory/CPU limit ayarlama
- **Configuration Errors:** ConfigMap/Secret düzeltme
- **Network Problems:** Service/Ingress fixes
- **Storage Issues:** PVC boyut artırma

### 4. Güvenlik Mekanizmaları
- **Dry-run mode:** Risk-free testing
- **Rollback capability:** Hata durumunda geri alma
- **Human approval:** Kritik işlemler için onay
- **Circuit breaker:** Sürekli hata durumunda durdurma
- **Audit logging:** Tüm işlemleri kaydetme

### 5. Deployment Stratejisi
- **Docker Container:** Uygulamayı paketleme
- **Helm Chart:** Kolay kurulum
- **Kubernetes Operator:** Native integration
- **RBAC:** Güvenli yetkilendirme

### 6. Başarı Kriterleri
- Yaygın K8s hatalarında %90+ otomatik çözüm oranı
- Production-ready güvenlik standartları
- Community adoption (GitHub stars, downloads)
- Gerçek dünyada kullanım örnekleri

## Multi-Agent Otomasyon Pipeline

### Sistem Akışı
```
Pod Crash → Detector Agent → K8sGPT Agent → Fixer Agent → Validator Agent
```

### Agent Rolleri

#### 1. **Detector Agent** (Watcher)
- Kubernetes Event Stream'i dinler
- Pod crash/failure event'lerini yakalar  
- Message queue'ya crash bilgisini gönderir
- **Teknoloji:** Kubernetes Watch API, Go client-go

#### 2. **K8sGPT Agent** (Analyzer)
- Crash event'ini message queue'dan alır
- `k8sgpt.exe analyze --explain` komutunu çalıştırır
- Structured analysis sonucunu parse eder
- Fixer Agent'a analysis sonucunu iletir

#### 3. **Fixer Agent** (Remediator)
- K8sGPT analysis sonucunu alır
- Hata tipine göre uygun fix script'ini belirler/generate eder
- Kubectl/Kubernetes API commands çalıştırır
- Fix işlemi completion bilgisini Validator'a gönderir

#### 4. **Validator Agent** (Verifier)
- Fix işlemi sonrası pod durumunu kontrol eder
- Başarılı ise pipeline'ı sonlandırır ve log kaydı yapar
- Başarısız ise rollback yapar ve alert gönderir
- Success/failure metrics'i toplar

### Teknik Mimari
- **Communication:** Redis/RabbitMQ message queue
- **Language:** Go (Kubernetes ecosystem uyumu)
- **Framework:** Gin/Echo (REST API) + Goroutines
- **Storage:** PostgreSQL (audit logs) + Redis (cache)

### Message Flow
1. **Detector → K8sGPT:** `{"event": "pod-crash", "namespace": "default", "pod": "broken-pod"}`
2. **K8sGPT → Fixer:** `{"analysis": "ImagePullBackOff", "solution": "fix-image-tag", "details": {...}}`
3. **Fixer → Validator:** `{"fix-applied": true, "command": "kubectl patch...", "timestamp": "..."}`
4. **Validator → System:** `{"status": "success", "verification": "pod-running", "duration": "30s"}`

## Sonraki Adımlar

- [ ] Detector Agent geliştirmesi (Kubernetes Watch API)
- [ ] Message queue infrastructure kurulumu 
- [ ] K8sGPT integration agent
- [ ] Fixer agent için fix script library
- [ ] Validator agent + rollback mechanism
- [ ] End-to-end test senaryoları
- [ ] Performance benchmarking
- [ ] Production deployment

## Sistem Gereksinimleri

- Windows 10/11
- Docker Desktop
- Kubernetes (Minikube/Kind/Docker Desktop)
- PowerShell 5.1+
- İnternet bağlantısı (OpenAI API için)

## Lisans

Bu proje akademik araştırma amaçlıdır.