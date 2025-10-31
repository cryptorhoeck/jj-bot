@echo off
echo ============================================================
echo JJ-Bot Startup Script
echo ============================================================
echo.

REM First, cleanup any old processes
echo Step 1: Cleaning up old processes...
python cleanup.py

echo.
echo Step 2: Starting JJ-Bot...
echo.

REM Start the GUI
python jj_bot_gui.py

echo.
echo JJ-Bot has stopped.
pause
