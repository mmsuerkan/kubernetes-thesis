@echo off
echo === Debug Test - Finding exact error ===
echo.

echo [1] Simple Reflection Test:
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" -H "Content-Type: application/json" -d "{\"error_type\":\"ImagePullBackOff\",\"success\":true,\"resolution_time\":45.0}"
echo.
echo.

echo [2] Full Process Test:
curl -X POST "http://localhost:8000/api/v1/reflexion/process" -H "Content-Type: application/json" -d "{\"pod_name\":\"debug-pod\",\"namespace\":\"default\",\"error_type\":\"ImagePullBackOff\",\"thread_id\":\"debug-thread\"}"
echo.
echo.

echo === Debug Complete ===
pause