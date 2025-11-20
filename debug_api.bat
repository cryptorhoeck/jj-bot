@echo off
REM Debug API Server - Opens in new window
echo Opening API Server in new window for debugging...
start "JJ-Bot API Server (Debug)" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && cd glue\api && python main.py"
echo API Server window opened. Check the new terminal for output.
