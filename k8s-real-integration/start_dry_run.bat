@echo off
echo 🧪 Starting K8s Reflexion System with DRY RUN MODE
echo =================================================

REM Set environment variables for dry run
set KUBECTL_DRY_RUN=true
set KUBECTL_TIMEOUT=120
set KUBECTL_MAX_RETRIES=3

echo ✅ DRY RUN MODE: Commands will be simulated, not executed
echo.
echo 🔧 Configuration:
echo    KUBECTL_DRY_RUN=%KUBECTL_DRY_RUN%
echo    KUBECTL_TIMEOUT=%KUBECTL_TIMEOUT%
echo    KUBECTL_MAX_RETRIES=%KUBECTL_MAX_RETRIES%
echo.

echo 🐍 Starting Python Reflexion Service...
python -m uvicorn main:app --port 8000 --log-level info

echo.
echo 🛑 Service stopped.
pause