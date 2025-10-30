# Building JJ-Bot Native Windows Application

This guide explains how to build JJ-Bot as a native Windows application with two options:

1. **Single .exe file** (PyInstaller) - Recommended for distribution
2. **Installer** (Inno Setup) - Professional installer package

## Option 1: Build Single .exe File (Recommended)

### Prerequisites
- Python 3.8+ installed
- Git installed

### Step 1: Clone and Setup

```bash
git clone https://github.com/cryptorhoeck/jj-bot.git
cd jj-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Build with PyInstaller

```bash
pyinstaller jj_bot.spec
```

This creates `dist/JJ-Bot.exe` - a single executable file with everything bundled!

### Step 3: Test the Executable

```bash
dist\JJ-Bot.exe
```

The native Windows application will launch with:
- ✅ Professional tabbed interface
- ✅ System tray integration
- ✅ No dependencies needed
- ✅ Single .exe file

### Distribution

Simply distribute `dist/JJ-Bot.exe` to users. They can:
1. Download JJ-Bot.exe
2. Double-click to run
3. Done!

No Python, Node.js, or any other dependencies required!

---

## Option 2: Build Installer Package

For a more professional installation experience with Start Menu shortcuts, desktop icons, and auto-start options.

### Prerequisites
- Python 3.8+ installed
- **Inno Setup** - Download from: https://jrsoftware.org/download.php/is.exe

### Step 1: Install Inno Setup

1. Download Inno Setup from link above
2. Run the installer
3. Install with default options

### Step 2: Build the Installer

1. Open **Inno Setup Compiler**
2. File → Open → Select `installer.iss` from jj-bot directory
3. Build → Compile (or press **F9**)
4. Wait for compilation to complete

### Step 3: Find Your Installer

The installer will be created at:
```
jj-bot/installer_output/JJ-Bot-Setup.exe
```

### Distribution

Distribute `JJ-Bot-Setup.exe` to users. The installer will:
- ✅ Check for Python (prompts to download if missing)
- ✅ Create Python virtual environment
- ✅ Install all dependencies automatically
- ✅ Create Start Menu shortcuts
- ✅ Create Desktop shortcut (optional)
- ✅ Add to Windows startup (optional)
- ✅ Professional uninstaller

---

## What's Different from the Web Version?

### Old Approach (Web-based):
- ❌ Required Node.js + Python
- ❌ 1000s of npm files
- ❌ Vite dev server
- ❌ Browser + API server
- ❌ Multiple processes

### New Approach (Native):
- ✅ Python only (or single .exe)
- ✅ Native Windows GUI (PyQt6)
- ✅ System tray integration
- ✅ Professional Windows feel
- ✅ Single process
- ✅ Faster startup
- ✅ Smaller footprint

---

## Features

### Main Window Tabs:

1. **Dashboard** - Overview with key metrics
   - Total trades, Win rate, P&L
   - Profit factor, Active services
   - Recent activity log

2. **Market Data** - Live cryptocurrency prices
   - Real-time price updates
   - 24h price changes
   - Multiple symbols

3. **Trades** - Trade history table
   - All executed trades
   - Buy/Sell indicators
   - P&L per trade

4. **Analytics** - Performance statistics
   - Win rate, Profit factor
   - Sharpe ratio, Max drawdown
   - Average win/loss

5. **Settings** - Bot controls
   - Enable/disable trading bot
   - Paper trading mode
   - Service status

### System Tray:
- Click to show/hide window
- Right-click for quick menu
- Runs in background

---

## Troubleshooting

### PyInstaller Build Fails

**Error**: "Module not found"
```bash
pip install --upgrade -r requirements.txt
```

**Error**: "Spec file error"
- Check that jj_bot_gui.py exists
- Verify all folders (glue, modules, services) exist

### Installer Build Fails

**Error**: "Python not found"
- Install Python 3.8+ from python.org
- Add Python to PATH during installation

**Error**: "Source file not found"
- Ensure you're in the jj-bot directory
- Check that all folders exist (glue, modules, services, docs)

### Application Won't Start

**Check**: Database initialization
```bash
# Run manually first time
python
>>> from glue.api import engine
>>> engine.init_db()
```

**Check**: Port conflicts
- Ensure port 8000 is not in use
- Close other instances of JJ-Bot

---

## For Developers

### Running in Development Mode

```bash
python jj_bot_gui.py
```

### Making Changes

After modifying code:
1. Test with `python jj_bot_gui.py`
2. Rebuild with `pyinstaller jj_bot.spec`
3. Test the .exe in `dist/`

### Modifying the UI

Edit `jj_bot_gui.py`:
- `DashboardTab` - Dashboard layout
- `MarketDataTab` - Market data table
- `TradesTab` - Trade history
- `AnalyticsTab` - Performance stats
- `SettingsTab` - Settings page

### Adding Dependencies

1. Add to `requirements.txt`
2. Update `jj_bot.spec` hiddenimports if needed
3. Rebuild

---

## Technical Details

### Architecture:
- **Frontend**: PyQt6 native Windows GUI
- **Backend**: FastAPI (embedded)
- **Database**: SQLite
- **Services**: Trading modules (market feed, analytics, bot)

### Data Flow:
1. API runs in background thread
2. DataUpdater fetches from API every 2 seconds
3. Qt signals update UI
4. All real-time, no page refreshes

### Single .exe Size:
Approximately 50-80 MB (includes Python interpreter, PyQt6, FastAPI, all dependencies)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/cryptorhoeck/jj-bot/issues
- Check logs in application data directory

---

## License

MIT License - See LICENSE.txt
