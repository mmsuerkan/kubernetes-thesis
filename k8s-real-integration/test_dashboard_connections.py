#!/usr/bin/env python3
"""
Dashboard Bağlantı Test Scripti
Bu script dashboard'un kullandığı tüm bağlantıları test eder.
"""
import asyncio
import os
import requests
import json
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def test_openai_api_key():
    """OpenAI API key'in çalışıp çalışmadığını test eder"""
    print("OpenAI API Key testi...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("HATA: OPENAI_API_KEY environment variable bulunamadi")
        return False
    
    if not api_key.startswith("sk-"):
        print("HATA: OPENAI_API_KEY gecersiz format (sk- ile baslamali)")
        return False
    
    # OpenAI API'ye basit bir istek gönder
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Models endpoint'ini test et (lightweight)
        response = requests.get(
            "https://api.openai.com/v1/models", 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ OpenAI API key geçerli ve çalışıyor")
            return True
        elif response.status_code == 401:
            print("❌ OpenAI API key geçersiz veya süresi dolmuş")
            return False
        else:
            print(f"⚠️ OpenAI API beklenmeyen yanıt: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenAI API bağlantı hatası: {e}")
        return False

def test_fastapi_backend():
    """FastAPI backend'in çalışıp çalışmadığını test eder"""
    print("\n🌐 FastAPI Backend testi...")
    
    try:
        # Health endpoint test
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI backend çalışıyor")
            
            # OpenAI status endpoint test
            try:
                openai_response = requests.get("http://localhost:8000/api/v1/debug/openai-status", timeout=5)
                if openai_response.status_code == 200:
                    data = openai_response.json()
                    if data.get("configured"):
                        print("✅ FastAPI backend OpenAI entegrasyonu aktif")
                    else:
                        print("❌ FastAPI backend OpenAI entegrasyonu pasif")
                else:
                    print("⚠️ FastAPI OpenAI status endpoint erişilemiyor")
            except Exception as e:
                print(f"⚠️ FastAPI OpenAI status kontrolü başarısız: {e}")
            
            return True
        else:
            print(f"❌ FastAPI backend yanıt vermiyor: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ FastAPI backend bağlantı hatası: {e}")
        print("💡 Önce 'python -m uvicorn main:app --port 8000' komutuyla servisi başlatın")
        return False

def test_go_watcher_service():
    """Go Watcher Service'in çalışıp çalışmadığını test eder"""
    print("\n🔍 Go Watcher Service testi...")
    
    try:
        response = requests.get("http://localhost:8080/api/v1/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Go Watcher Service çalışıyor: {data.get('message', 'OK')}")
            return True
        else:
            print(f"❌ Go Watcher Service yanıt vermiyor: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Go Watcher Service bağlantı hatası: {e}")
        print("💡 Önce './k8s-real-integration.exe' komutuyla servisi başlatın")
        return False

def test_dashboard_cors():
    """Dashboard için CORS ayarlarını test eder"""
    print("\n🌐 CORS testi...")
    
    try:
        # Preflight request simulation
        headers = {
            "Origin": "null",  # file:// origin için
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type"
        }
        
        response = requests.options("http://localhost:8000/health", headers=headers, timeout=5)
        
        if response.status_code == 200:
            cors_headers = response.headers
            if "Access-Control-Allow-Origin" in cors_headers:
                print("✅ CORS doğru yapılandırılmış")
                return True
            else:
                print("⚠️ CORS yapılandırması eksik olabilir")
                return False
        else:
            print(f"⚠️ CORS preflight testi başarısız: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ CORS testi bağlantı hatası: {e}")
        return False

def test_sample_api_endpoints():
    """Dashboard'un kullandığı temel API endpoint'leri test eder"""
    print("\n📊 API Endpoints testi...")
    
    endpoints = [
        "/api/v1/memory/statistics",
        "/api/v1/memory/strategies", 
        "/api/v1/memory/episodes"
    ]
    
    all_passed = True
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}")
            else:
                print(f"❌ {endpoint} (Status: {response.status_code})")
                all_passed = False
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} (Error: {e})")
            all_passed = False
    
    return all_passed

def main():
    """Ana test fonksiyonu"""
    print("K8s AI Auto-Fix Dashboard - Baglanti Testleri")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 5
    
    # Test 1: OpenAI API Key
    if test_openai_api_key():
        tests_passed += 1
    
    # Test 2: FastAPI Backend
    if test_fastapi_backend():
        tests_passed += 1
        
    # Test 3: Go Watcher Service
    if test_go_watcher_service():
        tests_passed += 1
        
    # Test 4: CORS
    if test_dashboard_cors():
        tests_passed += 1
        
    # Test 5: API Endpoints
    if test_sample_api_endpoints():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📈 Test Sonucu: {tests_passed}/{total_tests} başarılı")
    
    if tests_passed == total_tests:
        print("🎉 Tüm testler başarılı! Dashboard hazır.")
        print("📱 dashboard.html dosyasını tarayıcıda açabilirsiniz.")
    else:
        print("⚠️ Bazı testler başarısız. Eksik servisleri başlatın:")
        if tests_passed < 2:
            print("   - FastAPI: python -m uvicorn main:app --port 8000")
        if tests_passed < 3:
            print("   - Go Service: ./k8s-real-integration.exe")

if __name__ == "__main__":
    main()