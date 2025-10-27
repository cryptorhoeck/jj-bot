# Windows Setup Instructions

## Step 1: Create Project Structure
```
mkdir jj-bot-windows
cd jj-bot-windows
mkdir dashboard modules services glue data logs
mkdir dashboard\jj-dashboard
mkdir modules\data_feed modules\strategies modules\utils
mkdir services\trading
mkdir glue\api
```

## Step 2: Python Setup
```
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn aiofiles pandas numpy requests python-dotenv websocket-client pydantic
```

## Step 3: React Setup
```
cd dashboard\jj-dashboard
npm init vite@latest . -- --template react
npm install
```

## Step 4: Create Start Script (start_all.bat)
```batch
@echo off
echo Starting JJ-Bot Trading System...

REM Start API
start "JJ-Bot API" cmd /k "cd glue\api && ..\..\venv\Scripts\python.exe main.py"

REM Start Dashboard
start "JJ-Bot Dashboard" cmd /k "cd dashboard\jj-dashboard && npm run dev"

echo.
echo JJ-Bot Started!
echo API: http://127.0.0.1:8000
echo Dashboard: http://localhost:5173
```

## Step 5: File Placement
Place the retrieved files in these locations:
- main.py → glue\api\
- service_endpoints.py → glue\api\
- manager_v2.py → services\
- simulator_service.py → services\trading\
- enhanced_feed.py → modules\data_feed\
- App.jsx → dashboard\jj-dashboard\src\
- ControlPanel.jsx → dashboard\jj-dashboard\src\
```

### **3. Create `FILE_CONTENTS_NEEDED.txt`**
```
CRITICAL FILES NEEDED FROM UBUNTU SERVER

The user needs to retrieve these files from their Ubuntu server at ~/jj-bot/

Backend Files:
1. glue/api/main.py - Main API server
2. glue/api/service_endpoints.py - Service management endpoints
3. services/manager_v2.py - Service orchestrator
4. services/trading/simulator_service.py - Trading simulator
5. modules/data_feed/enhanced_feed.py - Market data fetcher

Frontend Files:
6. dashboard/jj-dashboard/src/App.jsx - Main React component
7. dashboard/jj-dashboard/src/ControlPanel.jsx - Service control panel

Configuration:
8. dashboard/jj-dashboard/vite.config.js - Vite configuration

To retrieve from Ubuntu:
1. SSH into Ubuntu server
2. Navigate to ~/jj-bot
3. Copy each file content or use SCP/SFTP to download
4. Provide these to Claude Code for recreation on Windows