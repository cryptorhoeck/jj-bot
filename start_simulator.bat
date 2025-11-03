@echo off
echo ========================================
echo JJ-Bot Trade Simulator
echo ========================================
echo.

REM Activate venv if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run simulator
python glue\api\sim_trader.py

echo.
echo ========================================
echo Simulator stopped
echo ========================================
pause
