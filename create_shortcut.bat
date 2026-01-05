@echo off
REM Creates a desktop shortcut for JJ-Bot with the gorilla icon
REM Run this once after setting up JJ-Bot

echo ========================================
echo Creating JJ-Bot Desktop Shortcut
echo ========================================
echo.

REM Get the current directory
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

REM Activate venv and generate the icon
echo [1/2] Generating gorilla icon...
call venv\Scripts\activate.bat
python generate_icon.py
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Could not generate icon, will use existing if available
)
echo.

REM Create shortcut using PowerShell
echo [2/2] Creating shortcut...
powershell -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$Shortcut = $WshShell.CreateShortcut('%PROJECT_ROOT%\JJ-Bot.lnk'); " ^
  "$Shortcut.TargetPath = '%PROJECT_ROOT%\start_all.bat'; " ^
  "$Shortcut.WorkingDirectory = '%PROJECT_ROOT%'; " ^
  "$Shortcut.IconLocation = '%PROJECT_ROOT%\assets\jjbot.ico'; " ^
  "$Shortcut.Description = 'JJ-Bot Trading System'; " ^
  "$Shortcut.WindowStyle = 7; " ^
  "$Shortcut.Save()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Shortcut created: %PROJECT_ROOT%\JJ-Bot.lnk
    echo.
    echo You can now:
    echo   1. Double-click JJ-Bot.lnk to start the application
    echo   2. Copy JJ-Bot.lnk to your Desktop
    echo   3. Pin it to your taskbar
    echo.
) else (
    echo Failed to create shortcut
)

REM Also copy to desktop if user wants
set /p COPY_TO_DESKTOP="Copy shortcut to Desktop? (y/n): "
if /i "%COPY_TO_DESKTOP%"=="y" (
    copy "%PROJECT_ROOT%\JJ-Bot.lnk" "%USERPROFILE%\Desktop\JJ-Bot.lnk"
    echo Copied to Desktop!
)

echo.
pause
