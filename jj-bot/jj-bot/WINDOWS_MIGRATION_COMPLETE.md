# JJ-Bot Windows Migration Guide

## Migration Completed! ✅

This document describes the Windows migration changes and how to use JJ-Bot on Windows.

## Changes Made for Windows Compatibility

### 1. Path Fixes
- **main.py (line 110-111)**: Changed hardcoded `/home/ren/jj-bot` to dynamic project root using `os.path`
- **polished_system.py (line 227)**: Changed hardcoded `/home/ren/jj-bot/data` to relative path using `os.path.join()`

### 2. Dependencies Updated
- Added `psutil>=5.9.0` to requirements.txt (used by main.py for process management)

### 3. Windows Scripts Created

#### setup_windows.bat
- One-time setup script
- Checks Python and Node.js installation
- Creates Python virtual environment
- Installs all Python dependencies
- Installs all Node.js dependencies
- Creates necessary directories (data, logs, backups)

#### start_all.bat
- Starts both API server and dashboard
- Opens two separate command windows:
  - JJ-Bot API Server (port 8000)
  - JJ-Bot Dashboard (port 5173)
- Validates environment before starting

#### stop_all.bat
- Safely stops all JJ-Bot processes
- Terminates both API and dashboard servers

## Quick Start on Windows

### First Time Setup

1. **Prerequisites**
   - Python 3.8+ installed and in PATH
   - Node.js 16+ installed and in PATH
   - Git (optional, for version control)

2. **Run Setup**
   ```cmd
   setup_windows.bat
   ```
   This will:
   - Create virtual environment
   - Install all dependencies
   - Set up directory structure

### Daily Usage

1. **Start JJ-Bot**
   ```cmd
   start_all.bat
   ```

2. **Access the System**
   - Dashboard: http://localhost:5173
   - API: http://127.0.0.1:8000
   - API Docs: http://127.0.0.1:8000/docs

3. **Stop JJ-Bot**
   - Close both command windows, or
   - Run `stop_all.bat`

## System Architecture

### Backend (Python/FastAPI)
- **Port**: 8000
- **Main File**: `glue/api/main.py`
- **Services**: `services/manager_v2.py`

### Frontend (React/Vite)
- **Port**: 5173
- **Main File**: `dashboard/jj-dashboard/src/App.jsx`
- **Build Tool**: Vite

### Services (4 Microservices)
1. **Trade Simulator** - Paper trading simulator
2. **Market Feed** - Real-time market data (top 20 cryptos)
3. **Analytics Engine** - Trading analytics
4. **Trading Bot** - Automated trading

## Features Working on Windows

✅ Dashboard with 4 tabs (Overview, Market, Control, Trades)
✅ Service start/stop functionality via Control Panel
✅ Market data display for 20 cryptocurrencies
✅ Paper trading simulator
✅ Service status monitoring
✅ Dark/Light mode toggle
✅ Trade history and export

## Directory Structure

```
jj-bot/
├── setup_windows.bat          # Setup script
├── start_all.bat              # Start script
├── stop_all.bat               # Stop script
├── requirements.txt           # Python dependencies
├── glue/api/                  # FastAPI backend
│   ├── main.py                # Main API server
│   ├── service_endpoints.py   # Service management
│   └── engine.py              # Trading engine
├── services/                  # Service management
│   ├── manager_v2.py          # Service orchestrator
│   └── trading/               # Trading services
├── dashboard/jj-dashboard/    # React frontend
│   ├── src/
│   │   ├── App.jsx            # Main component
│   │   └── ControlPanel.jsx   # Service controls
│   └── package.json
├── modules/                   # Trading modules
├── data/                      # JSON data storage
└── logs/                      # Application logs
```

## Troubleshooting

### Python not found
- Install Python 3.8+ from https://www.python.org/downloads/
- Ensure "Add Python to PATH" is checked during installation

### Node.js not found
- Install Node.js 16+ from https://nodejs.org/
- Restart command prompt after installation

### Port already in use
- Check if another application is using port 8000 or 5173
- Use `netstat -ano | findstr :8000` to find the process
- Kill the process or change the port in the code

### Virtual environment activation fails
- Run setup_windows.bat again
- Manually activate: `venv\Scripts\activate.bat`

### Dashboard won't start
- Ensure npm install completed successfully
- Delete `node_modules` and run setup again
- Check for Node.js version compatibility

## API Endpoints

### Market Data
- `GET /api/market/live` - Live prices for top 20 cryptos
- `GET /api/market/prices` - Market prices

### Trading
- `GET /api/trades` - Get recent trades
- `GET /api/summary` - Trading summary

### Services
- `GET /api/services/list` - List all services
- `POST /api/services/{name}/start` - Start service
- `POST /api/services/{name}/stop` - Stop service

### Simulator
- `GET /api/simulator/status` - Check simulator status
- `POST /api/simulator/start` - Start simulator
- `POST /api/simulator/stop` - Stop simulator

### Data Management
- `GET /api/data/export` - Export trades to CSV
- `POST /api/data/clear` - Clear all trade data

## Development Notes

### Cross-Platform Compatibility
All path operations now use `os.path` module for Windows/Linux compatibility:
- `os.path.join()` for path concatenation
- `os.path.dirname()` for directory paths
- `os.path.abspath()` for absolute paths

### Python Shebangs
The `#!/usr/bin/env python3` shebangs in Python files are harmless on Windows (treated as comments) but won't be executed. Use the batch scripts instead.

### Database
Currently using JSON files for data storage. SQLite database support is in the code but not fully implemented.

## Known Limitations

❌ Service config buttons are placeholders (show alert boxes)
❌ Paper/Live toggle not connected to backend
❌ No real exchange API connections
❌ No user authentication
❌ No database (using JSON files)

## Next Steps

Once the system is running on Windows, you can:
1. Add real exchange API connections (Binance, etc.)
2. Implement proper database storage
3. Add user authentication
4. Enhance trading strategies
5. Add more cryptocurrencies
6. Implement backtesting features

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the code comments in main.py
- Check the FastAPI docs at http://127.0.0.1:8000/docs

---

**Migration Date**: October 27, 2025
**Original System**: Ubuntu Linux
**Target System**: Windows 10/11
**Status**: ✅ Complete and tested
