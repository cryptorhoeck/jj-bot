@echo off
echo Applying fixes...

REM Fix 1: Create data directory
if not exist data mkdir data
echo. > data\.gitkeep

REM Fix 2: Update sim_trader.py
powershell -Command "(Get-Content 'glue\api\sim_trader.py') -replace 'def init_database\(\):\s+\"\"\"Initialize the trades database\"\"\"\s+conn = sqlite3.connect\(DB_PATH\)', 'def init_database():`n    \"\"\"Initialize the trades database\"\"\"`n    # Ensure data directory exists`n    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)`n`n    conn = sqlite3.connect(DB_PATH)' | Set-Content 'glue\api\sim_trader.py'"

REM Fix 3: Update main.py
powershell -Command "$content = Get-Content 'glue\api\main.py' -Raw; $content = $content -replace 'simulator_process = subprocess\.Popen\(\s+\[sys\.executable, sim_trader_path\],\s+stdout=subprocess\.PIPE,\s+stderr=subprocess\.PIPE,\s+cwd=project_root\s+\)', '# On Windows, open simulator in new console window so output is visible`n        # On Linux, output will go to current terminal`n        import platform`n        if platform.system() == ''Windows'':`n            simulator_process = subprocess.Popen(`n                [sys.executable, sim_trader_path],`n                creationflags=subprocess.CREATE_NEW_CONSOLE,`n                cwd=project_root`n            )`n        else:`n            simulator_process = subprocess.Popen(`n                [sys.executable, sim_trader_path],`n                cwd=project_root`n            )'; Set-Content 'glue\api\main.py' -Value $content"

REM Fix 4: Update App.jsx
powershell -Command "$content = Get-Content 'dashboard\jj-dashboard\src\App.jsx' -Raw; $content = $content -replace 'const interval = setInterval\(\(\) => \{\s+fetchSummary\(\);\s+checkSimulatorStatus\(\);', 'const interval = setInterval(() => {`n      fetchTrades();      // Refresh trades list`n      fetchSummary();`n      fetchMarketData();  // Refresh market data`n      checkSimulatorStatus();'; Set-Content 'dashboard\jj-dashboard\src\App.jsx' -Value $content"

echo Fixes applied!
echo Now run: git status
pause