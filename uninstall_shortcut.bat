@echo off
REM ============================================
REM JJ-Bot Desktop Shortcut Uninstaller
REM Removes the desktop shortcut
REM ============================================

echo Removing JJ-Bot desktop shortcut...

del "%USERPROFILE%\Desktop\JJ-Bot.lnk" 2>nul

if exist "%USERPROFILE%\Desktop\JJ-Bot.lnk" (
    echo ERROR: Failed to remove shortcut
    pause
    exit /b 1
)

echo.
echo Desktop shortcut removed successfully!
echo.
pause
