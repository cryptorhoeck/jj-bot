@echo off
REM JJ-Bot Stop Script for Windows
REM Stops all JJ-Bot processes and closes terminals

echo ========================================
echo Stopping JJ-Bot Trading System
echo ========================================
echo.

echo [1/4] Killing Python processes...
taskkill /F /T /IM python.exe >nul 2>&1

echo [2/4] Killing Node processes...
taskkill /F /T /IM node.exe >nul 2>&1

echo [3/4] Killing remaining services...
taskkill /F /T /IM uvicorn.exe >nul 2>&1
taskkill /F /T /IM npm.exe >nul 2>&1

echo [4/4] Closing terminal windows...
REM Kill cmd.exe windows by title - this closes the windows themselves
for /f "tokens=2" %%a in ('tasklist /v /fi "windowtitle eq JJ-Bot API Server*" /fo list ^| find "PID:"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /v /fi "windowtitle eq JJ-Bot Dashboard*" /fo list ^| find "PID:"') do taskkill /F /PID %%a >nul 2>&1

echo.
echo ========================================
echo All processes stopped and windows closed!
========================================
echo.
echo This window will close in 2 seconds...
timeout /t 2 /nobreak >nul
exit
