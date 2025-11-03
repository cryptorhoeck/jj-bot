@echo off
echo ========================================
echo Applying JJ-Bot Fixes Automatically
echo ========================================
echo.

REM Create data directory
if not exist data mkdir data
if not exist data\.gitkeep type nul > data\.gitkeep
echo [1/4] Created data directory

REM Create start_simulator.bat
(
echo @echo off
echo echo ========================================
echo echo JJ-Bot Trade Simulator
echo echo ========================================
echo echo.
echo.
echo REM Activate venv if it exists
echo if exist venv\Scripts\activate.bat ^(
echo     call venv\Scripts\activate.bat
echo ^)
echo.
echo REM Run simulator
echo python glue\api\sim_trader.py
echo.
echo echo.
echo echo ========================================
echo echo Simulator stopped
echo echo ========================================
echo pause
) > start_simulator.bat
echo [2/4] Created start_simulator.bat

REM Fix sim_trader.py - add makedirs
powershell -Command "$file='glue\api\sim_trader.py'; $content=Get-Content $file -Raw; if($content -notmatch 'os.makedirs'){$content=$content -replace '(def init_database\(\):\s+\"\"\"Initialize the trades database\"\"\"\s+)(conn = sqlite3\.connect)', '$1# Ensure data directory exists`n    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)`n`n    $2'; Set-Content $file $content -NoNewline}"
echo [3/4] Fixed glue\api\sim_trader.py

REM Fix main.py - use batch wrapper for simulator
powershell -Command "$file='glue\api\main.py'; $content=Get-Content $file -Raw; $content=$content -replace 'simulator_process = subprocess\.Popen\(\s+\[sys\.executable, sim_trader_path\],\s+stdout=subprocess\.PIPE,\s+stderr=subprocess\.PIPE,\s+cwd=project_root\s+\)', '# On Windows, open simulator in new console window so output is visible`n        # On Linux, output will go to current terminal`n        import platform`n        if platform.system() == ''Windows'':`n            # Use batch file wrapper to keep window open on error`n            bat_path = os.path.join(project_root, \"\"start_simulator.bat\"\")`n            simulator_process = subprocess.Popen(`n                [bat_path],`n                creationflags=subprocess.CREATE_NEW_CONSOLE,`n                cwd=project_root,`n                shell=True`n            )`n        else:`n            simulator_process = subprocess.Popen(`n                [sys.executable, sim_trader_path],`n                cwd=project_root`n            )'; Set-Content $file $content -NoNewline}"
echo [4/4] Fixed glue\api\main.py

REM Fix App.jsx - add fetchTrades and fetchMarketData to polling
powershell -Command "$file='dashboard\jj-dashboard\src\App.jsx'; $content=Get-Content $file -Raw; $content=$content -replace 'const interval = setInterval\(\(\) => \{\s+fetchSummary\(\);\s+checkSimulatorStatus\(\);', 'const interval = setInterval(() => {`n      fetchTrades();      // Refresh trades list`n      fetchSummary();`n      fetchMarketData();  // Refresh market data`n      checkSimulatorStatus();'; Set-Content $file $content -NoNewline}"
echo [5/5] Fixed dashboard\jj-dashboard\src\App.jsx

echo.
echo ========================================
echo All fixes applied successfully!
echo ========================================
echo.
echo Next steps:
echo 1. git add .
echo 2. git commit -m "Apply all fixes automatically"
echo 3. git push origin claude/teleport-session-011cudon9uw41swpwz4jpdam-011CUeT3ujwmyYTHznhJitmu
echo 4. stop_all.bat
echo 5. start_all.bat
echo.
pause