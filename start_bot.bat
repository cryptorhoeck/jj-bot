@echo off
REM JJ-Bot Pro - Windows Startup Script
REM ====================================

title JJ-Bot Pro - Autonomous Trading System

echo.
echo  ========================================
echo   JJ-Bot Pro - Autonomous Trading System
echo  ========================================
echo.

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Check if config exists
if not exist "config\bot_config.json" (
    echo Configuration not found. Running setup wizard...
    echo.
    python setup_wizard.py
    if errorlevel 1 (
        echo Setup failed. Please check errors above.
        pause
        exit /b 1
    )
)

REM Create required directories
if not exist "logs" mkdir logs
if not exist "models" mkdir models

REM Check for command line arguments
if "%1"=="--setup" (
    python setup_wizard.py
    goto :eof
)

if "%1"=="--train" (
    echo Starting AI Training Mode...
    python -c "from jjbot_pro import BotConfig, JJBotPro; c=BotConfig.load(); c.mode='training'; bot=JJBotPro(c); bot.run()"
    goto :eof
)

if "%1"=="--dashboard" (
    echo Starting Dashboard...
    cd dashboard\jj-dashboard
    npm run dev
    goto :eof
)

REM Display current configuration
echo Current Configuration:
echo ----------------------
python -c "import json; c=json.load(open('config/bot_config.json')); print(f\"  Mode: {c['mode'].upper()}\"); print(f\"  Exchange: {c['exchange'].capitalize()}\"); print(f\"  Symbols: {', '.join(c['symbols'])}\"); print(f\"  Capital: ${c['initial_capital']:,.2f}\")"
echo.

REM Confirm before starting
echo Press any key to start the bot...
echo (Press Ctrl+C to cancel)
pause > nul

echo.
echo Starting JJ-Bot Pro...
echo.
echo ========================================
echo   Bot is running. Press Ctrl+C to stop.
echo ========================================
echo.

REM Run the bot
python jjbot_pro.py

echo.
echo Bot stopped.
pause
