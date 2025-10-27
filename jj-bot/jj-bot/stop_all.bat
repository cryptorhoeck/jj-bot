@echo off
REM JJ-Bot Stop Script for Windows
REM Stops all JJ-Bot processes

echo ========================================
echo Stopping JJ-Bot Trading System
echo ========================================
echo.

echo Stopping Python API processes...
taskkill /FI "WINDOWTITLE eq JJ-Bot API Server*" /T /F >nul 2>&1
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python.exe"') do (
    wmic process where "ProcessId=%%a AND CommandLine LIKE '%%main.py%%'" delete >nul 2>&1
)

echo Stopping Node.js Dashboard processes...
taskkill /FI "WINDOWTITLE eq JJ-Bot Dashboard*" /T /F >nul 2>&1
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "node.exe"') do (
    wmic process where "ProcessId=%%a AND CommandLine LIKE '%%vite%%'" delete >nul 2>&1
)

echo.
echo ========================================
echo JJ-Bot Stopped
echo ========================================
echo.
pause
