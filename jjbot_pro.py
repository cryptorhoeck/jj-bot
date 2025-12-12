"""
JJ-Bot Pro - Unified Autonomous Trading System
One-click setup, fully autonomous operation

This is the main entry point that integrates:
- Real exchange data via CCXT
- Reinforcement Learning for decision making
- Alternative data (sentiment, funding, order flow)
- Edge-focused strategies
- Risk management
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import signal
import numpy as np

# Internal modules
from modules.exchange import create_connector, create_live_feed, CCXTConnector, LiveDataFeed
from modules.exchange import OrderRequest, OrderType, OrderSide, Ticker
from modules.event_bus import event_bus
from modules.risk import RiskManager, RiskLimits

# Database for trade logging
try:
    from glue.api.engine import log_trade as db_log_trade, init_db, get_trades as db_get_trades
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    db_log_trade = None
    init_db = None
    db_get_trades = None

# Import version
try:
    from config import APP_VERSION, APP_NAME
except ImportError:
    APP_VERSION = "3.0.0"
    APP_NAME = "JJ-Bot"

# RL modules are optional (require PyTorch)
try:
    from modules.rl import TradingEnvironment, create_agent, PPOAgent
    from modules.rl.trading_env import load_historical_data_sync, calculate_features
    RL_AVAILABLE = True
except ImportError:
    TradingEnvironment = None
    create_agent = None
    PPOAgent = None
    load_historical_data_sync = None
    calculate_features = None
    RL_AVAILABLE = False

# Alternative data modules (optional)
try:
    from modules.data_feeds import create_alternative_feed, AlternativeDataFeed, EdgeDetector
    ALT_DATA_AVAILABLE = True
except ImportError:
    create_alternative_feed = None
    AlternativeDataFeed = None
    EdgeDetector = None
    ALT_DATA_AVAILABLE = False

# Edge strategies
try:
    from modules.strategy.edge_strategies import create_edge_manager, EdgeStrategyManager, TradeSignal
    EDGE_AVAILABLE = True
except ImportError:
    create_edge_manager = None
    EdgeStrategyManager = None
    TradeSignal = None
    EDGE_AVAILABLE = False

# Notifications (optional)
try:
    from modules.notifications import NotificationManager, NotificationConfig, create_notifier
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NotificationManager = None
    NotificationConfig = None
    create_notifier = None
    NOTIFICATIONS_AVAILABLE = False

# Health check server (optional)
try:
    from modules.health_check import HealthCheckServer, create_health_server
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    HealthCheckServer = None
    create_health_server = None
    HEALTH_CHECK_AVAILABLE = False

# Audit trail (optional)
try:
    from modules.audit_trail import AuditTrail, AuditEventType, get_audit_trail, init_audit_trail
    AUDIT_AVAILABLE = True
except ImportError:
    AuditTrail = None
    AuditEventType = None
    get_audit_trail = None
    init_audit_trail = None
    AUDIT_AVAILABLE = False


logger = logging.getLogger(__name__)


class BotMode(Enum):
    """Operating modes"""
    PAPER = "paper"      # Paper trading with real prices
    LIVE = "live"        # Real money trading
    BACKTEST = "backtest"  # Historical backtesting
    TRAINING = "training"  # RL agent training


@dataclass
class BotConfig:
    """Bot configuration - edit this to customize"""
    # Mode
    mode: str = "paper"  # paper, live, backtest, training

    # Exchange settings
    exchange: str = "binance"
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = True  # ALWAYS True unless explicitly going live

    # Trading symbols - Top 30 by market cap
    symbols: List[str] = field(default_factory=lambda: [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT",
        "ADA/USDT", "DOGE/USDT", "TRX/USDT", "AVAX/USDT", "LINK/USDT",
        "DOT/USDT", "POL/USDT", "SHIB/USDT", "LTC/USDT", "BCH/USDT",
        "UNI/USDT", "XLM/USDT", "ATOM/USDT", "ETC/USDT", "FIL/USDT",
        "HBAR/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "NEAR/USDT",
        "INJ/USDT", "RUNE/USDT", "AAVE/USDT", "GRT/USDT", "FTM/USDT"
    ])

    # Capital and position sizing
    initial_capital: float = 10000.0
    max_position_pct: float = 0.05  # 5% per position (smaller for more symbols)
    max_positions: int = 10  # Allow more concurrent positions

    # Risk management
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit
    max_daily_loss_pct: float = 0.05  # 5% daily loss limit
    max_drawdown_pct: float = 0.10  # 10% max drawdown
    risk_per_trade: float = 0.02  # 2% of account per trade risk
    circuit_breaker_losses: int = 3  # Consecutive losses to trigger circuit breaker
    circuit_breaker_cooldown_minutes: int = 30  # Minutes to pause trading after breaker

    # Trailing stop settings
    use_trailing_stop: bool = True  # Enable trailing stops
    trailing_stop_activation_pct: float = 0.02  # Activate after 2% profit
    trailing_stop_distance_pct: float = 0.01  # Trail by 1%

    # Strategy settings
    use_rl_agent: bool = True
    use_edge_strategies: bool = True
    use_alternative_data: bool = True
    min_signal_confidence: float = 0.45  # Lower threshold for more trades

    # RL settings
    rl_model_path: str = "models/ppo_agent.pt"
    train_episodes: int = 100
    train_timeframe: str = "1h"  # Candle size for training data
    train_history_days: int = 90  # Days of historical data
    rl_max_steps: int = 500  # Steps per training episode
    rl_n_epochs: int = 4  # PPO optimization epochs
    rl_batch_size: int = 128  # PPO batch size

    # Timing
    analysis_interval_seconds: int = 60  # How often to analyze (minimum 30 seconds recommended)
    rest_api_interval_seconds: int = 30  # How often to fetch prices via REST (reduces API load)

    # Logging
    log_level: str = "INFO"
    log_trades: bool = True

    # Notifications (set via environment variables or config)
    telegram_bot_token: str = ""  # TELEGRAM_BOT_TOKEN env var
    telegram_chat_id: str = ""    # TELEGRAM_CHAT_ID env var
    discord_webhook_url: str = "" # DISCORD_WEBHOOK_URL env var
    notify_on_trades: bool = True

    # Health check server
    health_check_enabled: bool = True
    health_check_port: int = 8080

    # Dead man's switch - auto-close positions if bot becomes unresponsive
    dead_mans_switch_enabled: bool = False  # Disabled by default for safety
    dead_mans_switch_timeout: int = 90  # 90 seconds without heartbeat (was 300s)
    dead_mans_switch_close_positions: bool = True  # Close all positions when triggered

    # Audit trail
    audit_trail_enabled: bool = True
    audit_trail_dir: str = "logs/audit"

    # Configurable timeouts (seconds)
    order_fill_timeout: float = 30.0  # Max wait for order to fill
    price_feed_stale_timeout: float = 300.0  # 5 min - mark feed as stale
    state_save_interval: float = 300.0  # Save state every 5 min
    candle_refresh_interval: float = 300.0  # Refresh candles every 5 min
    position_sync_interval: float = 300.0  # Sync positions with exchange every 5 min
    order_dedup_window: float = 5.0  # Seconds between same-symbol orders

    def __post_init__(self):
        """Load API keys from environment variables if not set in config"""
        # Environment variable names follow pattern: {EXCHANGE}_API_KEY, {EXCHANGE}_API_SECRET
        exchange_upper = self.exchange.upper().replace("-", "_")

        # Try exchange-specific env vars first, then generic fallback
        env_key_names = [
            f"{exchange_upper}_API_KEY",
            "EXCHANGE_API_KEY",
            "API_KEY"
        ]
        env_secret_names = [
            f"{exchange_upper}_API_SECRET",
            "EXCHANGE_API_SECRET",
            "API_SECRET"
        ]

        # Load API key from environment if not set
        if not self.api_key:
            for env_name in env_key_names:
                env_value = os.environ.get(env_name)
                if env_value:
                    self.api_key = env_value
                    logger.info(f"Loaded API key from environment variable: {env_name}")
                    break

        # Load API secret from environment if not set
        if not self.api_secret:
            for env_name in env_secret_names:
                env_value = os.environ.get(env_name)
                if env_value:
                    self.api_secret = env_value
                    logger.info(f"Loaded API secret from environment variable: {env_name}")
                    break

        # Also check for trading mode override from environment
        env_mode = os.environ.get("TRADING_MODE")
        if env_mode and env_mode in ["paper", "live", "training", "backtest"]:
            self.mode = env_mode
            logger.info(f"Trading mode set from environment: {env_mode}")

    @classmethod
    def load(cls, path: str = "config/bot_config.json") -> "BotConfig":
        """Load config from file, ignoring unknown fields"""
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                # Filter to only known fields to avoid errors from old config files
                valid_fields = {f.name for f in fields(cls)}
                filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                config = cls(**filtered_data)
                return config
        return cls()

    def save(self, path: str = "config/bot_config.json"):
        """Save config to file (excludes API keys for security)"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = asdict(self)
        # Don't save API keys to file for security
        data["api_key"] = ""
        data["api_secret"] = ""
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


@dataclass
class Position:
    """Active trading position"""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    size: float  # Position value in USD
    stop_loss: float
    take_profit: float
    entry_time: datetime
    signal_source: str
    unrealized_pnl: float = 0.0
    # Actual filled contracts/coins from exchange (for accurate close orders)
    actual_contracts: float = 0.0
    # Exchange order IDs for tracking
    entry_order_id: Optional[str] = None
    stop_order_id: Optional[str] = None  # Stop loss order on exchange
    tp_order_id: Optional[str] = None    # Take profit order on exchange
    # Trailing stop tracking
    trailing_stop_active: bool = False  # Whether trailing stop is activated
    highest_price: float = 0.0  # Highest price since entry (for long)
    lowest_price: float = float('inf')  # Lowest price since entry (for short)
    trailing_stop_price: float = 0.0  # Current trailing stop price
    # Slippage tracking
    expected_entry_price: float = 0.0  # Price when signal was generated
    entry_slippage: float = 0.0  # Actual slippage on entry
    entry_slippage_pct: float = 0.0


@dataclass
class TradeRecord:
    """Completed trade record"""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: datetime
    signal_source: str
    exit_reason: str
    # Slippage tracking
    entry_slippage: float = 0.0  # Entry slippage in dollars
    entry_slippage_pct: float = 0.0  # Entry slippage as percentage
    exit_slippage: float = 0.0  # Exit slippage in dollars
    exit_slippage_pct: float = 0.0  # Exit slippage as percentage


