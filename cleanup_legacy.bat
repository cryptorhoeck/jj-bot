@echo off
REM JJ-Bot Legacy File Cleanup Script
REM Removes unused files from older versions

echo ========================================
echo JJ-Bot Legacy File Cleanup
echo ========================================
echo.
echo This will remove:
echo - Old standalone system (polished_system.py)
echo - Native GUI files (jj_bot_gui.py, jj_bot_tray.py)
echo - 8 old test files
echo - Old documentation (PR_DESCRIPTION.md, BUILD.md, etc.)
echo - Old scripts (cleanup.py, cleanup.bat, start.bat)
echo.
echo Current files will be KEPT:
echo - All service files (5 services)
echo - Current tests (5 files)
echo - README, requirements.txt
echo - start_all.bat, stop_all.bat
echo.

set /p confirm="Continue with cleanup? (y/n): "
if /i not "%confirm%"=="y" (
    echo Cleanup cancelled.
    pause
    exit /b
)

echo.
echo Starting cleanup...
echo.

REM Remove legacy standalone system
if exist modules\polished_system.py (
    echo Removing modules\polished_system.py
    del modules\polished_system.py
)

REM Remove native GUI files
if exist jj_bot_gui.py (
    echo Removing jj_bot_gui.py
    del jj_bot_gui.py
)

if exist jj_bot_tray.py (
    echo Removing jj_bot_tray.py
    del jj_bot_tray.py
)

REM Remove old test files
echo Removing old test files...
if exist tests\test_enhancements.py del tests\test_enhancements.py
if exist tests\test_enterprise_complete.py del tests\test_enterprise_complete.py
if exist tests\test_enterprise_system.py del tests\test_enterprise_system.py
if exist tests\test_data_feed.py del tests\test_data_feed.py
if exist tests\test_data_feed_fixed.py del tests\test_data_feed_fixed.py
if exist tests\test_strategy.py del tests\test_strategy.py
if exist tests\test_risk.py del tests\test_risk.py
if exist tests\test_notifications.py del tests\test_notifications.py

REM Remove old documentation
echo Removing old documentation...
if exist PR_DESCRIPTION.md del PR_DESCRIPTION.md
if exist BUILD.md del BUILD.md
if exist BUILD_INSTALLER.md del BUILD_INSTALLER.md

REM Remove old cleanup scripts
if exist cleanup.py del cleanup.py
if exist cleanup.bat del cleanup.bat

REM Remove old start script
if exist start.bat del start.bat

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo Removed files:
echo   - 3 legacy Python modules
echo   - 8 old test files
echo   - 5 old documentation/script files
echo.
echo Your project is now cleaner and leaner!
echo.
echo Next steps:
echo 1. Run: git status
echo 2. Run: git add -A
echo 3. Run: git commit -m "Clean up legacy and unused files"
echo 4. Run: git push
echo.
pause
