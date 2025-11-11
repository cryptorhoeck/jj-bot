#!/usr/bin/env python3

import os
import sys
import json
import math
import asyncio
from datetime import datetime, timedelta
import subprocess
import csv
from io import StringIO
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Try to import psutil, install if not available
try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

# Create FastAPI app
app = FastAPI(title="JJ-Bot API v2.1")

# Add CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import engine with proper path handling
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine
from service_endpoints import router as service_router
from backtest_endpoints import router as backtest_router
from simulator_config_endpoints import router as simulator_config_router
from strategy_config_endpoints import router as strategy_config_router
from enhanced_analytics_endpoints import router as enhanced_analytics_router
from websocket_manager import ws_manager

# Initialize database on startup
engine.init_db()
print("✅ Database initialized")

# Global state
simulator_process = None

# ===== ROOT ENDPOINT =====
@app.get("/")
async def root():
    return {"message": "JJ-Bot API v2.1", "status": "running"}

# ===== TRADES ENDPOINTS =====
@app.get("/api/trades")
async def get_trades(limit: int = 50):
    trades = engine.get_trades(limit=limit)
    return {"trades": trades}

@app.get("/api/summary")
async def get_summary():
    return engine.get_summary()

# ===== CONFIG ENDPOINTS =====
@app.get("/api/config")
async def get_config():
    return {
        "MAX_POSITION_SIZE": 1000,
        "MAX_DAILY_LOSS": 1000.0,
        "MAX_TRADES_PER_DAY": 20,
        "COOLDOWN_SECONDS": 60
    }

# ===== MARKET PRICES =====
@app.get("/api/market/prices")
async def get_market_prices():
    return {
        "BTCUSDT": {"price": 45000, "change_24h": 2.5},
        "ETHUSDT": {"price": 2500, "change_24h": -1.2},
        "BNBUSDT": {"price": 300, "change_24h": 0.8}
    }

# ===== SYSTEM HEALTH =====
@app.get("/api/system/health")
async def system_health():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# ===== SIMULATOR ENDPOINTS - THESE WILL WORK =====
@app.get("/api/simulator/status")
async def simulator_status():
    """Check if simulator is running"""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('sim_trader.py' in str(arg) for arg in cmdline):
                return {"running": True, "pid": proc.info['pid']}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"running": False}

@app.post("/api/simulator/start")
async def start_simulator():
    """Start the trade simulator"""
    global simulator_process
    
    # Check if already running
    status = await simulator_status()
    if status["running"]:
        return {"status": "already_running", "message": "Simulator is already running"}
    
    # Start the simulator
    try:
        # Use the project root directory (2 levels up from glue/api)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(project_root)
        sim_trader_path = os.path.join(project_root, "glue", "api", "sim_trader.py")

        # On Windows, open simulator in new console window so output is visible
        # On Linux, output will go to current terminal
        import platform
        if platform.system() == 'Windows':
            simulator_process = subprocess.Popen(
                [sys.executable, sim_trader_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=project_root
            )
        else:
            simulator_process = subprocess.Popen(
                [sys.executable, sim_trader_path],
                cwd=project_root
            )
        await asyncio.sleep(1)
        return {"status": "started", "message": "Trade simulator started successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to start simulator: {str(e)}"}

@app.post("/api/simulator/stop")
async def stop_simulator():
    """Stop the trade simulator"""
    stopped = False
    
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('sim_trader.py' in str(arg) for arg in cmdline):
                proc.terminate()
                stopped = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if stopped:
        return {"status": "stopped", "message": "Trade simulator stopped"}
    return {"status": "not_running", "message": "Simulator was not running"}

# ===== DATA MANAGEMENT ENDPOINTS =====
@app.get("/api/data/export")
async def export_data():
    """Export all trades as CSV"""
    trades = engine.get_trades(limit=10000)
    
    output = StringIO()
    if trades:
        fieldnames = ['timestamp', 'symbol', 'signal', 'last_price', 'vwap', 'pnl']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=trades_{timestamp}.csv"
        }
    )
    return response

