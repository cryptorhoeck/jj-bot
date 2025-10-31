@echo off
echo ============================================================
echo JJ-Bot Startup Script
echo ============================================================
echo.

REM First, cleanup any old processes
echo Step 1: Cleaning up old processes...
python cleanup.py

echo.
echo Step 2: Checking dependencies...
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/update requirements
echo Installing dependencies...
pip install -q -r requirements.txt

echo.
echo Step 3: Starting JJ-Bot...
echo.

REM Start the GUI
python jj_bot_gui.py

echo.
echo JJ-Bot has stopped.
pause
