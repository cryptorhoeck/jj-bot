@echo off
REM JJ-Bot Stop Script for Windows
REM Stops all JJ-Bot processes and closes terminals

echo ========================================
echo Stopping JJ-Bot Trading System
echo ========================================
echo.

echo [1/4] Stopping API server...
REM Kill Python processes
taskkill /F /FI "WINDOWTITLE eq JJ-Bot API Server*" >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

echo [2/4] Stopping Dashboard...
REM Kill Node processes
taskkill /F /FI "WINDOWTITLE eq JJ-Bot Dashboard*" >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

echo [3/4] Stopping any remaining services...
REM Kill any uvicorn processes
taskkill /F /IM uvicorn.exe >nul 2>&1
REM Kill any remaining npm/vite processes
taskkill /F /IM npm.exe >nul 2>&1

echo [4/4] Cleaning up...
REM Wait for processes to fully terminate
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo All processes stopped!
echo ========================================
echo.
echo NOTE: Terminal windows may remain open.
echo You can manually close them with X button.
echo.
pause
