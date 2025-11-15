@echo off
REM JJ-Bot Stop Script for Windows
REM Stops all JJ-Bot processes and closes terminals

echo ========================================
echo Stopping JJ-Bot Trading System
echo ========================================
echo.

echo [1/5] Killing Python processes...
taskkill /F /T /IM python.exe >nul 2>&1

echo [2/5] Killing Node processes...
taskkill /F /T /IM node.exe >nul 2>&1

echo [3/5] Killing remaining services...
taskkill /F /T /IM uvicorn.exe >nul 2>&1
taskkill /F /T /IM npm.exe >nul 2>&1

REM Small delay to ensure processes are terminated
timeout /t 1 /nobreak >nul

echo [4/5] Closing API Server window...
REM Use tasklist with window title filter to find and kill cmd windows
taskkill /F /FI "WINDOWTITLE eq JJ-Bot API Server" >nul 2>&1
REM Fallback with wildcard
taskkill /F /FI "WINDOWTITLE eq JJ-Bot API Server*" >nul 2>&1

echo [5/5] Closing Dashboard window...
taskkill /F /FI "WINDOWTITLE eq JJ-Bot Dashboard" >nul 2>&1
REM Fallback with wildcard
taskkill /F /FI "WINDOWTITLE eq JJ-Bot Dashboard*" >nul 2>&1

REM Additional cleanup: PowerShell method as final backup
powershell -WindowStyle Hidden -Command "Get-Process | Where-Object {$_.MainWindowTitle -like '*JJ-Bot*'} | Stop-Process -Force" >nul 2>&1

echo.
echo ========================================
echo All processes stopped and windows closed!
echo ========================================
echo.
echo This window will close in 2 seconds...
timeout /t 2 /nobreak >nul
exit
