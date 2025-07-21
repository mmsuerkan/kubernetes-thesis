@echo off
REM Log management script for K8s Reflexion System (Windows)

setlocal EnableDelayedExpansion

if "%1"=="" (
    echo Usage: %0 [COMMAND] [OPTIONS]
    echo.
    echo Commands:
    echo   tail         Show real-time logs for all services
    echo   follow       Follow logs for specific service  
    echo   export       Export logs to files
    echo   analyze      Analyze logs for errors and patterns
    echo   status       Show service health status
    echo.
    echo Examples:
    echo   %0 tail                    # Show all service logs
    echo   %0 follow reflexion-service # Follow Python service logs
    echo   %0 export                  # Export all logs
    echo   %0 analyze                 # Analyze for errors
    exit /b 1
)

REM Check if docker-compose is running
docker-compose ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo ❌ Services are not running. Start them with: docker-compose up -d
    exit /b 1
)

if "%1"=="tail" (
    echo 📋 Showing logs for all services...
    docker-compose logs --tail=100 -f
    goto end
)

if "%1"=="follow" (
    if "%2"=="" (
        echo ❌ Service name required
        echo Usage: %0 follow [service-name]
        exit /b 1
    )
    echo 📋 Following logs for %2...
    docker-compose logs --tail=100 -f %2
    goto end
)

if "%1"=="export" (
    set OUTPUT_DIR=logs_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    set OUTPUT_DIR=!OUTPUT_DIR: =0!
    mkdir "!OUTPUT_DIR!" 2>nul
    
    echo 📤 Exporting logs to !OUTPUT_DIR!\...
    
    docker-compose logs reflexion-service > "!OUTPUT_DIR!\reflexion-service.log" 2>&1
    docker-compose logs pod-watcher > "!OUTPUT_DIR!\pod-watcher.log" 2>&1
    docker-compose logs > "!OUTPUT_DIR!\combined.log" 2>&1
    
    echo Log export completed at: !OUTPUT_DIR!
    echo ✅ Logs exported to !OUTPUT_DIR!\
    goto end
)

if "%1"=="analyze" (
    echo 🔍 Analyzing logs for errors and patterns...
    echo.
    echo === ERROR ANALYSIS ===
    docker-compose logs | findstr /i "error failed exception"
    echo.
    echo === SUCCESS PATTERNS ===
    docker-compose logs | findstr /i "success completed ✅"
    echo.
    echo === REFLEXION PROCESSING ===
    docker-compose logs reflexion-service | findstr /i "processing strategy yaml"
    echo.
    echo === POD WATCHER ACTIVITY ===
    docker-compose logs pod-watcher | findstr /i "processing scanning"
    goto end
)

if "%1"=="status" (
    echo 📊 Service Health Status
    echo.
    docker-compose ps
    echo.
    echo === Service Endpoints ===
    echo Reflexion Service: http://localhost:8000
    echo Pod Watcher: http://localhost:8080
    echo.
    echo === Health Checks ===
    curl -s http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        echo ❌ Reflexion Service: Unhealthy
    ) else (
        echo ✅ Reflexion Service: Healthy
    )
    
    curl -s http://localhost:8080/health >nul 2>&1
    if errorlevel 1 (
        echo ❌ Pod Watcher: Unhealthy  
    ) else (
        echo ✅ Pod Watcher: Healthy
    )
    goto end
)

echo ❌ Unknown command: %1

:end