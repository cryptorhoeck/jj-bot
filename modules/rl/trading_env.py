"""
Trading Environment for Reinforcement Learning
OpenAI Gym compatible environment for training RL agents

Uses REAL historical data from Kraken for meaningful training.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import logging
import random
import time
import asyncio

logger = logging.getLogger(__name__)

# Global cache for historical data (avoid re-fetching)
_DATA_CACHE: Dict[str, np.ndarray] = {}
_CACHE_LOADED = False
_CACHE_SYMBOLS: List[str] = []
_CACHE_TIMEFRAME: str = ''
_CACHE_DAYS: int = 0


def load_historical_data_sync(symbols: Optional[List[str]] = None, timeframe: str = '1h', days: int = 90) -> Dict[str, np.ndarray]:
    """
    Synchronously fetch historical OHLCV data from Kraken with smart pagination.
    Automatically makes multiple requests to fetch the full history period.

    Args:
        symbols: List of trading pairs (e.g., ['BTC/USD', 'ETH/USD'])
        timeframe: Candle size ('5m', '15m', '1h', '4h', '1d')
        days: How many days of historical data to fetch

    Returns dict of symbol -> feature array (n_candles, n_features)
    """
    global _DATA_CACHE, _CACHE_LOADED, _CACHE_SYMBOLS, _CACHE_TIMEFRAME, _CACHE_DAYS

    # Check if cache is valid (same timeframe and days)
    if _CACHE_LOADED and _DATA_CACHE:
        if _CACHE_TIMEFRAME == timeframe and _CACHE_DAYS == days:
            logger.info(f"Using cached data for {len(_DATA_CACHE)} symbols (timeframe={timeframe}, days={days})")
            return _DATA_CACHE
        else:
            logger.info(f"Cache invalidated: settings changed from {_CACHE_TIMEFRAME}/{_CACHE_DAYS}d to {timeframe}/{days}d")
            _DATA_CACHE = {}
            _CACHE_LOADED = False
            _CACHE_SYMBOLS = []

    try:
        import ccxt
    except ImportError:
        logger.warning("ccxt not installed, using dummy data")
        return {}

    if not symbols:
        logger.error("No symbols provided for training data")
        return {}

    # Calculate candles needed based on timeframe and days
    timeframe_minutes = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440
    }
    minutes_per_candle = timeframe_minutes.get(timeframe, 60)
    total_candles_needed = (days * 24 * 60) // minutes_per_candle

    logger.info(f"Fetching {days} days of {timeframe} data ({total_candles_needed:,} candles) for {len(symbols)} symbols...")

    exchange = ccxt.kraken({
        'enableRateLimit': True,
        'rateLimit': 500,  # Faster but still safe
    })

    try:
        exchange.load_markets()
    except Exception as e:
        logger.error(f"Failed to load Kraken markets: {e}")
        return {}

    data_cache = {}
    kraken_limit = 720  # Kraken's max per request

    for symbol in symbols:
        if symbol not in exchange.markets:
            logger.warning(f"Symbol {symbol} not available on Kraken, skipping")
            continue

        try:
            all_ohlcv = []
            candles_fetched = 0
            since = None  # Start from most recent

            # Calculate how many requests we need
            requests_needed = (total_candles_needed + kraken_limit - 1) // kraken_limit

            for req_num in range(requests_needed):
                # Fetch batch
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=kraken_limit)

                if not ohlcv:
                    break

                # Prepend to get chronological order (we're going backwards)
                all_ohlcv = ohlcv + all_ohlcv
                candles_fetched += len(ohlcv)

                # Get the oldest timestamp from this batch to fetch older data next
                oldest_timestamp = ohlcv[0][0]
                # Go back one more candle to avoid duplicates
                since = oldest_timestamp - (minutes_per_candle * 60 * 1000 * kraken_limit)

                # Stop if we have enough or no more data
                if candles_fetched >= total_candles_needed or len(ohlcv) < kraken_limit:
                    break

                # Rate limit between requests
                time.sleep(0.3)

            if not all_ohlcv or len(all_ohlcv) < 100:
                logger.warning(f"Insufficient data for {symbol}: {len(all_ohlcv) if all_ohlcv else 0} candles")
                continue

            # Trim to requested amount if we got more
            if len(all_ohlcv) > total_candles_needed:
                all_ohlcv = all_ohlcv[-total_candles_needed:]

            # Convert to numpy array: [timestamp, open, high, low, close, volume]
            ohlcv_array = np.array(all_ohlcv, dtype=np.float64)

            # Calculate features from OHLCV
            features = calculate_features(ohlcv_array)

            if features is not None and len(features) > 50:
                data_cache[symbol] = features
                logger.info(f"Loaded {len(features):,} candles for {symbol}")

            # Rate limit between symbols
            time.sleep(0.3)

        except Exception as e:
            logger.warning(f"Failed to fetch {symbol}: {e}")
            continue

    if data_cache:
        _DATA_CACHE = data_cache
        _CACHE_LOADED = True
        _CACHE_SYMBOLS = list(data_cache.keys())
        _CACHE_TIMEFRAME = timeframe
        _CACHE_DAYS = days
        logger.info(f"Successfully cached {len(data_cache)} symbols: {timeframe} candles for {days} days")
    else:
        logger.warning("No data fetched, will use dummy data")

    return data_cache


def calculate_features(ohlcv: np.ndarray) -> np.ndarray:
    """
    Calculate technical indicators from OHLCV data.

    Input: (n_candles, 6) - [timestamp, open, high, low, close, volume]
    Output: (n_candles, 20) - [close, returns, volatility, rsi, macd, bb_upper, bb_lower, ...]
    """
    n = len(ohlcv)
    if n < 50:
        return None

    close = ohlcv[:, 4]
    high = ohlcv[:, 2]
    low = ohlcv[:, 3]
    volume = ohlcv[:, 5]

    features = np.zeros((n, 20), dtype=np.float32)

    # Feature 0: Close price (raw, for trading)
    features[:, 0] = close

    # Feature 1: Returns (price change %)
    features[1:, 1] = (close[1:] - close[:-1]) / (close[:-1] + 1e-8)

    # Feature 2: Log returns
    features[1:, 2] = np.log(close[1:] / (close[:-1] + 1e-8))

    # Feature 3: Volatility (20-period rolling std of returns)
    for i in range(20, n):
        features[i, 3] = np.std(features[i-20:i, 1])

    # Feature 4: RSI (14-period)
    rsi = calculate_rsi(close, period=14)
    features[:, 4] = rsi / 100.0  # Normalize to 0-1

    # Feature 5-6: MACD (12, 26, 9)
    macd_line, signal_line = calculate_macd(close)
    features[:, 5] = macd_line / (close + 1e-8)  # Normalize by price
    features[:, 6] = signal_line / (close + 1e-8)

    # Feature 7-9: Bollinger Bands (20-period, 2 std)
    bb_mid, bb_upper, bb_lower = calculate_bollinger_bands(close, period=20, std_mult=2)
    features[:, 7] = (close - bb_mid) / (bb_upper - bb_lower + 1e-8)  # Position within bands
    features[:, 8] = (bb_upper - close) / (close + 1e-8)  # Distance to upper band
    features[:, 9] = (close - bb_lower) / (close + 1e-8)  # Distance to lower band

    # Feature 10: Volume relative to 20-period average
    vol_sma = np.zeros(n)
    for i in range(20, n):
        vol_sma[i] = np.mean(volume[i-20:i])
    features[:, 10] = volume / (vol_sma + 1e-8) - 1  # Normalized volume

    # Feature 11: Price momentum (10-period)
    for i in range(10, n):
        features[i, 11] = (close[i] - close[i-10]) / (close[i-10] + 1e-8)

    # Feature 12: Price momentum (20-period)
    for i in range(20, n):
        features[i, 12] = (close[i] - close[i-20]) / (close[i-20] + 1e-8)

    # Feature 13: SMA crossover (10 vs 20)
    sma_10 = np.zeros(n)
    sma_20 = np.zeros(n)
    for i in range(20, n):
        sma_10[i] = np.mean(close[i-10:i])
        sma_20[i] = np.mean(close[i-20:i])
    features[:, 13] = (sma_10 - sma_20) / (close + 1e-8)

    # Feature 14: High-Low range (volatility proxy)
    features[:, 14] = (high - low) / (close + 1e-8)

    # Feature 15: Close position in day's range
    features[:, 15] = (close - low) / (high - low + 1e-8)

    # Feature 16-17: ATR (14-period Average True Range)
    atr = calculate_atr(high, low, close, period=14)
    features[:, 16] = atr / (close + 1e-8)  # Normalized ATR

    # Feature 17: Stochastic %K (14-period)
    stoch_k = calculate_stochastic(high, low, close, period=14)
    features[:, 17] = stoch_k / 100.0  # Normalize to 0-1

    # Feature 18: OBV trend (On-Balance Volume)
    obv = calculate_obv(close, volume)
    obv_sma = np.zeros(n)
    for i in range(20, n):
        obv_sma[i] = np.mean(obv[i-20:i])
    features[:, 18] = np.sign(obv - obv_sma)  # OBV above/below average

    # Feature 19: VWAP deviation
    vwap = np.cumsum(close * volume) / (np.cumsum(volume) + 1e-8)
    features[:, 19] = (close - vwap) / (vwap + 1e-8)

    return features


def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Relative Strength Index"""
    n = len(prices)
    rsi = np.full(n, 50.0)  # Default to neutral

    if n < period + 1:
        return rsi

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # Initial average gain/loss
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi[i + 1] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate MACD line and signal line"""
    n = len(prices)

    # EMA calculation
    def ema(data, period):
        result = np.zeros(n)
        multiplier = 2 / (period + 1)
        result[0] = data[0]
        for i in range(1, n):
            result[i] = (data[i] - result[i-1]) * multiplier + result[i-1]
        return result

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)

    return macd_line, signal_line


def calculate_bollinger_bands(prices: np.ndarray, period: int = 20, std_mult: float = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate Bollinger Bands"""
    n = len(prices)
    mid = np.zeros(n)
    upper = np.zeros(n)
    lower = np.zeros(n)

    for i in range(period, n):
        window = prices[i-period:i]
        mid[i] = np.mean(window)
        std = np.std(window)
        upper[i] = mid[i] + std_mult * std
        lower[i] = mid[i] - std_mult * std

    # Fill initial values
    mid[:period] = prices[:period]
    upper[:period] = prices[:period]
    lower[:period] = prices[:period]

    return mid, upper, lower


def calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Average True Range"""
    n = len(high)
    tr = np.zeros(n)
    atr = np.zeros(n)

    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )

    atr[period-1] = np.mean(tr[:period])
    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    return atr


def calculate_stochastic(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Stochastic %K"""
    n = len(close)
    stoch_k = np.full(n, 50.0)

    for i in range(period, n):
        highest = np.max(high[i-period:i])
        lowest = np.min(low[i-period:i])
        if highest != lowest:
            stoch_k[i] = 100 * (close[i] - lowest) / (highest - lowest)

    return stoch_k


def calculate_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """Calculate On-Balance Volume"""
    n = len(close)
    obv = np.zeros(n)
    obv[0] = volume[0]

    for i in range(1, n):
        if close[i] > close[i-1]:
            obv[i] = obv[i-1] + volume[i]
        elif close[i] < close[i-1]:
            obv[i] = obv[i-1] - volume[i]
        else:
            obv[i] = obv[i-1]

    return obv


class Action(Enum):
    """Trading actions"""
    HOLD = 0
    BUY = 1
    SELL = 2
    CLOSE = 3  # Close current position


@dataclass
class Position:
    """Current trading position"""
    side: str  # "long", "short", or "flat"
    entry_price: float = 0.0
    size: float = 0.0
    unrealized_pnl: float = 0.0
    entry_time: int = 0


