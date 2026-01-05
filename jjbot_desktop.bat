@echo off
REM JJ-Bot Desktop Application Launcher
REM Runs JJ-Bot as a standalone native window

echo ========================================
echo JJ-Bot Desktop Application
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Check if pywebview is installed
call venv\Scripts\activate.bat
python -c "import webview" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing pywebview for native window support...
    pip install pywebview >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install pywebview. Please run: pip install pywebview
        pause
        exit /b 1
    )
)

echo Starting JJ-Bot...
echo.

REM Run the desktop app (no window for this launcher)
pythonw jjbot_app.py

exit
