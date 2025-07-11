@echo off
echo === Phase 2 Detailed Test Script ===
echo.

echo [1] OpenAI Connection Test:
curl -X GET "http://localhost:8000/api/v1/debug/openai-status"
echo.
echo.

echo [2] Direct GPT-4 Test:
curl -X POST "http://localhost:8000/api/v1/debug/test-gpt4-direct" -H "Content-Type: application/json" -d "{\"prompt\":\"Say OK\"}"
echo.
echo.

echo [3] Simple Reflection Test:
curl -X POST "http://localhost:8000/api/v1/debug/simulate-reflection" -H "Content-Type: application/json" -d "{\"error_type\":\"ImagePullBackOff\",\"success\":true,\"resolution_time\":45.0}"
echo.
echo.

echo [4] Detailed Reflection Test:
curl -X POST "http://localhost:8000/api/v1/debug/reflection-full" -H "Content-Type: application/json" -d "{\"error_type\":\"ImagePullBackOff\",\"success\":true,\"resolution_time\":45.0}"
echo.
echo.

echo [5] Full Process Test with JSON file:
curl -X POST "http://localhost:8000/api/v1/reflexion/process" -H "Content-Type: application/json" -d @test2.json
echo.
echo.

echo [6] Metrics Check:
curl -X GET "http://localhost:8000/api/v1/reflexion/metrics"
echo.
echo.

echo [7] Strategies Check:
curl -X GET "http://localhost:8000/api/v1/reflexion/strategies"
echo.
echo.

echo [8] Episodic Memory Check:
curl -X GET "http://localhost:8000/api/v1/reflexion/memory/episodic"
echo.
echo.

echo === Test Complete ===
pause