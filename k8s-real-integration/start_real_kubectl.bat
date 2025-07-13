@echo off
echo 🚀 Starting K8s Reflexion System with REAL KUBECTL EXECUTION
echo ================================================================

REM Set environment variables for real kubectl execution
set KUBECTL_DRY_RUN=false
set KUBECTL_TIMEOUT=120
set KUBECTL_MAX_RETRIES=3

echo ⚠️  WARNING: REAL KUBECTL EXECUTION ENABLED!
echo This will execute actual kubectl commands on your cluster.
echo.
echo Press Ctrl+C to cancel, or any key to continue...
pause

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