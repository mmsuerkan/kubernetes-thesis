@echo off
echo ===============================================
echo    K8s AI Auto-Fix Agent Dashboard Launcher
echo ===============================================
echo.

echo 🧪 Baglanti testleri yapiliyor...
python test_dashboard_connections.py

echo.
echo 🚀 Dashboard baslatiliyor...
echo 📱 Dashboard URL: file://%CD%\dashboard.html
echo.

if exist "dashboard.html" (
    echo ✅ Dashboard bulundu, tarayicida aciliyor...
    start "" "dashboard.html"
) else (
    echo ❌ dashboard.html dosyasi bulunamadi!
    pause
    exit /b 1
)

echo.
echo 💡 Servis durumları:
echo    - FastAPI Backend: http://localhost:8000/health
echo    - Go Watcher Service: http://localhost:8080/api/v1/health
echo.
echo 🎯 Dashboard acildiktan sonra bu pencereyi kapatabilirsiniz.
echo.
pause