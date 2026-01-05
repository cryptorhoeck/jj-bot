@echo off
REM JJ-Bot Stop Script for Windows
REM Stops all JJ-Bot processes, invalidates sessions, and closes terminals

echo ========================================
echo Stopping JJ-Bot Trading System
echo ========================================
echo.

echo [1/6] Invalidating all login sessions...
REM Write current timestamp to force re-login on next start
powershell -Command "[System.IO.File]::WriteAllText('%~dp0data\session_invalidated.txt', (Get-Date).ToString('o'))"
echo Sessions invalidated - login required on next start.
echo.

echo [2/6] Closing browser tabs (localhost:5173)...
REM Close Chrome/Edge tabs showing localhost:5173
powershell -ExecutionPolicy Bypass -Command ^
  "Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }; " ^
  "Get-Process msedge -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }"
echo.

echo [3/6] Killing Python processes...
taskkill /F /T /IM python.exe >nul 2>&1

echo [4/6] Killing Node processes...
taskkill /F /T /IM node.exe >nul 2>&1

echo [5/6] Killing remaining services...
taskkill /F /T /IM uvicorn.exe >nul 2>&1
taskkill /F /T /IM npm.exe >nul 2>&1

REM Small delay to ensure processes are terminated
timeout /t 1 /nobreak >nul

echo [6/6] Closing terminal windows...
REM Use PowerShell script for reliable window closing
powershell -ExecutionPolicy Bypass -File "%~dp0close_windows.ps1"

echo Final cleanup...
REM Kill any remaining cmd.exe that might be hanging
for /f "tokens=2" %%a in ('tasklist /v /fi "IMAGENAME eq cmd.exe" 2^>nul ^| findstr /I "JJ-Bot"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ========================================
echo All processes stopped and windows closed!
echo ========================================
echo.
echo This window will close in 2 seconds...
timeout /t 2 /nobreak >nul
exit
