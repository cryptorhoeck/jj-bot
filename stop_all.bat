@echo off
REM JJ-Bot Stop Script for Windows
REM Stops all JJ-Bot processes and closes terminals

echo ========================================
echo Stopping JJ-Bot Trading System
echo ========================================
echo.

echo [1/4] Stopping API server...
REM Kill Python processes running main.py
taskkill /F /FI "WINDOWTITLE eq JJ-Bot API Server*" >nul 2>&1
taskkill /F /IM python.exe /FI "MEMUSAGE gt 10000" >nul 2>&1

echo [2/4] Stopping Dashboard...
REM Kill Node processes running Vite
taskkill /F /FI "WINDOWTITLE eq JJ-Bot Dashboard*" >nul 2>&1
taskkill /F /IM node.exe /FI "MEMUSAGE gt 10000" >nul 2>&1

echo [3/4] Stopping any remaining services...
REM Kill any uvicorn processes
taskkill /F /IM uvicorn.exe >nul 2>&1
REM Kill any remaining npm/vite processes
taskkill /F /IM npm.exe >nul 2>&1

echo [4/4] Closing terminal windows...
REM Close all cmd windows with JJ-Bot in title (except this one)
for /f "skip=1 tokens=1" %%s in ('wmic process where "name='cmd.exe' and commandline like '%%JJ-Bot%%'" get processid') do (
    if not "%%s"=="%~dpnx0" (
        taskkill /PID %%s /F >nul 2>&1
    )
)

timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo All processes stopped!
echo ========================================
echo.
echo You can now close this window.
echo.
pause
