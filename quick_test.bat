@echo off
echo === Quick Phase 1 Memory Test ===
echo.

echo [1] Health:
curl -s -X GET "http://localhost:8000/health" | findstr "status"
echo.

echo [2] Memory Stats:
curl -s -X GET "http://localhost:8000/api/v1/memory/statistics" 
echo.

echo [3] Test Process (ImagePullBackOff):
curl -s -X POST "http://localhost:8000/api/v1/reflexion/process" -H "Content-Type: application/json" -d "{\"pod_name\":\"quick-test\",\"namespace\":\"default\",\"error_type\":\"ImagePullBackOff\"}"
echo.

echo [4] Check Strategies:
curl -s -X GET "http://localhost:8000/api/v1/memory/strategies" | findstr "count"
echo.

echo === Quick Test Done ===
pause