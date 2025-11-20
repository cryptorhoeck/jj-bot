@echo off
REM Debug Dashboard - Opens in new window
echo Opening Dashboard in new window for debugging...
start "JJ-Bot Dashboard (Debug)" cmd /k "cd /d %~dp0dashboard\jj-dashboard && npm run dev"
echo Dashboard window opened. Check the new terminal for output.
