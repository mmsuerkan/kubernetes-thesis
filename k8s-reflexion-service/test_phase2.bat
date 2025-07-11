@echo off
echo === Phase 2 Test Script ===
echo.

echo [1] Health Check:
curl -X GET "http://localhost:8000/health"
echo.
echo.

echo [2] OpenAI Status:
curl -X GET "http://localhost:8000/api/v1/debug/openai-status"
echo.
echo.

echo [3] ImagePullBackOff Test:
curl -X POST "http://localhost:8000/api/v1/reflexion/process" -H "Content-Type: application/json" -d "{\"pod_name\":\"test-pod-1\",\"namespace\":\"default\",\"error_type\":\"ImagePullBackOff\",\"thread_id\":\"test-thread-1\"}"
echo.
echo.

timeout /t 5 /nobreak > nul

echo [4] Metrics Check:
curl -X GET "http://localhost:8000/api/v1/reflexion/metrics"
echo.
echo.

echo [5] CrashLoopBackOff Test:
curl -X POST "http://localhost:8000/api/v1/reflexion/process" -H "Content-Type: application/json" -d "{\"pod_name\":\"test-pod-2\",\"namespace\":\"default\",\"error_type\":\"CrashLoopBackOff\",\"thread_id\":\"test-thread-2\"}"
echo.
echo.

timeout /t 5 /nobreak > nul

echo [6] Direct Reflection Test:
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" -H "Content-Type: application/json" -d "{\"error_type\":\"ImagePullBackOff\",\"success\":true,\"resolution_time\":45.0}"
echo.
echo.

echo [7] Final Metrics:
curl -X GET "http://localhost:8000/api/v1/reflexion/metrics"
echo.
echo.

echo === Test Complete ===
pause