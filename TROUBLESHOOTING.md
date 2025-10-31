# JJ-Bot Troubleshooting Guide

## 🔧 Quick Fixes for Common Issues

### Issue 1: Market Tab is Blank ✅ **FIXED**

**Problem:** Market tab shows nothing, no cryptocurrency prices.

**Cause:** API returns data as object, dashboard expected array.

**Solution:** Pull latest code:
```cmd
git pull origin claude/teleport-session-011cudon9uw41swpwz4jpdam-011CUeT3ujwmyYTHznhJitmu
```

Then refresh dashboard (Ctrl+F5) or restart with `start_all.bat`.

---

### Issue 2: No Trades Showing (Empty/Fake Data)

**Problem:** Trades tab is empty, or shows old fake data.

**Root Cause:** Simulator service hasn't been started yet!

**Solution:**

#### Step 1: Check if Simulator is Running
1. Open dashboard: http://localhost:5173
2. Go to **Control Panel** tab
3. Look at "Trade Simulator" row
4. If it shows "Stopped" → Continue to Step 2

#### Step 2: Start the Simulator
**Option A: Via Dashboard (Recommended)**
1. Go to Control Panel tab
2. Find "Trade Simulator"
3. Click the **Start** button
4. Wait 5-10 seconds
5. Go to Trades tab → You should see new trades appearing!

**Option B: Via API**
```
Visit: http://127.0.0.1:8000/docs
Find: POST /api/simulator/start
Click: "Try it out" → "Execute"
```

**Option C: Via Command (Legacy)**
```cmd
# This starts the simulator directly (old method)
cd glue\api
python -m sim_trader
```

#### Step 3: Verify Trades Are Generating
1. Go to **Trades** tab
2. Wait 30-60 seconds
3. Trades should start appearing
4. Refresh manually if needed (F5)

---

### Issue 3: Services Won't Start

**Problem:** Clicking "Start" on services does nothing.

**Possible Causes:**
1. API server not running
2. Database permissions issue
3. Port conflicts

**Solutions:**

#### Check 1: Is API Running?
```cmd
# Visit this URL in browser
http://127.0.0.1:8000

# Should show: {"message":"JJ-Bot API v2.1","status":"running"}
```

If not working:
```cmd
stop_all.bat
start_all.bat
```

#### Check 2: Check Terminal for Errors
Look at the **JJ-Bot API Server** window for error messages like:
- `Port 8000 is already in use` → Something else using port 8000
- `Permission denied` → Run as Administrator
- `Module not found` → Run `pip install -r requirements.txt`

#### Check 3: Test Services Endpoint
```cmd
# Visit in browser:
http://127.0.0.1:8000/api/services/list

# Should return list of 5 services
```

---

### Issue 4: WebSocket Not Connecting

**Problem:** Dashboard shows "🔴 Offline" instead of "🟢 Live"

**Solution:**
1. **Check API is running** (see above)
2. **Refresh dashboard** (Ctrl+F5)
3. **Check browser console** (F12) for WebSocket errors
4. **Restart everything:**
   ```cmd
   stop_all.bat
   start_all.bat
   ```

---

### Issue 5: Real-Time Updates Not Working

**Problem:** Prices don't update without refreshing page.

**Required Services:**
1. ✅ **Market Feed** - Must be running for price updates
2. ✅ **Strategy Engine** - For trading signals
3. ✅ **Simulator** - For trade generation

**How to Start All Services:**

1. Open dashboard: http://localhost:5173
2. Go to **Control Panel** tab
3. Click **Start** on:
   - Market Feed
   - Strategy Engine
   - Analytics Engine
   - Trade Simulator
4. Leave **Trading Bot** stopped (it's disabled for safety)

**Verify Real-Time:**
1. Go to **Market** tab
2. Watch prices - should update every 30 seconds
3. Check console (F12) for: `{type: 'price_update', ...}`

---

## 🧪 System Diagnostic Tool

Run this to check everything:

```cmd
diagnose.bat
```

This will test:
- ✅ API server status
- ✅ Market data endpoint
- ✅ Services status
- ✅ Dashboard status
- ✅ WebSocket endpoint

---

## 📊 Expected Behavior (When Working)

### Market Tab:
- Shows 20 cryptocurrencies
- Prices update every 30 seconds (if Market Feed is running)
- Shows 24h change percentage
- Data is REAL from CoinGecko API

### Trades Tab:
- Shows trades when Simulator is running
- New trades appear every 5-15 seconds
- Can export to CSV
- Shows P&L calculations

### Control Panel:
- Shows 5 services
- Can start/stop each service
- Status updates in real-time

### Overview Tab:
- Shows summary statistics
- Updates when new trades occur
- Shows recent activity (last 5 trades)

---

## 🚀 Complete Reset (If Nothing Works)

```cmd
# 1. Stop everything
stop_all.bat

# 2. Pull latest fixes
git pull origin claude/teleport-session-011cudon9uw41swpwz4jpdam-011CUeT3ujwmyYTHznhJitmu

# 3. Reinstall dependencies
pip install -r requirements.txt

# 4. Clear browser cache
# Press Ctrl+Shift+Delete → Clear cache

# 5. Start fresh
start_all.bat

# 6. Wait 10 seconds

# 7. Open dashboard
http://localhost:5173

# 8. Start services manually
# Go to Control Panel → Click "Start" on each service
```

---

## 📝 Checklist: "Nothing Works!"

Work through this checklist:

- [ ] API server terminal window is open and running
- [ ] Dashboard terminal window is open and running
- [ ] http://127.0.0.1:8000 returns JSON
- [ ] http://localhost:5173 shows dashboard
- [ ] Dashboard shows v2.3 in header
- [ ] WebSocket shows 🟢 Live
- [ ] At least one service is "Running" in Control Panel
- [ ] Waited 30+ seconds for data to populate

**If all checked:** You should have working features!

**If any unchecked:** Fix that issue first.

---

## 🆘 Still Not Working?

### Check Logs:

**API Terminal Window:**
- Look for errors in red
- Common: `Port in use`, `Module not found`, `Permission denied`

**Dashboard Terminal Window:**
- Look for `Compiled successfully`
- Should NOT have continuous errors

**Browser Console (F12):**
- Should see: `✅ WebSocket connected`
- Should NOT see: Constant 404 errors

### Common Error Messages:

#### `EADDRINUSE` or `Port 8000 already in use`
**Solution:**
```cmd
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill that process
taskkill /PID <number> /F

# Restart
start_all.bat
```

#### `Module not found: pandas`
**Solution:**
```cmd
pip install -r requirements.txt
```

#### `Failed to fetch` in dashboard
**Solution:**
- API server is not running
- Run `start_all.bat`
- Wait 10 seconds
- Refresh dashboard

---

## ✅ When Everything is Working

You should see:

1. **Dashboard Header:**
   - v2.3
   - 🟢 Live
   - Trades: (number increasing)

2. **Market Tab:**
   - 20 cryptocurrency tiles
   - Real prices (BTC around $40k-$60k)
   - Prices updating periodically

3. **Control Panel:**
   - 5 services listed
   - At least 1 showing "Running"
   - Start/Stop buttons working

4. **Trades Tab:**
   - Rows of trade data
   - Timestamps recent
   - P&L values changing

5. **Overview Tab:**
   - Total trades > 0
   - Recent activity list
   - Summary stats

---

**Generated:** 2025-10-31
**System:** JJ-Bot v2.3
