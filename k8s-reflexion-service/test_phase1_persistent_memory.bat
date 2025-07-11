@echo off
echo === Phase 1 Persistent Memory System Test ===
echo Testing new SQLite-based memory capabilities
echo.

echo [0] Health Check:
curl -X GET "http://localhost:8000/health"
echo.
echo.

echo [1] Memory System Statistics:
curl -X GET "http://localhost:8000/api/v1/memory/statistics"
echo.
echo.

echo [2] Strategy Database (Empty initially):
curl -X GET "http://localhost:8000/api/v1/memory/strategies"
echo.
echo.

echo [3] Episodic Memory (Empty initially):
curl -X GET "http://localhost:8000/api/v1/memory/episodes?limit=5"
echo.
echo.

echo [4] Performance Insights (Empty initially):
curl -X GET "http://localhost:8000/api/v1/memory/performance?days=7"
echo.
echo.

echo [5] Learning Progression (Empty initially):
curl -X GET "http://localhost:8000/api/v1/memory/learning-progression?days=30"
echo.
echo.

echo === Running a Full Process Test to Generate Data ===
echo.

echo [6] Trigger Learning Process:
curl -X POST "http://localhost:8000/api/v1/reflexion/process" -H "Content-Type: application/json" -d "{\"pod_name\":\"test-memory-pod\",\"namespace\":\"default\",\"error_type\":\"ImagePullBackOff\",\"thread_id\":\"memory-test-1\"}"
echo.
echo.

echo Waiting 3 seconds for processing...
timeout /t 3 /nobreak > nul

echo [7] Check Memory After Learning:
echo.
echo Strategy Database (Should have new entries):
curl -X GET "http://localhost:8000/api/v1/memory/strategies"
echo.
echo.

echo [8] Check Episodes After Learning:
curl -X GET "http://localhost:8000/api/v1/memory/episodes?limit=3"
echo.
echo.

echo [9] Check Performance Metrics:
curl -X GET "http://localhost:8000/api/v1/memory/performance?days=1"
echo.
echo.

echo [10] Final Statistics:
curl -X GET "http://localhost:8000/api/v1/memory/statistics"
echo.
echo.

echo === Test Complete ===
echo.
echo Check the following files created:
echo - reflexion_strategies.db
echo - reflexion_episodes.db  
echo - reflexion_performance.db
echo.
pause