class JJBotPro:
    """
    Main Trading Bot - Integrates all components

    Usage:
        bot = JJBotPro()
        await bot.start()  # Runs forever
        # or
        bot.run()  # Blocking call
    """

    def __init__(self, config: Optional[BotConfig] = None):
        self.config = config or BotConfig.load()
        self._setup_logging()

        # State - try to load from saved state first
        self.running = False
        self._stopped = False  # Guard against double shutdown
        self._started_in_training_mode = False  # Track if bot was started in training mode
        saved_state = self._load_state()

        if saved_state:
            # Restore from saved state
            self.equity = saved_state.get("equity", self.config.initial_capital)
            self.peak_equity = saved_state.get("peak_equity", self.equity)
            self.daily_pnl = saved_state.get("daily_pnl", 0.0)
            self.daily_start_equity = saved_state.get("daily_start_equity", self.equity)
            self.stats = saved_state.get("stats", {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0.0,
                "signals_analyzed": 0,
                "start_time": None,
            })
            logger.info(f"Restored state: equity=${self.equity:.2f}, trades={self.stats['total_trades']}")
        else:
            # Fresh start
            self.equity = self.config.initial_capital
            self.peak_equity = self.config.initial_capital
            self.daily_pnl = 0.0
            self.daily_start_equity = self.config.initial_capital
            self.stats = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0.0,
                "signals_analyzed": 0,
                "start_time": None,
                "trading_iq": 0,
                "expertise_level": "Untrained",
                # Training history
                "training_sessions": 0,
                "total_training_episodes": 0,
                "total_training_trades": 0,
                "last_training_date": None,
                "avg_win_rate": 0.0,
                "avg_profit_factor": 0.0,
                "avg_reward": 0.0,
                # Slippage tracking
                "total_entry_slippage": 0.0,
                "total_exit_slippage": 0.0,
                "avg_entry_slippage_pct": 0.0,
                "avg_exit_slippage_pct": 0.0,
                "slippage_trades_count": 0,
            }

        # Track equity at session start for accurate return calculation
        self.session_starting_equity = self.equity

        # Positions and history
        self.positions: Dict[str, Position] = self._load_positions()
        self.trade_history: List[TradeRecord] = self._load_trade_history()

        # Lock for thread-safe position modifications
        self._position_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()  # Lock for state file operations

        # Order deduplication - track recent order requests to prevent duplicates
        self._recent_orders: Dict[str, datetime] = {}  # symbol -> last_order_time
        self._order_dedup_window = self.config.order_dedup_window

        # Training state - initialize from loaded stats if available
        self.training_progress = {
            "is_training": False,
            "current_episode": 0,
            "total_episodes": 0,
            "last_reward": 0.0,
            "last_pnl": 0.0,
            "last_win_rate": 0.0,
            "progress_pct": 0.0,
            "trading_iq": self.stats.get("trading_iq", 0),
            "expertise_level": self.stats.get("expertise_level", "Untrained"),
            "avg_win_rate": self.stats.get("avg_win_rate", 0.0),
            "avg_profit_factor": self.stats.get("avg_profit_factor", 0.0),
            "avg_reward": self.stats.get("avg_reward", 0.0),
            "total_trades": self.stats.get("total_training_trades", 0),
            "cumulative_pnl": 0.0,  # Total P&L if compounding across episodes
            "simulated_equity": self.config.initial_capital  # What equity would be if compounding
        }

        # Training metrics for IQ calculation
        self.training_metrics = {
            "episode_count": 0,
            "total_win_rate": 0.0,
            "total_profit_factor": 0.0,
            "total_reward": 0.0,
            "total_trades": 0,
            "cumulative_pnl": 0.0  # Track what P&L would be if compounding
        }

        # Components (initialized in start())
        self.exchange: Optional[CCXTConnector] = None
        self.data_feed: Optional[LiveDataFeed] = None
        self.alt_data: Optional[AlternativeDataFeed] = None
        self.edge_detector: Optional[EdgeDetector] = None
        self.edge_manager: Optional[EdgeStrategyManager] = None
        self.rl_agent: Optional[PPOAgent] = None
        self.rl_env: Optional[TradingEnvironment] = None

        # Notifications
        self.notifier: Optional[NotificationManager] = None
        if NOTIFICATIONS_AVAILABLE:
            notif_config = NotificationConfig(
                telegram_bot_token=self.config.telegram_bot_token,
                telegram_chat_id=self.config.telegram_chat_id,
                discord_webhook_url=self.config.discord_webhook_url,
                notify_on_entry=self.config.notify_on_trades,
                notify_on_exit=self.config.notify_on_trades,
            )
            self.notifier = create_notifier(notif_config)
            if self.notifier.is_enabled:
                logger.info("Trade notifications enabled")

        # Health check server
        self._health_server = None
        self._health_app = None

        # Audit trail
        self.audit: Optional[AuditTrail] = None
        if AUDIT_AVAILABLE and self.config.audit_trail_enabled:
            self.audit = init_audit_trail(
                log_dir=self.config.audit_trail_dir,
                enabled=True
            )
            logger.info("Audit trail enabled")

        # Risk manager with circuit breaker and comprehensive checks
        self.risk_manager = RiskManager(RiskLimits(
            max_risk_per_trade=self.config.risk_per_trade,
            max_total_exposure=0.20,  # 20% max exposure
            max_drawdown_pct=self.config.max_drawdown_pct,
            max_daily_loss=self.config.max_daily_loss_pct * self.config.initial_capital,
            max_open_positions=self.config.max_positions,
            circuit_breaker_loss_count=self.config.circuit_breaker_losses,
            circuit_breaker_cooldown_minutes=self.config.circuit_breaker_cooldown_minutes,
        ))
        logger.info("Risk manager initialized")

        # Price cache
        self.prices: Dict[str, float] = {}

        # Price feed health tracking
        self._last_price_update: datetime = datetime.now()
        self._last_rest_fetch: datetime = datetime.min  # Track REST API fetches separately
        self._price_feed_stale_threshold = self.config.price_feed_stale_timeout
        self._trading_paused_due_to_feed = False

        logger.info(f"JJ-Bot Pro initialized in {self.config.mode} mode")

    @property
    def total_equity(self) -> float:
        """Get total equity including unrealized P&L"""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.equity + unrealized

    def _setup_logging(self):
        """Configure logging"""
        # Create logs directory BEFORE setting up file handler
        os.makedirs("logs", exist_ok=True)

        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("logs/jjbot.log", mode="a")
            ]
        )

    def _load_state(self) -> Optional[Dict]:
        """Load saved bot state from bot_state.json (primary) and trades database (fallback)"""
        import sqlite3
        # Use absolute path relative to this file (same as engine.py does)
        project_root = Path(__file__).parent
        db_path = project_root / "data" / "trades.db"
        state_file = project_root / "data" / "bot_state.json"

        logger.info(f"Looking for state file at: {state_file}")
        logger.info(f"State file exists: {state_file.exists()}")

        # Primary: Load full state from bot_state.json
        saved_equity = None
        saved_peak_equity = None
        saved_daily_pnl = 0.0
        saved_daily_start_equity = None
        saved_iq = 0
        saved_level = "Untrained"
        saved_stats = {}  # Initialize empty - will be populated from state file if exists
        saved_training_history = {
            "training_sessions": 0,
            "total_training_episodes": 0,
            "last_training_date": None,
            "avg_win_rate": 0.0,
            "avg_profit_factor": 0.0,
            "avg_reward": 0.0,
        }

        if state_file.exists():
            try:
                with open(state_file) as f:
                    saved_data = json.load(f)
                    # Load equity and related fields
                    saved_equity = saved_data.get("equity")
                    saved_peak_equity = saved_data.get("peak_equity")
                    saved_daily_pnl = saved_data.get("daily_pnl", 0.0)
                    saved_daily_start_equity = saved_data.get("daily_start_equity")

                    saved_stats = saved_data.get("stats", {})
                    saved_iq = saved_stats.get("trading_iq", 0)
                    saved_level = saved_stats.get("expertise_level", "Untrained")
                    # Load training history
                    saved_training_history = {
                        "training_sessions": saved_stats.get("training_sessions", 0),
                        "total_training_episodes": saved_stats.get("total_training_episodes", 0),
                        "last_training_date": saved_stats.get("last_training_date"),
                        "avg_win_rate": saved_stats.get("avg_win_rate", 0.0),
                        "avg_profit_factor": saved_stats.get("avg_profit_factor", 0.0),
                        "avg_reward": saved_stats.get("avg_reward", 0.0),
                    }
                    logger.info(f"Loaded from state file: equity=${saved_equity}, IQ={saved_iq}, Level={saved_level}, Sessions={saved_training_history['training_sessions']}")
            except Exception as e:
                logger.warning(f"Failed to load from state file: {e}")
        else:
            logger.warning(f"No state file found at {state_file} - starting fresh")

        logger.info(f"Looking for trades database at: {db_path}")

        if not db_path.exists():
            # If we have saved state (equity or IQ), use it
            if saved_equity is not None or saved_iq > 0 or saved_training_history["training_sessions"] > 0:
                equity = saved_equity if saved_equity is not None else self.config.initial_capital
                # Use stats from saved state file (not hardcoded zeros!)
                return {
                    "equity": equity,
                    "peak_equity": saved_peak_equity if saved_peak_equity is not None else equity,
                    "daily_pnl": saved_daily_pnl,
                    "daily_start_equity": saved_daily_start_equity if saved_daily_start_equity is not None else equity,
                    "stats": {
                        "total_trades": saved_stats.get("total_trades", 0),
                        "winning_trades": saved_stats.get("winning_trades", 0),
                        "total_pnl": saved_stats.get("total_pnl", 0.0),
                        "signals_analyzed": saved_stats.get("signals_analyzed", 0),
                        "start_time": saved_stats.get("start_time"),
                        "trading_iq": saved_iq,
                        "expertise_level": saved_level,
                        **saved_training_history,
                    }
                }
            logger.info("No trades database found, starting fresh")
            return None

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Get stats from database (same queries as engine.get_summary)
            cur.execute("SELECT COUNT(*) FROM trades")
            total_trades = cur.fetchone()[0]

            cur.execute("SELECT SUM(pnl) FROM trades WHERE pnl IS NOT NULL")
            total_pnl = cur.fetchone()[0] or 0.0

            cur.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
            winning_trades = cur.fetchone()[0]

            conn.close()

            if total_trades > 0 or saved_equity is not None or saved_iq > 0 or saved_training_history["training_sessions"] > 0:
                # Use saved equity if available, otherwise calculate from initial capital + P&L
                if saved_equity is not None:
                    equity = saved_equity
                else:
                    equity = self.config.initial_capital + total_pnl

                state = {
                    "equity": equity,
                    "peak_equity": saved_peak_equity if saved_peak_equity is not None else max(equity, self.config.initial_capital),
                    "daily_pnl": saved_daily_pnl,
                    "daily_start_equity": saved_daily_start_equity if saved_daily_start_equity is not None else equity,
                    "stats": {
                        "total_trades": total_trades,
                        "winning_trades": winning_trades,
                        "total_pnl": total_pnl,
                        "signals_analyzed": 0,
                        "start_time": None,
                        "trading_iq": saved_iq,
                        "expertise_level": saved_level,
                        **saved_training_history,
                    }
                }
                logger.info(f"Loaded state from database: {total_trades} trades, equity=${equity:.2f}, IQ={saved_iq}")
                return state
            else:
                logger.info("Trades database exists but is empty, starting fresh")

        except Exception as e:
            logger.warning(f"Failed to load state from database: {e}")

        return None

    def _load_positions(self) -> Dict[str, Position]:
        """Load open positions from trades database"""
        import sqlite3
        project_root = Path(__file__).parent
        db_path = project_root / "data" / "trades.db"

        positions = {}

        if not db_path.exists():
            return positions

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Get all trades to determine open positions (same logic as engine.py)
            cur.execute("""
                SELECT id, timestamp, symbol, signal, last_price, entry_price, pnl, created_at
                FROM trades
                ORDER BY timestamp ASC
            """)

            all_trades = cur.fetchall()
            conn.close()

            # Track positions per symbol
            position_data = {}

            for trade in all_trades:
                trade_id, timestamp, symbol, signal, last_price, entry_price, pnl, created_at = trade

                if symbol not in position_data:
                    position_data[symbol] = {
                        "symbol": symbol,
                        "entry_time": timestamp,
                        "entry_price": entry_price or last_price,
                        "current_price": last_price,
                        "trade_count": 0,
                        "signal": signal,
                    }

                position_data[symbol]["trade_count"] += 1
                position_data[symbol]["current_price"] = last_price
                position_data[symbol]["signal"] = signal

            # Create Position objects for open positions (odd trade count)
            for symbol, data in position_data.items():
                if data["trade_count"] % 2 == 1:  # Odd = open position
                    try:
                        entry_time = datetime.fromisoformat(data["entry_time"]) if data["entry_time"] else datetime.now()
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not parse entry_time for {symbol}: {e}")
                        entry_time = datetime.now()

                    # Determine side from signal
                    side = "long" if data["signal"] == "BUY" else "short"

                    # Calculate position size (use a default based on config)
                    position_size = self.config.initial_capital * self.config.max_position_pct

                    entry_price = data["entry_price"]
                    current_price = data["current_price"]

                    # Calculate unrealized P&L based on last known price
                    if entry_price > 0 and current_price > 0:
                        if side == "long":
                            unrealized_pnl = (current_price - entry_price) / entry_price * position_size
                        else:
                            unrealized_pnl = (entry_price - current_price) / entry_price * position_size
                    else:
                        unrealized_pnl = 0.0

                    # Calculate stop/take profit from config (not hardcoded)
                    stop_loss = entry_price * (1 - self.config.stop_loss_pct if side == "long" else 1 + self.config.stop_loss_pct)
                    take_profit = entry_price * (1 + self.config.take_profit_pct if side == "long" else 1 - self.config.take_profit_pct)

                    positions[symbol] = Position(
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        size=position_size,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        entry_time=entry_time,
                        signal_source="restored",
                        unrealized_pnl=unrealized_pnl
                    )

                    logger.info(f"Restored position: {side} {symbol} @ ${entry_price:.2f}, unrealized P&L: ${unrealized_pnl:.2f}")

            if positions:
                logger.info(f"Restored {len(positions)} open positions from database")

        except Exception as e:
            logger.warning(f"Failed to load positions from database: {e}")

        return positions

    def _load_trade_history(self) -> List[TradeRecord]:
        """Load trade history from bot_state.json"""
        project_root = Path(__file__).parent
        state_file = project_root / "data" / "bot_state.json"

        trade_history = []

        if not state_file.exists():
            return trade_history

        try:
            with open(state_file) as f:
                saved_data = json.load(f)

            trade_history_data = saved_data.get("trade_history", [])

            for trade_data in trade_history_data:
                # Parse datetime strings
                entry_time = trade_data.get("entry_time")
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time)

                exit_time = trade_data.get("exit_time")
                if isinstance(exit_time, str):
                    exit_time = datetime.fromisoformat(exit_time)

                trade = TradeRecord(
                    symbol=trade_data.get("symbol", ""),
                    side=trade_data.get("side", ""),
                    entry_price=trade_data.get("entry_price", 0.0),
                    exit_price=trade_data.get("exit_price", 0.0),
                    size=trade_data.get("size", 0.0),
                    pnl=trade_data.get("pnl", 0.0),
                    pnl_pct=trade_data.get("pnl_pct", 0.0),
                    entry_time=entry_time,
                    exit_time=exit_time,
                    signal_source=trade_data.get("signal_source", ""),
                    exit_reason=trade_data.get("exit_reason", ""),
                )
                trade_history.append(trade)

            if trade_history:
                logger.info(f"Restored {len(trade_history)} trades from history")

        except Exception as e:
            logger.warning(f"Failed to load trade history: {e}")

        return trade_history

    def _save_state(self):
        """Save bot state to file (atomic write using temp file + rename)"""
        # Use absolute path relative to this file (same as _load_state does)
        project_root = Path(__file__).parent
        state_file = project_root / "data" / "bot_state.json"
        temp_file = project_root / "data" / "bot_state.json.tmp"

        try:
            os.makedirs(project_root / "data", exist_ok=True)
            logger.debug(f"Saving state to: {state_file}")

            # Convert trade history to serializable format
            trade_history_data = []
            for trade in self.trade_history:
                trade_history_data.append({
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "size": trade.size,
                    "pnl": trade.pnl,
                    "pnl_pct": trade.pnl_pct,
                    "entry_time": trade.entry_time.isoformat() if isinstance(trade.entry_time, datetime) else trade.entry_time,
                    "exit_time": trade.exit_time.isoformat() if isinstance(trade.exit_time, datetime) else trade.exit_time,
                    "signal_source": trade.signal_source,
                    "exit_reason": trade.exit_reason,
                })

            state = {
                "equity": self.equity,
                "peak_equity": self.peak_equity,
                "daily_pnl": self.daily_pnl,
                "daily_start_equity": self.daily_start_equity,
                "stats": self.stats.copy(),  # Make a copy to avoid modifying original
                "trade_history": trade_history_data,  # Save full trade history
                "last_updated": datetime.now().isoformat()
            }
            # Handle datetime in stats
            if state["stats"].get("start_time"):
                state["stats"]["start_time"] = state["stats"]["start_time"].isoformat() if isinstance(state["stats"]["start_time"], datetime) else state["stats"]["start_time"]

            # ATOMIC WRITE: Write to temp file first, then rename
            # This prevents corrupt state files from crashes during write
            with open(temp_file, "w") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

            # Atomic rename (works on POSIX systems including Linux)
            os.replace(temp_file, state_file)

            logger.debug(f"State saved: equity=${self.equity:.2f}, IQ={self.stats.get('trading_iq', 0)}")
        except Exception as e:
            logger.error(f"FAILED to save state: {e}", exc_info=True)
            # Clean up temp file if it exists
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass

    def _save_mode_to_config(self, mode: str):
        """Save mode to bot_config.json so next start uses correct mode"""
        project_root = Path(__file__).parent
        config_path = project_root / "config" / "bot_config.json"
        try:
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                config["mode"] = mode
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                logger.info(f"Config mode updated to '{mode}'")
        except Exception as e:
            logger.warning(f"Failed to update config mode: {e}")

    async def _sync_positions_with_exchange(self):
        """
        Synchronize local position state with actual exchange positions.
        Detects phantom positions (local but not on exchange) and
        orphan positions (on exchange but not tracked locally).
        """
        if self.config.mode != "live" or not self.exchange:
            return

        try:
            # Get actual positions from exchange
            exchange_positions = await self.exchange.get_positions()

            # Build set of symbols with open positions on exchange
            exchange_symbols = set()
            for pos in exchange_positions:
                if pos and pos.get("contracts", 0) != 0:
                    symbol = pos.get("symbol")
                    if symbol:
                        exchange_symbols.add(symbol)

            # Check for phantom positions (local but not on exchange)
            local_symbols = set(self.positions.keys())
            phantom_positions = local_symbols - exchange_symbols

            for symbol in phantom_positions:
                logger.warning(f"PHANTOM POSITION DETECTED: {symbol} exists locally but not on exchange")
                # The position may have been closed externally (e.g., by exchange stop)
                pos = self.positions[symbol]
                # Close the phantom position at last known price
                price = self.prices.get(symbol, pos.entry_price)
                await self._close_position(symbol, price, "phantom_cleanup")

            # Check for orphan positions (on exchange but not tracked)
            # CRITICAL: Auto-recover orphan positions to local state for tracking
            orphan_positions = exchange_symbols - local_symbols

            for symbol in orphan_positions:
                logger.warning(f"ORPHAN POSITION DETECTED: {symbol} exists on exchange but not tracked locally")
                # Find the position details and recover to local state
                for pos in exchange_positions:
                    if pos.get("symbol") == symbol:
                        contracts = pos.get("contracts", 0)
                        entry_price = pos.get("entryPrice", 0) or pos.get("averagePrice", 0)
                        side = "long" if contracts > 0 else "short"
                        position_value = abs(contracts) * entry_price

                        logger.warning(f"  RECOVERING orphan position: {side} {abs(contracts):.6f} @ ${entry_price:.2f}")

                        # Create Position object to track it locally
                        recovered_position = Position(
                            symbol=symbol,
                            side=side,
                            entry_price=entry_price,
                            size=position_value,
                            stop_loss=entry_price * (0.98 if side == "long" else 1.02),  # Default 2% stop
                            take_profit=entry_price * (1.04 if side == "long" else 0.96),  # Default 4% TP
                            entry_time=datetime.now(),  # Unknown, use current time
                            signal_source="recovered_from_exchange",
                            actual_contracts=abs(contracts),
                            entry_order_id=pos.get("id"),
                        )
                        self.positions[symbol] = recovered_position

                        # Log to audit trail
                        if self.audit:
                            self.audit.log_event(
                                event_type="POSITION_RECOVERED",
                                details={
                                    "symbol": symbol,
                                    "side": side,
                                    "contracts": abs(contracts),
                                    "entry_price": entry_price,
                                    "reason": "orphan_position_recovery"
                                }
                            )

                        logger.info(f"  Position {symbol} recovered and now tracked locally")
                        break

            # Also sync account balance
            balance = await self.exchange.get_balance()
            if balance:
                total_balance = balance.get("total", {}).get("USDT", 0) or \
                               balance.get("total", {}).get("USD", 0)
                if total_balance > 0:
                    # Log if significant discrepancy (>5%)
                    local_equity = self.equity
                    diff_pct = abs(total_balance - local_equity) / local_equity if local_equity else 0
                    if diff_pct > 0.05:
                        logger.warning(f"Balance discrepancy: Local=${local_equity:.2f}, Exchange=${total_balance:.2f} ({diff_pct:.1%} diff)")

            logger.debug("Position sync completed successfully")

        except Exception as e:
            logger.warning(f"Position sync failed: {e}")

    async def start(self):
        """Start the trading bot"""
        logger.info("=" * 50)
        logger.info(f"{APP_NAME} Pro v{APP_VERSION} Starting...")
        logger.info("=" * 50)
        logger.info(f"Mode: {self.config.mode}")
        logger.info(f"Symbols: {self.config.symbols}")
        # Show actual equity (from saved state) not just initial config value
        if self.equity != self.config.initial_capital:
            logger.info(f"Current Equity: ${self.equity:,.2f} (started with ${self.config.initial_capital:,.2f})")
        else:
            logger.info(f"Capital: ${self.config.initial_capital:,.2f}")

        # CRITICAL WARNING: Sandbox mode
        if self.config.sandbox:
            logger.warning("=" * 50)
            logger.warning("[WARNING] SANDBOX MODE ENABLED - Using testnet/demo exchange")
            logger.warning("[WARNING] No real funds will be used. Set sandbox=False for live trading.")
            logger.warning("=" * 50)
        elif self.config.mode == "live":
            logger.warning("=" * 50)
            logger.warning("[ALERT] LIVE TRADING MODE - REAL FUNDS AT RISK!")
            logger.warning("[ALERT] Ensure you have reviewed all settings carefully!")
            logger.warning("=" * 50)

        logger.info("=" * 50)

        self.running = True
        self.stats["start_time"] = datetime.now()
        self._started_in_training_mode = (self.config.mode == "training")

        # Initialize components
        await self._initialize_components()

        # Main loop
        try:
            if self.config.mode == "training":
                # Set training state immediately so API reflects it
                self.training_progress["is_training"] = True
                self.training_progress["total_episodes"] = self.config.train_episodes
                await self._training_loop()
            else:
                await self._trading_loop()
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
        finally:
            await self.stop()

    async def _initialize_components(self):
        """Initialize all trading components"""
        logger.info("Initializing components...")

        # 1. Exchange connector (optional for paper mode)
        self._demo_mode = False
        self.exchange = create_connector(
            self.config.exchange,
            self.config.api_key,
            self.config.api_secret,
            sandbox=self.config.sandbox
        )

        if self.config.mode != "training":
            connected = await self.exchange.connect()
            if not connected:
                if self.config.mode == "paper":
                    logger.warning("=" * 60)
                    logger.warning("[WARNING] EXCHANGE CONNECTION FAILED - DEMO MODE ACTIVATED")
                    logger.warning("[WARNING] Using SIMULATED prices - NOT real market data!")
                    logger.warning("[WARNING] This is for testing only. Results may not reflect real trading.")
                    logger.warning("=" * 60)
                    self._demo_mode = True
                    # Initialize with simulated prices
                    self._init_demo_prices()
                else:
                    raise RuntimeError("Failed to connect to exchange")
            else:
                logger.info(f"Connected to {self.config.exchange}")

        # 2. Live data feed (skip in demo mode)
        if not self._demo_mode:
            self.data_feed = create_live_feed(
                self.config.exchange,
                self.config.api_key,
                self.config.api_secret,
                sandbox=self.config.sandbox
            )

            if self.config.mode != "training":
                # Register price update callback
                self.data_feed.on_price(self._on_price_update)

                try:
                    await self.data_feed.start(
                        symbols=self.config.symbols,
                        timeframes=["1m", "5m", "1h"]
                    )
                    logger.info("Live data feed started")

                    # Verify historical candles were loaded
                    candle_status = []
                    for symbol in self.config.symbols[:3]:  # Check first 3 symbols
                        candles = self.data_feed.get_candles(symbol, "1h", 50)
                        candle_status.append(f"{symbol}: {len(candles)}")
                    logger.info(f"Historical candles loaded: {', '.join(candle_status)}")

                except Exception as e:
                    logger.warning(f"Live data feed failed: {e} - continuing in demo mode")
                    self._demo_mode = True
                    self._init_demo_prices()

        # 3. Alternative data (optional - requires aiohttp)
        if self.config.use_alternative_data and ALT_DATA_AVAILABLE:
            self.alt_data = create_alternative_feed()
            self.edge_detector = EdgeDetector(self.alt_data)
            logger.info("Alternative data feed initialized")
        elif self.config.use_alternative_data:
            logger.warning("Alternative data requested but modules not available")

        # 4. Edge strategies (optional)
        if self.config.use_edge_strategies and EDGE_AVAILABLE:
            base_symbols = [s.split("/")[0] for s in self.config.symbols]
            self.edge_manager = create_edge_manager(base_symbols)
            logger.info("Edge strategies initialized")
        elif self.config.use_edge_strategies:
            logger.warning("Edge strategies requested but modules not available")

        # 5. RL Agent (optional - requires PyTorch)
        if self.config.use_rl_agent and RL_AVAILABLE:
            # Only load historical training data when actually training
            # For paper/live trading, we just need the trained model
            if self.config.mode == "training" and load_historical_data_sync:
                # Validate symbols are configured
                if not self.config.symbols:
                    error_msg = "No symbols selected! Please select trading symbols in Settings before training."
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.info("Loading real historical data from Kraken for training...")
                training_symbols = self.config.symbols  # Use ALL configured symbols
                data = load_historical_data_sync(
                    symbols=training_symbols,
                    timeframe=self.config.train_timeframe,
                    days=self.config.train_history_days
                )
                if data:
                    logger.info(f"Loaded real data for {len(data)} symbols - Training will use REAL market data!")
                else:
                    logger.warning("Failed to load real data - training will use simulated data")

            self.rl_env = TradingEnvironment(
                initial_balance=self.config.initial_capital,
                max_position_size=self.config.max_position_pct,
                max_steps=self.config.rl_max_steps,
                inference_only=(self.config.mode != "training")  # Skip dummy data in paper/live
            )

            self.rl_agent = create_agent(
                "ppo",
                state_dim=self.rl_env.observation_space_dim,
                action_dim=self.rl_env.action_space_dim,
                n_epochs=self.config.rl_n_epochs,
                batch_size=self.config.rl_batch_size
            )

            # Load existing model if available
            if os.path.exists(self.config.rl_model_path):
                self.rl_agent.load(self.config.rl_model_path)
                logger.info(f"Loaded RL model from {self.config.rl_model_path}")
            else:
                logger.info("No existing RL model found - starting fresh")
        elif self.config.use_rl_agent:
            logger.warning("RL agent requested but PyTorch not available - trading without AI")

        # 6. Sync positions with exchange on startup (live mode only)
        if self.config.mode == "live" and not self._demo_mode:
            logger.info("Syncing positions with exchange...")
            await self._sync_positions_with_exchange()

        # 7. Health check server (for monitoring)
        if HEALTH_CHECK_AVAILABLE and self.config.health_check_enabled:
            self._health_server = HealthCheckServer(
                port=self.config.health_check_port,
                status_callback=self._get_health_status,
                dead_mans_switch_timeout=float(self.config.dead_mans_switch_timeout),
                dead_mans_switch_callback=self._on_dead_mans_switch if self.config.dead_mans_switch_close_positions else None,
                dead_mans_switch_enabled=self.config.dead_mans_switch_enabled
            )
            await self._health_server.start()

        logger.info("All components initialized")

    def _on_price_update(self, update):
        """Handle real-time price updates"""
        self.prices[update.symbol] = update.price
        self._last_price_update = datetime.now()

        # Resume trading if it was paused due to stale feed
        if self._trading_paused_due_to_feed:
            logger.info("Price feed restored - resuming trading")
            self._trading_paused_due_to_feed = False

        # Update position P&L
        if update.symbol in self.positions:
            pos = self.positions[update.symbol]
            if pos.entry_price > 0:  # Protect against division by zero
                if pos.side == "long":
                    pos.unrealized_pnl = (update.price - pos.entry_price) / pos.entry_price * pos.size
                else:
                    pos.unrealized_pnl = (pos.entry_price - update.price) / pos.entry_price * pos.size

    def _init_demo_prices(self):
        """Initialize demo prices for offline/demo mode"""
        import random
        # Realistic starting prices for top coins (supports both USD and USDT pairs)
        base_prices = {
            # Top coins - Kraken verified
            "BTC": 97000.0, "ETH": 3500.0, "SOL": 250.0,
            "XRP": 1.40, "DOGE": 0.40, "ADA": 1.00,
            "AVAX": 45.0, "DOT": 9.0, "LINK": 18.0,
            "ATOM": 12.0, "UNI": 12.0, "LTC": 95.0,
            "BCH": 500.0, "XLM": 0.35, "ALGO": 0.35,
            "POL": 0.50, "FIL": 6.5, "APE": 1.50,
            "AAVE": 180.0, "CRV": 0.50, "MKR": 1800.0,
            "COMP": 60.0, "SNX": 3.0, "GRT": 0.25,
            "SAND": 0.50, "MANA": 0.45, "AXS": 8.0,
            "ENJ": 0.30, "BAT": 0.25, "ZEC": 50.0,
            "DASH": 35.0, "EOS": 0.80, "XTZ": 1.10,
            "TRX": 0.20, "ETC": 32.0, "SHIB": 0.000025,
            "PEPE": 0.00001, "OP": 2.50, "ARB": 1.20,
            "INJ": 35.0, "RUNE": 6.0, "KAVA": 0.50,
            "STORJ": 0.60, "SUSHI": 1.20, "YFI": 8000.0,
            "1INCH": 0.40, "RNDR": 8.0, "FET": 1.50,
            "IMX": 2.0, "APT": 12.0,
            # Legacy/fallback
            "BNB": 650.0, "MATIC": 0.50, "HBAR": 0.12,
            "NEAR": 6.50, "FTM": 1.10, "CHZ": 0.10, "OCEAN": 0.50,
        }
        # Build demo_prices dict with both USD and USDT pairs
        demo_prices = {}
        for base, price in base_prices.items():
            demo_prices[f"{base}/USD"] = price
            demo_prices[f"{base}/USDT"] = price
        self._price_history = {}
        for symbol in self.config.symbols:
            base_price = demo_prices.get(symbol, 100.0)
            self.prices[symbol] = base_price
            # Pre-fill price history so trading can start immediately
            self._price_history[symbol] = [
                base_price * (1 + random.uniform(-0.01, 0.01)) for _ in range(10)
            ]
        logger.info(f"Demo prices initialized: {self.prices}")

    async def _update_demo_prices(self):
        """Simulate price movements in demo mode"""
        import random
        for symbol in self.prices:
            # Random walk: -2% to +2% per update (active demo)
            change = random.uniform(-0.02, 0.02)
            self.prices[symbol] *= (1 + change)
            price = self.prices[symbol]

            # Track price history for strategy
            if not hasattr(self, '_price_history'):
                self._price_history = {}
            if symbol not in self._price_history:
                self._price_history[symbol] = []
            self._price_history[symbol].append(price)
            # Keep last 20 prices
            self._price_history[symbol] = self._price_history[symbol][-20:]

            # Update position P&L for demo mode
            if symbol in self.positions:
                pos = self.positions[symbol]
                if pos.entry_price > 0:  # Protect against division by zero
                    if pos.side == "long":
                        pos.unrealized_pnl = (price - pos.entry_price) / pos.entry_price * pos.size
                    else:
                        pos.unrealized_pnl = (pos.entry_price - price) / pos.entry_price * pos.size

    async def _fetch_prices_rest(self):
        """Fetch prices via REST API as fallback when WebSocket isn't working"""
        if not self.exchange:
            return

        try:
            tickers = await self.exchange.get_tickers(self.config.symbols)
            if tickers:
                updated_count = 0
                for symbol, ticker in tickers.items():
                    if ticker.last and ticker.last > 0:
                        self.prices[symbol] = ticker.last
                        updated_count += 1

                        # Also update position P&L when prices update
                        if symbol in self.positions:
                            pos = self.positions[symbol]
                            if pos.entry_price > 0:  # Protect against division by zero
                                if pos.side == "long":
                                    pos.unrealized_pnl = (ticker.last - pos.entry_price) / pos.entry_price * pos.size
                                else:
                                    pos.unrealized_pnl = (pos.entry_price - ticker.last) / pos.entry_price * pos.size

                if updated_count > 0:
                    self._last_price_update = datetime.now()
                    # Resume trading if it was paused
                    if self._trading_paused_due_to_feed:
                        logger.info("Price feed restored via REST API - resuming trading")
                        self._trading_paused_due_to_feed = False
                    logger.debug(f"REST API updated {updated_count} prices")
        except Exception as e:
            logger.warning(f"REST API price fetch failed: {e}")

    async def _refresh_candles_rest(self):
        """Periodically refresh candle data via REST API when WebSocket fails"""
        if not self.data_feed or not hasattr(self.data_feed, 'connector'):
            return

        try:
            refreshed_count = 0
            for symbol in self.config.symbols:
                try:
                    # Fetch fresh 1h candles (most important for RL)
                    candles = await self.data_feed.connector.get_ohlcv(symbol, "1h", limit=100)
                    if candles:
                        # Update the data feed cache
                        if symbol not in self.data_feed._candle_cache:
                            self.data_feed._candle_cache[symbol] = {}
                        if "1h" not in self.data_feed._candle_cache[symbol]:
                            from collections import deque
                            self.data_feed._candle_cache[symbol]["1h"] = deque(maxlen=1000)

                        # Clear and refill with fresh data
                        self.data_feed._candle_cache[symbol]["1h"].clear()
                        for candle in candles:
                            self.data_feed._candle_cache[symbol]["1h"].append(candle)
                        refreshed_count += 1
                except Exception as e:
                    logger.debug(f"Failed to refresh candles for {symbol}: {e}")

            if refreshed_count > 0:
                logger.info(f"Refreshed candles for {refreshed_count}/{len(self.config.symbols)} symbols via REST")
        except Exception as e:
            logger.warning(f"Candle refresh failed: {e}")

    async def _demo_strategy(self, symbol: str, price: float):
        """Simple momentum strategy for demo mode - ACTUALLY TRADES"""
        import random

        # Skip if already have position
        if symbol in self.positions:
            return None

        # Initialize trade counter for immediate first trade
        if not hasattr(self, '_demo_trade_count'):
            self._demo_trade_count = 0

        # Need price history
        if not hasattr(self, '_price_history') or symbol not in self._price_history:
            return None

        history = self._price_history[symbol]
        if len(history) < 3:  # Reduced from 5 to 3
            return None

        # Calculate momentum (price change over last 3 periods)
        momentum = (price - history[-3]) / history[-3] if history[-3] > 0 else 0

        # Generate signal based on momentum
        signal = None

        # FIRST TRADE: Always make a trade quickly to show bot is working
        if self._demo_trade_count < 2:
            self._demo_trade_count += 1
            direction = "long" if momentum >= 0 else "short"
            signal = self._create_signal(
                symbol, price, direction, 0.75, "demo_kickstart",
                f"Initial demo trade #{self._demo_trade_count}"
            )
            logger.info(f"DEMO SIGNAL: {direction.upper()} {symbol} - kickstart trade #{self._demo_trade_count}")
            return signal

        # Momentum up = BUY (lower threshold: 0.3% instead of 1%)
        if momentum > 0.003:
            signal = self._create_signal(
                symbol, price, "long", 0.7, "demo_momentum",
                f"Bullish momentum: {momentum:.2%}"
            )
            logger.info(f"DEMO SIGNAL: BUY {symbol} - momentum {momentum:.2%}")

        # Momentum down = mean reversion buy
        elif momentum < -0.003:
            signal = self._create_signal(
                symbol, price, "long", 0.65, "demo_mean_reversion",
                f"Mean reversion: oversold {momentum:.2%}"
            )
            logger.info(f"DEMO SIGNAL: BUY {symbol} (mean reversion) - dip {momentum:.2%}")

        # Random trade occasionally (increased to 35% chance)
        elif random.random() < 0.35:
            direction = random.choice(["long", "short"])
            signal = self._create_signal(
                symbol, price, direction, 0.65, "demo_random",
                f"Demo trade for testing"
            )
            logger.info(f"DEMO SIGNAL: {direction.upper()} {symbol} - random demo trade")

        return signal

    def _create_signal(self, symbol, price, direction, confidence, edge_type, reason):
        """Create a signal dict (works without TradeSignal class)"""
        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "edge_type": edge_type,
            "entry_price": price,
            "reason": reason,
        }

    async def _trading_loop(self):
        """Main trading loop"""
        logger.info("Entering main trading loop...")
        if self._demo_mode:
            logger.info("Running in DEMO mode - prices are simulated")

        # Track time for periodic saves
        last_save_time = datetime.now()
        save_interval = self.config.state_save_interval

        # Track time for periodic candle refresh (fallback when WebSocket fails)
        last_candle_refresh = datetime.now()
        candle_refresh_interval = self.config.candle_refresh_interval

        # Track time for position sync with exchange
        last_position_sync = datetime.now()
        position_sync_interval = self.config.position_sync_interval

        while self.running:
            try:
                # Update heartbeat for health monitoring
                if self._health_server:
                    self._health_server.update_heartbeat()

                # Update prices - demo mode uses simulation, live mode uses REST API fallback
                if self._demo_mode:
                    await self._update_demo_prices()
                else:
                    # Rate-limit REST API fetches to reduce load
                    time_since_rest = (datetime.now() - self._last_rest_fetch).total_seconds()
                    if time_since_rest >= self.config.rest_api_interval_seconds:
                        # Fetch fresh prices via REST API to ensure P&L is accurate
                        # This supplements WebSocket data which may be stale or disconnected
                        await self._fetch_prices_rest()
                        self._last_rest_fetch = datetime.now()

                # Check price feed health (only in non-demo mode)
                if not self._demo_mode:
                    time_since_update = (datetime.now() - self._last_price_update).total_seconds()
                    if time_since_update > self._price_feed_stale_threshold:
                        if not self._trading_paused_due_to_feed:
                            logger.warning("=" * 60)
                            logger.warning("[WARNING] PRICE FEED STALE - PAUSING NEW TRADES")
                            logger.warning(f"[WARNING] No price updates for {time_since_update:.0f} seconds")
                            logger.warning("[WARNING] Existing positions will NOT be auto-closed.")
                            logger.warning("[WARNING] Trading will resume when price feed is restored.")
                            logger.warning("=" * 60)
                            self._trading_paused_due_to_feed = True

                            # Publish event to WebSocket clients
                            event_bus.publish("TRADING_SIGNAL", {
                                "symbol": "SYSTEM",
                                "action": "PAUSED",
                                "price": 0,
                                "strength": 0,
                                "reason": ["Price feed stale", f"No updates for {time_since_update:.0f}s"],
                                "timestamp": datetime.now().isoformat()
                            })

                # Periodically refresh candles via REST (fallback when WebSocket fails)
                if not self._demo_mode and self.data_feed:
                    time_since_candle_refresh = (datetime.now() - last_candle_refresh).total_seconds()
                    if time_since_candle_refresh >= candle_refresh_interval:
                        try:
                            await self._refresh_candles_rest()
                            last_candle_refresh = datetime.now()
                        except Exception as e:
                            logger.debug(f"Candle refresh failed: {e}")

                # Periodic position sync with exchange (live mode only)
                if self.config.mode == "live" and not self._demo_mode:
                    time_since_sync = (datetime.now() - last_position_sync).total_seconds()
                    if time_since_sync >= position_sync_interval:
                        try:
                            await self._sync_positions_with_exchange()
                            last_position_sync = datetime.now()
                        except Exception as e:
                            logger.warning(f"Position sync failed: {e}")

                # Reset daily stats at midnight
                await self._check_daily_reset()

                # Check risk limits
                if not self._check_risk_limits():
                    logger.warning("Risk limits exceeded - pausing trading")
                    await asyncio.sleep(60)
                    continue

                # Skip analysis if price feed is stale (but still check exits for existing positions)
                if not self._trading_paused_due_to_feed:
                    # Analyze each symbol
                    for symbol in self.config.symbols:
                        await self._analyze_symbol(symbol)

                # Check open positions for exits
                await self._check_exits()

                # Update equity
                self._update_equity()

                # Log status
                self._log_status()

                # Periodic state save (every 5 minutes)
                if (datetime.now() - last_save_time).total_seconds() >= save_interval:
                    self._save_state()
                    last_save_time = datetime.now()
                    logger.debug("Periodic state save completed")

                # Wait for next cycle
                await asyncio.sleep(self.config.analysis_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trading loop error: {e}", exc_info=True)
                await asyncio.sleep(10)

    def _build_rl_observation(self, symbol: str, candles: list) -> Optional[np.ndarray]:
        """
        Build the full RL observation matching training environment.

        Returns 1007-feature observation:
        - 50 candles × 20 technical indicators = 1000 features
        - 4 position features (side, unrealized P&L, holding time, size)
        - 3 account features (equity change, drawdown, recent volatility)
        """
        if not candles or len(candles) < 50:
            return None

        try:
            # Convert candles to OHLCV numpy array format
            # calculate_features expects: [timestamp, open, high, low, close, volume]
            ohlcv_data = []
            for c in candles[-50:]:  # Use last 50 candles
                if hasattr(c, 'timestamp'):
                    ts = c.timestamp.timestamp() * 1000 if hasattr(c.timestamp, 'timestamp') else float(c.timestamp)
                else:
                    ts = 0
                ohlcv_data.append([
                    ts,
                    float(c.open) if hasattr(c, 'open') else float(c.get('open', 0)),
                    float(c.high) if hasattr(c, 'high') else float(c.get('high', 0)),
                    float(c.low) if hasattr(c, 'low') else float(c.get('low', 0)),
                    float(c.close) if hasattr(c, 'close') else float(c.get('close', 0)),
                    float(c.volume) if hasattr(c, 'volume') else float(c.get('volume', 0)),
                ])

            ohlcv_array = np.array(ohlcv_data, dtype=np.float64)

            # Calculate technical features using the same function as training
            if calculate_features is None:
                return None
            features = calculate_features(ohlcv_array)

            if features is None or len(features) < 50:
                return None

            # Build observation matching training environment's _get_observation()
            obs = []

            # Use the last 50 candles of features (lookback_window=50)
            window_data = features[-50:]

            # Normalize price features (same as training)
            price_mean = np.mean(window_data[:, 0])
            price_std = np.std(window_data[:, 0]) + 1e-8
            normalized_prices = (window_data[:, 0] - price_mean) / price_std
            obs.extend(normalized_prices.flatten())

            # Add other features (already normalized in calculate_features)
            for i in range(1, min(20, window_data.shape[1])):
                feature = window_data[:, i]
                feature = np.clip(feature, -5, 5)  # Clip extreme values
                obs.extend(feature.flatten())

            # Pad if needed to reach 1000 price features
            while len(obs) < 50 * 20:
                obs.append(0.0)

            # Position features (4 features)
            position = self.positions.get(symbol)
            if position:
                # Position side encoding
                position_encoding = {"flat": 0.0, "long": 1.0, "short": -1.0}
                obs.append(position_encoding.get(position.side, 0.0))
                # Unrealized P&L (normalized)
                unrealized_pnl_pct = position.unrealized_pnl / self.config.initial_capital
                obs.append(np.clip(unrealized_pnl_pct, -1, 1))
                # Holding time (normalized) - assume entry_time is datetime
                if hasattr(position, 'entry_time') and position.entry_time:
                    holding_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
                    obs.append(np.clip(holding_hours / 100, 0, 1))
                else:
                    obs.append(0.0)
                # Position size (normalized)
                obs.append(position.size / self.config.initial_capital if self.config.initial_capital else 0)
            else:
                # No position - flat state
                obs.extend([0.0, 0.0, 0.0, 0.0])

            # Account features (3 features)
            # Equity change
            equity_change = (self.equity - self.config.initial_capital) / self.config.initial_capital
            obs.append(np.clip(equity_change, -1, 1))

            # Drawdown
            drawdown = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity else 0
            obs.append(np.clip(drawdown, 0, 1))

            # Recent volatility (use daily P&L as proxy)
            recent_vol = abs(self.daily_pnl / self.equity) if self.equity else 0
            obs.append(np.clip(recent_vol * 10, 0, 1))

            return np.array(obs, dtype=np.float32)

        except Exception as e:
            logger.warning(f"Error building RL observation for {symbol}: {e}")
            return None

    async def _analyze_symbol(self, symbol: str):
        """Analyze a symbol for trading opportunities"""
        self.stats["signals_analyzed"] += 1

        base_symbol = symbol.split("/")[0]
        price = self.prices.get(symbol, 0)

        if price <= 0:
            return

        signals = []

        # DEMO MODE: Use simple momentum strategy that actually trades
        if self._demo_mode:
            signal = await self._demo_strategy(symbol, price)
            if signal:
                signals.append(signal)
        else:
            # Production: Use edge strategies and alternative data
            # 1. Get edge strategy signals
            if self.edge_manager and EDGE_AVAILABLE:
                try:
                    alt_signals = {}
                    if self.alt_data:
                        alt_signals = await self.alt_data.get_alternative_signals(base_symbol)

                    edge_data = {
                        "symbol": base_symbol,
                        "price": price,
                        "funding_rate": alt_signals.get("funding", {}).get("rate", 0),
                        "fear_greed_index": alt_signals.get("sentiment", {}).get("fear_greed", 50),
                        "long_short_ratio": alt_signals.get("funding", {}).get("long_short_ratio", 1.0),
                    }

                    edge_signals = await self.edge_manager.analyze_all(edge_data)
                    signals.extend(edge_signals)
                except Exception as e:
                    logger.debug(f"Edge analysis error for {symbol}: {e}")

            # 2. Get alternative data signals
            if self.edge_detector:
                try:
                    recommendation = await self.edge_detector.get_trade_recommendation(base_symbol)
                    if recommendation["action"] != "hold" and recommendation["confidence"] > 0.5:
                        signals.append(self._create_signal(
                            symbol, price,
                            "long" if recommendation["action"] == "buy" else "short",
                            recommendation["confidence"],
                            "alternative_data",
                            recommendation.get("reason", "Alternative data signal")
                        ))
                except Exception as e:
                    logger.debug(f"Alt data error for {symbol}: {e}")

        # 3. Get RL agent signal
        if self.rl_agent:
            try:
                # Get candles for RL observation (need 50 for full technical indicator calculation)
                candles = self.data_feed.get_candles(symbol, "1h", 100) if self.data_feed else []

                if len(candles) < 50:
                    # Log this issue periodically (not every cycle)
                    if not hasattr(self, '_candle_warning_count'):
                        self._candle_warning_count = {}
                    self._candle_warning_count[symbol] = self._candle_warning_count.get(symbol, 0) + 1
                    if self._candle_warning_count[symbol] == 1 or self._candle_warning_count[symbol] % 60 == 0:
                        logger.warning(f"Insufficient candles for {symbol}: {len(candles)}/50 required (check #{self._candle_warning_count[symbol]})")
                else:
                    # Build proper RL observation with all 1007 features matching training
                    state = self._build_rl_observation(symbol, candles)

                    if state is not None:
                        action, log_prob, value = self.rl_agent.select_action(state, training=False)

                        # Convert log_prob to confidence (probability of chosen action)
                        # log_prob is negative, so exp(log_prob) gives probability [0, 1]
                        confidence = float(np.exp(log_prob))
                        # Ensure confidence is in reasonable range [0.5, 0.95]
                        confidence = max(0.5, min(0.95, confidence))

                        if action == 1:  # BUY
                            signals.append(TradeSignal(
                                symbol=symbol,
                                direction="long",
                                strength=2,
                                confidence=confidence,
                                edge_type="rl_agent",
                                entry_price=price,
                                reason=f"RL agent buy signal (conf: {confidence:.1%})"
                            ))
                        elif action == 2:  # SELL
                            signals.append(TradeSignal(
                                symbol=symbol,
                                direction="short",
                                strength=2,
                                confidence=confidence,
                                edge_type="rl_agent",
                                entry_price=price,
                                reason=f"RL agent sell signal (conf: {confidence:.1%})"
                            ))
            except Exception as e:
                logger.warning(f"RL signal error for {symbol}: {e}")

        # 4. Combine signals and decide
        if signals:
            # Use first signal (demo mode) or combine (production)
            if self._demo_mode or not self.edge_manager:
                combined = signals[0]
            else:
                combined = self.edge_manager.get_combined_signal(signals)

            # Get confidence (works with dict or object)
            conf = combined.get("confidence", 0) if isinstance(combined, dict) else getattr(combined, "confidence", 0)
            direction = combined.get("direction", "unknown") if isinstance(combined, dict) else getattr(combined, "direction", "unknown")
            edge_type = combined.get("edge_type", "unknown") if isinstance(combined, dict) else getattr(combined, "edge_type", "unknown")

            if combined and conf >= self.config.min_signal_confidence:
                await self._handle_signal(symbol, combined)
            elif combined and conf < self.config.min_signal_confidence:
                # Log low confidence rejection
                logger.debug(f"Signal rejected for {symbol}: confidence too low ({conf:.2%} < {self.config.min_signal_confidence:.2%})")
                if self.audit:
                    self.audit.log_signal_rejected(
                        symbol=symbol,
                        signal_type=f"{direction}_{edge_type}",
                        reason="low_confidence",
                        details={"confidence": conf, "min_required": self.config.min_signal_confidence}
                    )

    async def _place_stop_order(self, symbol: str, side: str, amount: float, stop_price: float) -> Optional[str]:
        """
        Place a stop-loss order on the exchange.

        Args:
            symbol: Trading pair
            side: Original position side ("long" or "short")
            amount: Position size in base currency
            stop_price: Price at which stop should trigger

        Returns:
            Order ID if successful, None otherwise
        """
        if not self.exchange or self.config.mode != "live":
            return None

        try:
            # Stop order is opposite of position side
            # Long position -> Sell stop (to close)
            # Short position -> Buy stop (to close)
            stop_side = OrderSide.SELL if side == "long" else OrderSide.BUY

            # Create stop-market order
            order = OrderRequest(
                symbol=symbol,
                side=stop_side,
                order_type=OrderType.STOP_LOSS,
                amount=amount,
                stop_price=stop_price,
                params={"stopPrice": stop_price, "type": "stop_market"}
            )

            result = await self.exchange.create_order(order)
            if result:
                return result.order_id
            return None

        except Exception as e:
            logger.warning(f"Failed to place stop order for {symbol}: {e}")
            return None

    async def _cancel_stop_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an existing stop order on the exchange."""
        if not self.exchange or not order_id:
            return False

        try:
            success = await self.exchange.cancel_order(order_id, symbol)
            if success:
                logger.info(f"Cancelled stop order {order_id} for {symbol}")
            return success
        except Exception as e:
            logger.warning(f"Failed to cancel stop order {order_id}: {e}")
            return False

    async def _handle_signal(self, symbol: str, signal):
        """Handle a trading signal (dict or TradeSignal object)"""
        # Acquire position lock for thread-safe modifications
        async with self._position_lock:
            await self._handle_signal_locked(symbol, signal)

    async def _handle_signal_locked(self, symbol: str, signal):
        """Internal signal handler (must be called with _position_lock held)"""
        # Helper to get attribute from dict or object
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        direction = get_attr(signal, "direction", "long")
        confidence = get_attr(signal, "confidence", 0.5)
        edge_type = get_attr(signal, "edge_type", "unknown")

        # Skip if already have position in this symbol
        if symbol in self.positions:
            logger.debug(f"Signal rejected for {symbol}: already have position")
            if self.audit:
                self.audit.log_signal_rejected(
                    symbol=symbol,
                    signal_type=f"{direction}_{edge_type}",
                    reason="position_exists",
                    details={"confidence": confidence}
                )
            return

        # Order deduplication - prevent rapid duplicate orders for same symbol
        now = datetime.now()
        if symbol in self._recent_orders:
            time_since_last = (now - self._recent_orders[symbol]).total_seconds()
            if time_since_last < self._order_dedup_window:
                logger.warning(f"Signal rejected for {symbol}: duplicate order (last order {time_since_last:.1f}s ago)")
                if self.audit:
                    self.audit.log_signal_rejected(
                        symbol=symbol,
                        signal_type=f"{direction}_{edge_type}",
                        reason="duplicate_order",
                        details={"seconds_since_last": time_since_last, "window": self._order_dedup_window}
                    )
                return

        # Clean up old entries from dedup tracker (older than 60 seconds)
        stale_cutoff = now - timedelta(seconds=60)
        self._recent_orders = {s: t for s, t in self._recent_orders.items() if t > stale_cutoff}

        # Comprehensive risk check using RiskManager (includes circuit breaker, drawdown, daily loss, max positions)
        current_drawdown = self.peak_equity - self.total_equity
        recent_trades = [
            {"timestamp": t.exit_time.isoformat() if isinstance(t.exit_time, datetime) else t.exit_time, "pnl": t.pnl}
            for t in self.trade_history[-10:]  # Last 10 trades
        ]
        risk_check = self.risk_manager.check_can_trade(
            current_equity=self.equity,
            current_drawdown=current_drawdown,
            open_positions_count=len(self.positions),
            recent_trades=recent_trades
        )
        if not risk_check["can_trade"]:
            logger.warning(f"Signal rejected for {symbol}: {risk_check['reason']} [{risk_check['code']}]")
            if self.audit:
                self.audit.log_signal_rejected(
                    symbol=symbol,
                    signal_type=f"{direction}_{edge_type}",
                    reason=risk_check["code"].lower(),
                    details={
                        "message": risk_check["reason"],
                        "confidence": confidence,
                        "daily_pnl": self.daily_pnl,
                        "drawdown": current_drawdown
                    }
                )
            return

        # Skip if price feed is stale
        if self._trading_paused_due_to_feed:
            logger.debug(f"Signal rejected for {symbol}: price feed stale")
            if self.audit:
                self.audit.log_signal_rejected(
                    symbol=symbol,
                    signal_type=f"{direction}_{edge_type}",
                    reason="price_feed_stale",
                    details={"confidence": confidence}
                )
            return

        reason = get_attr(signal, "reason", "")
        entry_price = get_attr(signal, "entry_price", 0)

        price = self.prices.get(symbol, entry_price or 0)
        if price <= 0:
            logger.debug(f"Signal rejected for {symbol}: invalid price ({price})")
            if self.audit:
                self.audit.log_signal_rejected(
                    symbol=symbol,
                    signal_type=f"{direction}_{edge_type}",
                    reason="invalid_price",
                    details={"price": price, "confidence": confidence}
                )
            return

        # Calculate position size
        position_value = self.equity * self.config.max_position_pct

        # Calculate stops
        if direction == "long":
            stop_loss = price * (1 - self.config.stop_loss_pct)
            take_profit = price * (1 + self.config.take_profit_pct)
        else:
            stop_loss = price * (1 + self.config.stop_loss_pct)
            take_profit = price * (1 - self.config.take_profit_pct)

        logger.info(f"SIGNAL: {direction.upper()} {symbol} @ ${price:.2f}")
        logger.info(f"  Confidence: {confidence:.1%}, Edge: {edge_type}")
        logger.info(f"  Reason: {reason}")

        # Execute based on mode
        if self.config.mode == "live":
            # PRE-TRADE BALANCE VERIFICATION
            # Fetch current balance to ensure sufficient funds before placing order
            try:
                balance = await self.exchange.get_balance()
                # Get base currency (USD for most pairs)
                base_currency = symbol.split("/")[1] if "/" in symbol else "USD"
                available_balance = balance.get("free", {}).get(base_currency, 0)

                # Account for trading fees (estimate 0.2% buffer)
                required_balance = position_value * 1.002

                if available_balance < required_balance:
                    logger.warning(
                        f"INSUFFICIENT BALANCE: Need ${required_balance:.2f} but only "
                        f"${available_balance:.2f} {base_currency} available"
                    )
                    if self.audit:
                        self.audit.log_signal_rejected(
                            symbol=symbol,
                            signal_type=f"{direction}_{edge_type}",
                            reason="insufficient_balance",
                            details={
                                "required": required_balance,
                                "available": available_balance,
                                "currency": base_currency
                            }
                        )
                    return

                logger.debug(f"Balance check passed: ${available_balance:.2f} available, ${required_balance:.2f} required")
            except Exception as e:
                logger.error(f"Failed to verify balance before trade: {e}")
                # In live mode, reject trade if we can't verify balance
                if self.audit:
                    self.audit.log_signal_rejected(
                        symbol=symbol,
                        signal_type=f"{direction}_{edge_type}",
                        reason="balance_check_failed",
                        details={"error": str(e)}
                    )
                return

            # Real order execution
            side = OrderSide.BUY if direction == "long" else OrderSide.SELL
            requested_amount = position_value / price
            order = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                amount=requested_amount,
            )

            result = await self.exchange.create_order(order)
            if not result:
                logger.error("Order failed")
                return

            entry_order_id = result.order_id
            filled_amount = result.filled
            filled_price = result.price

            # Handle partial fills
            if result.remaining > 0:
                logger.warning(f"PARTIAL FILL: {filled_amount:.6f}/{requested_amount:.6f} filled")

                # Wait for the order to fully fill
                final_result = await self.exchange.wait_for_order_fill(
                    order_id=result.order_id,
                    symbol=symbol,
                    timeout_seconds=self.config.order_fill_timeout
                )

                if final_result and final_result.filled > filled_amount:
                    filled_amount = final_result.filled
                    filled_price = final_result.price
                    logger.info(f"ORDER FILL UPDATE: {filled_amount:.6f} filled @ ${filled_price:.2f}")

                # Check if still partially filled
                if filled_amount < requested_amount * 0.95:  # Less than 95% filled
                    # Cancel remaining order
                    try:
                        await self.exchange.cancel_order(result.order_id, symbol)
                        logger.info(f"Cancelled unfilled portion of order {result.order_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cancel partial order: {e}")

                    # Adjust position size to actual filled amount
                    position_value = filled_amount * filled_price
                    logger.info(f"Adjusted position size to ${position_value:.2f} based on fill")

            logger.info(f"ORDER FILLED: {result.order_id} @ ${filled_price:.2f} (qty: {filled_amount:.6f})")

            # Place exchange-based stop loss order for protection
            stop_order_id = await self._place_stop_order(
                symbol=symbol,
                side=direction,
                amount=filled_amount,  # Use actual filled amount
                stop_price=stop_loss
            )
            if stop_order_id:
                logger.info(f"STOP ORDER PLACED: {stop_order_id} @ ${stop_loss:.2f}")
            else:
                logger.warning(f"Failed to place stop order - local monitoring only")
        else:
            # Paper trading
            filled_price = price
            filled_amount = position_value / price  # Calculate contracts for paper trading
            entry_order_id = None
            stop_order_id = None
            logger.info(f"PAPER TRADE: {direction.upper()} {symbol} @ ${filled_price:.2f} (qty: {filled_amount:.6f})")

        # Calculate entry slippage (difference between expected and actual fill)
        expected_price = price  # The price when we decided to trade
        if direction == "long":
            # For longs, positive slippage = paid more than expected
            entry_slippage = filled_price - expected_price
        else:
            # For shorts, positive slippage = received less than expected
            entry_slippage = expected_price - filled_price

        entry_slippage_pct = (entry_slippage / expected_price) * 100 if expected_price > 0 else 0

        if abs(entry_slippage_pct) > 0.01:  # Only log if slippage > 0.01%
            logger.info(f"  Entry slippage: ${entry_slippage:.4f} ({entry_slippage_pct:+.3f}%)")

        # Record position
        entry_time = datetime.now()
        self.positions[symbol] = Position(
            symbol=symbol,
            side=direction,
            entry_price=filled_price,
            size=position_value,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=entry_time,
            signal_source=edge_type,
            actual_contracts=filled_amount,  # Store actual filled amount for accurate close
            entry_order_id=entry_order_id,
            stop_order_id=stop_order_id if self.config.mode == "live" else None,
            # Initialize trailing stop tracking
            highest_price=filled_price,  # Start tracking from entry
            lowest_price=filled_price,   # Start tracking from entry
            # Slippage tracking
            expected_entry_price=expected_price,
            entry_slippage=entry_slippage,
            entry_slippage_pct=entry_slippage_pct,
        )

        self.stats["total_trades"] += 1

        # Record order time for deduplication
        self._recent_orders[symbol] = entry_time

        # Log trade entry to database for persistence
        if DB_AVAILABLE and db_log_trade:
            try:
                db_log_trade({
                    "timestamp": entry_time.isoformat(),
                    "symbol": symbol,
                    "signal": f"OPEN_{direction.upper()}",
                    "last_price": filled_price,
                    "vwap": filled_price,
                    "pnl": 0.0  # No P&L on entry
                })
            except Exception as e:
                logger.warning(f"Failed to log trade entry to database: {e}")

        # Audit trail logging
        if self.audit:
            self.audit.log_trade_entry(
                symbol=symbol,
                side=direction,
                entry_price=filled_price,
                size=position_value,
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_source=edge_type,
                order_id=entry_order_id,
                slippage_pct=entry_slippage_pct
            )

        # Publish trade event to WebSocket clients
        trade_event = {
            "symbol": symbol,
            "action": "OPEN_" + direction.upper(),
            "price": filled_price,
            "quantity": position_value,
            "pnl": 0,  # No P&L on open
            "timestamp": datetime.now().isoformat()
        }
        event_bus.publish("TRADE_EXECUTED", trade_event)

        # Send trade notification (Telegram/Discord)
        if self.notifier and self.notifier.is_enabled:
            try:
                await self.notifier.notify_trade_entry(trade_event)
            except Exception as e:
                logger.warning(f"Failed to send trade notification: {e}")

        # Save state after opening position
        self._save_state()

    async def _check_exits(self):
        """Check positions for exit conditions including trailing stops"""
        # Acquire position lock for thread-safe modifications
        async with self._position_lock:
            positions_to_close = []

            for symbol, pos in self.positions.items():
                price = self.prices.get(symbol, 0)
                if price <= 0:
                    continue

                exit_reason = None

                # Update trailing stop tracking
                if self.config.use_trailing_stop:
                    self._update_trailing_stop(pos, price)

                # Check trailing stop (takes precedence over fixed stop)
                if pos.trailing_stop_active and pos.trailing_stop_price > 0:
                    if pos.side == "long" and price <= pos.trailing_stop_price:
                        exit_reason = "trailing_stop"
                    elif pos.side == "short" and price >= pos.trailing_stop_price:
                        exit_reason = "trailing_stop"

                # Check fixed stop loss (if trailing not triggered)
                if not exit_reason:
                    if pos.side == "long" and price <= pos.stop_loss:
                        exit_reason = "stop_loss"
                    elif pos.side == "short" and price >= pos.stop_loss:
                        exit_reason = "stop_loss"

                # Check take profit
                if not exit_reason:
                    if pos.side == "long" and price >= pos.take_profit:
                        exit_reason = "take_profit"
                    elif pos.side == "short" and price <= pos.take_profit:
                        exit_reason = "take_profit"

                if exit_reason:
                    positions_to_close.append((symbol, price, exit_reason))

            # Close positions (lock already held)
            for symbol, exit_price, reason in positions_to_close:
                await self._close_position_locked(symbol, exit_price, reason)

    def _update_trailing_stop(self, pos: Position, current_price: float):
        """Update trailing stop for a position"""
        if pos.side == "long":
            # Track highest price
            if current_price > pos.highest_price:
                pos.highest_price = current_price

            # Calculate current profit percentage
            profit_pct = (current_price - pos.entry_price) / pos.entry_price

            # Activate trailing stop once profit threshold is reached
            if not pos.trailing_stop_active and profit_pct >= self.config.trailing_stop_activation_pct:
                pos.trailing_stop_active = True
                pos.trailing_stop_price = current_price * (1 - self.config.trailing_stop_distance_pct)
                logger.info(f"TRAILING STOP ACTIVATED: {pos.symbol} @ ${pos.trailing_stop_price:.2f} (profit: {profit_pct:.2%})")

            # Update trailing stop price as price moves up
            elif pos.trailing_stop_active:
                new_stop = pos.highest_price * (1 - self.config.trailing_stop_distance_pct)
                if new_stop > pos.trailing_stop_price:
                    pos.trailing_stop_price = new_stop
                    logger.debug(f"Trailing stop updated: {pos.symbol} @ ${pos.trailing_stop_price:.2f}")

        else:  # Short position
            # Track lowest price
            if current_price < pos.lowest_price:
                pos.lowest_price = current_price

            # Calculate current profit percentage (inverted for shorts)
            profit_pct = (pos.entry_price - current_price) / pos.entry_price

            # Activate trailing stop once profit threshold is reached
            if not pos.trailing_stop_active and profit_pct >= self.config.trailing_stop_activation_pct:
                pos.trailing_stop_active = True
                pos.trailing_stop_price = current_price * (1 + self.config.trailing_stop_distance_pct)
                logger.info(f"TRAILING STOP ACTIVATED: {pos.symbol} @ ${pos.trailing_stop_price:.2f} (profit: {profit_pct:.2%})")

            # Update trailing stop price as price moves down
            elif pos.trailing_stop_active:
                new_stop = pos.lowest_price * (1 + self.config.trailing_stop_distance_pct)
                if new_stop < pos.trailing_stop_price:
                    pos.trailing_stop_price = new_stop
                    logger.debug(f"Trailing stop updated: {pos.symbol} @ ${pos.trailing_stop_price:.2f}")

    async def _close_position_locked(self, symbol: str, exit_price: float, reason: str):
        """Close a position (must be called with _position_lock held)"""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]

        # Validate prices to prevent division by zero
        if pos.entry_price <= 0 or exit_price <= 0:
            logger.warning(f"Invalid prices for {symbol}: entry={pos.entry_price}, exit={exit_price}")
            del self.positions[symbol]
            return

        logger.info(f"CLOSE: {pos.side.upper()} {symbol}")

        # Cancel exchange stop order if exists (unless this close IS the stop trigger)
        if self.config.mode == "live" and pos.stop_order_id and reason != "stop_loss_exchange":
            await self._cancel_stop_order(symbol, pos.stop_order_id)

        # Execute close order in live mode (skip if exchange stop already executed)
        actual_exit_price = exit_price  # Will be updated with actual fill price
        close_order_failed = False
        if self.config.mode == "live" and reason != "stop_loss_exchange":
            try:
                side = OrderSide.SELL if pos.side == "long" else OrderSide.BUY
                # Use actual contracts if available (accurate), else calculate from USD value
                close_amount = pos.actual_contracts if pos.actual_contracts > 0 else pos.size / exit_price
                order = OrderRequest(
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    amount=close_amount,
                )
                result = await self.exchange.create_order(order)

                if result:
                    actual_exit_price = result.price

                    # Handle partial fills on close
                    if result.remaining > 0:
                        logger.warning(f"PARTIAL CLOSE: {result.filled:.6f}/{close_amount:.6f} filled")

                        # Wait for full fill
                        final_result = await self.exchange.wait_for_order_fill(
                            order_id=result.order_id,
                            symbol=symbol,
                            timeout_seconds=self.config.order_fill_timeout
                        )

                        if final_result:
                            actual_exit_price = final_result.price
                            if final_result.remaining > 0:
                                # Still not fully filled - log warning but proceed
                                # The position will be marked as closed but some may remain on exchange
                                logger.warning(f"Close order not fully filled - {final_result.remaining:.6f} may remain on exchange")
                else:
                    logger.error(f"Failed to execute close order for {symbol}")
                    close_order_failed = True
                    # Continue with estimated exit price for record keeping
            except Exception as e:
                logger.error(f"EXCEPTION closing position {symbol}: {e}", exc_info=True)
                close_order_failed = True
                # Log to audit trail
                if self.audit:
                    self.audit.log_error(
                        error_type="close_order_exception",
                        message=f"Failed to close {symbol}: {e}",
                        details={"reason": reason, "exit_price": exit_price},
                        symbol=symbol
                    )
                # Continue with estimated exit price - position will be marked closed locally
                # but may still exist on exchange - sync will reconcile

        # Calculate P&L using actual fill price
        if pos.side == "long":
            pnl_pct = (actual_exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - actual_exit_price) / pos.entry_price

        pnl = pnl_pct * pos.size

        # Calculate exit slippage (difference between expected and actual)
        expected_exit = exit_price  # Price when we decided to close
        if pos.side == "long":
            # For longs closing (selling), positive slippage = received less than expected
            exit_slippage = expected_exit - actual_exit_price
        else:
            # For shorts closing (buying), positive slippage = paid more than expected
            exit_slippage = actual_exit_price - expected_exit

        exit_slippage_pct = (exit_slippage / expected_exit) * 100 if expected_exit > 0 else 0

        logger.info(f"  Entry: ${pos.entry_price:.2f} -> Exit: ${actual_exit_price:.2f}")
        logger.info(f"  P&L: ${pnl:.2f} ({pnl_pct:.2%}) - {reason}")

        # Log slippage summary
        total_slippage = pos.entry_slippage + exit_slippage
        total_slippage_pct = pos.entry_slippage_pct + exit_slippage_pct
        if abs(total_slippage_pct) > 0.01:
            logger.info(f"  Slippage: ${total_slippage:.4f} ({total_slippage_pct:+.3f}%) [entry: {pos.entry_slippage_pct:+.3f}%, exit: {exit_slippage_pct:+.3f}%]")

        # Update slippage stats
        self.stats["total_entry_slippage"] = self.stats.get("total_entry_slippage", 0) + pos.entry_slippage
        self.stats["total_exit_slippage"] = self.stats.get("total_exit_slippage", 0) + exit_slippage
        self.stats["slippage_trades_count"] = self.stats.get("slippage_trades_count", 0) + 1
        slippage_count = self.stats["slippage_trades_count"]
        if slippage_count > 0:
            self.stats["avg_entry_slippage_pct"] = (
                (self.stats.get("avg_entry_slippage_pct", 0) * (slippage_count - 1) + pos.entry_slippage_pct) / slippage_count
            )
            self.stats["avg_exit_slippage_pct"] = (
                (self.stats.get("avg_exit_slippage_pct", 0) * (slippage_count - 1) + exit_slippage_pct) / slippage_count
            )

        # Record trade (use actual_exit_price and include slippage)
        exit_time = datetime.now()
        trade = TradeRecord(
            symbol=symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=actual_exit_price,
            size=pos.size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            signal_source=pos.signal_source,
            exit_reason=reason,
            entry_slippage=pos.entry_slippage,
            entry_slippage_pct=pos.entry_slippage_pct,
            exit_slippage=exit_slippage,
            exit_slippage_pct=exit_slippage_pct,
        )
        self.trade_history.append(trade)

        # Log trade to database for persistence
        if DB_AVAILABLE and db_log_trade:
            try:
                db_log_trade({
                    "timestamp": exit_time.isoformat(),
                    "symbol": symbol,
                    "signal": f"CLOSE_{pos.side.upper()}",
                    "last_price": actual_exit_price,
                    "vwap": (pos.entry_price + actual_exit_price) / 2,
                    "pnl": pnl
                })
            except Exception as e:
                logger.warning(f"Failed to log trade to database: {e}")

        # Audit trail logging
        if self.audit:
            self.audit.log_trade_exit(
                symbol=symbol,
                side=pos.side,
                entry_price=pos.entry_price,
                exit_price=actual_exit_price,
                size=pos.size,
                pnl=pnl,
                pnl_pct=pnl_pct * 100,
                reason=reason,
                slippage_pct=total_slippage_pct
            )

        # Update stats
        self.stats["total_pnl"] += pnl
        self.daily_pnl += pnl
        if pnl > 0:
            self.stats["winning_trades"] += 1

        # Record trade result in RiskManager for circuit breaker tracking
        self.risk_manager.record_trade_result(pnl)

        # Update equity
        self.equity += pnl
        self.peak_equity = max(self.peak_equity, self.equity)

        # Remove position
        del self.positions[symbol]

        # Publish trade event to WebSocket clients
        trade_event = {
            "symbol": symbol,
            "action": "CLOSE_" + pos.side.upper(),
            "price": actual_exit_price,
            "quantity": pos.size,
            "pnl": pnl,
            "pnl_pct": pnl_pct * 100,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        event_bus.publish("TRADE_EXECUTED", trade_event)

        # Send trade notification (Telegram/Discord)
        if self.notifier and self.notifier.is_enabled:
            try:
                await self.notifier.notify_trade_exit(trade_event)
            except Exception as e:
                logger.warning(f"Failed to send trade notification: {e}")

        # Save state after each trade
        self._save_state()

    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position (thread-safe wrapper that acquires lock)"""
        async with self._position_lock:
            await self._close_position_locked(symbol, exit_price, reason)

    def _check_risk_limits(self) -> bool:
        """Check if risk limits allow trading"""
        # Daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss_pct * self.daily_start_equity:
            logger.warning(f"Daily loss limit hit: ${self.daily_pnl:.2f}")
            return False

        # Max drawdown (include unrealized P&L for accurate risk assessment)
        current_equity = self.total_equity  # Uses property that includes unrealized P&L
        drawdown = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0
        if drawdown > self.config.max_drawdown_pct:
            logger.warning(f"Max drawdown hit: {drawdown:.2%}")
            return False

        return True

    async def _check_daily_reset(self):
        """Reset daily stats at midnight"""
        now = datetime.now()
        if hasattr(self, "_last_reset_date"):
            if now.date() > self._last_reset_date:
                self.daily_pnl = 0.0
                self.daily_start_equity = self.equity
                self._last_reset_date = now.date()
                logger.info("Daily stats reset")
        else:
            self._last_reset_date = now.date()

    def _update_equity(self):
        """Update equity with unrealized P&L"""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        # Note: equity already includes realized P&L, add unrealized
        total_equity = self.equity + unrealized
        self.peak_equity = max(self.peak_equity, total_equity)

    def _log_status(self):
        """Log current status"""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_equity = self.equity + unrealized

        win_rate = (self.stats["winning_trades"] / max(self.stats["total_trades"], 1)) * 100

        logger.info(
            f"STATUS | Equity: ${total_equity:,.2f} | "
            f"Positions: {len(self.positions)} | "
            f"Trades: {self.stats['total_trades']} | "
            f"Win Rate: {win_rate:.1f}% | "
            f"P&L: ${self.stats['total_pnl']:,.2f}"
        )

    def _calculate_trading_iq(self):
        """Calculate Trading IQ based on cumulative performance (mimics human IQ scale)

        Scoring is deliberately difficult:
        - Requires large sample sizes for high scores
        - 160 IQ (Genius) requires 1000+ episodes with exceptional metrics
        - Small samples are heavily penalized
        """
        episodes = self.training_metrics["episode_count"]
        total_trades = self.training_metrics["total_trades"]

        if episodes == 0:
            return 0, "Untrained"

        # Calculate averages
        avg_win_rate = self.training_metrics["total_win_rate"] / episodes
        avg_profit_factor = self.training_metrics["total_profit_factor"] / episodes
        avg_reward = self.training_metrics["total_reward"] / episodes

        # === SAMPLE SIZE MULTIPLIER ===
        # Balanced approach - reward experience but don't over-penalize early progress
        # Based on: professional traders make ~500-2000 trades/year
        if episodes < 1000:
            sample_multiplier = 0.30  # Just started
        elif episodes < 2500:
            sample_multiplier = 0.45  # Learning
        elif episodes < 5000:
            sample_multiplier = 0.60  # Getting experienced
        elif episodes < 10000:
            sample_multiplier = 0.75  # Experienced
        elif episodes < 25000:
            sample_multiplier = 0.90  # Very experienced
        else:
            sample_multiplier = 1.0  # Master (25,000+ episodes)

        # Trade counts - reasonable thresholds
        # Professional traders: 5,000-20,000 career trades is expert level
        if total_trades < 2500:
            trade_multiplier = 0.35  # Beginner
        elif total_trades < 5000:
            trade_multiplier = 0.50  # Novice
        elif total_trades < 10000:
            trade_multiplier = 0.65  # Intermediate
        elif total_trades < 25000:
            trade_multiplier = 0.80  # Experienced
        elif total_trades < 50000:
            trade_multiplier = 0.90  # Expert
        else:
            trade_multiplier = 1.0  # Master (50,000+ trades)

        # Combined sample penalty (use average, not product, to be less harsh)
        sample_penalty = (sample_multiplier + trade_multiplier) / 2

        # === PERFORMANCE SCORES (balanced thresholds) ===

        # Win rate: 50% is baseline (random), need 40%+ for points with good profit factor
        # Max 25 points at 65%+ win rate
        # NOTE: Low win rate is OK if profit factor is high (trend-following strategies)
        if avg_win_rate <= 0.35:
            win_rate_score = 0
        elif avg_win_rate <= 0.45:
            win_rate_score = (avg_win_rate - 0.35) / 0.10 * 8  # 0-8 points
        elif avg_win_rate <= 0.55:
            win_rate_score = 8 + (avg_win_rate - 0.45) / 0.10 * 8  # 8-16 points
        elif avg_win_rate <= 0.65:
            win_rate_score = 16 + (avg_win_rate - 0.55) / 0.10 * 6  # 16-22 points
        else:
            win_rate_score = min(25, 22 + (avg_win_rate - 0.65) / 0.10 * 3)  # 22-25 points

        # Profit factor: THE MOST IMPORTANT METRIC
        # 1.0 = break even, 1.5+ is good, 2.0+ is great, 3.0+ is exceptional
        # Max 45 points - this is the primary driver of IQ
        if avg_profit_factor <= 1.0:
            profit_factor_score = 0
        elif avg_profit_factor <= 1.3:
            profit_factor_score = (avg_profit_factor - 1.0) / 0.3 * 8  # 0-8 points
        elif avg_profit_factor <= 1.8:
            profit_factor_score = 8 + (avg_profit_factor - 1.3) / 0.5 * 12  # 8-20 points
        elif avg_profit_factor <= 2.5:
            profit_factor_score = 20 + (avg_profit_factor - 1.8) / 0.7 * 10  # 20-30 points
        elif avg_profit_factor <= 4.0:
            profit_factor_score = 30 + (avg_profit_factor - 2.5) / 1.5 * 10  # 30-40 points
        else:
            profit_factor_score = min(45, 40 + (avg_profit_factor - 4.0) / 3.0 * 5)  # 40-45 points

        # Bonus: High profit factor can compensate for low win rate
        # If profit factor > 3.0 and win rate > 20%, give bonus points
        pf_winrate_synergy = 0
        if avg_profit_factor > 3.0 and avg_win_rate > 0.20:
            # This rewards trend-following strategies that lose often but win big
            pf_winrate_synergy = min(15, (avg_profit_factor - 3.0) * 3)

        # Consistency bonus: reward stable positive performance
        # Max 15 points (reduced from 30 since profit factor is now weighted more)
        if avg_reward <= 0:
            reward_score = 0
        elif avg_reward <= 10:
            reward_score = avg_reward / 10 * 5  # 0-5 points
        elif avg_reward <= 25:
            reward_score = 5 + (avg_reward - 10) / 15 * 5  # 5-10 points
        else:
            reward_score = min(15, 10 + (avg_reward - 25) / 25 * 5)  # 10-15 points

        # Raw performance score (0-100)
        raw_score = win_rate_score + profit_factor_score + reward_score + pf_winrate_synergy

        # Apply sample size penalty
        adjusted_score = raw_score * sample_penalty

        # Convert to IQ scale (70-160)
        # 0 adjusted = 70 IQ
        # 50 adjusted = 115 IQ (above average - hard to reach)
        # 100 adjusted = 160 IQ (genius - very hard to reach)
        iq = int(70 + (adjusted_score * 0.9))
        iq = max(70, min(160, iq))  # Clamp to valid range

        # Determine expertise level
        if iq < 85:
            level = "Below Average"
        elif iq < 100:
            level = "Average"
        elif iq < 115:
            level = "Above Average"
        elif iq < 130:
            level = "Bright"
        elif iq < 145:
            level = "Gifted"
        else:
            level = "Genius"

        return iq, level

    async def _training_loop(self):
        """Training loop for RL agent"""
        logger.info("Starting RL training...")

        if not self.rl_agent or not self.rl_env:
            logger.error("RL components not initialized")
            return

        # Check if we have real data loaded
        from modules.rl.trading_env import _CACHE_LOADED, _CACHE_SYMBOLS
        using_real_data = _CACHE_LOADED and len(_CACHE_SYMBOLS) > 0
        if using_real_data:
            logger.info(f"Training with REAL market data from {len(_CACHE_SYMBOLS)} symbols: {', '.join(_CACHE_SYMBOLS)}")
        else:
            logger.warning("Training with SIMULATED data - consider loading real data for better results")

        self.training_progress["is_training"] = True
        self.training_progress["total_episodes"] = self.config.train_episodes
        self.training_progress["using_real_data"] = using_real_data
        self.training_progress["data_symbols"] = _CACHE_SYMBOLS if using_real_data else []

        completed_episodes = 0
        for episode in range(self.config.train_episodes):
            if not self.running:
                logger.info(f"Training stopped by user at episode {episode}")
                break

            # Run training episode in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            metrics = await loop.run_in_executor(
                None, self.rl_agent.train_episode, self.rl_env
            )
            completed_episodes = episode + 1

            # Yield control to allow UI updates
            await asyncio.sleep(0)

            # Update cumulative metrics for IQ calculation (convert numpy to Python types)
            win_rate = float(metrics.get('win_rate', 0))
            # Use actual profit factor from trading environment (gross_profit / gross_loss)
            profit_factor = float(metrics.get('profit_factor', 1.0))

            self.training_metrics["episode_count"] += 1
            self.training_metrics["total_win_rate"] += win_rate
            self.training_metrics["total_profit_factor"] += profit_factor
            self.training_metrics["total_reward"] += float(metrics.get('episode_reward', 0))
            self.training_metrics["total_trades"] += int(metrics.get('total_trades', 0))

            # Track cumulative P&L (what it would be if compounding)
            episode_pnl = float(metrics.get('total_pnl', 0))
            self.training_metrics["cumulative_pnl"] += episode_pnl

            # Calculate Trading IQ
            iq, level = self._calculate_trading_iq()

            # Update progress (convert numpy types to Python native for JSON serialization)
            self.training_progress["current_episode"] = int(completed_episodes)
            self.training_progress["last_reward"] = float(metrics.get('episode_reward', 0))
            self.training_progress["last_pnl"] = float(metrics.get('total_pnl', 0))
            self.training_progress["last_win_rate"] = float(win_rate * 100)
            self.training_progress["progress_pct"] = float((completed_episodes / self.config.train_episodes) * 100)
            self.training_progress["trading_iq"] = int(iq)
            self.training_progress["expertise_level"] = level
            self.training_progress["avg_win_rate"] = float((self.training_metrics["total_win_rate"] / self.training_metrics["episode_count"]) * 100)
            self.training_progress["avg_profit_factor"] = float(self.training_metrics["total_profit_factor"] / self.training_metrics["episode_count"])
            self.training_progress["avg_reward"] = float(self.training_metrics["total_reward"] / self.training_metrics["episode_count"])
            self.training_progress["total_trades"] = int(self.training_metrics["total_trades"])

            # Cumulative P&L tracking (what equity would be if compounding)
            self.training_progress["cumulative_pnl"] = float(self.training_metrics["cumulative_pnl"])
            self.training_progress["simulated_equity"] = float(self.config.initial_capital + self.training_metrics["cumulative_pnl"])

            # Track which symbol was used in this episode
            current_symbol = getattr(self.rl_env, 'current_symbol', 'N/A')
            self.training_progress["current_symbol"] = current_symbol

            if episode % 10 == 0:
                symbol_info = f" [{current_symbol}]" if using_real_data else ""
                cumulative = self.training_metrics["cumulative_pnl"]
                sim_equity = self.config.initial_capital + cumulative
                logger.info(
                    f"Episode {episode}/{self.config.train_episodes}{symbol_info} | "
                    f"P&L: ${metrics.get('total_pnl', 0):.2f} | "
                    f"Cumulative: ${cumulative:+,.2f} | "
                    f"Sim Equity: ${sim_equity:,.2f}"
                )

            # Save periodically (model + state with IQ)
            if episode % 50 == 0 and episode > 0:
                os.makedirs(os.path.dirname(self.config.rl_model_path), exist_ok=True)
                self.rl_agent.save(self.config.rl_model_path)
                # Also save IQ progress so it persists if training is interrupted
                self.stats["trading_iq"] = self.training_progress["trading_iq"]
                self.stats["expertise_level"] = self.training_progress["expertise_level"]
                self._save_state()
                logger.info(f"Checkpoint saved at episode {episode} - IQ: {self.stats['trading_iq']}")

        # Always save model at end (whether completed or stopped)
        os.makedirs(os.path.dirname(self.config.rl_model_path), exist_ok=True)
        self.rl_agent.save(self.config.rl_model_path)
        self.training_progress["is_training"] = False

        # Save IQ and training history to persistent stats
        self.stats["trading_iq"] = self.training_progress["trading_iq"]
        self.stats["expertise_level"] = self.training_progress["expertise_level"]

        # Update training history
        self.stats["training_sessions"] = self.stats.get("training_sessions", 0) + 1
        self.stats["total_training_episodes"] = self.stats.get("total_training_episodes", 0) + completed_episodes
        self.stats["total_training_trades"] = self.stats.get("total_training_trades", 0) + self.training_metrics.get("total_trades", 0)
        self.stats["last_training_date"] = datetime.now().isoformat()
        self.stats["avg_win_rate"] = self.training_progress.get("avg_win_rate", 0)
        self.stats["avg_profit_factor"] = self.training_progress.get("avg_profit_factor", 0)
        self.stats["avg_reward"] = self.training_progress.get("avg_reward", 0)

        self._save_state()  # Persist IQ and training history to file

        # Switch back to paper mode (both in-memory and config file)
        self.config.mode = "paper"
        self._save_mode_to_config("paper")

        if completed_episodes == self.config.train_episodes:
            logger.info(f"Training complete! {completed_episodes} episodes. Model saved to {self.config.rl_model_path}")
        else:
            logger.info(f"Training stopped after {completed_episodes} episodes. Progress saved to {self.config.rl_model_path}")

    async def stop(self):
        """Stop the bot gracefully"""
        # Guard against double shutdown
        if self._stopped:
            return
        self._stopped = True

        logger.info("Stopping JJ-Bot Pro...")
        was_training = self.training_progress["is_training"]
        self.running = False

        # If training, wait a moment for it to save
        if was_training:
            logger.info("Waiting for training to save progress...")
            await asyncio.sleep(2)

        # Close all positions (paper/live trading mode only - not during training)
        # CRITICAL: Add timeout protection to prevent hanging on position close
        if not self._started_in_training_mode:
            positions_to_close = list(self.positions.keys())
            if positions_to_close:
                logger.info(f"Closing {len(positions_to_close)} open positions...")
                close_errors = []

                for symbol in positions_to_close:
                    price = self.prices.get(symbol, self.positions[symbol].entry_price)
                    try:
                        # Timeout per position close: 30 seconds max
                        await asyncio.wait_for(
                            self._close_position(symbol, price, "shutdown"),
                            timeout=30.0
                        )
                        logger.info(f"  Closed {symbol}")
                    except asyncio.TimeoutError:
                        error_msg = f"Timeout closing {symbol} - position may still be open on exchange"
                        logger.error(error_msg)
                        close_errors.append(error_msg)
                        # Continue with other positions, don't block shutdown
                    except Exception as e:
                        error_msg = f"Error closing {symbol}: {e}"
                        logger.error(error_msg)
                        close_errors.append(error_msg)
                        # Continue with other positions

                if close_errors:
                    logger.warning(f"Shutdown completed with {len(close_errors)} position close errors")
                    logger.warning("Manual reconciliation may be required for failed closes")
                else:
                    logger.info("All positions closed successfully")

        # CRITICAL: Save state before shutdown
        logger.info("Saving state before shutdown...")
        self._save_state()
        logger.info(f"State saved - Equity: ${self.equity:.2f}, IQ: {self.stats.get('trading_iq', 0)}")

        # Cleanup
        if self.data_feed:
            await self.data_feed.stop()

        if self.exchange:
            await self.exchange.disconnect()

        if self.alt_data:
            await self.alt_data.close()

        # Stop health check server
        if self._health_server:
            await self._health_server.stop()

        # Close notification manager
        if self.notifier:
            await self.notifier.close()

        # Log final stats
        self._log_final_stats()

        logger.info("JJ-Bot Pro stopped")

    def _log_final_stats(self):
        """Log final performance statistics"""
        start_time = self.stats["start_time"]
        if start_time:
            # Handle both datetime and string formats
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            runtime = datetime.now() - start_time
        else:
            runtime = timedelta(0)

        logger.info("=" * 50)

        if self._started_in_training_mode:
            # Show training-specific statistics
            logger.info("TRAINING STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Runtime: {runtime}")
            logger.info(f"Episodes Completed: {self.training_progress['current_episode']}/{self.training_progress['total_episodes']}")
            logger.info(f"Trading IQ: {self.training_progress['trading_iq']}")
            logger.info(f"Expertise Level: {self.training_progress['expertise_level']}")
            logger.info(f"Avg Win Rate: {self.training_progress['avg_win_rate']:.1f}%")
            logger.info(f"Avg Profit Factor: {self.training_progress['avg_profit_factor']:.2f}")
            logger.info(f"Avg Reward: {self.training_progress['avg_reward']:.2f}")
            logger.info(f"Last Episode Reward: {self.training_progress['last_reward']:.2f}")
            logger.info(f"Last Episode P&L: ${self.training_progress['last_pnl']:.2f}")
            logger.info(f"Last Episode Win Rate: {self.training_progress['last_win_rate']:.1f}%")
            logger.info(f"Total Training Sessions: {self.stats.get('training_sessions', 1)}")
            logger.info(f"Total Episodes (All Sessions): {self.stats.get('total_training_episodes', self.training_progress['current_episode'])}")
        else:
            # Show trading statistics
            win_rate = (self.stats["winning_trades"] / max(self.stats["total_trades"], 1)) * 100
            # Session return (from when this session started)
            session_return_pct = ((self.equity - self.session_starting_equity) / self.session_starting_equity) * 100
            # All-time return (from initial capital)
            alltime_return_pct = ((self.equity - self.config.initial_capital) / self.config.initial_capital) * 100

            logger.info("FINAL STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Runtime: {runtime}")
            logger.info(f"Session Start: ${self.session_starting_equity:,.2f}")
            logger.info(f"Final Equity: ${self.equity:,.2f}")
            logger.info(f"Session Return: {session_return_pct:.2f}%")
            logger.info(f"All-Time Return: {alltime_return_pct:.2f}% (from ${self.config.initial_capital:,.2f})")
            logger.info(f"Total Trades: {self.stats['total_trades']}")
            logger.info(f"Winning Trades: {self.stats['winning_trades']}")
            logger.info(f"Win Rate: {win_rate:.1f}%")
            logger.info(f"Total P&L: ${self.stats['total_pnl']:,.2f}")
            logger.info(f"Signals Analyzed: {self.stats['signals_analyzed']}")

        logger.info("=" * 50)

    def run(self):
        """Run the bot (blocking)"""
        # Handle shutdown signals
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                pass  # Windows doesn't support this

        try:
            loop.run_until_complete(self.start())
        finally:
            loop.close()

    def get_status(self) -> Dict:
        """Get current bot status (for API)"""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())

        return {
            "running": self.running,
            "mode": self.config.mode,
            "equity": self.equity,
            "unrealized_pnl": unrealized,
            "total_equity": self.equity + unrealized,
            "positions": len(self.positions),
            "total_trades": self.stats["total_trades"],
            "winning_trades": self.stats["winning_trades"],
            "total_pnl": self.stats["total_pnl"],
            "daily_pnl": self.daily_pnl,
            "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None,
        }

    def _get_health_status(self) -> Dict:
        """Get health status for monitoring endpoint"""
        return {
            "running": self.running,
            "mode": self.config.mode,
            "equity": self.equity,
            "total_pnl": self.stats["total_pnl"],
            "daily_pnl": self.daily_pnl,
            "total_trades": self.stats["total_trades"],
            "open_positions": len(self.positions),
            "exchange_connected": self.exchange is not None and self.exchange._exchange is not None,
            "price_feed_stale": self._trading_paused_due_to_feed,
        }

    async def _on_dead_mans_switch(self):
        """
        Called when the dead man's switch triggers (bot unresponsive).
        Emergency close all positions to protect capital.
        """
        logger.warning("=" * 60)
        logger.warning("[DEAD MAN'S SWITCH] EMERGENCY POSITION CLOSE TRIGGERED")
        logger.warning("=" * 60)

        # Send notification if available
        if self.notifier and self.notifier.is_enabled:
            try:
                await self.notifier.notify_error(
                    "Dead Man's Switch",
                    "Bot unresponsive - emergency closing all positions"
                )
            except Exception:
                pass

        # Close all positions
        positions_to_close = list(self.positions.keys())
        for symbol in positions_to_close:
            try:
                price = self.prices.get(symbol, self.positions[symbol].entry_price)
                await self._close_position(symbol, price, "dead_mans_switch")
                logger.info(f"[DEAD MAN'S SWITCH] Closed {symbol}")
            except Exception as e:
                logger.error(f"[DEAD MAN'S SWITCH] Failed to close {symbol}: {e}")

        # Save state
        self._save_state()

        logger.warning("[DEAD MAN'S SWITCH] Emergency close complete")

    def get_positions(self) -> List[Dict]:
        """Get open positions (for API)"""
        positions_list = []
        for pos in self.positions.values():
            current_price = self.prices.get(pos.symbol, pos.entry_price)
            # Calculate unrealized P&L on-the-fly for accuracy
            if pos.side == "long":
                unrealized_pnl = (current_price - pos.entry_price) / pos.entry_price * pos.size
            else:
                unrealized_pnl = (pos.entry_price - current_price) / pos.entry_price * pos.size

            positions_list.append({
                "symbol": pos.symbol,
                "side": pos.side,
                "entry_price": pos.entry_price,
                "current_price": current_price,
                "size": pos.size,
                "unrealized_pnl": unrealized_pnl,
                "stop_loss": pos.stop_loss,
                "take_profit": pos.take_profit,
                "entry_time": pos.entry_time.isoformat(),
                "signal_source": pos.signal_source,
            })
        return positions_list

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history (for API)"""
        return [
            {
                "symbol": t.symbol,
                "side": t.side,
                "signal": "BUY" if t.side == "long" else "SELL",  # Frontend expects signal
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "last_price": t.exit_price,  # Frontend expects last_price
                "size": t.size,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat(),
                "timestamp": t.exit_time.isoformat(),  # Frontend expects timestamp
                "signal_source": t.signal_source,
                "exit_reason": t.exit_reason,
            }
            for t in self.trade_history[-limit:]
        ]


# Simple entry point
def run_bot(config_path: str = "config/bot_config.json"):
    """Run the trading bot"""
    config = BotConfig.load(config_path)
    bot = JJBotPro(config)
    bot.run()


if __name__ == "__main__":
    run_bot()
