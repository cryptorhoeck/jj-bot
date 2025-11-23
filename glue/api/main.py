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
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Try to import psutil, install if not available
try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

# Import engine and managers (need these before lifespan)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine
from service_endpoints import router as service_router, service_manager
from backtest_endpoints import router as backtest_router
from simulator_config_endpoints import router as simulator_config_router
from strategy_config_endpoints import router as strategy_config_router
from enhanced_analytics_endpoints import router as enhanced_analytics_router
from symbol_management_endpoints import router as symbol_management_router
from learning_endpoints import router as learning_router
from market_data_endpoints import router as market_data_router
from indicators_endpoints import router as indicators_router
from streaming_endpoints import router as streaming_router
from ml_endpoints import router as ml_router
from analytics_endpoints import router as analytics_router
from alerts_endpoints import router as alerts_router
from execution_endpoints import router as execution_router
from bot_pro_endpoints import router as bot_pro_router
from websocket_manager import ws_manager

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("✅ Database initialized")
    engine.init_db()

    print("🚀 Starting auto-start services...")
    started = service_manager.start_auto_services()
    if started:
        print(f"✅ Auto-started services: {', '.join(started)}")
    else:
        print("ℹ️  No auto-start services configured")

    yield

    # Shutdown (add cleanup here if needed)
    print("👋 Shutting down API...")

# Create FastAPI app with lifespan
app = FastAPI(title="JJ-Bot API v2.1", lifespan=lifespan)

# Add CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import rate limiter
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from utils.rate_limiter import wait_for_rate_limit
except ImportError:
    # Fallback if utils not available
    def wait_for_rate_limit(*args, **kwargs):
        return True

# Import advanced analytics
try:
    from modules.advanced_analytics import AdvancedAnalytics
    import pandas as pd
    analytics_available = True
except ImportError:
    analytics_available = False

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

@app.get("/api/equity-curve")
async def get_equity_curve(starting_capital: float = 10000.0):
    """Get equity curve over time for portfolio visualization"""
    return {
        "equity_curve": engine.get_equity_curve(starting_capital),
        "starting_capital": starting_capital
    }

@app.get("/api/positions/open")
async def get_open_positions():
    """Get currently open trading positions with unrealized PnL"""
    return {
        "open_positions": engine.get_open_positions(),
        "count": len(engine.get_open_positions())
    }

