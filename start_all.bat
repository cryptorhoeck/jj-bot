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

REM Build dashboard with latest changes
echo [1/4] Building dashboard with latest changes...
cd dashboard\jj-dashboard
call npm run build
cd ..\..
echo Dashboard built successfully!
echo.

REM Start API Server in new window
echo [2/4] Starting API Server on port 8000...
start "JJ-Bot API Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && cd glue\api && python main.py"

REM Wait for API to start
timeout /t 2 /nobreak >nul

REM Start Dashboard in new window
echo [3/4] Starting Dashboard on port 5173...
start "JJ-Bot Dashboard" cmd /k "cd /d %~dp0dashboard\jj-dashboard && npm run dev"

REM Wait for dashboard to start before opening browser
timeout /t 3 /nobreak >nul

REM Open browser automatically
echo [4/4] Opening dashboard in your browser...
start http://localhost:5173

echo.
echo ========================================
echo JJ-Bot Started Successfully!
echo ========================================
echo.
echo Services running:
echo   - API Server:  http://127.0.0.1:8000
echo   - Dashboard:   http://localhost:5173
echo.
echo To stop the system, run: stop_all.bat
echo.
echo This window will close in 2 seconds...
timeout /t 2 /nobreak >nul
exit
