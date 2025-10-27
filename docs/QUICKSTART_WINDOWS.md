# JJ-Bot Quick Start Guide (Windows)

## 🚀 Get Started in 3 Steps

### Prerequisites
- ✅ Python 3.8+ (Download: https://www.python.org/downloads/)
- ✅ Node.js 16+ (Download: https://nodejs.org/)

### Step 1: Setup (First Time Only)
```cmd
setup_windows.bat
```
Wait for installation to complete (~2-5 minutes)

### Step 2: Start JJ-Bot
```cmd
start_all.bat
```
Two windows will open:
- **API Server** on port 8000
- **Dashboard** on port 5173

### Step 3: Access Dashboard
Open your browser to: **http://localhost:5173**

---

## 🎮 Using JJ-Bot

### Dashboard Tabs

#### 📊 Overview Tab
- System status
- Active services count
- Recent trades summary
- Quick stats

#### 💹 Market Tab
- Live prices for top 20 cryptocurrencies
- 24-hour price changes
- Real-time updates from CoinGecko API

#### ⚙️ Control Panel Tab
- **4 Services Available:**
  1. Trade Simulator - Paper trading engine
  2. Market Feed - Real-time market data
  3. Analytics Engine - Trading analytics
  4. Trading Bot - Automated trading (paper mode)

- **Start/Stop Services:** Click the green/red buttons
- **Service Status:** Running (green) / Stopped (gray)

#### 📈 Trades Tab
- View recent trades
- Trade history
- Export to CSV

### Common Tasks

**Start Trading Simulator:**
1. Go to Control Panel tab
2. Click "Start" on Trade Simulator card
3. Watch trades appear in Trades tab

**View Live Market Data:**
1. Go to Market tab
2. See real-time prices for 20 cryptos
3. Prices update automatically

**Export Trade History:**
1. Go to Trades tab
2. Click "Export CSV" button
3. Save file to your computer

---

## 🛠️ Stopping JJ-Bot

**Option 1:** Close both command windows (API and Dashboard)

**Option 2:** Run the stop script:
```cmd
stop_all.bat
```

---

## 📁 Project Structure

```
jj-bot/
├── setup_windows.bat       ← Run this first
├── start_all.bat           ← Run this to start
├── stop_all.bat            ← Run this to stop
├── glue/api/               ← Backend API
├── dashboard/jj-dashboard/ ← React frontend
├── services/               ← Trading services
├── data/                   ← Database & JSON files
└── logs/                   ← Log files
```

---

## 🔧 Troubleshooting

### "Python not found"
1. Install Python from https://www.python.org/downloads/
2. ✅ Check "Add Python to PATH" during installation
3. Restart Command Prompt
4. Run `python --version` to verify

### "Node.js not found"
1. Install Node.js from https://nodejs.org/
2. Restart Command Prompt
3. Run `node --version` to verify

### "Port already in use"
**Port 8000 conflict:**
```cmd
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

**Port 5173 conflict:**
```cmd
netstat -ano | findstr :5173
taskkill /PID <process_id> /F
```

### Dashboard won't load
1. Check if both windows are open
2. Wait 10-15 seconds for services to start
3. Try refreshing browser (Ctrl+F5)
4. Check API is running: http://127.0.0.1:8000

### Services won't start
1. Check API is running (port 8000)
2. Look for errors in API window
3. Restart using stop_all.bat then start_all.bat

---

## 🌐 URLs

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:5173 | Main web interface |
| API | http://127.0.0.1:8000 | Backend API |
| API Docs | http://127.0.0.1:8000/docs | Interactive API documentation |

---

## 📚 API Endpoints

### Market Data
```
GET  /api/market/live      - Top 20 crypto prices
GET  /api/market/prices    - Market prices
```

### Trading
```
GET  /api/trades           - Recent trades
GET  /api/summary          - Trading summary
```

### Services
```
GET  /api/services/list                  - List all services
POST /api/services/{name}/start          - Start service
POST /api/services/{name}/stop           - Stop service
GET  /api/services/{name}/status         - Get service status
```

### Simulator
```
GET  /api/simulator/status               - Check if running
POST /api/simulator/start                - Start simulator
POST /api/simulator/stop                 - Stop simulator
```

### Data Management
```
GET  /api/data/export                    - Export trades (CSV)
POST /api/data/clear                     - Clear all data
```

---

## ✨ Features

### Working Features ✅
- ✅ Web dashboard (4 tabs)
- ✅ Real-time market data (20 cryptos)
- ✅ Paper trading simulator
- ✅ Service management
- ✅ Trade history & export
- ✅ Dark/Light mode toggle
- ✅ Live price updates

### Coming Soon 🚧
- Database integration (currently JSON)
- User authentication
- Real exchange connections
- Advanced charting
- Backtesting

---

## 💡 Tips

1. **First Time Users:** Start with the Trade Simulator service only
2. **Monitoring:** Keep both windows visible to see logs
3. **Data Safety:** Export trades regularly using CSV export
4. **Performance:** Close unused browser tabs for best performance
5. **Development:** Use API docs at /docs for testing endpoints

---

## 🆘 Need Help?

1. **Check Logs:** Look at the command windows for error messages
2. **Restart:** Stop and start the system
3. **Reinstall:** Run `setup_windows.bat` again
4. **API Test:** Visit http://127.0.0.1:8000 (should show {"message": "JJ-Bot API v2.1"})

---

## 🔐 Security Notes

- System runs locally on your computer
- No external connections except CoinGecko API (read-only)
- No real trading - paper mode only
- No user data collected
- All data stored locally in `/data` folder

---

## 📝 Daily Workflow

### Morning Routine
```cmd
1. start_all.bat
2. Open http://localhost:5173
3. Check Market tab for overnight changes
4. Start Trade Simulator if needed
```

### During the Day
- Monitor active services in Control Panel
- Check trades in Trades tab
- Watch market prices in Market tab

### End of Day
```cmd
1. Export trades (CSV)
2. Stop all services
3. Run stop_all.bat or close windows
```

---

**Version:** 1.0.0
**Platform:** Windows 10/11
**Last Updated:** October 27, 2025
