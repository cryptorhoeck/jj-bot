#!/usr/bin/env python3

import os
import sys
import json
import math
import asyncio
import logging
from datetime import datetime, timedelta
import subprocess
import csv
from io import StringIO
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
import secrets

logger = logging.getLogger(__name__)

# API Key Authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_API_KEY = None  # Will be loaded from config or generated

def get_api_key() -> str:
    """Get or generate the API key"""
    global _API_KEY
    if _API_KEY is None:
        # Try to load from config
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'api_config.json')
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = json.load(f)
                    _API_KEY = config.get('api_key', '')
        except Exception:
            pass

        # Generate new key if not found
        if not _API_KEY:
            _API_KEY = secrets.token_urlsafe(32)
            # Save it
            try:
                config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'api_config.json')
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump({'api_key': _API_KEY, 'auth_enabled': False}, f, indent=2)
                logger.info(f"Generated new API key (saved to config/api_config.json)")
            except Exception as e:
                logger.warning(f"Could not save API key: {e}")
    return _API_KEY

def is_auth_enabled() -> bool:
    """Check if API authentication is enabled"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'api_config.json')
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                return config.get('auth_enabled', False)
    except Exception:
        pass
    return False

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Verify API key if authentication is enabled"""
    if not is_auth_enabled():
        return True  # Auth disabled

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required. Set X-API-Key header.")

    if api_key != get_api_key():
        raise HTTPException(status_code=403, detail="Invalid API key")

    return True
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
from ai_endpoints import router as ai_router
from websocket_manager import ws_manager

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[OK] Database initialized")
    engine.init_db()

    print("[START] Starting auto-start services...")
    started = service_manager.start_auto_services()
    if started:
        print(f"[OK] Auto-started services: {', '.join(started)}")
    else:
        print("[INFO] No auto-start services configured")

    yield

    # Shutdown (add cleanup here if needed)
    print("[SHUTDOWN] Shutting down API...")

# Import version from config
try:
    from config import APP_VERSION, APP_NAME
except ImportError:
    APP_VERSION = "3.0.0"
    APP_NAME = "JJ-Bot"

# Create FastAPI app with lifespan
app = FastAPI(title=f"{APP_NAME} API v{APP_VERSION}", lifespan=lifespan)

# Add CORS middleware for dashboard - restricted to localhost for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # API itself (for testing)
        "http://127.0.0.1:8000",
    ],
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
    return {"message": f"{APP_NAME} API v{APP_VERSION}", "status": "running", "version": APP_VERSION}

# ===== TRADES ENDPOINTS - Uses unified bot when running =====
@app.get("/api/trades")
async def get_trades(limit: int = 50):
    # Use bot trades when running
    bot = get_bot()
    if bot and bot.running:
        return {"trades": bot.get_trade_history(limit), "source": "unified_bot"}
    # Fallback to database
    trades = engine.get_trades(limit=limit)
    return {"trades": trades}

@app.get("/api/summary")
async def get_summary():
    # Use bot summary when running
    bot = get_bot()
    if bot and bot.running:
        win_rate = (bot.stats["winning_trades"] / max(bot.stats["total_trades"], 1)) * 100
        return {
            "total_trades": bot.stats["total_trades"],
            "winning_trades": bot.stats["winning_trades"],
            "losing_trades": bot.stats["total_trades"] - bot.stats["winning_trades"],
            "win_rate": win_rate,
            "total_pnl": bot.stats["total_pnl"],
            "current_equity": bot.total_equity,
            "starting_capital": bot.config.initial_capital,
            "daily_pnl": bot.daily_pnl,
            "open_positions": len(bot.positions),
            "mode": bot.config.mode,
            "source": "unified_bot"
        }
    return engine.get_summary()

