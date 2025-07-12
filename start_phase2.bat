@echo off
echo === Phase 2 K8s Reflexion Service Starter ===
echo.

echo [1] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found, trying python3...
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python not found! Please install Python 3.8+
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)
echo Python found: %PYTHON_CMD%
echo.

echo [2] Checking OpenAI API Key...
if not exist .env (
    echo WARNING: .env file not found
    echo Please create .env file with: OPENAI_API_KEY=your_key_here
    echo.
    echo Do you want to continue anyway? (y/n)
    set /p continue=
    if /i not "%continue%"=="y" (
        echo Exiting...
        pause
        exit /b 1
    )
)
echo.

echo [3] Installing/checking dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies OK
echo.

echo [4] Initializing Persistent Memory System...
echo - Strategy Database (SQLite)
echo - Episodic Memory Manager  
echo - Performance Tracker
echo.

echo [5] Starting K8s Reflexion Service...
echo Server will start on: http://localhost:8000
echo API Documentation: http://localhost:8000/api/docs
echo.
echo === NEW PERSISTENT MEMORY ENDPOINTS ===
echo - GET /api/v1/memory/statistics
echo - GET /api/v1/memory/strategies
echo - GET /api/v1/memory/episodes
echo - GET /api/v1/memory/performance
echo - GET /api/v1/memory/learning-progression
echo.
echo Press Ctrl+C to stop the server
echo.

%PYTHON_CMD% main.py