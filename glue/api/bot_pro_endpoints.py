"""
JJ-Bot Pro API Endpoints
Control and monitor the autonomous trading bot
"""

import os
import sys
import json
import asyncio
import psutil
import subprocess
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

router = APIRouter(prefix="/api/pro", tags=["JJ-Bot Pro"])


# Request/Response models
class BotConfigUpdate(BaseModel):
    mode: Optional[str] = None
    exchange: Optional[str] = None
    symbols: Optional[list] = None
    initial_capital: Optional[float] = None
    max_position_pct: Optional[float] = None
    max_positions: Optional[int] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_daily_loss_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    use_rl_agent: Optional[bool] = None
    use_edge_strategies: Optional[bool] = None
    use_alternative_data: Optional[bool] = None
    min_signal_confidence: Optional[float] = None


# Global bot instance reference
_bot_instance = None
_bot_process = None


def get_config_path():
    """Get path to bot config"""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    return os.path.join(project_root, 'config', 'bot_config.json')


def load_config():
    """Load bot configuration"""
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return None


def save_config(config):
    """Save bot configuration"""
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def is_bot_running():
    """Check if JJ-Bot Pro is running"""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('jjbot_pro.py' in str(arg) for arg in cmdline):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None


# ===== STATUS & INFO =====

@router.get("/status")
async def get_bot_status():
    """Get JJ-Bot Pro status and statistics"""
    running, pid = is_bot_running()
    config = load_config()

    status = {
        "running": running,
        "pid": pid,
        "mode": config.get("mode", "paper") if config else "not_configured",
        "configured": config is not None,
    }

    if config:
        status["config"] = {
            "exchange": config.get("exchange", "binance"),
            "symbols": config.get("symbols", []),
            "initial_capital": config.get("initial_capital", 10000),
            "max_position_pct": config.get("max_position_pct", 0.10),
            "use_rl_agent": config.get("use_rl_agent", True),
            "use_edge_strategies": config.get("use_edge_strategies", True),
            "use_alternative_data": config.get("use_alternative_data", True),
        }

    # Check for existing model
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    model_path = os.path.join(project_root, 'models', 'ppo_agent.pt')
    status["rl_model_trained"] = os.path.exists(model_path)

    return status


@router.get("/config")
async def get_bot_config():
    """Get current bot configuration"""
    config = load_config()
    if not config:
        return {"status": "not_configured", "config": None}
    return {"status": "ok", "config": config}


@router.put("/config")
async def update_bot_config(updates: BotConfigUpdate):
    """Update bot configuration"""
    config = load_config() or {}

    # Apply updates
    for field, value in updates.dict(exclude_none=True).items():
        config[field] = value

    save_config(config)

    return {
        "status": "updated",
        "config": config,
        "message": "Configuration updated. Restart bot to apply changes."
    }


# ===== BOT CONTROL =====