@app.post("/api/data/clear")
async def clear_data():
    """Clear all trade data with backup"""
    import shutil
    
    # Backup database
    db_path = "data/jj_trades.db"
    if os.path.exists(db_path):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = f"{backup_dir}/jj_trades_backup_{timestamp}.db"
        shutil.copy2(db_path, backup_path)
    
    # Clear trades
    try:
        with engine.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM trades")
            conn.commit()
        return {"status": "cleared", "message": "Database cleared and backed up"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== DASHBOARD =====
@app.get("/dashboard")
@app.get("/dashboard/")
async def dashboard():
    return HTMLResponse("""
    <html>
    <head><title>JJ-Bot Dashboard</title></head>
    <body>
        <h1>JJ-Bot Dashboard</h1>
        <p>Access the React dashboard at: <a href="http://localhost:5173">http://localhost:5173</a></p>
    </body>
    </html>
    """)


# ===== REAL MARKET DATA FROM COINGECKO (FREE) =====
@app.get("/api/market/live")
async def get_market_live():
    """Get live market data for top 20 cryptos"""
    import requests

    try:
        # Top 20 cryptos (excluding stablecoins)
        coins = [
            "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
            "cardano", "dogecoin", "avalanche-2", "tron", "chainlink",
            "polkadot", "polygon", "wrapped-bitcoin", "shiba-inu",
            "litecoin", "bitcoin-cash", "uniswap", "stellar", "cosmos",
            "ethereum-classic"
        ]

        symbols = {
            "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
            "solana": "SOL", "ripple": "XRP", "cardano": "ADA",
            "dogecoin": "DOGE", "avalanche-2": "AVAX", "tron": "TRX",
            "chainlink": "LINK", "polkadot": "DOT", "polygon": "MATIC",
            "wrapped-bitcoin": "WBTC", "shiba-inu": "SHIB", "litecoin": "LTC",
            "bitcoin-cash": "BCH", "uniswap": "UNI", "stellar": "XLM",
            "cosmos": "ATOM", "ethereum-classic": "ETC"
        }

        # Fetch from CoinGecko
        ids = ",".join(coins)
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true"
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        # Format for frontend - return as dict keyed by symbol
        result = {}
        for coin_id in coins:
            if coin_id in data:
                symbol = symbols[coin_id]
                result[symbol.lower()] = {
                    "symbol": symbol,
                    "usd": data[coin_id].get("usd", 0),
                    "usd_24h_change": data[coin_id].get("usd_24h_change", 0),
                    "usd_market_cap": data[coin_id].get("usd_market_cap", 0),
                    "usd_24h_vol": data[coin_id].get("usd_24h_vol", 0),
                    "timestamp": datetime.now().isoformat()
                }

        return {"status": "success", "data": result}

    except Exception as e:
        # Return placeholder data if API fails - as dict
        return {
            "status": "error",
            "data": {
                "btc": {"symbol": "BTC", "usd": 45000, "usd_24h_change": 0, "timestamp": datetime.now().isoformat()},
                "eth": {"symbol": "ETH", "usd": 2500, "usd_24h_change": 0, "timestamp": datetime.now().isoformat()},
                "bnb": {"symbol": "BNB", "usd": 350, "usd_24h_change": 0, "timestamp": datetime.now().isoformat()}
            }
        }

# Include service endpoints
app.include_router(service_router)
app.include_router(backtest_router)
app.include_router(simulator_config_router)
app.include_router(strategy_config_router)
app.include_router(enhanced_analytics_router)

# ===== WEBSOCKET ENDPOINT =====
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    Broadcasts: price_update, trading_signal, trade_executed, etc.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()

            # Handle client requests
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/api/websocket/stats")
async def websocket_stats():
    """Get WebSocket manager statistics"""
    return ws_manager.get_stats()

if __name__ == "__main__":
    import uvicorn
    print("JJ-Bot API v2.1 starting...")
    print("API: http://127.0.0.1:8000")
    print("Dashboard: http://localhost:5173")
    uvicorn.run(app, host="127.0.0.1", port=8000)

