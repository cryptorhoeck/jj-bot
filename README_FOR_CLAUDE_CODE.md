# JJ-Bot Trading System - Windows Migration Guide

## Current Situation
This project currently exists on Ubuntu Linux at ~/jj-bot
It needs to be recreated on Windows from scratch.

## Project Overview
- Cryptocurrency trading system with dashboard
- FastAPI backend + React frontend
- Service management for trading modules
- Paper trading simulator

## Linux File Structure to Recreate
```
jj-bot/
├── dashboard/jj-dashboard/     # React frontend (Vite)
├── modules/                    # Trading modules
│   ├── data_feed/              # Market data
│   ├── strategies/             # Trading strategies
│   └── utils/                  # Utilities
├── services/                   # Service management
│   ├── manager_v2.py          # Service orchestrator
│   └── trading/               # Trading services
├── glue/api/                  # FastAPI backend
├── data/                      # JSON storage
└── logs/                      # Application logs
```

## Key Components to Rebuild

### Backend (Python/FastAPI)
- Main API: glue/api/main.py
- Service endpoints: glue/api/service_endpoints.py
- Service manager: services/manager_v2.py
- Enhanced feed: modules/data_feed/enhanced_feed.py

### Frontend (React)
- Main app: dashboard/jj-dashboard/src/App.jsx
- Control panel: dashboard/jj-dashboard/src/ControlPanel.jsx
- Uses Vite as build tool
- No additional UI libraries (pure React)

## Windows Setup Requirements
1. Python 3.8+ 
2. Node.js 16+
3. Git Bash (for Unix-like commands)
4. VS Code or similar IDE

## Python Dependencies
```
fastapi==0.104.1
uvicorn==0.24.0
aiofiles==23.2.1
pandas==2.1.3
numpy==1.24.3
requests==2.31.0
python-dotenv==1.0.0
websocket-client==1.6.4
pydantic==2.5.0
```

## Features Working on Linux
✅ Dashboard with 4 tabs (Overview, Market, Control, Trades)
✅ Control panel with 4 services
✅ Market tab showing 20 cryptocurrencies
✅ Paper trading simulator
✅ Service start/stop functionality
✅ Dark/Light mode toggle

## Features Not Implemented
❌ Real trading (only paper)
❌ Service configurations (placeholders)
❌ Database storage (using JSON)
❌ User authentication
❌ Exchange API connections

## Critical Files to Request from Linux Server

Request these exact files from the Ubuntu server:

1. `/home/ren/jj-bot/glue/api/main.py`
2. `/home/ren/jj-bot/glue/api/service_endpoints.py`
3. `/home/ren/jj-bot/services/manager_v2.py`
4. `/home/ren/jj-bot/services/trading/simulator_service.py`
5. `/home/ren/jj-bot/modules/data_feed/enhanced_feed.py`
6. `/home/ren/jj-bot/dashboard/jj-dashboard/src/App.jsx`
7. `/home/ren/jj-bot/dashboard/jj-dashboard/src/ControlPanel.jsx`
8. `/home/ren/jj-bot/dashboard/jj-dashboard/vite.config.js`

## Windows-Specific Changes Needed
1. Replace Unix paths (/) with Windows paths (\)
2. Change `python3` commands to `python`
3. Remove `nohup` and `&` from start scripts
4. Use `start` command for background processes
5. Create .bat files instead of .sh scripts