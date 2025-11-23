@echo off
REM JJ-Bot Pro - Windows Silent Startup
REM Runs API server in background, then opens dashboard

REM Create required directories
if not exist "logs" mkdir logs
if not exist "models" mkdir models
if not exist "config" mkdir config

REM Start API server hidden (no window)
start /B pythonw glue\api\main.py > logs\api.log 2>&1

REM Wait for API to start
timeout /t 3 /nobreak > nul

REM Open dashboard in browser
start http://localhost:5173

REM Start dashboard dev server hidden
cd dashboard\jj-dashboard
start /B npm run dev > ..\..\logs\dashboard.log 2>&1