@router.post("/start")
async def start_bot(mode: Optional[str] = None):
    """Start JJ-Bot Pro"""
    global _bot_process

    running, pid = is_bot_running()
    if running:
        return {"status": "already_running", "pid": pid}

    config = load_config()
    if not config:
        return {
            "status": "error",
            "message": "Bot not configured. Run setup wizard first."
        }

    # Override mode if specified
    if mode:
        config["mode"] = mode
        save_config(config)

    try:
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        bot_script = os.path.join(project_root, 'jjbot_pro.py')

        import platform
        if platform.system() == 'Windows':
            _bot_process = subprocess.Popen(
                [sys.executable, bot_script],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=project_root
            )
        else:
            _bot_process = subprocess.Popen(
                [sys.executable, bot_script],
                cwd=project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        await asyncio.sleep(1)

        running, pid = is_bot_running()
        if running:
            return {
                "status": "started",
                "pid": pid,
                "mode": config.get("mode", "paper"),
                "message": f"JJ-Bot Pro started in {config.get('mode', 'paper')} mode"
            }
        else:
            return {"status": "error", "message": "Bot failed to start. Check logs."}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/stop")
async def stop_bot():
    """Stop JJ-Bot Pro gracefully"""
    stopped = False

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('jjbot_pro.py' in str(arg) for arg in cmdline):
                proc.terminate()
                stopped = True
                # Wait for graceful shutdown
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if stopped:
        return {"status": "stopped", "message": "JJ-Bot Pro stopped"}
    return {"status": "not_running", "message": "Bot was not running"}


@router.post("/train")
async def start_training(episodes: int = 100):
    """Start RL agent training"""
    running, pid = is_bot_running()
    if running:
        return {
            "status": "error",
            "message": "Stop the bot before training"
        }

    config = load_config() or {}
    config["mode"] = "training"
    config["train_episodes"] = episodes
    save_config(config)

    # Start in training mode
    return await start_bot(mode="training")


# ===== POSITIONS & TRADES =====

@router.get("/positions")
async def get_positions():
    """Get current open positions"""
    # This would connect to the running bot via shared state or API
    # For now, read from the positions file if it exists
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    positions_file = os.path.join(project_root, 'data', 'positions.json')

    if os.path.exists(positions_file):
        with open(positions_file) as f:
            return {"positions": json.load(f)}

    return {"positions": [], "message": "No position data available"}


@router.get("/trades")
async def get_trade_history(limit: int = 50):
    """Get recent trade history from JJ-Bot Pro"""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    trades_file = os.path.join(project_root, 'data', 'pro_trades.json')

    if os.path.exists(trades_file):
        with open(trades_file) as f:
            trades = json.load(f)
            return {"trades": trades[-limit:], "total": len(trades)}

    return {"trades": [], "message": "No trade history available"}


# ===== ALTERNATIVE DATA & EDGE =====

@router.get("/edge/status")
async def get_edge_status():
    """Get current edge detection status"""
    try:
        from modules.data_feeds import create_alternative_feed, EdgeDetector

        alt_feed = create_alternative_feed()
        edge_detector = EdgeDetector(alt_feed)

        # Get edge signals for BTC
        signals = await alt_feed.get_alternative_signals("BTC")
        recommendation = await edge_detector.get_trade_recommendation("BTC")

        await alt_feed.close()

        return {
            "status": "ok",
            "signals": signals,
            "recommendation": recommendation
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/sentiment")
async def get_market_sentiment():
    """Get current market sentiment data"""
    try:
        from modules.data_feeds import create_alternative_feed

        alt_feed = create_alternative_feed()
        sentiment = await alt_feed.get_sentiment("BTC")
        await alt_feed.close()

        return {
            "status": "ok",
            "sentiment": sentiment
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/funding-rates")
async def get_funding_rates():
    """Get current funding rates"""
    try:
        from modules.data_feeds import create_alternative_feed

        alt_feed = create_alternative_feed()
        funding = await alt_feed.get_funding_rates("BTC")
        await alt_feed.close()

        return {
            "status": "ok",
            "funding": funding
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===== RL AGENT =====

@router.get("/rl/status")
async def get_rl_status():
    """Get RL agent training status"""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    model_path = os.path.join(project_root, 'models', 'ppo_agent.pt')

    status = {
        "model_exists": os.path.exists(model_path),
        "model_path": model_path,
    }

    if os.path.exists(model_path):
        stat = os.stat(model_path)
        status["model_size"] = stat.st_size
        status["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

    # Check for training metrics
    metrics_path = os.path.join(project_root, 'logs', 'training_metrics.json')
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            status["training_metrics"] = json.load(f)

    return status


# ===== LOGS =====

@router.get("/logs")
async def get_bot_logs(lines: int = 100):
    """Get recent bot logs"""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    log_path = os.path.join(project_root, 'logs', 'jjbot.log')

    if not os.path.exists(log_path):
        return {"logs": [], "message": "No log file found"}

    with open(log_path) as f:
        all_lines = f.readlines()
        return {
            "logs": all_lines[-lines:],
            "total_lines": len(all_lines)
        }


# ===== EXCHANGE INFO =====

@router.get("/exchanges")
async def list_supported_exchanges():
    """List supported exchanges"""
    return {
        "exchanges": [
            {"id": "binance", "name": "Binance", "has_futures": True, "has_spot": True},
            {"id": "coinbase", "name": "Coinbase Pro", "has_futures": False, "has_spot": True},
            {"id": "kraken", "name": "Kraken", "has_futures": True, "has_spot": True},
            {"id": "kucoin", "name": "KuCoin", "has_futures": True, "has_spot": True},
            {"id": "bybit", "name": "Bybit", "has_futures": True, "has_spot": True},
        ]
    }


@router.get("/exchange/test")
async def test_exchange_connection():
    """Test exchange API connection"""
    config = load_config()
    if not config or not config.get("api_key"):
        return {
            "status": "no_api_key",
            "message": "No API key configured. Public endpoints will be used."
        }

    try:
        from modules.exchange import create_connector

        connector = create_connector(
            config.get("exchange", "binance"),
            config.get("api_key", ""),
            config.get("api_secret", ""),
            sandbox=config.get("sandbox", True)
        )

        connected = await connector.connect()

        if connected:
            balance = await connector.get_balance()
            await connector.disconnect()

            return {
                "status": "connected",
                "exchange": config.get("exchange"),
                "sandbox": config.get("sandbox", True),
                "balance": balance
            }
        else:
            return {"status": "failed", "message": "Connection failed"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===== QUICK ACTIONS =====

@router.post("/quick-start")
async def quick_start_paper():
    """Quick start paper trading with defaults"""
    config = load_config()

    if not config:
        # Create default config
        config = {
            "mode": "paper",
            "exchange": "binance",
            "api_key": "",
            "api_secret": "",
            "sandbox": True,
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "initial_capital": 10000.0,
            "max_position_pct": 0.10,
            "max_positions": 3,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04,
            "max_daily_loss_pct": 0.05,
            "max_drawdown_pct": 0.10,
            "use_rl_agent": True,
            "use_edge_strategies": True,
            "use_alternative_data": True,
            "min_signal_confidence": 0.6,
            "rl_model_path": "models/ppo_agent.pt",
            "train_episodes": 100,
            "analysis_interval_seconds": 60,
            "log_level": "INFO",
            "log_trades": True,
        }
        save_config(config)

    config["mode"] = "paper"
    save_config(config)

    return await start_bot(mode="paper")
