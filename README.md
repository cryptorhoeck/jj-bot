# JJ-Bot - Cryptocurrency Trading System

A full-featured cryptocurrency trading bot with paper trading, real-time market data, and a modern web dashboard.

**Platform:** Windows 10/11
**Status:** ✅ Ready for Production
**Version:** 2.3.0

---

## 🚀 Quick Start (Windows)

### First Time Setup

1. **Prerequisites**
   - Python 3.8+ ([Download](https://www.python.org/downloads/))
   - Node.js 16+ ([Download](https://nodejs.org/))

2. **Clone and Setup**
   ```cmd
   git clone https://github.com/cryptorhoeck/jj-bot.git
   cd jj-bot
   setup_windows.bat
   ```
   *Wait 5-10 minutes for installation*

3. **Start JJ-Bot**
   ```cmd
   start_all.bat
   ```

4. **Open Dashboard**
   - Browser: http://localhost:5173
   - API Docs: http://127.0.0.1:8000/docs

---

## 📁 Project Structure

```
jj-bot/
├── glue/api/              # FastAPI backend server
│   ├── main.py            # Main API (port 8000)
│   ├── engine.py          # Trading engine
│   └── service_endpoints.py
│
├── services/              # Service management
│   ├── manager_v2.py      # Service orchestrator
│   ├── base/              # Base service classes
│   └── trading/           # Trading services
│
├── dashboard/             # React frontend
│   └── jj-dashboard/      # Vite + React app (port 5173)
│       ├── src/
│       │   ├── App.jsx
│       │   └── ControlPanel.jsx
│       └── package.json
│
├── modules/               # Trading modules
│   ├── data_feed/         # Market data fetcher
│   ├── strategy/          # Trading strategies
│   └── risk/              # Risk management
│
├── data/                  # Runtime data (gitignored)
│   ├── trades.db          # Trade history
│   └── jjbot.db           # Service state
│
├── docs/                  # Documentation
│   ├── QUICKSTART_WINDOWS.md
│   └── WINDOWS_MIGRATION_COMPLETE.md
│
├── tests/                 # Test files
│
├── setup_windows.bat      # One-time setup
├── start_all.bat          # Start system
├── stop_all.bat           # Stop system
└── requirements.txt       # Python dependencies
```

---

## ✨ Features

### Working Features ✅
- ✅ **Web Dashboard** - Modern React interface with 4 tabs
- ✅ **Real-Time Market Data** - Live prices for top 20 cryptocurrencies via CoinGecko (Canada-compatible)
- ✅ **WebSocket Updates** - Real-time price, signal, and trade notifications
- ✅ **Paper Trading** - Simulated trading without real money
- ✅ **Service Management** - Start/stop 5 microservices
- ✅ **Strategy Engine** - Automated trading signal generation with technical indicators
- ✅ **Backtesting Framework** - Test strategies on historical data
- ✅ **Trade History** - View and export trades to CSV
- ✅ **Dark/Light Mode** - Theme switcher
- ✅ **Live Connection Status** - Real-time connection indicator

### Dashboard Tabs
1. **Overview** - System status and quick stats
2. **Market** - Live crypto prices (20 coins)
3. **Control Panel** - Service management (5 services)
4. **Trades** - Trade history and export

### Services
1. **Trade Simulator** - Paper trading engine
2. **Market Feed** - Real-time market data fetcher (CoinGecko API)
3. **Strategy Engine** - Technical analysis and signal generation (RSI, SMA, MACD, Bollinger Bands)
4. **Analytics Engine** - Trading analytics and performance metrics
5. **Trading Bot** - Automated trading with risk management (paper mode)

---

## 🎮 Usage

### Daily Workflow

**Morning:**
```cmd
cd jj-bot
start_all.bat
```

**During the Day:**
- Monitor prices in Market tab
- Start/stop services in Control Panel
- View trades in Trades tab

**Evening:**
- Export trades (CSV)
- Close both command windows or run `stop_all.bat`

---

## 🌐 URLs

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:5173 | Main web interface |
| API | http://127.0.0.1:8000 | Backend REST API |
| API Docs | http://127.0.0.1:8000/docs | Interactive API documentation |

---

## 📚 API Endpoints

### Market Data
```
GET  /api/market/live      - Top 20 crypto prices (CoinGecko)
GET  /api/market/prices    - Market price summary
```

### Trading
```
GET  /api/trades           - Recent trades
GET  /api/summary          - Trading summary & stats
```

### Services
```
GET  /api/services/list                  - List all services
POST /api/services/{name}/start          - Start a service
POST /api/services/{name}/stop           - Stop a service
GET  /api/services/{name}/status         - Service status
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
POST /api/data/clear                     - Clear all trade data
```

### WebSocket
```
WS   /ws                                 - WebSocket endpoint for real-time updates
GET  /api/websocket/stats                - WebSocket connection statistics
```

### Backtesting
```
POST /api/backtest/load-data             - Load historical price data
POST /api/backtest/run                   - Run backtest with configuration
GET  /api/backtest/results               - Get backtest results
GET  /api/backtest/summary               - Get formatted backtest summary
POST /api/backtest/generate-sample-data  - Generate sample data for testing
```

---

## 🔧 Configuration

### Python Dependencies
See `requirements.txt`:
- FastAPI - Web framework
- Uvicorn - ASGI server
- Pandas - Data analysis
- Requests - HTTP client
- psutil - Process management

### Node.js Dependencies
See `dashboard/jj-dashboard/package.json`:
- React 19 - UI framework
- Vite - Build tool
- Axios - HTTP client
- Recharts - Charting library
- TailwindCSS - Styling

---

## 🛠️ Development

### Running Tests
```cmd
cd tests
python test_real_services.py
python final_system_test.py
```

### Project Commands
```cmd
setup_windows.bat    # Install all dependencies
start_all.bat        # Start API + Dashboard
stop_all.bat         # Stop all processes
```

### Directory Locations
- **API Server:** `glue/api/main.py`
- **Dashboard:** `dashboard/jj-dashboard/`
- **Services:** `services/manager_v2.py`
- **Database:** `data/` (created at runtime)

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART_WINDOWS.md](docs/QUICKSTART_WINDOWS.md) | Step-by-step Windows guide |
| [WINDOWS_MIGRATION_COMPLETE.md](docs/WINDOWS_MIGRATION_COMPLETE.md) | Technical migration details |
| [MIGRATION_SUMMARY.md](docs/MIGRATION_SUMMARY.md) | Complete change summary |
| [CLEANUP_PLAN.md](CLEANUP_PLAN.md) | Directory restructure plan |

---

## 🐛 Troubleshooting

### Python not found
```cmd
python --version
```
If error: Install from https://python.org (check "Add to PATH")

### Node.js not found
```cmd
node --version
```
If error: Install from https://nodejs.org

### Port already in use
```cmd
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

### Dashboard won't load
1. Wait 15 seconds after starting
2. Check both windows are open
3. Try http://localhost:5173 in browser
4. Refresh with Ctrl+F5

### Services won't start
1. Ensure API is running (port 8000)
2. Check API window for errors
3. Restart: `stop_all.bat` then `start_all.bat`

---

## 🔐 Security

- **Local Only** - Runs on localhost, no external access
- **Paper Trading** - No real money involved
- **No Auth** - Single user system
- **Data Privacy** - All data stored locally in `/data`

---

## 🚧 Future Enhancements

- [ ] Real exchange API integration (Kraken, Coinbase - Canada-compatible)
- [ ] Database backend (PostgreSQL/MongoDB)
- [ ] User authentication system
- [ ] Advanced charting and indicators
- [x] **Backtesting framework** ✅ **DONE v2.3**
- [ ] Multi-user support
- [ ] Mobile responsive design
- [x] **WebSocket live updates** ✅ **DONE v2.3**
- [ ] Trading strategies editor
- [x] **Performance analytics** ✅ **DONE v2.3**

---

## 📊 System Requirements

**Minimum:**
- Windows 10 or 11
- Python 3.8+
- Node.js 16+
- 4GB RAM
- 2GB free disk space

**Recommended:**
- Windows 11
- Python 3.11+
- Node.js 20+
- 8GB RAM
- 5GB free disk space
- SSD for better performance

---

## 📝 License

Private project. All rights reserved.

---

## 🙏 Credits

- **CoinGecko API** - Free crypto market data
- **FastAPI** - Modern Python web framework
- **React** - UI library
- **Vite** - Frontend build tool

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review documentation in `/docs`
3. Check API documentation at http://127.0.0.1:8000/docs

---

**Built with Claude Code** 🤖
**Last Updated:** October 31, 2025
**Version:** 2.3.0
**Status:** Production Ready ✅

---

## 🆕 What's New in v2.3

### WebSocket Real-Time Updates
- Live price updates without polling
- Instant trading signal notifications
- Real-time trade execution alerts
- Connection status indicator in dashboard
- Auto-reconnect on disconnect

### Backtesting Framework
- Test strategies on historical data
- Advanced performance metrics (Win rate, Profit factor, Sharpe ratio, Max drawdown)
- Configurable commission and slippage
- Position sizing controls
- Sample data generation for testing
- API endpoints for automated backtesting

### Strategy Engine Service
- Automated technical analysis (RSI, SMA, MACD, Bollinger Bands)
- Real-time signal generation
- Configurable strategy parameters
- Service management through dashboard

### Canada-Compatible Market Data
- Uses CoinGecko API (no geographic restrictions)
- Works from anywhere including Canada
- No Binance or restricted exchanges required
- Free tier available for development
