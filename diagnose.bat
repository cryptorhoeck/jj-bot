@echo off
REM JJ-Bot System Diagnostic
REM Run this to check system status

echo ========================================
echo JJ-Bot System Diagnostic
echo ========================================
echo.

echo [1/5] Checking if API server is responding...
curl -s http://127.0.0.1:8000/ >nul 2>&1
if %errorlevel%==0 (
    echo   ✓ API server is running on port 8000
) else (
    echo   ✗ API server is NOT responding
    echo   → Run start_all.bat first!
)
echo.

echo [2/5] Testing market data endpoint...
curl -s http://127.0.0.1:8000/api/market/live >temp_market.json 2>&1
if %errorlevel%==0 (
    echo   ✓ Market endpoint accessible
    type temp_market.json | findstr "status" >nul 2>&1
    if %errorlevel%==0 (
        echo   ✓ Market data returned
    ) else (
        echo   ✗ Market endpoint returned error
    )
) else (
    echo   ✗ Cannot reach market endpoint
)
if exist temp_market.json del temp_market.json
echo.

echo [3/5] Checking services status...
curl -s http://127.0.0.1:8000/api/services/list 2>nul
echo.
echo.

echo [4/5] Checking dashboard...
curl -s http://localhost:5173/ >nul 2>&1
if %errorlevel%==0 (
    echo   ✓ Dashboard is running on port 5173
) else (
    echo   ✗ Dashboard is NOT running
)
echo.

echo [5/5] Checking WebSocket...
echo   Testing WebSocket endpoint...
echo.

echo ========================================
echo Diagnosis Complete
echo ========================================
echo.
echo If you see errors above:
echo 1. Make sure start_all.bat is running
echo 2. Check both terminal windows for errors
echo 3. Try running: stop_all.bat then start_all.bat
echo.
pause