@app.get("/api/equity-curve")
async def get_equity_curve(starting_capital: float = 10000.0):
    """Get equity curve over time for portfolio visualization"""
    bot = get_bot()
    if bot and bot.running:
        # Build simple equity curve from bot
        return {
            "equity_curve": [{"equity": bot.total_equity, "timestamp": datetime.now().isoformat()}],
            "starting_capital": bot.config.initial_capital,
            "current_equity": bot.total_equity,
            "source": "unified_bot"
        }
    return {
        "equity_curve": engine.get_equity_curve(starting_capital),
        "starting_capital": starting_capital
    }

@app.get("/api/positions/open")
async def get_open_positions():
    """Get currently open trading positions with unrealized PnL"""
    bot = get_bot()
    if bot and bot.running:
        return {
            "open_positions": bot.get_positions(),
            "count": len(bot.positions),
            "source": "unified_bot"
        }
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

@app.get("/api/system/version")
async def system_version():
    """Get system version information"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "api_title": app.title,
        "changelog": "See CHANGELOG.md for full version history"
    }

# ===== AUTHENTICATION =====
@app.get("/api/auth/status")
async def auth_status():
    """Get authentication status and info"""
    return {
        "auth_enabled": is_auth_enabled(),
        "message": "Set auth_enabled=true in config/api_config.json to require API keys"
    }

@app.post("/api/auth/enable")
async def enable_auth(enabled: bool = True, _: bool = Depends(verify_api_key)):
    """Enable or disable API authentication"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'api_config.json')
        config = {'api_key': get_api_key(), 'auth_enabled': enabled}
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return {"status": "ok", "auth_enabled": enabled, "api_key": get_api_key() if enabled else None}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== BOT ENDPOINTS - Uses unified JJBotPro =====
# Import the unified bot module
from bot_pro_endpoints import get_bot, start_bot as pro_start_bot, stop_bot as pro_stop_bot, load_config

@app.get("/api/bot/status")
@app.get("/api/simulator/status")  # Keep old endpoint for compatibility
async def bot_status():
    """Check if trading bot is running - uses unified JJBotPro"""
    bot = get_bot()
    config = load_config()

    if bot and bot.running:
        return {
            "running": True,
            "mode": config.get("mode", "paper") if config else "paper",
            "equity": bot.total_equity,
            "positions": len(bot.positions),
            "total_trades": bot.stats["total_trades"],
            "total_pnl": bot.stats["total_pnl"],
            "symbols": list(bot.prices.keys()) if bot.prices else [],
            "prices": bot.prices,
        }
    return {"running": False}

@app.post("/api/bot/start")
@app.post("/api/simulator/start")  # Keep old endpoint for compatibility
async def start_bot_endpoint():
    """Start the unified trading bot"""
    return await pro_start_bot()

