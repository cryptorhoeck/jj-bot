@echo off
REM JJ-Bot Startup Script for Windows
REM Starts both the API server and React dashboard

echo ========================================
echo Starting JJ-Bot Trading System
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist dashboard\jj-dashboard\node_modules (
    echo ERROR: Dashboard dependencies not installed!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

echo Starting services...
echo.

REM Start API Server in new window
echo [1/2] Starting API Server on port 8000...
start "JJ-Bot API Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && cd glue\api && python main.py"

REM Wait a moment for API to start
timeout /t 3 /nobreak >nul

REM Start Dashboard in new window
echo [2/2] Starting Dashboard on port 5173...
start "JJ-Bot Dashboard" cmd /k "cd /d %~dp0dashboard\jj-dashboard && npm run dev"

echo.
echo ========================================
echo JJ-Bot Started Successfully!
echo ========================================
echo.
echo Two windows have been opened:
echo   1. API Server  - http://127.0.0.1:8000
echo   2. Dashboard   - http://localhost:5173
echo.
echo To stop the system:
echo   Close both command windows or press Ctrl+C in each
echo.
echo Your browser should automatically open to the dashboard.
echo If not, navigate to: http://localhost:5173
echo.
pause
