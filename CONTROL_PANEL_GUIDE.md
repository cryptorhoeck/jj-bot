# Control Panel & Services - User Guide

## ✅ What Was Fixed

### Issue 1: stop_all.bat Doesn't Stop Services ✅ FIXED
**Before:** Terminals stayed open, processes kept running
**After:** Properly kills all Python/Node processes and closes terminals

### Issue 2: Service Buttons Don't Update UI ✅ FIXED
**Before:** Clicking START/STOP showed no visual feedback
**After:** Button changes to "Starting..." then updates status after 1 second

### Issue 3: "Configure" Buttons Say "Coming Soon" ✅ FIXED
**Before:** Useless buttons showing "coming soon" alerts
**After:** Configure buttons removed (not needed yet)

### Issue 4: Services Start But Nothing Happens on Page ✅ FIXED
**Before:** Terminal showed activity but UI didn't update
**After:** UI updates after 1s delay + auto-refresh every 5s

---

## 🚀 How to Use (After Pulling Updates)

### Step 1: Pull Latest Fixes
```cmd
cd "E:\JJ Gorilla\jj-bot"
git pull origin claude/teleport-session-011cudon9uw41swpwz4jpdam-011CUeT3ujwmyYTHznhJitmu
```

### Step 2: Restart System
```cmd
stop_all.bat   # Now actually stops everything!
start_all.bat
```

### Step 3: Open Control Panel
```
http://localhost:5173
Click: Control Panel tab
```

---

## 📊 Understanding the Control Panel

### Service Grid Layout:
```
┌─────────────────────┬─────────────────────┐
│ 📊 Trade Simulator  │ 📈 Market Data Feed │
│ [Running] [STOP]    │ [Stopped] [START]   │
├─────────────────────┼─────────────────────┤
│ 🎯 Strategy Engine  │ 📉 Analytics Engine │
│ [Stopped] [START]   │ [Stopped] [START]   │
├─────────────────────┼─────────────────────┤
│ 🤖 Trading Bot      │                     │
│ [Stopped] [START]   │                     │
└─────────────────────┴─────────────────────┘
```

### Service Descriptions:

**📊 Trade Simulator**
- Generates simulated trades for testing
- Required for Trades tab to show data
- Safe to run (paper trading only)

**📈 Market Data Feed**
- Fetches real prices from CoinGecko every 30s
- Required for real-time price updates in Market tab
- Publishes price updates via WebSocket

**🎯 Strategy Engine** ← NEW!
- Analyzes market data using RSI, SMA, MACD, Bollinger Bands
- Generates BUY/SELL signals
- Shows signals in terminal and via WebSocket

**📉 Analytics Engine**
- Calculates win rate, Sharpe ratio, max drawdown
- Tracks performance metrics
- Updates every 60 seconds

**🤖 Trading Bot**
- Automated trading (DISABLED by default for safety)
- Only works in paper trading mode
- Requires manual enable in code

---

## 🎮 How to Start Services

### Option 1: Start Individual Services (Recommended)

1. **For Trades Data:**
   - Click START on "📊 Trade Simulator"
   - Wait 2 seconds
   - Button changes: [Stopped] → [⏳ Starting...] → [Running]
   - Go to Trades tab → Trades will appear in 30-60s

2. **For Real-Time Prices:**
   - Click START on "📈 Market Data Feed"
   - Wait 2 seconds
   - Market tab will update every 30s (no refresh needed!)

3. **For Trading Signals:**
   - Click START on "🎯 Strategy Engine"
   - Check API terminal for signals: `🎯 SIGNAL: BUY BTC | Reason: RSI oversold`
   - Signals appear in browser console too

### Option 2: Start All at Once

Click "🚀 Start All Services" button at bottom

**What happens:**
1. All stopped services start sequentially
2. 500ms delay between each
3. UI updates after all complete

---

## 🛑 How to Stop Services

### Option 1: Stop Individual Service
- Click STOP button on any running service
- Button changes: [Running] → [⏳ Stopping...] → [Stopped]
- Service stops after 500ms

### Option 2: Stop All Services
- Click "⏹ Stop All Services" button at bottom
- Confirms: "Stop all running services?"
- Stops all running services sequentially

### Option 3: Stop Entire System
```cmd
stop_all.bat   # Kills everything and closes terminals
```

---

## 🔍 Troubleshooting

### Problem: Button shows "Starting..." forever

**Cause:** Service failed to start (check API terminal for errors)

**Solution:**
1. Look at API terminal window for red errors
2. Common issues:
   - Port already in use
   - Missing dependencies
   - Database locked
3. Try: `stop_all.bat` then `start_all.bat`

---

### Problem: Service shows "Running" but not working

**Cause:** Service started but encountered an error

**Solution:**
1. Check API terminal for errors
2. Click STOP then START again
3. Check browser console (F12) for API errors

---

### Problem: UI doesn't update after clicking START

**Cause:** Network delay or API not responding

**Solution:**
1. Wait 2-3 seconds (there's a built-in delay)
2. Check if API is responding: http://127.0.0.1:8000
3. Manually refresh page (F5)
4. Services auto-refresh every 5 seconds

---

### Problem: stop_all.bat doesn't close terminals

**Cause:** Old version of script

**Solution:**
1. Make sure you pulled latest code
2. The new script has 4 steps:
   ```
   [1/4] Stopping API server...
   [2/4] Stopping Dashboard...
   [3/4] Stopping any remaining services...
   [4/4] Closing terminal windows...
   ```
3. If still not working, manually close terminals with X button

---

## 📈 Expected Behavior (When Working)

### After Starting Trade Simulator:
- Status changes to "Running" (green dot)
- Terminal shows: `🎰 Generated trade: BUY BTC...`
- Trades tab fills up every 10-30s
- No page refresh needed!

### After Starting Market Feed:
- Status changes to "Running"
- Terminal shows: `🌐 Market Feed Service starting...`
- Market tab updates every 30s
- Prices change without refresh

### After Starting Strategy Engine:
- Status changes to "Running"
- Terminal shows: `🧠 Strategy Engine Service starting...`
- Signals appear: `🎯 SIGNAL: BUY BTC | Reason: RSI oversold (28.5)`
- Browser console shows WebSocket messages

---

## 🎯 Recommended Service Setup

### For Basic Monitoring:
```
✅ Market Data Feed → START
✅ Trade Simulator → START
❌ Everything else → STOP
```

### For Full System:
```
✅ Market Data Feed → START
✅ Strategy Engine → START
✅ Analytics Engine → START
✅ Trade Simulator → START
❌ Trading Bot → STOP (keep disabled for safety)
```

---

## 💡 Tips

1. **Auto-refresh:** Services status auto-updates every 5 seconds
2. **Be patient:** Wait 1-2 seconds after clicking START/STOP
3. **Check terminal:** API window shows detailed logs
4. **Console logs:** Press F12 to see service API calls
5. **Stop properly:** Use `stop_all.bat` instead of X on terminals

---

## 🔄 Quick Reference

**Start Everything:**
```cmd
start_all.bat
```

**Stop Everything:**
```cmd
stop_all.bat
```

**Restart Service:**
```
1. Click STOP
2. Wait for status to change to "Stopped"
3. Click START
4. Wait for status to change to "Running"
```

**Check if Working:**
- Green dot = Running ✅
- Gray dot = Stopped ⚠️
- Button shows "Starting..." = In progress ⏳

---

Generated: 2025-10-31
Version: JJ-Bot v2.3