@app.post("/api/bot/stop")
@app.post("/api/simulator/stop")  # Keep old endpoint for compatibility
async def stop_bot_endpoint():
    """Stop the unified trading bot"""
    return await pro_stop_bot()

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
    """Clear trading data only (trades.db) - preserves training IQ but resets equity"""
    import shutil
    from pathlib import Path
    import json

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)

    # Load config to get initial_capital
    config_path = PROJECT_ROOT / "config" / "bot_config.json"
    initial_capital = 10000.0
    try:
        with open(config_path) as f:
            config = json.load(f)
            initial_capital = config.get("initial_capital", 10000.0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass  # Use default initial_capital

    # Backup trades.db (JJ-Bot Pro database)
    trades_db = PROJECT_ROOT / "data" / "trades.db"
    backed_up = None
    if trades_db.exists():
        backup_path = backup_dir / f"trades_backup_{timestamp}.db"
        shutil.copy2(trades_db, backup_path)
        backed_up = backup_path.name

    # Clear trades from database
    try:
        with engine.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM trades")
            conn.commit()

        # Reset equity in bot_state.json but preserve IQ
        state_file = PROJECT_ROOT / "data" / "bot_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state_data = json.load(f)

                # Reset equity to initial_capital
                state_data["equity"] = initial_capital
                state_data["peak_equity"] = initial_capital
                state_data["daily_pnl"] = 0.0
                state_data["daily_start_equity"] = initial_capital

                # Reset trade stats but keep IQ
                if "stats" in state_data:
                    state_data["stats"]["total_trades"] = 0
                    state_data["stats"]["winning_trades"] = 0
                    state_data["stats"]["total_pnl"] = 0.0
                    # Keep trading_iq, expertise_level, training_sessions, etc.

                with open(state_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not update state file: {e}")

        return {
            "status": "cleared",
            "message": f"Trading data cleared, equity reset to ${initial_capital:,.2f}{f' (backed up to {backed_up})' if backed_up else ''}. Training IQ preserved."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/data/clear-training")
async def clear_training_data():
    """Clear training data (bot_state.json with IQ) - resets the AI to untrained state"""
    import shutil
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)

    backed_up = []

    # Backup bot_state.json (contains trading_iq and training progress)
    state_file = PROJECT_ROOT / "data" / "bot_state.json"
    if state_file.exists():
        backup_path = backup_dir / f"bot_state_backup_{timestamp}.json"
        shutil.copy2(state_file, backup_path)
        backed_up.append(f"bot_state.json -> {backup_path.name}")
        state_file.unlink()

    # Backup and remove trained model if exists
    model_file = PROJECT_ROOT / "models" / "ppo_agent.pt"
    if model_file.exists():
        backup_path = backup_dir / f"ppo_agent_backup_{timestamp}.pt"
        shutil.copy2(model_file, backup_path)
        backed_up.append(f"ppo_agent.pt -> {backup_path.name}")
        model_file.unlink()

    if backed_up:
        return {
            "status": "cleared",
            "message": f"Training data cleared and backed up: {', '.join(backed_up)}. AI reset to untrained state."
        }
    else:
        return {
            "status": "cleared",
            "message": "No training data found to clear."
        }


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
    """List all available backups with detailed metadata"""
    from pathlib import Path
    try:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        backup_dir = PROJECT_ROOT / "backups"
        archive_dir = PROJECT_ROOT / "backups" / "archives"

        backups = []

        def get_backup_info(file_path: Path, backup_type: str, category: str):
            """Extract backup info from file"""
            size = file_path.stat().st_size
            modified = file_path.stat().st_mtime
            filename = file_path.name

            # Parse timestamp from filename (format: name_backup_YYYYMMDD_HHMMSS.ext)
            created_str = None
            parts = filename.replace('.db', '').replace('.json', '').replace('.pt', '').split('_')
            if len(parts) >= 2:
                # Try to find date/time parts
                for i, part in enumerate(parts):
                    if len(part) == 8 and part.isdigit():  # YYYYMMDD
                        date_part = part
                        time_part = parts[i+1] if i+1 < len(parts) and len(parts[i+1]) == 6 else "000000"
                        try:
                            created_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                        except:
                            pass
                        break

            return {
                "filename": filename,
                "path": str(file_path),
                "type": backup_type,  # 'trading', 'state', 'model'
                "category": category,  # 'backup', 'archive'
                "size": size,
                "size_formatted": f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB",
                "modified": datetime.fromtimestamp(modified).isoformat(),
                "created": created_str,
            }

        # List all backups in backup directory
        if backup_dir.exists():
            for file_path in backup_dir.iterdir():
                if file_path.is_file():
                    if file_path.suffix == '.db':
                        backups.append(get_backup_info(file_path, 'trading', 'backup'))
                    elif file_path.suffix == '.json':
                        backups.append(get_backup_info(file_path, 'state', 'backup'))
                    elif file_path.suffix == '.pt':
                        backups.append(get_backup_info(file_path, 'model', 'backup'))

        # List archives
        if archive_dir.exists():
            for file_path in archive_dir.iterdir():
                if file_path.is_file() and file_path.suffix == '.db':
                    backups.append(get_backup_info(file_path, 'trading', 'archive'))

        # Sort by modified date (newest first)
        backups.sort(key=lambda x: x['modified'], reverse=True)

        # Group by type for summary
        summary = {
            'trading': len([b for b in backups if b['type'] == 'trading']),
            'state': len([b for b in backups if b['type'] == 'state']),
            'model': len([b for b in backups if b['type'] == 'model']),
            'total_size': sum(b['size'] for b in backups),
        }

        return {
            "status": "success",
            "backups": backups,
            "total": len(backups),
            "summary": summary
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/data/backup")
async def create_full_backup():
    """Create a full backup of all data (trades, state, and model)"""
    import shutil
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)

    backed_up = []
    errors = []

    # Backup trades.db
    trades_db = PROJECT_ROOT / "data" / "trades.db"
    if trades_db.exists():
        try:
            backup_path = backup_dir / f"trades_backup_{timestamp}.db"
            shutil.copy2(trades_db, backup_path)
            backed_up.append({"file": "trades.db", "backup": backup_path.name, "type": "trading"})
        except Exception as e:
            errors.append(f"trades.db: {str(e)}")

    # Backup bot_state.json
    state_file = PROJECT_ROOT / "data" / "bot_state.json"
    if state_file.exists():
        try:
            backup_path = backup_dir / f"bot_state_backup_{timestamp}.json"
            shutil.copy2(state_file, backup_path)
            backed_up.append({"file": "bot_state.json", "backup": backup_path.name, "type": "state"})
        except Exception as e:
            errors.append(f"bot_state.json: {str(e)}")

    # Backup ppo_agent.pt (trained model)
    model_file = PROJECT_ROOT / "models" / "ppo_agent.pt"
    if model_file.exists():
        try:
            backup_path = backup_dir / f"ppo_agent_backup_{timestamp}.pt"
            shutil.copy2(model_file, backup_path)
            backed_up.append({"file": "ppo_agent.pt", "backup": backup_path.name, "type": "model"})
        except Exception as e:
            errors.append(f"ppo_agent.pt: {str(e)}")

    if backed_up:
        return {
            "status": "success",
            "message": f"Backed up {len(backed_up)} files",
            "backed_up": backed_up,
            "errors": errors if errors else None,
            "timestamp": timestamp
        }
    else:
        return {
            "status": "warning",
            "message": "No files found to backup",
            "errors": errors if errors else None
        }


@app.post("/api/data/restore")
async def restore_backup(request: dict):
    """Restore from a specific backup file"""
    import shutil
    from pathlib import Path

    filename = request.get("filename")
    if not filename:
        return {"status": "error", "message": "No filename provided"}

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    backup_dir = PROJECT_ROOT / "backups"
    archive_dir = PROJECT_ROOT / "backups" / "archives"

    # Find the backup file
    backup_path = None
    for search_dir in [backup_dir, archive_dir]:
        potential_path = search_dir / filename
        if potential_path.exists():
            backup_path = potential_path
            break

    if not backup_path:
        return {"status": "error", "message": f"Backup file not found: {filename}"}

    try:
        # Determine restore target based on filename
        if 'trades' in filename and filename.endswith('.db'):
            target = PROJECT_ROOT / "data" / "trades.db"
            backup_type = "trading"
        elif 'bot_state' in filename and filename.endswith('.json'):
            target = PROJECT_ROOT / "data" / "bot_state.json"
            backup_type = "state"
        elif 'ppo_agent' in filename and filename.endswith('.pt'):
            target = PROJECT_ROOT / "models" / "ppo_agent.pt"
            backup_type = "model"
        else:
            return {"status": "error", "message": f"Unknown backup type: {filename}"}

        # Create current backup before restoring (safety)
        if target.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safety_backup = backup_dir / f"{target.stem}_pre_restore_{timestamp}{target.suffix}"
            shutil.copy2(target, safety_backup)

        # Ensure target directory exists
        target.parent.mkdir(parents=True, exist_ok=True)

        # Restore the backup
        shutil.copy2(backup_path, target)

        return {
            "status": "success",
            "message": f"Restored {backup_type} data from {filename}",
            "restored_to": str(target),
            "backup_type": backup_type
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/data/backup/{filename}")
async def delete_backup(filename: str):
    """Delete a specific backup file"""
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    backup_dir = PROJECT_ROOT / "backups"
    archive_dir = PROJECT_ROOT / "backups" / "archives"

    # Find and delete the backup file
    for search_dir in [backup_dir, archive_dir]:
        file_path = search_dir / filename
        if file_path.exists():
            try:
                file_path.unlink()
                return {
                    "status": "success",
                    "message": f"Deleted backup: {filename}"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

    return {"status": "error", "message": f"Backup not found: {filename}"}

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


# ===== REAL MARKET DATA =====
@app.get("/api/market/live")
async def get_market_live():
    """Get live market data - prefers unified bot data when running"""
    try:
        # FIRST: Check if unified bot is running and has prices
        bot = get_bot()
        if bot and bot.running and bot.prices:
            result = {}
            for symbol, price in bot.prices.items():
                base = symbol.split("/")[0] if "/" in symbol else symbol
                result[base.lower()] = {
                    "symbol": base,
                    "name": base,
                    "usd": price,
                    "usd_24h_change": 0,
                    "usd_market_cap": 0,
                    "usd_24h_vol": 0,
                    "image": "",
                    "timestamp": datetime.now().isoformat()
                }
            if result:
                return {"status": "success", "data": result, "count": len(result), "source": "unified_bot"}

        from modules.data import cached_market_data_service
        from services.streaming.market_stream_service import market_stream_service
        from symbol_management_endpoints import get_db_path
        import sqlite3

        # Get enabled symbols from database
        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT symbol FROM symbols WHERE enabled = 1 ORDER BY symbol ASC")
            symbols = [row[0] for row in cursor.fetchall()]
            conn.close()
        except Exception as db_err:
            logger.warning(f"Failed to load symbols from DB: {db_err}, using defaults from config")
            # Try to load from bot config, or use comprehensive fallback
            try:
                import json
                config_path = os.path.join(os.path.dirname(__file__), '../../config/bot_config.json')
                with open(config_path) as f:
                    config = json.load(f)
                    # Extract base symbol from pairs like "BTC/USD" -> "BTC"
                    symbols = [s.split('/')[0] for s in config.get('symbols', [])]
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                # Verified Kraken USD pairs
                symbols = [
                    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK", "ATOM",
                    "UNI", "LTC", "BCH", "XLM", "ALGO", "POL", "FIL", "APE", "AAVE", "CRV",
                    "SNX", "GRT", "SAND", "MANA", "AXS", "ENJ", "BAT", "ZEC", "DASH", "EOS",
                    "XTZ", "TRX", "ETC", "SHIB", "PEPE", "OP", "ARB", "INJ", "RUNE", "KAVA",
                    "STORJ", "SUSHI", "YFI", "1INCH", "FET", "IMX", "APT", "RNDR", "NEAR", "FTM"
                ]

        result = {}

        # Try to get data from WebSocket stream if it's running
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
                print(f"[OK] Fetched {len(result)} prices from WebSocket stream")
                return {"status": "success", "data": result, "count": len(result), "source": "websocket"}

        # Fallback: Use CCXT to batch fetch from Kraken (like jjbot_pro does)
        try:
            import ccxt
            kraken = ccxt.kraken()
            kraken.load_markets()

            # Filter to only valid Kraken symbols (skip stocks like AAPL, TSLA)
            valid_pairs = []
            for s in symbols:
                pair = f"{s}/USD"
                if pair in kraken.symbols:
                    valid_pairs.append(pair)

            if not valid_pairs:
                raise Exception("No valid Kraken symbols found")

            # Batch fetch tickers
            try:
                tickers = kraken.fetch_tickers(valid_pairs)
            except Exception as batch_err:
                # If batch fails, try individual fetches
                logger.warning(f"Batch ticker fetch failed: {batch_err}, trying individual...")
                tickers = {}
                for pair in valid_pairs:
                    try:
                        ticker = kraken.fetch_ticker(pair)
                        tickers[pair] = ticker
                    except Exception:
                        continue  # Skip failed tickers, try next

            for pair, ticker in tickers.items():
                base = pair.split("/")[0]
                result[base.lower()] = {
                    "symbol": base,
                    "name": base,
                    "usd": ticker.get("last", 0) or ticker.get("close", 0) or 0,
                    "usd_24h_change": ticker.get("percentage", 0) or 0,
                    "usd_market_cap": 0,
                    "usd_24h_vol": ticker.get("quoteVolume", 0) or 0,
                    "image": "",
                    "timestamp": datetime.now().isoformat()
                }

            if result:
                print(f"[OK] Fetched {len(result)} prices from Kraken via CCXT")
                return {"status": "success", "data": result, "count": len(result), "source": "kraken_ccxt"}

        except Exception as ccxt_err:
            logger.warning(f"CCXT fallback failed: {ccxt_err}")

        # Last resort: Return error instead of misleading placeholder data
        raise Exception("No price data available from any source")

    except Exception as e:
        logger.warning(f"Market data fetch failed: {e}")
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
        crypto_symbols = [
            'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'LINK', 'ATOM',
            'UNI', 'LTC', 'BCH', 'XLM', 'ALGO', 'MATIC', 'NEAR', 'FIL', 'APE', 'AAVE',
            'CRV', 'MKR', 'COMP', 'SNX', 'GRT', 'SAND', 'MANA', 'AXS', 'ENJ', 'CHZ',
            'BAT', 'ZEC', 'DASH', 'EOS', 'XTZ', 'TRX', 'ETC', 'SHIB', 'PEPE', 'FTM',
            'OP', 'ARB', 'INJ', 'RUNE', 'KAVA', 'OCEAN', 'STORJ', 'SUSHI', 'YFI', '1INCH', 'BNB', 'POL'
        ]

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
                "DOT": 7.5, "POL": 0.45, "AAPL": 180, "TSLA": 250,
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
        crypto_symbols = [
            'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'LINK', 'ATOM',
            'UNI', 'LTC', 'BCH', 'XLM', 'ALGO', 'MATIC', 'NEAR', 'FIL', 'APE', 'AAVE',
            'CRV', 'MKR', 'COMP', 'SNX', 'GRT', 'SAND', 'MANA', 'AXS', 'ENJ', 'CHZ',
            'BAT', 'ZEC', 'DASH', 'EOS', 'XTZ', 'TRX', 'ETC', 'SHIB', 'PEPE', 'FTM',
            'OP', 'ARB', 'INJ', 'RUNE', 'KAVA', 'OCEAN', 'STORJ', 'SUSHI', 'YFI', '1INCH', 'BNB', 'POL'
        ]

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
            crypto_symbols = [
            'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'LINK', 'ATOM',
            'UNI', 'LTC', 'BCH', 'XLM', 'ALGO', 'MATIC', 'NEAR', 'FIL', 'APE', 'AAVE',
            'CRV', 'MKR', 'COMP', 'SNX', 'GRT', 'SAND', 'MANA', 'AXS', 'ENJ', 'CHZ',
            'BAT', 'ZEC', 'DASH', 'EOS', 'XTZ', 'TRX', 'ETC', 'SHIB', 'PEPE', 'FTM',
            'OP', 'ARB', 'INJ', 'RUNE', 'KAVA', 'OCEAN', 'STORJ', 'SUSHI', 'YFI', '1INCH', 'BNB', 'POL'
        ]
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
app.include_router(ai_router)

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
        logger.warning(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/api/websocket/stats")
async def websocket_stats():
    """Get WebSocket manager statistics"""
    return ws_manager.get_stats()

if __name__ == "__main__":
    import uvicorn
    print(f"{APP_NAME} API v{APP_VERSION} starting...")
    print("API: http://127.0.0.1:8000")
    print("Dashboard: http://localhost:5173")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        access_log=False,  # Disable HTTP request logging
        log_level="warning"  # Only show warnings and errors
    )

