"""
JJ-Bot Pro API Endpoints
Control and monitor the autonomous trading bot - runs integrated with API

Thread-safe implementation with proper locking and error handling.
"""

import os
import sys
import json
import asyncio
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pro", tags=["JJ-Bot Pro"])


# ===== Request/Response Models with Validation =====

class BotConfigUpdate(BaseModel):
    """Configuration update model with validation"""
    mode: Optional[str] = Field(None, pattern="^(paper|live|training|demo)$")
    exchange: Optional[str] = Field(None, pattern="^(binance|coinbase|kraken|kucoin|bybit)$")
    symbols: Optional[List[str]] = None
    initial_capital: Optional[float] = Field(None, gt=0, le=10000000)
    max_position_pct: Optional[float] = Field(None, gt=0, le=1.0)
    max_positions: Optional[int] = Field(None, ge=1, le=100)
    stop_loss_pct: Optional[float] = Field(None, gt=0, le=0.5)
    take_profit_pct: Optional[float] = Field(None, gt=0, le=1.0)
    max_daily_loss_pct: Optional[float] = Field(None, gt=0, le=1.0)
    max_drawdown_pct: Optional[float] = Field(None, gt=0, le=1.0)
    use_rl_agent: Optional[bool] = None
    use_edge_strategies: Optional[bool] = None
    use_alternative_data: Optional[bool] = None
    min_signal_confidence: Optional[float] = Field(None, ge=0, le=1.0)

    @validator('symbols', pre=True)
    def validate_symbols(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError("Maximum 50 symbols allowed")
        return v


class BotStatusResponse(BaseModel):
    """Bot status response model"""
    running: bool
    mode: str
    configured: bool
    integrated: bool = True
    equity: Optional[float] = None
    positions: Optional[int] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    total_pnl: Optional[float] = None
    daily_pnl: Optional[float] = None
    start_time: Optional[str] = None
    win_rate: Optional[float] = None
    config: Optional[Dict[str, Any]] = None
    rl_model_trained: Optional[bool] = None
    training: Optional[Dict[str, Any]] = None


class APIResponse(BaseModel):
    """Standard API response model"""
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ===== Thread-Safe Bot Manager =====

class BotManager:
    """
    Thread-safe manager for bot instance and lifecycle.

    Uses locks to prevent race conditions when starting/stopping
    the bot from concurrent API requests.
    """

    def __init__(self):
        self._bot_instance = None
        self._bot_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._async_lock = asyncio.Lock()
        self._startup_event = asyncio.Event()

    @property
    def bot(self):
        """Get current bot instance (thread-safe read)"""
        with self._lock:
            return self._bot_instance

    @property
    def is_running(self) -> bool:
        """Check if bot is currently running"""
        with self._lock:
            return (
                self._bot_instance is not None
                and hasattr(self._bot_instance, 'running')
                and self._bot_instance.running
            )

    async def start_bot(self, config: Dict) -> Dict[str, Any]:
        """
        Start the bot with given configuration.

        Returns:
            Dict with status and message
        """
        async with self._async_lock:
            if self.is_running:
                return {
                    "status": "already_running",
                    "message": "Bot is already running"
                }

            try:
                # Import and create bot
                from jjbot_pro import JJBotPro, BotConfig

                bot_config = BotConfig(**config)

                with self._lock:
                    self._bot_instance = JJBotPro(bot_config)
                    self._startup_event.clear()

                # Start bot as background task
                self._bot_task = asyncio.create_task(self._run_bot())

                # Wait for initialization (max 10 seconds)
                try:
                    await asyncio.wait_for(self._startup_event.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    logger.warning("Bot startup timed out, checking status...")

                if self.is_running:
                    logger.info(f"Bot started in {config.get('mode', 'paper')} mode")
                    return {
                        "status": "started",
                        "mode": config.get("mode", "paper"),
                        "message": f"JJ-Bot Pro started in {config.get('mode', 'paper')} mode",
                        "integrated": True
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Bot failed to start. Check logs for details."
                    }

            except ImportError as e:
                logger.error(f"Failed to import bot module: {e}")
                return {
                    "status": "error",
                    "message": f"Bot module not available: {e}"
                }
            except Exception as e:
                logger.exception(f"Failed to start bot: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }

    async def stop_bot(self) -> Dict[str, Any]:
        """
        Stop the bot gracefully.

        Returns:
            Dict with status and message
        """
        async with self._async_lock:
            if not self.is_running:
                return {
                    "status": "not_running",
                    "message": "Bot is not running"
                }

            try:
                with self._lock:
                    bot = self._bot_instance

                if bot:
                    # Stop the bot gracefully
                    await bot.stop()

                # Cancel the background task
                if self._bot_task and not self._bot_task.done():
                    self._bot_task.cancel()
                    try:
                        await self._bot_task
                    except asyncio.CancelledError:
                        pass

                with self._lock:
                    self._bot_task = None
                    # Keep instance for stats access, but it's no longer running

                logger.info("Bot stopped successfully")
                return {
                    "status": "stopped",
                    "message": "JJ-Bot Pro stopped"
                }

            except Exception as e:
                logger.exception(f"Error stopping bot: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }

    async def _run_bot(self):
        """Background task to run the bot"""
        try:
            bot = self.bot
            if bot:
                # Signal that startup is complete
                self._startup_event.set()
                await bot.start()
        except asyncio.CancelledError:
            logger.info("Bot task cancelled")
            if self.bot:
                await self.bot.stop()
        except Exception as e:
            logger.exception(f"Bot error: {e}")
            if self.bot:
                await self.bot.stop()
        finally:
            self._startup_event.set()  # Ensure event is set even on error

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status (thread-safe)"""
        with self._lock:
            bot = self._bot_instance

            if not bot:
                return {
                    "running": False,
                    "instance_exists": False
                }

            status = {
                "running": bot.running if hasattr(bot, 'running') else False,
                "instance_exists": True,
            }

            if bot.running:
                try:
                    status.update({
                        "equity": getattr(bot, 'equity', 0),
                        "positions": len(getattr(bot, 'positions', {})),
                        "total_trades": bot.stats.get("total_trades", 0) if hasattr(bot, 'stats') else 0,
                        "winning_trades": bot.stats.get("winning_trades", 0) if hasattr(bot, 'stats') else 0,
                        "total_pnl": bot.stats.get("total_pnl", 0) if hasattr(bot, 'stats') else 0,
                        "daily_pnl": getattr(bot, 'daily_pnl', 0),
                        "start_time": (bot.stats.get("start_time").isoformat() if hasattr(bot.stats.get("start_time"), 'isoformat') else bot.stats.get("start_time")) if hasattr(bot, 'stats') and bot.stats.get("start_time") else None,
                    })

                    total_trades = status.get("total_trades", 0)
                    if total_trades > 0:
                        status["win_rate"] = (status.get("winning_trades", 0) / total_trades) * 100
                    else:
                        status["win_rate"] = 0.0

                except Exception as e:
                    logger.warning(f"Error getting bot status: {e}")

            # Training progress
            if hasattr(bot, 'training_progress'):
                status["training"] = bot.training_progress

            return status

    def get_positions(self) -> List[Dict]:
        """Get current positions (thread-safe)"""
        with self._lock:
            bot = self._bot_instance
            if bot and hasattr(bot, 'get_positions'):
                return bot.get_positions()
            return []

    def get_prices(self) -> Dict[str, float]:
        """Get current prices (thread-safe)"""
        with self._lock:
            bot = self._bot_instance
            if bot and hasattr(bot, 'prices'):
                return dict(bot.prices)
            return {}

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history (thread-safe)"""
        with self._lock:
            bot = self._bot_instance
            if bot and hasattr(bot, 'get_trade_history'):
                return bot.get_trade_history(limit)
            return []


# Global bot manager instance
_bot_manager = BotManager()


def get_bot():
    """Get the current bot instance for external access"""
    return _bot_manager.bot


# ===== Config Utilities =====

def get_config_path() -> str:
    """Get path to bot config"""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    return os.path.join(project_root, 'config', 'bot_config.json')


def load_config() -> Optional[Dict]:
    """Load bot configuration"""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid config JSON: {e}")
            return None
    return None


def save_config(config: Dict) -> bool:
    """Save bot configuration"""
    config_path = get_config_path()
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def get_project_root() -> str:
    """Get project root path"""
    return os.path.join(os.path.dirname(__file__), '..', '..')


# ===== API Endpoints =====

@router.get("/status", response_model=None)
async def get_bot_status() -> Dict[str, Any]:
    """
    Get JJ-Bot Pro status and statistics.

    Returns comprehensive bot status including:
    - Running state
    - Mode (paper/live/training)
    - Equity and P&L
    - Position count
    - Trade statistics
    - Configuration summary
    """
    config = load_config()
    bot_status = _bot_manager.get_status()

    response = {
        "running": bot_status.get("running", False),
        "mode": config.get("mode", "paper") if config else "not_configured",
        "configured": config is not None,
        "integrated": True,
    }

    # Add live stats if running
    if bot_status.get("running"):
        response.update({
            "equity": bot_status.get("equity"),
            "positions": bot_status.get("positions"),
            "total_trades": bot_status.get("total_trades"),
            "winning_trades": bot_status.get("winning_trades"),
            "total_pnl": bot_status.get("total_pnl"),
            "daily_pnl": bot_status.get("daily_pnl"),
            "start_time": bot_status.get("start_time"),
            "win_rate": bot_status.get("win_rate"),
        })

    # Add training progress
    if "training" in bot_status:
        response["training"] = bot_status["training"]

    # Add config summary
    if config:
        response["config"] = {
            "exchange": config.get("exchange", "binance"),
            "symbols": config.get("symbols", []),
            "initial_capital": config.get("initial_capital", 10000),
            "max_position_pct": config.get("max_position_pct", 0.10),
            "use_rl_agent": config.get("use_rl_agent", True),
            "use_edge_strategies": config.get("use_edge_strategies", True),
            "use_alternative_data": config.get("use_alternative_data", True),
        }

    # Check for trained model
    model_path = os.path.join(get_project_root(), 'models', 'ppo_agent.pt')
    response["rl_model_trained"] = os.path.exists(model_path)

    return response


@router.get("/config")
async def get_bot_config() -> Dict[str, Any]:
    """Get current bot configuration"""
    config = load_config()
    if not config:
        return {"status": "not_configured", "config": None}
    return {"status": "ok", "config": config}


@router.put("/config")
async def update_bot_config(updates: BotConfigUpdate) -> Dict[str, Any]:
    """
    Update bot configuration.

    Changes are saved but require a bot restart to take effect.
    """
    config = load_config() or {}

    # Apply updates (only non-None values)
    update_dict = updates.dict(exclude_none=True)
    for field, value in update_dict.items():
        config[field] = value

    if save_config(config):
        return {
            "status": "updated",
            "config": config,
            "message": "Configuration updated. Restart bot to apply changes."
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration"
        )


@router.post("/start")
async def start_bot(mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Start JJ-Bot Pro.

    Args:
        mode: Optional mode override (paper/live/training/demo)

    The bot runs in the same process as the API for integrated operation.
    """
    config = load_config()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot not configured. Run setup wizard or use /api/pro/quick-start"
        )

    # Override mode if specified
    if mode:
        if mode not in ("paper", "live", "training", "demo"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode: {mode}. Must be paper, live, training, or demo"
            )
        config["mode"] = mode
        save_config(config)

    result = await _bot_manager.start_bot(config)

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )

    return result


@router.post("/stop")
async def stop_bot() -> Dict[str, Any]:
    """
    Stop JJ-Bot Pro gracefully.

    Saves state and closes all positions if configured to do so.
    """
    # If in training mode, switch back to paper
    config = load_config()
    if config and config.get("mode") == "training":
        config["mode"] = "paper"
        save_config(config)

    result = await _bot_manager.stop_bot()
    return result


@router.post("/train")
async def start_training(episodes: int = 100) -> Dict[str, Any]:
    """
    Start RL agent training.

    Args:
        episodes: Number of training episodes (default: 100)

    Bot must be stopped before training can begin.
    """
    if episodes < 1 or episodes > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Episodes must be between 1 and 10000"
        )

    if _bot_manager.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the bot before training"
        )

    config = load_config() or {}
    config["mode"] = "training"
    config["train_episodes"] = episodes
    save_config(config)

    return await start_bot(mode="training")


@router.get("/positions")
async def get_positions() -> Dict[str, Any]:
    """Get current open positions"""
    positions = _bot_manager.get_positions()
    return {
        "positions": positions,
        "count": len(positions)
    }


@router.get("/trades")
async def get_trade_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent trade history.

    Args:
        limit: Maximum number of trades to return (default: 50, max: 500)
    """
    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 500"
        )

    trades = _bot_manager.get_trade_history(limit)
    return {
        "trades": trades,
        "count": len(trades)
    }


@router.get("/prices")
async def get_live_prices() -> Dict[str, Any]:
    """Get current prices from the bot"""
    prices = _bot_manager.get_prices()
    return {
        "prices": prices,
        "timestamp": datetime.now().isoformat(),
        "count": len(prices)
    }


@router.get("/edge/status")
async def get_edge_status() -> Dict[str, Any]:
    """Get current edge detection status"""
    try:
        from modules.data_feeds import create_alternative_feed, EdgeDetector

        alt_feed = create_alternative_feed()
        edge_detector = EdgeDetector(alt_feed)

        signals = await alt_feed.get_alternative_signals("BTC")
        recommendation = await edge_detector.get_trade_recommendation("BTC")

        await alt_feed.close()

        return {
            "status": "ok",
            "signals": signals,
            "recommendation": recommendation
        }
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Edge detection module not available"
        }
    except Exception as e:
        logger.exception(f"Edge status error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/sentiment")
async def get_market_sentiment() -> Dict[str, Any]:
    """Get current market sentiment data"""
    try:
        from modules.data_feeds import create_alternative_feed

        alt_feed = create_alternative_feed()
        sentiment = await alt_feed.get_sentiment("BTC")
        await alt_feed.close()

        return {"status": "ok", "sentiment": sentiment}
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Sentiment module not available"
        }
    except Exception as e:
        logger.exception(f"Sentiment error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/funding-rates")
async def get_funding_rates() -> Dict[str, Any]:
    """Get current funding rates"""
    try:
        from modules.data_feeds import create_alternative_feed

        alt_feed = create_alternative_feed()
        funding = await alt_feed.get_funding_rates("BTC")
        await alt_feed.close()

        return {"status": "ok", "funding": funding}
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Funding rates module not available"
        }
    except Exception as e:
        logger.exception(f"Funding rates error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/rl/status")
async def get_rl_status() -> Dict[str, Any]:
    """Get RL agent training status"""
    project_root = get_project_root()
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
        try:
            with open(metrics_path) as f:
                status["training_metrics"] = json.load(f)
        except json.JSONDecodeError:
            status["training_metrics"] = None

    return status


@router.get("/logs")
async def get_bot_logs(lines: int = 100) -> Dict[str, Any]:
    """
    Get recent bot logs.

    Args:
        lines: Number of recent log lines to return (default: 100, max: 1000)
    """
    if lines < 1 or lines > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lines must be between 1 and 1000"
        )

    log_path = os.path.join(get_project_root(), 'logs', 'jjbot.log')

    if not os.path.exists(log_path):
        return {"logs": [], "message": "No log file found"}

    try:
        with open(log_path) as f:
            all_lines = f.readlines()
            return {
                "logs": all_lines[-lines:],
                "total_lines": len(all_lines)
            }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"logs": [], "message": f"Error reading logs: {e}"}


