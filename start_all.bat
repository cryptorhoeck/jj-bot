@echo off
REM JJ-Bot Startup Script for Windows
REM Launches JJ-Bot as a native desktop application

echo ========================================
echo Starting JJ-Bot Trading System
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist dashboard\jj-dashboard\node_modules (
    echo ERROR: Dashboard dependencies not installed!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if pywebview is installed
python -c "import webview" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing pywebview for native window support...
    pip install pywebview requests
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [WARNING] Failed to install pywebview.
        echo This might be due to missing Microsoft Visual C++ Build Tools.
        echo Falling back to browser mode...
        echo.
        goto browser_mode
    )
    REM Verify installation worked
    python -c "import webview" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [WARNING] pywebview installed but cannot be imported.
        echo Falling back to browser mode...
        echo.
        goto browser_mode
    )
)

echo Starting JJ-Bot as native desktop app...
echo.

REM Run the desktop app (pythonw = no console window)
pythonw jjbot_app.py
goto end

:browser_mode
REM Fallback: Start with visible terminals and browser
echo [1/4] Building dashboard...
cd dashboard\jj-dashboard
call npm run build
cd ..\..
echo.

echo [2/4] Starting API Server on port 8000...
start "JJ-Bot API Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && cd glue\api && python main.py"
timeout /t 2 /nobreak >nul

echo [3/4] Starting Dashboard on port 5173...
start "JJ-Bot Dashboard" cmd /k "cd /d %~dp0dashboard\jj-dashboard && npm run dev"
timeout /t 3 /nobreak >nul

echo [4/4] Opening dashboard...
where chrome >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" chrome --app=http://localhost:5173 --window-size=1400,900
) else (
    start http://localhost:5173
)

echo.
echo ========================================
echo JJ-Bot Started Successfully!
echo ========================================
echo.
echo To stop: run stop_all.bat or close the windows
echo.

:end
exit
