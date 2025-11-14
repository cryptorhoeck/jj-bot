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
REM Close windows by window title using nircmd alternative
powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -like '*JJ-Bot API Server*'} | Stop-Process -Force" >nul 2>&1

echo [5/5] Closing Dashboard window...
powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -like '*JJ-Bot Dashboard*'} | Stop-Process -Force" >nul 2>&1

REM Backup method: Kill any remaining cmd.exe windows running our scripts
for /f "tokens=2" %%a in ('tasklist /v /fi "IMAGENAME eq cmd.exe" ^| findstr /I "JJ-Bot"') do (
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
