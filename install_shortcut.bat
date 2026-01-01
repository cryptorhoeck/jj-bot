@echo off
REM ============================================
REM JJ-Bot Desktop Shortcut Installer
REM Creates a desktop shortcut for JJ-Bot
REM ============================================

echo Installing JJ-Bot desktop shortcut...
echo.

REM Get the current directory
set "JJBOT_DIR=%~dp0"
set "JJBOT_DIR=%JJBOT_DIR:~0,-1%"

REM Create shortcut using PowerShell
powershell -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; ^
   $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\JJ-Bot.lnk'); ^
   $Shortcut.TargetPath = '%JJBOT_DIR%\JJ-Bot.vbs'; ^
   $Shortcut.WorkingDirectory = '%JJBOT_DIR%'; ^
   $Shortcut.IconLocation = '%JJBOT_DIR%\assets\jjbot.ico'; ^
   $Shortcut.Description = 'JJ-Bot Autonomous Trading Dashboard'; ^
   $Shortcut.Save()"

if errorlevel 1 (
    echo ERROR: Failed to create shortcut
    pause
    exit /b 1
)

echo.
echo ========================================
echo Desktop shortcut created successfully!
echo ========================================
echo.
echo You can now launch JJ-Bot from your desktop.
echo.
echo The shortcut will:
echo   1. Start the API server
echo   2. Start the dashboard server
echo   3. Open the app in standalone mode
echo.
pause