@dataclass
class TradeResult:
    """Result of a completed trade"""
    entry_price: float
    exit_price: float
    side: str
    size: float
    pnl: float
    pnl_pct: float
    holding_period: int
    timestamp: int


class TradingEnvironment:
    """
    Reinforcement Learning Environment for Trading

    State Space:
    - Price features (returns, volatility, momentum)
    - Technical indicators (RSI, MACD, BB)
    - Position info (side, unrealized P&L, holding time)
    - Account info (equity, drawdown)

    Action Space:
    - 0: Hold
    - 1: Buy/Long
    - 2: Sell/Short
    - 3: Close position

    Reward:
    - Realized P&L on trade close
    - Risk-adjusted returns (Sharpe-like)
    - Penalties for excessive trading
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        max_position_size: float = 0.1,  # 10% of equity
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.0005,  # 0.05%
        lookback_window: int = 50,
        max_steps: int = 10000,
        reward_scaling: float = 1.0,
        risk_penalty: float = 0.1,
        trade_penalty: float = 0.0001,
    ):
        self.initial_balance = initial_balance
        self.max_position_size = max_position_size
        self.commission = commission
        self.slippage = slippage
        self.lookback_window = lookback_window
        self.max_steps = max_steps
        self.reward_scaling = reward_scaling
        self.risk_penalty = risk_penalty
        self.trade_penalty = trade_penalty

        # State dimensions
        self.n_features = 20  # Price/indicator features
        self.n_position_features = 4  # Position state
        self.n_account_features = 3  # Account state

        self.observation_space_dim = (
            self.lookback_window * self.n_features +
            self.n_position_features +
            self.n_account_features
        )
        self.action_space_dim = 4  # HOLD, BUY, SELL, CLOSE

        self.reset()

    def reset(self, price_data: Optional[np.ndarray] = None, use_real_data: bool = True) -> np.ndarray:
        """Reset environment to initial state

        Args:
            price_data: Optional pre-loaded price data
            use_real_data: If True, use cached real Kraken data (default)
        """
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.peak_equity = self.initial_balance

        self.position = Position(side="flat")
        self.trade_history: List[TradeResult] = []

        self.current_step = 0
        self.done = False

        # Price data: shape (n_steps, n_features)
        if price_data is not None:
            self.price_data = price_data
        elif use_real_data and _CACHE_LOADED and _DATA_CACHE:
            # Use random segment from cached real data
            self.price_data = self._get_real_data_segment()
        else:
            # Fallback: Generate dummy data for testing
            logger.warning("Using dummy data - real data not loaded!")
            self.price_data = self._generate_dummy_data()

        self.prices = self.price_data[:, 0]  # First column is close price
        self.current_price = self.prices[self.lookback_window]

        # Performance tracking
        self.returns_history = deque(maxlen=100)
        self.equity_history = [self.initial_balance]

        # Track which symbol we're trading (for logging)
        self.current_symbol = getattr(self, '_current_symbol', 'UNKNOWN')

        return self._get_observation()

    def _get_real_data_segment(self) -> np.ndarray:
        """Get a random segment of real market data for training"""
        global _DATA_CACHE, _CACHE_SYMBOLS

        if not _DATA_CACHE:
            return self._generate_dummy_data()

        # Pick a random symbol
        symbol = random.choice(_CACHE_SYMBOLS)
        self._current_symbol = symbol
        data = _DATA_CACHE[symbol]

        # Required length
        required_length = self.max_steps + self.lookback_window

        if len(data) >= required_length:
            # Pick a random starting point
            max_start = len(data) - required_length
            start_idx = random.randint(0, max_start) if max_start > 0 else 0
            segment = data[start_idx:start_idx + required_length].copy()
        else:
            # Data is shorter than required - use all of it and pad if needed
            segment = data.copy()
            # Update max_steps for this episode
            self.max_steps = len(segment) - self.lookback_window - 1

        return segment

    def _generate_dummy_data(self) -> np.ndarray:
        """Generate dummy price data for testing"""
        n_steps = self.max_steps + self.lookback_window
        n_features = self.n_features

        # Random walk prices
        returns = np.random.randn(n_steps) * 0.02
        prices = 100 * np.exp(np.cumsum(returns))

        # Create feature matrix
        data = np.zeros((n_steps, n_features))
        data[:, 0] = prices  # Close price

        # Simple derived features
        for i in range(1, n_features):
            lag = min(i, 20)
            data[lag:, i] = np.diff(prices[:n_steps - lag + 1], n=1) / prices[:-lag]

        return data

    def _get_observation(self) -> np.ndarray:
        """Build observation vector from current state"""
        obs = []

        # Price/indicator features (lookback window)
        start_idx = max(0, self.current_step)
        end_idx = self.current_step + self.lookback_window

        if end_idx > len(self.price_data):
            end_idx = len(self.price_data)
            start_idx = end_idx - self.lookback_window

        window_data = self.price_data[start_idx:end_idx]

        # Normalize price features
        price_mean = np.mean(window_data[:, 0])
        price_std = np.std(window_data[:, 0]) + 1e-8

        normalized_prices = (window_data[:, 0] - price_mean) / price_std
        obs.extend(normalized_prices.flatten())

        # Add other features (already returns/normalized)
        for i in range(1, min(self.n_features, window_data.shape[1])):
            feature = window_data[:, i]
            feature = np.clip(feature, -5, 5)  # Clip extreme values
            obs.extend(feature.flatten())

        # Pad if needed
        while len(obs) < self.lookback_window * self.n_features:
            obs.append(0.0)

        # Position features
        position_encoding = {
            "flat": 0.0,
            "long": 1.0,
            "short": -1.0
        }
        obs.append(position_encoding.get(self.position.side, 0.0))

        # Unrealized P&L (normalized)
        unrealized_pnl_pct = self.position.unrealized_pnl / self.initial_balance
        obs.append(np.clip(unrealized_pnl_pct, -1, 1))

        # Holding time (normalized)
        holding_time = (self.current_step - self.position.entry_time) / 100
        obs.append(np.clip(holding_time, 0, 1))

        # Position size (normalized)
        obs.append(self.position.size / self.initial_balance if self.initial_balance else 0)

        # Account features
        equity_change = (self.equity - self.initial_balance) / self.initial_balance
        obs.append(np.clip(equity_change, -1, 1))

        drawdown = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity else 0
        obs.append(np.clip(drawdown, 0, 1))

        # Recent return volatility
        if len(self.returns_history) > 0:
            recent_vol = np.std(list(self.returns_history))
            obs.append(np.clip(recent_vol * 10, 0, 1))
        else:
            obs.append(0.0)

        return np.array(obs, dtype=np.float32)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute action and return (observation, reward, done, info)
        """
        if self.done:
            return self._get_observation(), 0.0, True, {}

        self.current_step += 1
        prev_equity = self.equity

        # Get current price
        price_idx = min(self.current_step + self.lookback_window, len(self.prices) - 1)
        self.current_price = self.prices[price_idx]

        # Execute action
        reward = 0.0
        trade_executed = False

        action_enum = Action(action)

        if action_enum == Action.BUY:
            if self.position.side == "flat":
                # Open long position
                self._open_position("long")
                trade_executed = True
            elif self.position.side == "short":
                # Close short, open long
                reward += self._close_position()
                self._open_position("long")
                trade_executed = True

        elif action_enum == Action.SELL:
            if self.position.side == "flat":
                # Open short position
                self._open_position("short")
                trade_executed = True
            elif self.position.side == "long":
                # Close long, open short
                reward += self._close_position()
                self._open_position("short")
                trade_executed = True

        elif action_enum == Action.CLOSE:
            if self.position.side != "flat":
                reward += self._close_position()
                trade_executed = True

        # Update unrealized P&L
        self._update_position_pnl()

        # Update equity
        self.equity = self.balance + self.position.unrealized_pnl
        self.peak_equity = max(self.peak_equity, self.equity)

        # Calculate step return
        step_return = (self.equity - prev_equity) / prev_equity if prev_equity else 0
        self.returns_history.append(step_return)
        self.equity_history.append(self.equity)

        # Calculate reward
        reward += self._calculate_reward(step_return, trade_executed)

        # Check termination conditions
        self.done = self._check_done()

        info = {
            "equity": self.equity,
            "balance": self.balance,
            "position": self.position.side,
            "unrealized_pnl": self.position.unrealized_pnl,
            "n_trades": len(self.trade_history),
            "step": self.current_step,
        }

        return self._get_observation(), reward, self.done, info

    def _open_position(self, side: str):
        """Open a new position"""
        # Calculate position size
        position_value = self.equity * self.max_position_size

        # Apply slippage
        if side == "long":
            entry_price = self.current_price * (1 + self.slippage)
        else:
            entry_price = self.current_price * (1 - self.slippage)

        # Deduct commission
        commission_cost = position_value * self.commission
        self.balance -= commission_cost

        self.position = Position(
            side=side,
            entry_price=entry_price,
            size=position_value,
            unrealized_pnl=0.0,
            entry_time=self.current_step
        )

    def _close_position(self) -> float:
        """Close current position and return realized P&L"""
        if self.position.side == "flat":
            return 0.0

        # Calculate exit price with slippage
        if self.position.side == "long":
            exit_price = self.current_price * (1 - self.slippage)
            pnl = (exit_price - self.position.entry_price) / self.position.entry_price
        else:
            exit_price = self.current_price * (1 + self.slippage)
            pnl = (self.position.entry_price - exit_price) / self.position.entry_price

        realized_pnl = pnl * self.position.size

        # Deduct commission
        commission_cost = self.position.size * self.commission
        realized_pnl -= commission_cost

        # Update balance
        self.balance += realized_pnl

        # Record trade
        trade = TradeResult(
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            side=self.position.side,
            size=self.position.size,
            pnl=realized_pnl,
            pnl_pct=pnl * 100,
            holding_period=self.current_step - self.position.entry_time,
            timestamp=self.current_step
        )
        self.trade_history.append(trade)

        # Reset position
        self.position = Position(side="flat")

        return realized_pnl

    def _update_position_pnl(self):
        """Update unrealized P&L for current position"""
        if self.position.side == "flat":
            self.position.unrealized_pnl = 0.0
            return

        if self.position.side == "long":
            pnl = (self.current_price - self.position.entry_price) / self.position.entry_price
        else:
            pnl = (self.position.entry_price - self.current_price) / self.position.entry_price

        self.position.unrealized_pnl = pnl * self.position.size

    def _calculate_reward(self, step_return: float, trade_executed: bool) -> float:
        """
        Calculate reward for the current step

        Components:
        1. P&L reward (scaled)
        2. Risk penalty (drawdown, volatility)
        3. Trade penalty (discourage overtrading)
        """
        reward = 0.0

        # P&L component
        reward += step_return * self.reward_scaling * 100

        # Risk penalty
        if len(self.returns_history) > 10:
            volatility = np.std(list(self.returns_history))
            drawdown = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity else 0

            # Penalize high volatility and drawdown
            reward -= volatility * self.risk_penalty
            reward -= drawdown * self.risk_penalty

        # Trade penalty (discourage churning)
        if trade_executed:
            reward -= self.trade_penalty

        return reward

    def _check_done(self) -> bool:
        """Check if episode should terminate"""
        # Max steps reached
        if self.current_step >= self.max_steps - 1:
            return True

        # Out of data
        if self.current_step + self.lookback_window >= len(self.prices) - 1:
            return True

        # Bankruptcy
        if self.equity <= self.initial_balance * 0.5:  # Lost 50%
            return True

        return False

    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics for the episode"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
            }

        wins = [t for t in self.trade_history if t.pnl > 0]
        losses = [t for t in self.trade_history if t.pnl < 0]

        total_pnl = sum(t.pnl for t in self.trade_history)
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 1

        # Calculate Sharpe ratio
        if len(self.returns_history) > 1:
            returns = np.array(list(self.returns_history))
            sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Calculate max drawdown
        equity_array = np.array(self.equity_history)
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak
        max_drawdown = np.max(drawdown)

        # Convert numpy types to Python native for JSON serialization
        return {
            "total_trades": len(self.trade_history),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": float(len(wins) / len(self.trade_history)) if self.trade_history else 0.0,
            "total_pnl": float(total_pnl),
            "avg_pnl": float(total_pnl / len(self.trade_history)),
            "gross_profit": float(gross_profit),
            "gross_loss": float(gross_loss),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else 0.0,
            "final_equity": float(self.equity),
            "return_pct": float((self.equity - self.initial_balance) / self.initial_balance * 100),
        }

    def render(self, mode: str = "human"):
        """Render current state (for debugging)"""
        print(f"\n=== Step {self.current_step} ===")
        print(f"Price: ${self.current_price:.2f}")
        print(f"Position: {self.position.side}")
        print(f"Unrealized P&L: ${self.position.unrealized_pnl:.2f}")
        print(f"Balance: ${self.balance:.2f}")
        print(f"Equity: ${self.equity:.2f}")
        print(f"Trades: {len(self.trade_history)}")
