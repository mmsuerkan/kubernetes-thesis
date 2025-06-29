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
🔍 K8sGPT        →  🤖 AI Agent      →  ⚡ Executor     →  ✅ Validator
(Hata Tespiti)     (Çözüm Üretimi)    (Otomatik Fix)     (Doğrulama)
```

### 1. **🔍 K8sGPT (Dedektif)**
- **Görevi:** Cluster'daki tüm hataları bulur ve analiz eder
- **Nasıl Çalışır:** Kubernetes'ten aldığı verileri GPT-4'e gönderir
- **Çıktısı:** "Bu hata nedir?" ve "Neden oluştu?" sorularının cevabı

### 2. **🤖 AI Agent (Doktor)**  
- **Görevi:** Hatanın çözümünü bulur ve karar verir
- **Nasıl Çalışır:** K8sGPT'nin teşhisini alır, en uygun tedavi yöntemini belirler
- **Çıktısı:** "Bu hatayı şu komutlarla çözebiliriz" planı

### 3. **⚡ Executor (Tamirci)**
- **Görevi:** AI Agent'ın önerdiği çözümü otomatik uygular
- **Nasıl Çalışır:** Kubernetes API'sine komutlar gönderir
- **Çıktısı:** Düzeltme işlemlerini gerçekleştirir

### 4. **✅ Validator (Kontrol Memuru)**
- **Görevi:** Düzeltmenin başarılı olup olmadığını kontrol eder
- **Nasıl Çalışır:** Sistem durumunu tekrar kontrol eder
- **Çıktısı:** "Sorun çözüldü" ✅ veya "Geri al" ❌ kararı

---

## 🔧 Teknoloji Seçenekleri

### **Backend (Sistemin Kalbi)**
- **🟢 Go (Tavsiye Edilen):** Kubernetes'in kendi diliyle uyumlu, hızlı ve güvenli
- **🟡 Python:** AI kütüphaneleri çok, ama Kubernetes için biraz yavaş

### **AI Framework (Beyin)**
- **LangChain + OpenAI:** Çözüm planları oluşturur
- **CrewAI:** Birden fazla AI agent'ın koordinasyonu

### **Kubernetes Entegrasyonu (Sinir Sistemi)**
- **Operator Pattern:** Kubernetes'e doğal entegrasyon
- **Controller Manager:** 7/24 sürekli izleme
- **client-go:** Kubernetes ile direkt konuşma kütüphanesi

---

## 🚀 Kubernetes-Native Sistem Nasıl Çalışır?

> **Analoji:** Bu sistem, hastanedeki 7/24 çalışan bir doktor ekibi gibidir. Sürekli hastaları (pod'ları) izler, hastalık belirtilerini tespit eder, teşhis koyar ve tedavi eder.

### **1️⃣ Sistem Kurulumu (Hastane İnşaatı)**

```
📋 Kurallar Tanımla → 🏥 Hastane Kur → 👨‍⚕️ Doktor Görevlendir
```

**Ne Yapılır:**
- **AutoFixPolicy:** "Hangi hastalıkları tedavi edeceğiz?" kuralları yazılır
- **CRD (Custom Resource Definition):** Kubernetes'e yeni bir kavram öğretilir
- **Controller:** 7/24 nöbet tutan doktor hastaneye yerleştirilir

**Örnek Kural:**
```yaml
# "default" bölümünde ImagePullBackOff hatalarını otomatik düzelt
namespace: default
auto-fix-enabled: 
  - ImagePullBackOff: true
  - OutOfMemory: false  # Bu hataya dokunma