@app.get("/api/risk/status")
async def get_risk_status():
    """Get current risk management status and limits"""
    try:
        # Import risk manager
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from modules.risk.risk_manager import risk_manager

        # Get current summary for equity and drawdown
        summary = engine.get_summary()

        return {
            "status": "success",
            "risk_status": risk_manager.get_risk_status(
                current_equity=summary.get("current_equity", 10000),
                current_drawdown=summary.get("max_drawdown", 0)
            ),
            "limits": {
                "max_risk_per_trade_pct": risk_manager.config.max_risk_per_trade * 100,
                "max_drawdown_pct": risk_manager.config.max_drawdown_pct * 100,
                "max_daily_loss": risk_manager.config.max_daily_loss,
                "max_open_positions": risk_manager.config.max_open_positions,
                "min_risk_reward_ratio": risk_manager.config.min_risk_reward_ratio
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/performance/stats")
async def get_performance_stats():
    """Get performance profiling statistics"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from modules.performance_profiler import profiler

        return profiler.get_stats(limit=30)
    except Exception as e:
        return {
            "error": str(e),
            "stats": []
        }

@app.get("/api/errors/recent")
async def get_recent_errors(limit: int = 50):
    """Get recent errors from error log"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from modules.error_recovery import get_recent_errors

        return {
            "errors": get_recent_errors(limit=limit),
            "count": len(get_recent_errors(limit=limit))
        }
    except Exception as e:
        return {
            "error": str(e),
            "errors": []
        }

@app.get("/api/analytics/advanced")
async def get_advanced_analytics():
    """Get advanced performance analytics"""
    if not analytics_available:
        return {
            "status": "unavailable",
            "message": "Advanced analytics module not available"
        }

    try:
        # Get trades
        trades = engine.get_trades(limit=10000)

        if not trades or len(trades) < 2:
            return {
                "status": "insufficient_data",
                "message": "Not enough trade data for analytics"
            }

        # Build equity curve from trades
        equity = [10000]  # Starting capital
        for trade in sorted(trades, key=lambda x: x.get('timestamp', '')):
            pnl = float(trade.get('pnl', 0))
            equity.append(equity[-1] + pnl)

        equity_curve = pd.Series(equity)

        # Calculate metrics
        analytics = AdvancedAnalytics(risk_free_rate=0.02)
        metrics = analytics.calculate_all_metrics(equity_curve, trades, periods_per_year=252)

        return {
            "status": "success",
            "metrics": {
                "returns": {
                    "total_return": metrics.total_return,
                    "annualized_return": metrics.annualized_return,
                    "average_return": metrics.average_return,
                },
                "risk": {
                    "volatility": metrics.volatility,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "sortino_ratio": metrics.sortino_ratio,
                    "calmar_ratio": metrics.calmar_ratio,
                },
                "drawdown": {
                    "max_drawdown": metrics.max_drawdown,
                    "max_drawdown_duration": metrics.max_drawdown_duration,
                    "current_drawdown": metrics.current_drawdown,
                },
                "trades": {
                    "total_trades": metrics.total_trades,
                    "winning_trades": metrics.winning_trades,
                    "losing_trades": metrics.losing_trades,
                    "win_rate": metrics.win_rate,
                    "profit_factor": metrics.profit_factor,
                    "average_win": metrics.average_win,
                    "average_loss": metrics.average_loss,
                    "largest_win": metrics.largest_win,
                    "largest_loss": metrics.largest_loss,
                    "expectancy": metrics.expectancy,
                }
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error calculating analytics: {str(e)}"
        }

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
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ===== BOT ENDPOINTS - Trading bot with learning =====
@app.get("/api/bot/status")
@app.get("/api/simulator/status")  # Keep old endpoint for compatibility
async def bot_status():
    """Check if trading bot is running"""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('sim_trader.py' in str(arg) for arg in cmdline):
                return {"running": True, "pid": proc.info['pid']}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"running": False}

@app.post("/api/bot/start")
@app.post("/api/simulator/start")  # Keep old endpoint for compatibility
async def start_bot():
    """Start the trading bot (learns and trades automatically)"""
    global simulator_process

    # Check if already running
    status = await bot_status()
    if status["running"]:
        return {"status": "already_running", "message": "Bot is already running"}

    # Start the bot
    try:
        # Use the project root directory (2 levels up from glue/api)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(project_root)
        sim_trader_path = os.path.join(project_root, "glue", "api", "sim_trader.py")

        # On Windows, open bot in new console window so output is visible
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
        return {"status": "started", "message": "Trading bot started successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to start bot: {str(e)}"}

@app.post("/api/bot/stop")
@app.post("/api/simulator/stop")  # Keep old endpoint for compatibility
async def stop_bot():
    """Stop the trading bot"""
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
        return {"status": "stopped", "message": "Trading bot stopped"}
    return {"status": "not_running", "message": "Bot was not running"}

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
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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


@app.post("/api/data/import")
async def import_data():
    """Import trades from CSV file"""
    from fastapi import File, UploadFile
    # Will be implemented with file upload
    return {"status": "not_implemented", "message": "Import functionality coming soon"}


@app.post("/api/data/archive")
async def archive_data():
    """Archive all trade data to timestamped backup"""
    import shutil

    try:
        db_path = "data/jj_trades.db"
        if not os.path.exists(db_path):
            return {"status": "error", "message": "No database to archive"}

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = "backups/archives"
        os.makedirs(backup_dir, exist_ok=True)
        archive_path = f"{backup_dir}/jj_trades_archive_{timestamp}.db"

        # Copy database
        shutil.copy2(db_path, archive_path)

        # Get trade count
        trades = engine.get_trades(limit=100000)
        trade_count = len(trades)

        return {
            "status": "archived",
            "message": f"Archived {trade_count} trades",
            "archive_path": archive_path,
            "trade_count": trade_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/data/backups")
async def list_backups():
    """List all available backups"""
    try:
        backup_dir = "backups"
        archive_dir = "backups/archives"

        backups = []

        # List regular backups
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith('.db'):
                    file_path = os.path.join(backup_dir, file)
                    size = os.path.getsize(file_path)
                    modified = os.path.getmtime(file_path)
                    backups.append({
                        "filename": file,
                        "type": "backup",
                        "size": size,
                        "modified": datetime.fromtimestamp(modified).isoformat(),
                        "path": file_path
                    })

        # List archives
        if os.path.exists(archive_dir):
            for file in os.listdir(archive_dir):
                if file.endswith('.db'):
                    file_path = os.path.join(archive_dir, file)
                    size = os.path.getsize(file_path)
                    modified = os.path.getmtime(file_path)
                    backups.append({
                        "filename": file,
                        "type": "archive",
                        "size": size,
                        "modified": datetime.fromtimestamp(modified).isoformat(),
                        "path": file_path
                    })

        # Sort by modified date (newest first)
        backups.sort(key=lambda x: x['modified'], reverse=True)

        return {
            "status": "success",
            "backups": backups,
            "total": len(backups)
        }
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
    """Get live market data using our market data infrastructure"""
    try:
        from modules.data import cached_market_data_service
        from services.streaming.market_stream_service import market_stream_service

        # Define supported symbols (top cryptocurrencies)
        symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC"]

        result = {}

        # First, try to get data from WebSocket stream if it's running
        if market_stream_service.running:
            stream_prices = market_stream_service.get_latest_prices()
            for symbol in symbols:
                if symbol in stream_prices and stream_prices[symbol]:
                    price_data = stream_prices[symbol]
                    result[symbol.lower()] = {
                        "symbol": symbol,
                        "name": symbol,  # Use symbol as name
                        "usd": price_data.get("price", 0),
                        "usd_24h_change": price_data.get("change_24h", 0),
                        "usd_market_cap": 0,  # Not available from stream
                        "usd_24h_vol": price_data.get("volume_24h", 0),
                        "image": "",
                        "timestamp": price_data.get("timestamp", datetime.now().isoformat())
                    }

            if result:
                print(f"✅ Fetched {len(result)} prices from WebSocket stream")
                return {"status": "success", "data": result, "count": len(result), "source": "websocket"}

        # Fallback: Get current prices from our market data service
        for symbol in symbols:
            try:
                price_result = cached_market_data_service.get_current_price(symbol, source='kraken')
                if price_result.get("success"):
                    result[symbol.lower()] = {
                        "symbol": symbol,
                        "name": symbol,
                        "usd": price_result.get("price", 0),
                        "usd_24h_change": 0,  # Calculate from recent data if needed
                        "usd_market_cap": 0,
                        "usd_24h_vol": price_result.get("volume", 0),
                        "image": "",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"⚠️  Failed to fetch {symbol}: {e}")
                continue

        if result:
            print(f"✅ Fetched {len(result)} prices from market data service")
            return {"status": "success", "data": result, "count": len(result), "source": "market_data_service"}

        # Last resort: Return error instead of misleading placeholder data
        raise Exception("No price data available from any source")

    except Exception as e:
        print(f"⚠️  Market data fetch failed: {e}")
        # Return error with clear message instead of fake prices
        return {
            "status": "error",
            "message": "Market data unavailable. Start WebSocket stream or check market data service.",
            "data": {},
            "count": 0,
            "error": str(e)
        }

# ===== HISTORICAL MARKET DATA ENDPOINTS =====

# Import market data service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from modules.data import market_data_service

@app.get("/api/market/ohlc/{symbol}")
async def get_ohlc_data(symbol: str, timeframe: str = "1h", source: str = "auto"):
    """
    Get OHLC candlestick data for a symbol
    Uses real APIs when available, falls back to realistic generated data

    Args:
        symbol: Crypto symbol (BTC, ETH) or stock ticker (AAPL, TSLA)
        timeframe: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
        source: 'kraken', 'yahoo', or 'auto' (auto-detect based on symbol)
    """
    try:
        # Auto-detect source
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'BNB']

        if source == "auto":
            source = "kraken" if symbol.upper() in crypto_symbols else "yahoo"

        # Try to get real data first
        result = None

        if source == "kraken":
            # Convert symbol to Kraken pair
            pair = market_data_service.standardize_kraken_pair(symbol)
            interval = market_data_service.convert_timeframe_to_kraken(timeframe)
            result = market_data_service.get_kraken_ohlc(pair, interval)
        else:
            # Yahoo Finance
            interval_str, range_str = market_data_service.convert_timeframe_to_yahoo(timeframe)
            result = market_data_service.get_yahoo_ohlc(symbol, interval_str, range_str)

        # If real data fails, generate realistic data based on current price
        if not result or not result.get("success"):
            # Use fallback prices directly (avoid circular dependency)
            price_map = {
                "BTC": 45000, "ETH": 2500, "SOL": 100, "BNB": 350,
                "XRP": 0.65, "ADA": 0.45, "DOGE": 0.08, "AVAX": 35,
                "DOT": 7.5, "MATIC": 0.85, "AAPL": 180, "TSLA": 250,
                "GOOGL": 140, "MSFT": 380, "AMZN": 150, "SPY": 450,
                "QQQ": 380, "DIA": 350
            }
            current_price = price_map.get(symbol.upper(), 100)

            # Generate realistic OHLC data
            num_candles_map = {
                "1m": 60, "5m": 72, "15m": 96, "30m": 96,
                "1h": 168, "4h": 180, "1d": 90, "1w": 52, "1M": 24
            }
            num_candles = num_candles_map.get(timeframe, 168)

            candles = market_data_service.generate_realistic_ohlc(current_price, timeframe, num_candles)

            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": candles,
                "count": len(candles),
                "source": "generated",
                "note": "Generated realistic data based on current market price"
            }

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/market/ticker/{symbol}")
async def get_ticker_data(symbol: str, source: str = "auto"):
    """
    Get current ticker/quote data for a symbol

    Args:
        symbol: Crypto symbol or stock ticker
        source: 'kraken', 'yahoo', or 'auto'
    """
    try:
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'BNB']

        if source == "auto":
            source = "kraken" if symbol.upper() in crypto_symbols else "yahoo"

        if source == "kraken":
            pair = market_data_service.standardize_kraken_pair(symbol)
            result = market_data_service.get_kraken_ticker([pair])
        else:
            result = market_data_service.get_yahoo_quote([symbol])

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/market/batch-ohlc")
async def get_batch_ohlc(symbols: str, timeframe: str = "1h", source: str = "auto"):
    """
    Get OHLC data for multiple symbols at once

    Args:
        symbols: Comma-separated symbols (e.g., "BTC,ETH,AAPL,TSLA")
        timeframe: Timeframe string
        source: Data source
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        results = {}

        for symbol in symbol_list:
            # Determine source for each symbol
            crypto_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'BNB']
            sym_source = "kraken" if symbol in crypto_symbols else "yahoo"

            if sym_source == "kraken":
                pair = market_data_service.standardize_kraken_pair(symbol)
                interval = market_data_service.convert_timeframe_to_kraken(timeframe)
                results[symbol] = market_data_service.get_kraken_ohlc(pair, interval)
            else:
                interval_str, range_str = market_data_service.convert_timeframe_to_yahoo(timeframe)
                results[symbol] = market_data_service.get_yahoo_ohlc(symbol, interval_str, range_str)

        return {"success": True, "data": results}

    except Exception as e:
        return {"success": False, "error": str(e)}

# Include service endpoints
app.include_router(service_router)
app.include_router(backtest_router)
app.include_router(simulator_config_router)
app.include_router(strategy_config_router)
app.include_router(enhanced_analytics_router)
app.include_router(symbol_management_router)
app.include_router(learning_router)
app.include_router(market_data_router)
app.include_router(indicators_router)
app.include_router(streaming_router)
app.include_router(ml_router)
app.include_router(analytics_router)
app.include_router(alerts_router)
app.include_router(execution_router)
app.include_router(bot_pro_router)

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
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        access_log=False,  # Disable HTTP request logging
        log_level="warning"  # Only show warnings and errors
    )

