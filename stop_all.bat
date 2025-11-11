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
REM Give processes a moment to die
timeout /t 1 /nobreak >nul

REM Close all cmd windows except this one (using WMIC to find orphaned cmd processes)
for /f "skip=1" %%p in ('wmic process where "name='cmd.exe' and commandline like '%%JJ-Bot%%'" get processid 2^>nul') do (
    if not "%%p"=="%%" taskkill /F /PID %%p >nul 2>&1
)

echo.
echo ========================================
echo All processes stopped!
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