```

### **2️⃣ Sürekli İzleme (Hasta Takibi)**

```
👀 Gözlem → 📊 Veri Toplama → 🔄 Sürekli Kontrol → 📋 Kayıt Tutma
```

**Ne Olur:**
- **client-go:** Kubernetes'teki her değişikliği saniyede 100+ kez kontrol eder
- **Watch Events:** "Yeni hasta geldi!" bildirimlerini yakalar
- **Reconcile Loop:** Her bildirimde "Ne yapmam gerek?" diye sorar
- **Policy Check:** Kuralları kontrol eder: "Bu hastayı tedavi edebilir miyim?"

**Gerçek Hayat Örneği:**
```
11:30:25 - Pod "web-app" oluşturuldu ✅
11:30:27 - Pod "web-app" ImagePullBackOff durumunda ❌
11:30:28 - Controller: "Yeni hasta! Teşhis gerekli."
```

### **3️⃣ Hata Tespiti ve Karar Verme (Teşhis)**

```
🚨 Alarm → 🔍 İnceleme → 📋 Kural Kontrolü → ⚖️ Karar
```

**Adım Adım Süreç:**
1. **Event Yakalama:** "Pod ImagePullBackOff durumunda!"
2. **Hata Analizi:** "Bu ne demek? Neden oldu?"
3. **Policy Kontrolü:** "Bu hatayı düzeltmem için izin var mı?"
4. **Karar:** "Evet, otomatik düzeltme başlatılsın!"

**Örnek Senaryo:**
```
❌ Pod Durumu: ImagePullBackOff
🔍 Tespit: "nginx:nonexistent-tag" image'ı bulunamıyor
📋 Policy: "ImagePullBackOff → Auto-fix: ENABLED"
⚖️ Karar: "Tedavi başlatılsın!"
```

### **4️⃣ Otomatik Düzeltme (Tedavi)**

```
🎯 Hedef Belirleme → 🤖 AI Çağırma → 💊 Çözüm Uygulama → ✅ Sonuç Kontrolü
```

**Ne Yapar:**
1. **K8sGPT Çağrısı:** "Bu sorunu nasıl çözeriz?"
2. **AI Analizi:** GPT-4: "Image tag'ini 'latest' olarak değiştirin"
3. **Komut Üretimi:** `kubectl patch deployment web-app...`
4. **Otomatik Uygulama:** Komutu Kubernetes'e gönderir

**Gerçek Düzeltme Örneği:**
```bash
# AI'ın önerdiği çözüm:
kubectl patch deployment web-app -p '{"spec":{"template":{"spec":{"containers":[{"name":"web","image":"nginx:latest"}]}}}}'
```

### **5️⃣ Doğrulama ve Takip (İyileşme Kontrolü)**

```
⏱️ Bekleme → 🔍 Kontrol → 📊 Sonuç → 📝 Rapor
```

**Süreç:**
1. **Bekleme:** Düzeltme işleminden sonra 30 saniye bekler
2. **Durum Kontrolü:** Pod'un durumunu tekrar kontrol eder
3. **Başarı Değerlendirmesi:** "Running" durumunda mı?
4. **Kayıt Tutma:** Sonucu loglar ve raporlar

**Başarı Senaryosu:**
```
✅ Pod Status: Running
✅ Duration: 45 seconds
✅ Fix Applied: Image tag updated to 'latest'
✅ Audit Log: Operation completed successfully
```

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

### 6. Yayın Kanalları
- **GitHub:** Open source repository
- **Docker Hub/GHCR:** Container registry
- **Helm Repository:** Chart distribution
- **OperatorHub:** Kubernetes marketplace
- **Cloud Marketplaces:** AWS, Azure, GCP

### 7. Enterprise Özellikler
- **Multi-tenant:** Çok müşteri desteği
- **Web Dashboard:** Yönetim arayüzü
- **Analytics:** Performans raporları
- **Integrations:** Slack, JIRA, Prometheus

### 8. Development Timeline
- **Hafta 1-2:** Backend + K8sGPT entegrasyonu
- **Hafta 3-4:** AI agent logic + OpenAI
- **Hafta 5-6:** Kubernetes operator geliştirme
- **Hafta 7-8:** Güvenlik + test senaryoları
- **Hafta 9-10:** Dokümantasyon + paketleme
- **Hafta 11-12:** Community release + geri bildirim

### 9. Başarı Kriterleri
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