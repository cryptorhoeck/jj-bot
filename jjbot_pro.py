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

# Internal modules
from modules.exchange import create_connector, create_live_feed, CCXTConnector, LiveDataFeed
from modules.exchange import OrderRequest, OrderType, OrderSide, Ticker

# RL modules are optional (require PyTorch)
try:
    from modules.rl import TradingEnvironment, create_agent, PPOAgent
    RL_AVAILABLE = True
except ImportError:
    TradingEnvironment = None
    create_agent = None
    PPOAgent = None
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

    # Strategy settings
    use_rl_agent: bool = True
    use_edge_strategies: bool = True
    use_alternative_data: bool = True
    min_signal_confidence: float = 0.45  # Lower threshold for more trades

    # RL settings
    rl_model_path: str = "models/ppo_agent.pt"
    train_episodes: int = 100

    # Timing
    analysis_interval_seconds: int = 60  # How often to analyze

    # Logging
    log_level: str = "INFO"
    log_trades: bool = True

    @classmethod
    def load(cls, path: str = "config/bot_config.json") -> "BotConfig":
        """Load config from file, ignoring unknown fields"""
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                # Filter to only known fields to avoid errors from old config files
                valid_fields = {f.name for f in fields(cls)}
                filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                return cls(**filtered_data)
        return cls()

    def save(self, path: str = "config/bot_config.json"):
        """Save config to file"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)


@dataclass
class Position:
    """Active trading position"""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    signal_source: str
    unrealized_pnl: float = 0.0


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
            }

        # Positions and history
        self.positions: Dict[str, Position] = self._load_positions()
        self.trade_history: List[TradeRecord] = []

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
            "total_trades": self.stats.get("total_training_trades", 0)
        }

        # Training metrics for IQ calculation
        self.training_metrics = {
            "episode_count": 0,
            "total_win_rate": 0.0,
            "total_profit_factor": 0.0,
            "total_reward": 0.0,
            "total_trades": 0
        }

        # Components (initialized in start())
        self.exchange: Optional[CCXTConnector] = None
        self.data_feed: Optional[LiveDataFeed] = None
        self.alt_data: Optional[AlternativeDataFeed] = None
        self.edge_detector: Optional[EdgeDetector] = None
        self.edge_manager: Optional[EdgeStrategyManager] = None
        self.rl_agent: Optional[PPOAgent] = None
        self.rl_env: Optional[TradingEnvironment] = None

        # Price cache
        self.prices: Dict[str, float] = {}

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
                return {
                    "equity": equity,
                    "peak_equity": saved_peak_equity if saved_peak_equity is not None else equity,
                    "daily_pnl": saved_daily_pnl,
                    "daily_start_equity": saved_daily_start_equity if saved_daily_start_equity is not None else equity,
                    "stats": {
                        "total_trades": 0,
                        "winning_trades": 0,
                        "total_pnl": 0.0,
                        "signals_analyzed": 0,
                        "start_time": None,
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
                    except:
                        entry_time = datetime.now()

                    # Determine side from signal
                    side = "long" if data["signal"] == "BUY" else "short"

                    # Calculate position size (use a default based on config)
                    position_size = self.config.initial_capital * self.config.max_position_pct

                    positions[symbol] = Position(
                        symbol=symbol,
                        side=side,
                        entry_price=data["entry_price"],
                        size=position_size,
                        stop_loss=data["entry_price"] * (0.95 if side == "long" else 1.05),
                        take_profit=data["entry_price"] * (1.10 if side == "long" else 0.90),
                        entry_time=entry_time,
                        signal_source="restored",
                        unrealized_pnl=0.0  # Will be calculated when prices update
                    )

            if positions:
                logger.info(f"Restored {len(positions)} open positions from database")

        except Exception as e:
            logger.warning(f"Failed to load positions from database: {e}")

        return positions

    def _save_state(self):
        """Save bot state to file"""
        # Use absolute path relative to this file (same as _load_state does)
        project_root = Path(__file__).parent
        state_file = project_root / "data" / "bot_state.json"

        try:
            os.makedirs(project_root / "data", exist_ok=True)
            logger.info(f"Saving state to: {state_file}")

            state = {
                "equity": self.equity,
                "peak_equity": self.peak_equity,
                "daily_pnl": self.daily_pnl,
                "daily_start_equity": self.daily_start_equity,
                "stats": self.stats.copy(),  # Make a copy to avoid modifying original
                "last_updated": datetime.now().isoformat()
            }
            # Handle datetime in stats
            if state["stats"].get("start_time"):
                state["stats"]["start_time"] = state["stats"]["start_time"].isoformat() if isinstance(state["stats"]["start_time"], datetime) else state["stats"]["start_time"]

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.info(f"State saved successfully: equity=${self.equity:.2f}, IQ={self.stats.get('trading_iq', 0)}")
        except Exception as e:
            logger.error(f"FAILED to save state: {e}", exc_info=True)

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

    async def start(self):
        """Start the trading bot"""
        logger.info("=" * 50)
        logger.info("JJ-Bot Pro Starting...")
        logger.info(f"Mode: {self.config.mode}")
        logger.info(f"Symbols: {self.config.symbols}")
        logger.info(f"Capital: ${self.config.initial_capital:,.2f}")
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
                    logger.warning("Exchange connection failed - running in DEMO mode with simulated prices")
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
            self.rl_env = TradingEnvironment(
                initial_balance=self.config.initial_capital,
                max_position_size=self.config.max_position_pct
            )

            self.rl_agent = create_agent(
                "ppo",
                state_dim=self.rl_env.observation_space_dim,
                action_dim=self.rl_env.action_space_dim
            )

            # Load existing model if available
            if os.path.exists(self.config.rl_model_path):
                self.rl_agent.load(self.config.rl_model_path)
                logger.info(f"Loaded RL model from {self.config.rl_model_path}")
            else:
                logger.info("No existing RL model found - starting fresh")
        elif self.config.use_rl_agent:
            logger.warning("RL agent requested but PyTorch not available - trading without AI")

        logger.info("All components initialized")

    def _on_price_update(self, update):
        """Handle real-time price updates"""
        self.prices[update.symbol] = update.price

        # Update position P&L
        if update.symbol in self.positions:
            pos = self.positions[update.symbol]
            if pos.side == "long":
                pos.unrealized_pnl = (update.price - pos.entry_price) / pos.entry_price * pos.size
            else:
                pos.unrealized_pnl = (pos.entry_price - update.price) / pos.entry_price * pos.size

    def _init_demo_prices(self):
        """Initialize demo prices for offline/demo mode"""
        import random
        # Realistic starting prices for top coins (supports both USD and USDT pairs)
        base_prices = {
            "BTC": 97000.0, "ETH": 3500.0, "BNB": 650.0,
            "XRP": 1.40, "SOL": 250.0, "ADA": 1.00,
            "DOGE": 0.40, "TRX": 0.20, "AVAX": 45.0,
            "LINK": 18.0, "DOT": 9.0, "POL": 0.50,
            "SHIB": 0.000025, "LTC": 95.0, "BCH": 500.0,
            "UNI": 12.0, "XLM": 0.35, "ATOM": 12.0,
            "ETC": 32.0, "FIL": 6.5, "HBAR": 0.12,
            "APT": 12.0, "ARB": 1.20, "OP": 2.50,
            "NEAR": 6.50, "INJ": 35.0, "RUNE": 6.0,
            "AAVE": 180.0, "GRT": 0.25, "FTM": 1.10,
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
                            if pos.side == "long":
                                pos.unrealized_pnl = (ticker.last - pos.entry_price) / pos.entry_price * pos.size
                            else:
                                pos.unrealized_pnl = (pos.entry_price - ticker.last) / pos.entry_price * pos.size

                if updated_count > 0:
                    logger.debug(f"REST API updated {updated_count} prices")
        except Exception as e:
            logger.warning(f"REST API price fetch failed: {e}")

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
        save_interval = 300  # Save state every 5 minutes

        while self.running:
            try:
                # Update prices - demo mode uses simulation, live mode uses REST API fallback
                if self._demo_mode:
                    await self._update_demo_prices()
                else:
                    # Always fetch fresh prices via REST API to ensure P&L is accurate
                    # This supplements WebSocket data which may be stale or disconnected
                    await self._fetch_prices_rest()

                # Reset daily stats at midnight
                await self._check_daily_reset()

                # Check risk limits
                if not self._check_risk_limits():
                    logger.warning("Risk limits exceeded - pausing trading")
                    await asyncio.sleep(60)
                    continue

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

        # 3. Get RL agent signal (if no position)
        if self.rl_agent and symbol not in self.positions:
            try:
                # Build state for RL
                candles = self.data_feed.get_candles(symbol, "1h", 50) if self.data_feed else []
                if len(candles) >= 20:
                    # Simple state: returns and volatility
                    closes = [c.close for c in candles[-50:]]
                    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

                    state = list(returns[-20:]) + [0] * (self.rl_env.observation_space_dim - 20)
                    state = state[:self.rl_env.observation_space_dim]

                    import numpy as np
                    action, _, _ = self.rl_agent.select_action(np.array(state), training=False)

                    if action == 1:  # BUY
                        signals.append(TradeSignal(
                            symbol=symbol,
                            direction="long",
                            strength=2,
                            confidence=0.6,
                            edge_type="rl_agent",
                            entry_price=price,
                            reason="RL agent buy signal"
                        ))
                    elif action == 2:  # SELL
                        signals.append(TradeSignal(
                            symbol=symbol,
                            direction="short",
                            strength=2,
                            confidence=0.6,
                            edge_type="rl_agent",
                            entry_price=price,
                            reason="RL agent sell signal"
                        ))
            except Exception as e:
                logger.debug(f"RL signal error for {symbol}: {e}")

        # 4. Combine signals and decide
        if signals:
            # Use first signal (demo mode) or combine (production)
            if self._demo_mode or not self.edge_manager:
                combined = signals[0]
            else:
                combined = self.edge_manager.get_combined_signal(signals)

            # Get confidence (works with dict or object)
            conf = combined.get("confidence", 0) if isinstance(combined, dict) else getattr(combined, "confidence", 0)

            if combined and conf >= self.config.min_signal_confidence:
                await self._handle_signal(symbol, combined)

    async def _handle_signal(self, symbol: str, signal):
        """Handle a trading signal (dict or TradeSignal object)"""
        # Helper to get attribute from dict or object
        def get_attr(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Skip if already have position in this symbol
        if symbol in self.positions:
            return

        # Skip if max positions reached
        if len(self.positions) >= self.config.max_positions:
            return

        direction = get_attr(signal, "direction", "long")
        confidence = get_attr(signal, "confidence", 0.5)
        edge_type = get_attr(signal, "edge_type", "unknown")
        reason = get_attr(signal, "reason", "")
        entry_price = get_attr(signal, "entry_price", 0)

        price = self.prices.get(symbol, entry_price or 0)
        if price <= 0:
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
            # Real order execution
            side = OrderSide.BUY if direction == "long" else OrderSide.SELL
            order = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                amount=position_value / price,
            )

            result = await self.exchange.create_order(order)
            if result:
                filled_price = result.price
                logger.info(f"ORDER FILLED: {result.order_id} @ ${filled_price:.2f}")
            else:
                logger.error("Order failed")
                return
        else:
            # Paper trading
            filled_price = price
            logger.info(f"PAPER TRADE: {direction.upper()} {symbol} @ ${filled_price:.2f}")

        # Record position
        self.positions[symbol] = Position(
            symbol=symbol,
            side=direction,
            entry_price=filled_price,
            size=position_value,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.now(),
            signal_source=edge_type
        )

        self.stats["total_trades"] += 1

        # Save state after opening position
        self._save_state()

    async def _check_exits(self):
        """Check positions for exit conditions"""
        positions_to_close = []

        for symbol, pos in self.positions.items():
            price = self.prices.get(symbol, 0)
            if price <= 0:
                continue

            exit_reason = None

            # Check stop loss
            if pos.side == "long" and price <= pos.stop_loss:
                exit_reason = "stop_loss"
            elif pos.side == "short" and price >= pos.stop_loss:
                exit_reason = "stop_loss"

            # Check take profit
            if pos.side == "long" and price >= pos.take_profit:
                exit_reason = "take_profit"
            elif pos.side == "short" and price <= pos.take_profit:
                exit_reason = "take_profit"

            if exit_reason:
                positions_to_close.append((symbol, price, exit_reason))

        # Close positions
        for symbol, exit_price, reason in positions_to_close:
            await self._close_position(symbol, exit_price, reason)

    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]

        # Calculate P&L
        if pos.side == "long":
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price

        pnl = pnl_pct * pos.size

        logger.info(f"CLOSE: {pos.side.upper()} {symbol}")
        logger.info(f"  Entry: ${pos.entry_price:.2f} -> Exit: ${exit_price:.2f}")
        logger.info(f"  P&L: ${pnl:.2f} ({pnl_pct:.2%}) - {reason}")

        # Execute close order in live mode
        if self.config.mode == "live":
            side = OrderSide.SELL if pos.side == "long" else OrderSide.BUY
            order = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                amount=pos.size / exit_price,
            )
            await self.exchange.create_order(order)

        # Record trade
        trade = TradeRecord(
            symbol=symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size=pos.size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=pos.entry_time,
            exit_time=datetime.now(),
            signal_source=pos.signal_source,
            exit_reason=reason
        )
        self.trade_history.append(trade)

        # Update stats
        self.stats["total_pnl"] += pnl
        self.daily_pnl += pnl
        if pnl > 0:
            self.stats["winning_trades"] += 1

        # Update equity
        self.equity += pnl
        self.peak_equity = max(self.peak_equity, self.equity)

        # Remove position
        del self.positions[symbol]

        # Save state after each trade
        self._save_state()

    def _check_risk_limits(self) -> bool:
        """Check if risk limits allow trading"""
        # Daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss_pct * self.daily_start_equity:
            logger.warning(f"Daily loss limit hit: ${self.daily_pnl:.2f}")
            return False

        # Max drawdown
        drawdown = (self.peak_equity - self.equity) / self.peak_equity
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
        """Calculate Trading IQ based on cumulative performance"""
        if self.training_metrics["episode_count"] == 0:
            return 0, "Untrained"

        # Calculate averages
        avg_win_rate = self.training_metrics["total_win_rate"] / self.training_metrics["episode_count"]
        avg_profit_factor = self.training_metrics["total_profit_factor"] / self.training_metrics["episode_count"]
        avg_reward = self.training_metrics["total_reward"] / self.training_metrics["episode_count"]

        # Normalize and score (0-100 scale)
        # Win rate: 0-50% = 0-40 points
        win_rate_score = min(40, (avg_win_rate / 0.5) * 40)

        # Profit factor: 0-3 = 0-30 points
        profit_factor_score = min(30, (avg_profit_factor / 3.0) * 30)

        # Reward: normalize to 0-30 points (assuming rewards typically -100 to +100)
        reward_normalized = max(0, min(100, avg_reward + 100)) / 100
        reward_score = reward_normalized * 30

        # Total IQ (0-100)
        iq = int(win_rate_score + profit_factor_score + reward_score)

        # Determine expertise level
        if iq < 20:
            level = "Novice"
        elif iq < 40:
            level = "Beginner"
        elif iq < 60:
            level = "Intermediate"
        elif iq < 75:
            level = "Advanced"
        elif iq < 90:
            level = "Expert"
        else:
            level = "Master"

        return iq, level

    async def _training_loop(self):
        """Training loop for RL agent"""
        logger.info("Starting RL training...")

        if not self.rl_agent or not self.rl_env:
            logger.error("RL components not initialized")
            return

        self.training_progress["is_training"] = True
        self.training_progress["total_episodes"] = self.config.train_episodes

        completed_episodes = 0
        for episode in range(self.config.train_episodes):
            if not self.running:
                logger.info(f"Training stopped by user at episode {episode}")
                break

            metrics = self.rl_agent.train_episode(self.rl_env)
            completed_episodes = episode + 1

            # Update cumulative metrics for IQ calculation
            win_rate = metrics.get('win_rate', 0)
            total_wins = metrics.get('winning_trades', 0)
            total_losses = metrics.get('losing_trades', 0)
            profit_factor = (total_wins / max(1, total_losses)) if total_losses > 0 else 1.0

            self.training_metrics["episode_count"] += 1
            self.training_metrics["total_win_rate"] += win_rate
            self.training_metrics["total_profit_factor"] += profit_factor
            self.training_metrics["total_reward"] += metrics.get('episode_reward', 0)
            self.training_metrics["total_trades"] += metrics.get('total_trades', 0)

            # Calculate Trading IQ
            iq, level = self._calculate_trading_iq()

            # Update progress
            self.training_progress["current_episode"] = completed_episodes
            self.training_progress["last_reward"] = metrics.get('episode_reward', 0)
            self.training_progress["last_pnl"] = metrics.get('total_pnl', 0)
            self.training_progress["last_win_rate"] = win_rate * 100
            self.training_progress["progress_pct"] = (completed_episodes / self.config.train_episodes) * 100
            self.training_progress["trading_iq"] = iq
            self.training_progress["expertise_level"] = level
            self.training_progress["avg_win_rate"] = (self.training_metrics["total_win_rate"] / self.training_metrics["episode_count"]) * 100
            self.training_progress["avg_profit_factor"] = self.training_metrics["total_profit_factor"] / self.training_metrics["episode_count"]
            self.training_progress["avg_reward"] = self.training_metrics["total_reward"] / self.training_metrics["episode_count"]
            self.training_progress["total_trades"] = self.training_metrics["total_trades"]

            if episode % 10 == 0:
                logger.info(
                    f"Episode {episode}/{self.config.train_episodes} | "
                    f"Reward: {metrics.get('episode_reward', 0):.2f} | "
                    f"P&L: ${metrics.get('total_pnl', 0):.2f} | "
                    f"Win Rate: {metrics.get('win_rate', 0):.1%}"
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
        logger.info("Stopping JJ-Bot Pro...")
        was_training = self.training_progress["is_training"]
        self.running = False

        # If training, wait a moment for it to save
        if was_training:
            logger.info("Waiting for training to save progress...")
            await asyncio.sleep(2)

        # Close all positions (paper/live trading mode only - not during training)
        if not self._started_in_training_mode:
            for symbol in list(self.positions.keys()):
                price = self.prices.get(symbol, self.positions[symbol].entry_price)
                await self._close_position(symbol, price, "shutdown")

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
            return_pct = ((self.equity - self.config.initial_capital) / self.config.initial_capital) * 100

            logger.info("FINAL STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Runtime: {runtime}")
            logger.info(f"Initial Capital: ${self.config.initial_capital:,.2f}")
            logger.info(f"Final Equity: ${self.equity:,.2f}")
            logger.info(f"Total Return: {return_pct:.2f}%")
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
