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

echo Debug: JJBOT_DIR = %JJBOT_DIR%
echo Debug: Creating PowerShell script...

REM Create a temporary PowerShell script with proper escaping
(
echo $ErrorActionPreference = 'Stop'
echo try {
echo     $WshShell = New-Object -ComObject WScript.Shell
echo     $Desktop = [Environment]::GetFolderPath('Desktop'^)
echo     $ShortcutPath = Join-Path $Desktop 'JJ-Bot.lnk'
echo     $Shortcut = $WshShell.CreateShortcut($ShortcutPath^)
echo     $Shortcut.TargetPath = '%JJBOT_DIR%\JJ-Bot.vbs'
echo     $Shortcut.WorkingDirectory = '%JJBOT_DIR%'
echo     $Shortcut.IconLocation = '%JJBOT_DIR%\assets\jjbot.ico'
echo     $Shortcut.Description = 'JJ-Bot Autonomous Trading Dashboard'
echo     $Shortcut.Save(^)
echo     Write-Host "Shortcut created at: $ShortcutPath"
echo } catch {
echo     Write-Host "Error: $_"
echo     exit 1
echo }
) > "%TEMP%\create_shortcut.ps1"

echo Debug: Running PowerShell script...
echo.

REM Run the PowerShell script and show output
powershell -ExecutionPolicy Bypass -File "%TEMP%\create_shortcut.ps1"
set PS_EXIT=%ERRORLEVEL%

echo.
echo Debug: PowerShell exit code = %PS_EXIT%

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
    echo.
    echo ERROR: Failed to create shortcut
    echo.
    echo Trying alternative method...

    REM Alternative: Use PowerShell directly with simpler syntax
    powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\JJ-Bot.lnk'); $s.TargetPath = '%JJBOT_DIR%\JJ-Bot.vbs'; $s.WorkingDirectory = '%JJBOT_DIR%'; $s.IconLocation = '%JJBOT_DIR%\assets\jjbot.ico'; $s.Save()"

    if exist "%USERPROFILE%\Desktop\JJ-Bot.lnk" (
        echo.
        echo ========================================
        echo Desktop shortcut created successfully!
        echo ========================================
    ) else (
        echo.
        echo Both methods failed. Please create shortcut manually:
        echo   1. Right-click on Desktop
        echo   2. New ^> Shortcut
        echo   3. Location: %JJBOT_DIR%\JJ-Bot.vbs
        echo   4. Name: JJ-Bot
    )
)

echo.
pause