@router.get("/exchanges")
async def list_supported_exchanges() -> Dict[str, Any]:
    """List supported exchanges with their capabilities"""
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
async def test_exchange_connection() -> Dict[str, Any]:
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

    except ImportError:
        return {
            "status": "unavailable",
            "message": "Exchange connector module not available"
        }
    except Exception as e:
        logger.exception(f"Exchange test error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/quick-start")
async def quick_start_paper() -> Dict[str, Any]:
    """
    Quick start paper trading with sensible defaults.

    No setup required - creates default configuration and starts
    the bot in paper trading mode.
    """
    config = load_config()

    if not config:
        # Create default config with sensible production-ready defaults
        config = {
            "mode": "paper",
            "exchange": "kraken",
            "api_key": "",
            "api_secret": "",
            "sandbox": True,
            "symbols": ["BTC/USD", "ETH/USD", "SOL/USD"],
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


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.

    Returns:
        - API status
        - Bot status
        - Database connectivity
        - Timestamp
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api": "ok",
        "bot_running": _bot_manager.is_running,
    }

    # Check database connectivity
    try:
        from modules.database.connection import get_connection, TRADES_DB_PATH
        conn = get_connection(TRADES_DB_PATH)
        conn.execute("SELECT 1")
        health["database"] = "ok"
    except Exception as e:
        health["database"] = f"error: {e}"
        health["status"] = "degraded"

    return health
