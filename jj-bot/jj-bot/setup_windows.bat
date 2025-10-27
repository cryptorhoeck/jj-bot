@echo off
REM JJ-Bot Windows Setup Script
REM This script sets up the development environment for Windows

echo ========================================
echo JJ-Bot Windows Setup
echo ========================================
echo.

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

REM Check Node.js installation
echo [2/5] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 16+ from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo.

REM Create virtual environment
echo [3/5] Creating Python virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    echo Virtual environment created successfully
)
echo.

REM Install Python dependencies
echo [4/5] Installing Python dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Python dependencies installed
echo.

REM Install Node.js dependencies
echo [5/5] Installing Node.js dependencies for dashboard...
cd dashboard\jj-dashboard
if exist node_modules (
    echo Node modules already exist, skipping...
) else (
    call npm install
    echo Dashboard dependencies installed
)
cd ..\..
echo.

REM Create necessary directories
echo Creating necessary directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist backups mkdir backups
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Run 'start_all.bat' to start the system
echo 2. Access dashboard at: http://localhost:5173
echo 3. Access API at: http://127.0.0.1:8000
echo.
pause
