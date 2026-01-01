@echo off
REM ============================================
REM JJ-Bot Desktop App Launcher
REM Starts all servers and opens the standalone app
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Check if already running
tasklist /FI "WINDOWTITLE eq JJ-Bot API Server" 2>nul | find /I "cmd.exe" >nul
if not errorlevel 1 (
    echo JJ-Bot is already running!
    echo Opening dashboard...
    goto :open_app
)

REM Check prerequisites
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

if not exist dashboard\jj-dashboard\node_modules (
    echo ERROR: Dashboard dependencies not installed!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

echo Starting JJ-Bot...

REM Start API Server (minimized)
start /min "JJ-Bot API Server" cmd /c "cd /d %~dp0 && call venv\Scripts\activate.bat && cd glue\api && python main.py"

REM Wait for API to be ready
echo Waiting for API server...
set /a attempts=0
:wait_api
set /a attempts+=1
if !attempts! gtr 30 (
    echo ERROR: API server failed to start
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/api/system/health >nul 2>&1
if errorlevel 1 goto :wait_api
echo API server ready!

REM Start Dashboard (minimized)
start /min "JJ-Bot Dashboard" cmd /c "cd /d %~dp0dashboard\jj-dashboard && npm run dev"

REM Wait for Dashboard to be ready
echo Waiting for dashboard...
set /a attempts=0
:wait_dashboard
set /a attempts+=1
if !attempts! gtr 30 (
    echo ERROR: Dashboard failed to start
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
curl -s http://localhost:5173 >nul 2>&1
if errorlevel 1 goto :wait_dashboard
echo Dashboard ready!

:open_app
REM Open as standalone PWA app (tries Chrome first, then Edge, then default browser)
echo Opening JJ-Bot app...

REM Try to find and use Chrome in app mode
set "chrome_path="
for %%p in (
    "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do (
    if exist "%%~p" set "chrome_path=%%~p"
)

if defined chrome_path (
    start "" "%chrome_path%" --app=http://localhost:5173 --window-size=1400,900
    goto :done
)

REM Try Edge in app mode
set "edge_path="
for %%p in (
    "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
    "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
) do (
    if exist "%%~p" set "edge_path=%%~p"
)

if defined edge_path (
    start "" "%edge_path%" --app=http://localhost:5173 --window-size=1400,900
    goto :done
)

REM Fallback to default browser
start http://localhost:5173

:done
echo.
echo JJ-Bot is running!
echo.
echo To stop: Run stop_all.bat or close the terminal windows
exit
