"""
JJ-Bot Pro API Endpoints
Control and monitor the autonomous trading bot - runs integrated with API
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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

# Import database module
try:
    from modules.database import data_manager
    DATA_MANAGER_AVAILABLE = True
except ImportError:
    data_manager = None
    DATA_MANAGER_AVAILABLE = False

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
    circuit_breaker_losses: Optional[int] = None
    circuit_breaker_cooldown_minutes: Optional[int] = None
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

    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
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
            "start_time": bot.stats["start_time"].isoformat() if hasattr(bot.stats.get("start_time"), 'isoformat') else bot.stats.get("start_time"),
            "win_rate": (bot.stats["winning_trades"] / max(bot.stats["total_trades"], 1)) * 100,
        })

    # Include training progress if bot exists
    if bot:
        status["training"] = bot.training_progress
        # Include persistent IQ and training history from bot stats
        status["trading_iq"] = bot.stats.get("trading_iq", 0)
        status["expertise_level"] = bot.stats.get("expertise_level", "Untrained")
        status["training_history"] = {
            "training_sessions": bot.stats.get("training_sessions", 0),
            "total_training_episodes": bot.stats.get("total_training_episodes", 0),
            "total_training_trades": bot.stats.get("total_training_trades", 0),
            "last_training_date": bot.stats.get("last_training_date"),
            "avg_win_rate": bot.stats.get("avg_win_rate", 0),
            "avg_profit_factor": bot.stats.get("avg_profit_factor", 0),
            "avg_reward": bot.stats.get("avg_reward", 0),
            "best_win_rate": bot.stats.get("best_win_rate", 0),
            "best_profit_factor": bot.stats.get("best_profit_factor", 0),
        }
    else:
        # Load persistent IQ and training history from database when bot is not running
        if DATA_MANAGER_AVAILABLE:
            try:
                # Use cumulative metrics from database as source of truth
                cumulative = data_manager.get_cumulative_training_metrics()
                bot_state = data_manager.get_bot_state()
                status["trading_iq"] = cumulative.get("trading_iq", 0)
                status["expertise_level"] = cumulative.get("expertise_level", "Untrained")
                status["training_history"] = {
                    "training_sessions": cumulative.get("total_sessions", 0),
                    "total_training_episodes": cumulative.get("total_episodes", 0),
                    "total_training_trades": bot_state.get("total_training_trades", 0),
                    "last_training_date": bot_state.get("last_training_date"),
                    "avg_win_rate": cumulative.get("avg_win_rate", 0),
                    "avg_profit_factor": cumulative.get("avg_profit_factor", 0),
                    "avg_reward": 0,  # Not tracked in cumulative
                    "best_win_rate": cumulative.get("best_win_rate", 0),
                    "best_profit_factor": cumulative.get("best_profit_factor", 0),
                }
            except Exception as e:
                logger.warning(f"Could not load training stats from database: {e}")
                status["trading_iq"] = 0
                status["expertise_level"] = "Untrained"
                status["training_history"] = {}
        else:
            # Fallback to JSON file if database not available
            state_file = os.path.join(project_root, 'data', 'bot_state.json')
            if os.path.exists(state_file):
                try:
                    with open(state_file) as f:
                        saved_state = json.load(f)
                        saved_stats = saved_state.get("stats", {})
                        status["trading_iq"] = saved_stats.get("trading_iq", 0)
                        status["expertise_level"] = saved_stats.get("expertise_level", "Untrained")
                        status["training_history"] = {
                            "training_sessions": saved_stats.get("training_sessions", 0),
                            "total_training_episodes": saved_stats.get("total_training_episodes", 0),
                            "total_training_trades": saved_stats.get("total_training_trades", 0),
                            "last_training_date": saved_stats.get("last_training_date"),
                            "avg_win_rate": saved_stats.get("avg_win_rate", 0),
                            "avg_profit_factor": saved_stats.get("avg_profit_factor", 0),
                            "avg_reward": saved_stats.get("avg_reward", 0),
                            "best_win_rate": saved_stats.get("best_win_rate", 0),
                            "best_profit_factor": saved_stats.get("best_profit_factor", 0),
                        }
                except Exception as e:
                    logger.warning(f"Could not load trading stats: {e}")
                    status["trading_iq"] = 0
                    status["expertise_level"] = "Untrained"
                    status["training_history"] = {}
            else:
                status["trading_iq"] = 0
                status["expertise_level"] = "Untrained"
                status["training_history"] = {}

    if config:
        status["config"] = {
            "exchange": config.get("exchange", "binance"),
            "symbols": config.get("symbols", []),
            "initial_capital": config.get("initial_capital", 0),
            "max_position_pct": config.get("max_position_pct", 0.10),
            "use_rl_agent": config.get("use_rl_agent", True),
            "use_edge_strategies": config.get("use_edge_strategies", True),
            "use_alternative_data": config.get("use_alternative_data", True),
        }

    # Check for existing model
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
    print(f"[START_BOT] Called with mode={mode}")

    if _bot_instance and _bot_instance.running:
        return {"status": "already_running", "message": "Bot is already running"}

    config = load_config()
    if not config:
        return {
            "status": "error",
            "message": "Bot not configured. Run setup wizard or use /api/pro/quick-start"
        }
    print(f"[START_BOT] Loaded config with mode={config.get('mode')}")

    # Override mode if specified
    if mode:
        config["mode"] = mode
        save_config(config)
        print(f"[START_BOT] Mode overridden to: {mode}")

    try:
        # Import and create bot
        from jjbot_pro import JJBotPro, BotConfig
        from dataclasses import fields

        # Filter config to only known BotConfig fields (handles old config files with extra fields)
        valid_fields = {f.name for f in fields(BotConfig)}
        filtered_config = {k: v for k, v in config.items() if k in valid_fields}
        print(f"[START_BOT] Filtered config mode={filtered_config.get('mode')}", flush=True)

        bot_config = BotConfig(**filtered_config)
        print(f"[START_BOT] BotConfig created with mode={bot_config.mode}", flush=True)

        # FORCE the mode - something in BotConfig.__post_init__ is overriding it
        if mode:
            bot_config.mode = mode
            print(f"[START_BOT] Mode FORCED to: {bot_config.mode}", flush=True)

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
        logger.error(f"Bot error: {e}", exc_info=True)
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


@router.post("/emergency-stop")
async def emergency_stop(close_positions: bool = True, auth_token: Optional[str] = None):
    """
    EMERGENCY STOP - Immediately halt trading and optionally close all positions.

    This endpoint provides a remote kill switch for emergency situations.
    Use when you need to immediately stop all trading activity.

    Args:
        close_positions: If True (default), close all open positions immediately
        auth_token: Optional authentication token (set EMERGENCY_STOP_TOKEN env var)
    """
    global _bot_instance, _bot_task

    # Optional authentication - check EMERGENCY_STOP_TOKEN env var
    required_token = os.environ.get("EMERGENCY_STOP_TOKEN")
    if required_token and auth_token != required_token:
        raise HTTPException(status_code=401, detail="Invalid or missing auth_token")

    result = {
        "status": "emergency_stop_triggered",
        "timestamp": datetime.now().isoformat(),
        "positions_closed": 0,
        "close_errors": [],
        "message": ""
    }

    try:
        if not _bot_instance:
            result["message"] = "Bot instance not found - nothing to stop"
            return result

        # Log emergency stop to audit trail
        if hasattr(_bot_instance, 'audit') and _bot_instance.audit:
            _bot_instance.audit.log_event(
                event_type="EMERGENCY_STOP",
                details={"close_positions": close_positions, "triggered_via": "api"}
            )

        # Close all positions if requested
        if close_positions and hasattr(_bot_instance, 'positions'):
            positions_to_close = list(_bot_instance.positions.keys())
            logger.warning(f"EMERGENCY STOP: Closing {len(positions_to_close)} positions")

            for symbol in positions_to_close:
                try:
                    if hasattr(_bot_instance, '_close_position'):
                        await _bot_instance._close_position(symbol, reason="emergency_stop")
                        result["positions_closed"] += 1
                        logger.info(f"Emergency closed position: {symbol}")
                except Exception as e:
                    error_msg = f"Failed to close {symbol}: {str(e)}"
                    result["close_errors"].append(error_msg)
                    logger.error(error_msg)

        # Stop the bot immediately
        if _bot_instance.running:
            _bot_instance.running = False  # Immediate halt flag

            # Try graceful stop with short timeout
            try:
                await asyncio.wait_for(_bot_instance.stop(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Graceful stop timed out, forcing shutdown")

        # Cancel background task
        if _bot_task:
            _bot_task.cancel()
            try:
                await asyncio.wait_for(_bot_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            _bot_task = None

        result["message"] = f"Emergency stop complete. Closed {result['positions_closed']} positions."
        if result["close_errors"]:
            result["message"] += f" {len(result['close_errors'])} errors occurred."

        logger.warning(f"EMERGENCY STOP COMPLETE: {result}")
        return result

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Emergency stop failed: {str(e)}"
        logger.error(f"Emergency stop error: {e}", exc_info=True)
        return result


@router.post("/train")
async def start_training(episodes: int = 100, timeframe: str = "1h", history_days: int = 90):
    """Start RL agent training with configurable data settings"""
    global _bot_instance
    import sys

    # Force output to show
    print(f"\n{'='*60}", flush=True)
    print(f"[TRAIN] TRAIN ENDPOINT CALLED - episodes={episodes}", flush=True)
    print(f"{'='*60}", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

    if _bot_instance and _bot_instance.running:
        return {
            "status": "error",
            "message": "Stop the bot before training"
        }

    config = load_config() or {}
    config["mode"] = "training"
    config["train_episodes"] = episodes
    config["train_timeframe"] = timeframe
    config["train_history_days"] = history_days
    save_config(config)
    print(f"[TRAIN] Config saved with mode={config['mode']}", flush=True)

    # Verify config was saved correctly
    verify_config = load_config()
    print(f"[TRAIN] Verify: config file now has mode={verify_config.get('mode')}", flush=True)

    # Start in training mode
    result = await start_bot(mode="training")
    print(f"[TRAIN] start_bot returned: {result}", flush=True)
    return result


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


@router.get("/rl/cumulative-metrics")
async def get_cumulative_training_metrics():
    """Get cumulative training metrics that persist across all sessions"""
    if not DATA_MANAGER_AVAILABLE:
        return {"status": "error", "message": "Database not available"}

    try:
        metrics = data_manager.get_cumulative_training_metrics()
        return {
            "status": "ok",
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to get cumulative training metrics: {e}")
        return {"status": "error", "message": str(e)}


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
            "initial_capital": 0.0,
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
