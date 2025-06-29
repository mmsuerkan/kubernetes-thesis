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

## Tez Katkısı: K8s AI Auto-Fix Agent

### Proje Hedefi
K8sGPT'nin tespit ettiği hataları AI agent'lar ile tamamen otomatik çözecek bir sistem geliştirmek. Bu sistem sadece hata tespiti yapmakla kalmayıp, çözümleri de otomatik olarak uygulayacak.

### 1. Sistem Mimarisi
- **K8sGPT:** Hata tespiti ve analizi
- **AI Agent:** Çözüm önerisi ve karar verme
- **Executor:** Otomatik çözüm uygulama
- **Validator:** Başarı doğrulama

### 2. Teknoloji Stack Seçenekleri

**Backend Development:**
- **Go** (Önerilen): Kubernetes ecosystem uyumu
- **Python**: AI framework desteği

**AI Framework:**
- **LangChain + OpenAI:** Çözüm generasyonu
- **CrewAI:** Multi-agent orchestration

**Kubernetes Integration:**
- **Operator Pattern:** Custom Resource Definitions
- **Controller Manager:** Reconcile loop
- **client-go:** Kubernetes API erişimi

Sistem, Kubernetes-native bir yaklaşım benimser ve Operator Pattern kullanarak cluster'a entegre olur. **Custom Resource Definition (CRD)** ile `AutoFixPolicy` adında yeni bir Kubernetes kaynağı tanımlanır - bu kaynak hangi namespace'lerde hangi hata türlerinin otomatik düzeltileceğini belirtir. **Controller Manager** sürekli çalışan bir reconcile loop içinde cluster event'lerini dinler ve CRD'de tanımlanan policy'lere göre action alır. **client-go** library'si ile Kubernetes API'sine direkt erişim sağlanarak pod status'ları, event'ler ve resource durumları real-time takip edilir. Örneğin bir pod ImagePullBackOff durumuna düştüğünde, controller bu event'i yakalar, CRD policy'sini kontrol eder, eğer bu hata tipi için auto-fix enabled ise K8sGPT agent'ını tetikler ve çözüm uygulandıktan sonra pod'un Running durumuna geçişini client-go ile validate eder. Bu yaklaşım sayesinde sistem kubectl komutları yerine native Kubernetes API kullanarak hem daha performanslı hem de daha güvenli operasyonlar gerçekleştirir.

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