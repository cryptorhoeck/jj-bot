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

REM Create a temporary PowerShell script
echo $WshShell = New-Object -ComObject WScript.Shell > "%TEMP%\create_shortcut.ps1"
echo $Desktop = [Environment]::GetFolderPath('Desktop') >> "%TEMP%\create_shortcut.ps1"
echo $Shortcut = $WshShell.CreateShortcut("$Desktop\JJ-Bot.lnk") >> "%TEMP%\create_shortcut.ps1"
echo $Shortcut.TargetPath = '%JJBOT_DIR%\JJ-Bot.vbs' >> "%TEMP%\create_shortcut.ps1"
echo $Shortcut.WorkingDirectory = '%JJBOT_DIR%' >> "%TEMP%\create_shortcut.ps1"
echo $Shortcut.IconLocation = '%JJBOT_DIR%\assets\jjbot.ico' >> "%TEMP%\create_shortcut.ps1"
echo $Shortcut.Description = 'JJ-Bot Autonomous Trading Dashboard' >> "%TEMP%\create_shortcut.ps1"
echo $Shortcut.Save() >> "%TEMP%\create_shortcut.ps1"

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%TEMP%\create_shortcut.ps1"

REM Clean up
del "%TEMP%\create_shortcut.ps1" 2>nul

REM Check if shortcut was created
if exist "%USERPROFILE%\Desktop\JJ-Bot.lnk" (
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
) else (
    echo ERROR: Failed to create shortcut
)

pause
