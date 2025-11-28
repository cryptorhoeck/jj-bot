"""
JJ-Bot Pro API Endpoints
Control and monitor the autonomous trading bot - runs integrated with API
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import AI modules
try:
    from modules.ai.config import get_ai_config
    from modules.ai.llm_client import get_llm_client
    from services.ai.inference_service import ai_inference_service
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

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


# Global bot instance - runs in same process as API
_bot_instance = None
_bot_task = None


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


def get_bot():
    """Get or create bot instance"""
    global _bot_instance
    return _bot_instance


# ===== STATUS & INFO =====

@router.get("/status")
async def get_bot_status():
    """Get JJ-Bot Pro status and statistics"""
    global _bot_instance

    config = load_config()
    bot = get_bot()

    status = {
        "running": bot is not None and bot.running if bot else False,
        "mode": config.get("mode", "paper") if config else "not_configured",
        "configured": config is not None,
        "integrated": True,  # Running in same process as API
    }

    # Get live stats from running bot
    if bot and bot.running:
        status.update({
            "equity": bot.equity,
            "positions": len(bot.positions),
            "total_trades": bot.stats["total_trades"],
            "winning_trades": bot.stats["winning_trades"],
            "total_pnl": bot.stats["total_pnl"],
            "daily_pnl": bot.daily_pnl,
            "start_time": bot.stats["start_time"].isoformat() if bot.stats["start_time"] else None,
            "win_rate": (bot.stats["winning_trades"] / max(bot.stats["total_trades"], 1)) * 100,
        })

    # Include training progress if bot exists
    if bot:
        status["training"] = bot.training_progress

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

    # Add AI status
    if AI_AVAILABLE:
        try:
            ai_config = get_ai_config()
            llm_client = get_llm_client()
            ai_service_status = ai_inference_service.get_status()

            status["ai"] = {
                "enabled": ai_config.enabled,
                "available": llm_client.is_available,
                "model": ai_config.model,
                "service_running": ai_service_status.get("status") == "running",
                "stats": {
                    "signals_enhanced": ai_service_status.get("stats", {}).get("signals_enhanced", 0),
                    "signals_confirmed": ai_service_status.get("stats", {}).get("signals_confirmed", 0),
                    "signals_rejected": ai_service_status.get("stats", {}).get("ai_rejected_signals", 0),
                    "avg_latency_ms": llm_client.get_stats().get("avg_latency_ms", 0)
                },
                "features": {
                    "sentiment_analysis": ai_config.sentiment_analysis_enabled,
                    "signal_enhancement": ai_config.signal_enhancement_enabled,
                    "risk_assessment": ai_config.risk_assessment_enabled
                }
            }
        except Exception as e:
            status["ai"] = {"available": False, "error": str(e)}
    else:
        status["ai"] = {"available": False, "message": "AI module not installed"}

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
    """Start JJ-Bot Pro (runs in same process as API)"""
    global _bot_instance, _bot_task

    if _bot_instance and _bot_instance.running:
        return {"status": "already_running", "message": "Bot is already running"}

    config = load_config()
    if not config:
        return {
            "status": "error",
            "message": "Bot not configured. Run setup wizard or use /api/pro/quick-start"
        }

    # Override mode if specified
    if mode:
        config["mode"] = mode
        save_config(config)

    try:
        # Import and create bot
        from jjbot_pro import JJBotPro, BotConfig

        bot_config = BotConfig(**config)
        _bot_instance = JJBotPro(bot_config)

        # Start bot as background task
        _bot_task = asyncio.create_task(_run_bot(_bot_instance))

        # Wait a moment for initialization
        await asyncio.sleep(2)

        if _bot_instance.running:
            return {
                "status": "started",
                "mode": config.get("mode", "paper"),
                "message": f"JJ-Bot Pro started in {config.get('mode', 'paper')} mode",
                "integrated": True
            }
        else:
            return {"status": "error", "message": "Bot failed to start. Check logs."}

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _run_bot(bot):
    """Run bot in background"""
    try:
        await bot.start()
    except asyncio.CancelledError:
        await bot.stop()
    except Exception as e:
        print(f"Bot error: {e}")
        await bot.stop()


@router.post("/stop")
async def stop_bot():
    """Stop JJ-Bot Pro gracefully"""
    global _bot_instance, _bot_task

    if not _bot_instance or not _bot_instance.running:
        return {"status": "not_running", "message": "Bot is not running"}

    try:
        # If in training mode, switch back to paper
        if _bot_instance.config.mode == "training":
            config = load_config() or {}
            config["mode"] = "paper"
            save_config(config)

        # Stop the bot gracefully
        await _bot_instance.stop()

        # Cancel the task
        if _bot_task:
            _bot_task.cancel()
            try:
                await _bot_task
            except asyncio.CancelledError:
                pass
            _bot_task = None

        return {"status": "stopped", "message": "JJ-Bot Pro stopped"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/train")
async def start_training(episodes: int = 100):
    """Start RL agent training"""
    global _bot_instance

    if _bot_instance and _bot_instance.running:
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
    global _bot_instance

    if _bot_instance and _bot_instance.running:
        return {
            "positions": _bot_instance.get_positions(),
            "count": len(_bot_instance.positions)
        }

    return {"positions": [], "message": "Bot not running"}


@router.get("/trades")
async def get_trade_history(limit: int = 50):
    """Get recent trade history from JJ-Bot Pro"""
    global _bot_instance

    if _bot_instance:
        return {
            "trades": _bot_instance.get_trade_history(limit),
            "total": len(_bot_instance.trade_history)
        }

    return {"trades": [], "message": "No trade history available"}


# ===== LIVE PRICES =====

@router.get("/prices")
async def get_live_prices():
    """Get current prices from the bot"""
    global _bot_instance

    if _bot_instance and _bot_instance.running:
        return {
            "prices": _bot_instance.prices,
            "timestamp": datetime.now().isoformat()
        }

    return {"prices": {}, "message": "Bot not running"}


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
    """Quick start paper trading with defaults - no setup needed"""
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
