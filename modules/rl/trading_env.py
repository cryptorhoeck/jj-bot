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
_CACHE_SOURCE: str = ''


def _load_yahoo_data(symbols: List[str], timeframe: str, days: int) -> Dict[str, np.ndarray]:
    """
    Load historical data from Yahoo Finance using yfinance.
    Much faster than exchange APIs with no rate limits.

    Crypto symbols are converted: BTC/USD -> BTC-USD
    """
    global _DATA_CACHE, _CACHE_LOADED, _CACHE_SYMBOLS, _CACHE_TIMEFRAME, _CACHE_DAYS, _CACHE_SOURCE

    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed. Install with: pip install yfinance")
        return {}

    # Yahoo Finance interval mapping
    yf_interval_map = {
        '1m': '1m',    # Only last 7 days available
        '5m': '5m',    # Only last 60 days available
        '15m': '15m',  # Only last 60 days available
        '30m': '30m',  # Only last 60 days available
        '1h': '1h',    # Only last 730 days available
        '4h': '4h',    # Not directly supported, use 1h
        '1d': '1d',    # Full history available
    }

    yf_interval = yf_interval_map.get(timeframe, '1h')

    # Yahoo has limitations on historical data for intraday
    # Adjust days based on interval
    max_days = {
        '1m': 7, '5m': 60, '15m': 60, '30m': 60, '1h': 730, '4h': 730, '1d': 10000
    }
    effective_days = min(days, max_days.get(timeframe, 90))
    if effective_days < days:
        logger.warning(f"Yahoo Finance limits {timeframe} data to {effective_days} days (requested {days})")

    logger.info(f"Fetching {effective_days} days of {timeframe} data for {len(symbols)} symbols from Yahoo Finance...")

    data_cache = {}

    for symbol_idx, symbol in enumerate(symbols):
        # Convert symbol format: BTC/USD -> BTC-USD for Yahoo
        yahoo_symbol = symbol.replace('/', '-')

        try:
            logger.info(f"[{symbol_idx+1}/{len(symbols)}] Fetching {yahoo_symbol}...")

            ticker = yf.Ticker(yahoo_symbol)

            # Calculate period string
            if effective_days <= 7:
                period = '7d'
            elif effective_days <= 30:
                period = '1mo'
            elif effective_days <= 90:
                period = '3mo'
            elif effective_days <= 180:
                period = '6mo'
            elif effective_days <= 365:
                period = '1y'
            elif effective_days <= 730:
                period = '2y'
            elif effective_days <= 1825:
                period = '5y'
            else:
                period = '10y'

            df = ticker.history(period=period, interval=yf_interval)

            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {yahoo_symbol}: {len(df)} candles")
                continue

            # Convert to OHLCV format: [timestamp, open, high, low, close, volume]
            ohlcv_array = np.column_stack([
                df.index.astype('int64') // 10**6,  # timestamp in ms
                df['Open'].values,
                df['High'].values,
                df['Low'].values,
                df['Close'].values,
                df['Volume'].values
            ]).astype(np.float64)

            # Calculate features
            features = calculate_features(ohlcv_array)

            if features is not None and len(features) > 50:
                data_cache[symbol] = features
                logger.info(f"[OK] {symbol}: Loaded {len(features):,} candles from Yahoo")

        except Exception as e:
            logger.warning(f"Failed to fetch {yahoo_symbol} from Yahoo: {e}")
            continue

    if data_cache:
        _DATA_CACHE = data_cache
        _CACHE_LOADED = True
        _CACHE_SYMBOLS = list(data_cache.keys())
        _CACHE_TIMEFRAME = timeframe
        _CACHE_DAYS = effective_days
        _CACHE_SOURCE = 'yahoo'
        logger.info(f"Successfully cached {len(data_cache)} symbols from Yahoo Finance")
    else:
        logger.warning("No data fetched from Yahoo Finance")

    return data_cache


def load_historical_data_sync(symbols: Optional[List[str]] = None, timeframe: str = '1h', days: int = 90, data_source: str = 'kraken') -> Dict[str, np.ndarray]:
    """
    Synchronously fetch historical OHLCV data from exchange with smart pagination.
    Automatically makes multiple requests to fetch the full history period.

    Supported data sources:
    - 'kraken': Default, slower due to rate limits (720 candles/request, 4s interval)
    - 'binance': Faster (1000 candles/request, 0.5s interval), public API works worldwide
    - 'yahoo': Uses yfinance (very fast, no rate limits, but limited crypto coverage)

    Args:
        symbols: List of trading pairs (e.g., ['BTC/USD', 'ETH/USD'])
        timeframe: Candle size ('5m', '15m', '1h', '4h', '1d')
        days: How many days of historical data to fetch
        data_source: 'kraken', 'binance', or 'yahoo'

    Returns dict of symbol -> feature array (n_candles, n_features)
    """
    global _DATA_CACHE, _CACHE_LOADED, _CACHE_SYMBOLS, _CACHE_TIMEFRAME, _CACHE_DAYS, _CACHE_SOURCE

    # Check if cache is valid (same symbols, timeframe, days, and source)
    if _CACHE_LOADED and _DATA_CACHE:
        # Check if requested symbols match cached symbols
        requested_symbols_set = set(symbols) if symbols else set()
        cached_symbols_set = set(_CACHE_SYMBOLS)
        symbols_match = requested_symbols_set == cached_symbols_set

        if symbols_match and _CACHE_TIMEFRAME == timeframe and _CACHE_DAYS == days and _CACHE_SOURCE == data_source:
            logger.info(f"Using cached data for {len(_DATA_CACHE)} symbols (source={data_source}, timeframe={timeframe}, days={days})")
            return _DATA_CACHE
        else:
            # Log why cache was invalidated
            if not symbols_match:
                logger.info(f"Cache invalidated: symbols changed ({len(_CACHE_SYMBOLS)} cached -> {len(symbols) if symbols else 0} requested)")
            else:
                logger.info(f"Cache invalidated: settings changed from {_CACHE_SOURCE}/{_CACHE_TIMEFRAME}/{_CACHE_DAYS}d to {data_source}/{timeframe}/{days}d")
            _DATA_CACHE = {}
            _CACHE_LOADED = False
            _CACHE_SYMBOLS = []

    if not symbols:
        logger.error("No symbols provided for training data")
        return {}

    # Handle Yahoo Finance separately (uses yfinance library)
    if data_source == 'yahoo':
        return _load_yahoo_data(symbols, timeframe, days)

    try:
        import ccxt
    except ImportError:
        logger.warning("ccxt not installed, using dummy data")
        return {}

    # Calculate candles needed based on timeframe and days
    timeframe_minutes = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440
    }
    minutes_per_candle = timeframe_minutes.get(timeframe, 60)
    total_candles_needed = (days * 24 * 60) // minutes_per_candle

    logger.info(f"Fetching {days} days of {timeframe} data ({total_candles_needed:,} candles) for {len(symbols)} symbols from {data_source.upper()}...")

    # Configure exchange based on data source
    if data_source == 'binance':
        # Binance: 1000 candles/request, very generous rate limits
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'rateLimit': 500,  # 0.5 seconds between requests (Binance allows 1200 req/min)
        })
        candles_per_request = 1000
        MIN_REQUEST_INTERVAL = 0.5  # Much faster than Kraken
        # Convert symbols from /USD to /USDT for Binance
        symbol_map = {s: s.replace('/USD', '/USDT') for s in symbols}
    else:
        # Kraken (default): 720 candles/request, strict rate limits
        exchange = ccxt.kraken({
            'enableRateLimit': True,
            'rateLimit': 4000,  # 4 seconds between requests
        })
        candles_per_request = 720
        MIN_REQUEST_INTERVAL = 4.0  # Conservative for Kraken
        symbol_map = {s: s for s in symbols}  # No conversion needed

    try:
        exchange.load_markets()
    except Exception as e:
        logger.error(f"Failed to load {data_source} markets: {e}")
        return {}

    data_cache = {}

    # Track request timing for adaptive rate limiting
    request_count = 0
    last_request_time = 0
    rate_limit_hits = 0
    current_interval = MIN_REQUEST_INTERVAL  # Adaptive interval

    for symbol_idx, symbol in enumerate(symbols):
        # Get the exchange-specific symbol (e.g., BTC/USDT for Binance)
        exchange_symbol = symbol_map.get(symbol, symbol)

        if exchange_symbol not in exchange.markets:
            logger.warning(f"Symbol {exchange_symbol} not available on {data_source}, skipping")
            continue

        try:
            all_ohlcv = []
            candles_fetched = 0
            since = None  # Start from most recent

            # Calculate how many requests we need
            requests_needed = (total_candles_needed + candles_per_request - 1) // candles_per_request

            logger.info(f"[{symbol_idx+1}/{len(symbols)}] Fetching {exchange_symbol}: {requests_needed} requests needed...")

            for req_num in range(requests_needed):
                # Adaptive rate limiting - increase interval after rate limit hits
                current_time = time.time()
                elapsed = current_time - last_request_time
                if elapsed < current_interval:
                    sleep_time = current_interval - elapsed
                    time.sleep(sleep_time)

                # Retry logic with exponential backoff
                max_retries = 5  # Increased from 3
                retry_delay = 15  # Start with 15 second delay (increased from 5)

                for retry in range(max_retries):
                    try:
                        last_request_time = time.time()
                        ohlcv = exchange.fetch_ohlcv(exchange_symbol, timeframe, since=since, limit=candles_per_request)
                        request_count += 1
                        # Gradually decrease interval on success (min 4s)
                        if current_interval > MIN_REQUEST_INTERVAL:
                            current_interval = max(MIN_REQUEST_INTERVAL, current_interval * 0.95)
                        break  # Success, exit retry loop
                    except ccxt.RateLimitExceeded as e:
                        rate_limit_hits += 1
                        # Increase base interval after rate limit
                        current_interval = min(10.0, current_interval * 1.25)
                        if retry < max_retries - 1:
                            logger.warning(f"Rate limited on {symbol}, waiting {retry_delay}s before retry {retry+1}/{max_retries} (interval now {current_interval:.1f}s)...")
                            time.sleep(retry_delay)
                            retry_delay = min(60, retry_delay * 2)  # Cap at 60s
                        else:
                            raise e
                    except Exception as e:
                        if "Too many requests" in str(e) or "rate" in str(e).lower():
                            rate_limit_hits += 1
                            current_interval = min(10.0, current_interval * 1.25)
                            if retry < max_retries - 1:
                                logger.warning(f"Rate limited on {symbol}, waiting {retry_delay}s before retry {retry+1}/{max_retries} (interval now {current_interval:.1f}s)...")
                                time.sleep(retry_delay)
                                retry_delay = min(60, retry_delay * 2)
                            else:
                                raise e
                        else:
                            raise e

                if not ohlcv:
                    break

                # Prepend to get chronological order (we're going backwards)
                all_ohlcv = ohlcv + all_ohlcv
                candles_fetched += len(ohlcv)

                # Progress logging
                if req_num > 0 and (req_num + 1) % 5 == 0:
                    logger.info(f"  {exchange_symbol}: {candles_fetched:,}/{total_candles_needed:,} candles fetched...")

                # Get the oldest timestamp from this batch to fetch older data next
                oldest_timestamp = ohlcv[0][0]
                # Go back one more candle to avoid duplicates
                since = oldest_timestamp - (minutes_per_candle * 60 * 1000 * candles_per_request)

                # Stop if we have enough or no more data
                if candles_fetched >= total_candles_needed or len(ohlcv) < candles_per_request:
                    break

            if not all_ohlcv or len(all_ohlcv) < 100:
                logger.warning(f"Insufficient data for {exchange_symbol}: {len(all_ohlcv) if all_ohlcv else 0} candles")
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
                logger.info(f"[OK] {symbol}: Loaded {len(features):,} candles")

        except Exception as e:
            logger.warning(f"Failed to fetch {symbol}: {e}")
            # On rate limit failure, add extra delay before next symbol
            if "Too many requests" in str(e) or "rate" in str(e).lower():
                cooldown = 60  # Increased from 30 to 60 seconds
                logger.info(f"Rate limit hit, adding {cooldown}s cooldown before next symbol...")
                time.sleep(cooldown)
                # Also increase the base interval
                current_interval = min(10.0, current_interval * 1.5)
            continue

    if data_cache:
        _DATA_CACHE = data_cache
        _CACHE_LOADED = True
        _CACHE_SYMBOLS = list(data_cache.keys())
        _CACHE_TIMEFRAME = timeframe
        _CACHE_DAYS = days
        _CACHE_SOURCE = data_source
        logger.info(f"Successfully cached {len(data_cache)} symbols from {data_source.upper()}: {timeframe} candles for {days} days")
        logger.info(f"  Total API requests: {request_count}, Rate limit hits: {rate_limit_hits}, Final interval: {current_interval:.1f}s")
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

    REALISTIC COST MODEL (for real money trading):
    - Slippage: 0.2% per trade (market orders in crypto)
    - Spread: 0.1% bid-ask (0.05% each side)
    - Commission: 0.1% per trade (Kraken taker fee)
    - TOTAL ROUND-TRIP COST: ~0.7%

    This means a trade must capture >0.7% price move just to break even.
    The model must learn strategies with real edge, not exploit unrealistic execution.

    NO LOOK-AHEAD BIAS:
    - At step T, observations use candles [T : T+lookback] (already closed)
    - Trading occurs at the CLOSE price of candle T+lookback+1
    - All HIGH/LOW/CLOSE values in observation are from completed candles
    - This accurately simulates real trading where you see history, then act

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
        commission: float = 0.001,  # 0.1% (Kraken taker fee)
        slippage: float = 0.002,  # 0.2% - realistic for crypto market orders
        spread: float = 0.001,  # 0.1% bid-ask spread (half-spread applied each side)
        lookback_window: int = 50,
        max_steps: int = 10000,
        reward_scaling: float = 100.0,  # Increased 100x for effective RL learning
        risk_penalty: float = 0.1,
        trade_penalty: float = 0.005,  # Higher penalty to prevent overtrading (real costs matter)
        inference_only: bool = False,  # If True, skip reset (no dummy data warning)
        use_price_inversion: bool = False,  # DISABLED: synthetic bear market augmentation destroys real patterns
    ):
        self.initial_balance = initial_balance
        self.max_position_size = max_position_size
        self.commission = commission
        self.slippage = slippage
        self.spread = spread  # Bid-ask spread
        self.lookback_window = lookback_window
        self.max_steps = max_steps
        self.reward_scaling = reward_scaling
        self.risk_penalty = risk_penalty
        self.trade_penalty = trade_penalty
        self.inference_only = inference_only
        self.use_price_inversion = use_price_inversion  # Disabled by default - destroys real market patterns

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

        # Only reset with data during training, not during inference
        if not inference_only:
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
        """Get a random segment of real market data for training

        Includes data augmentation to prevent long/short bias:
        - 50% chance to invert price data (turns bull market into bear market)
        - This teaches the model that shorts can be profitable too
        """
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

        # DATA AUGMENTATION: Optional price inversion (DISABLED BY DEFAULT)
        # WARNING: Synthetic inversion destroys real market microstructure patterns.
        # Real bear markets have different volatility, order flow, and momentum characteristics.
        # Only enable this if you have insufficient bear market data and understand the risks.
        if self.use_price_inversion and random.random() < 0.5:
            segment = self._invert_price_data(segment)
            self._current_symbol = f"{symbol}_INV"  # Mark as inverted for logging
            logger.debug(f"Price inversion applied to {symbol} (synthetic bear market)")

        return segment

    def _invert_price_data(self, data: np.ndarray) -> np.ndarray:
        """
        Invert price data to create synthetic bear market from bull market.

        This transforms an uptrend into a downtrend while preserving:
        - Volatility patterns
        - Volume patterns
        - Technical indicator relationships

        The key insight: if price goes from 100 -> 110 (10% gain),
        inverted it becomes 100 -> 90.9 (10% loss equivalent).
        """
        inverted = data.copy()

        # Feature 0: Close price - invert around the mean
        prices = data[:, 0]
        price_mean = np.mean(prices)
        # Reflect prices around the mean: new_price = 2*mean - old_price
        # This turns uptrends into downtrends
        inverted[:, 0] = 2 * price_mean - prices

        # Ensure prices stay positive (shift up if needed)
        min_price = np.min(inverted[:, 0])
        if min_price <= 0:
            inverted[:, 0] += abs(min_price) + 1.0

        # Feature 1: Returns - negate (up becomes down)
        inverted[:, 1] = -data[:, 1]

        # Feature 2: Log returns - negate
        inverted[:, 2] = -data[:, 2]

        # Feature 3: Volatility - keep same (volatility is symmetric)
        # inverted[:, 3] = data[:, 3]  # Already copied

        # Feature 4: RSI - invert (high RSI becomes low RSI)
        # RSI is 0-1 normalized, so: inverted = 1 - original
        inverted[:, 4] = 1.0 - data[:, 4]

        # Feature 5-6: MACD - negate (bullish becomes bearish)
        inverted[:, 5] = -data[:, 5]
        inverted[:, 6] = -data[:, 6]

        # Feature 7: BB position - negate (above band becomes below band)
        inverted[:, 7] = -data[:, 7]

        # Feature 8-9: BB distances - swap (upper becomes lower)
        inverted[:, 8] = data[:, 9]  # Distance to upper <- distance to lower
        inverted[:, 9] = data[:, 8]  # Distance to lower <- distance to upper

        # Feature 10: Volume - keep same (volume patterns preserved)
        # inverted[:, 10] = data[:, 10]  # Already copied

        # Feature 11-12: Momentum - negate
        inverted[:, 11] = -data[:, 11]
        inverted[:, 12] = -data[:, 12]

        # Feature 13: SMA crossover - negate
        inverted[:, 13] = -data[:, 13]

        # Feature 14: High-Low range - keep same (range is symmetric)
        # inverted[:, 14] = data[:, 14]  # Already copied

        # Feature 15: Close position in range - invert
        inverted[:, 15] = 1.0 - data[:, 15]

        # Feature 16: ATR - keep same (volatility measure)
        # inverted[:, 16] = data[:, 16]  # Already copied

        # Feature 17: Stochastic %K - invert
        inverted[:, 17] = 1.0 - data[:, 17]

        # Feature 18: OBV trend - negate
        inverted[:, 18] = -data[:, 18]

        # Feature 19: VWAP deviation - negate
        inverted[:, 19] = -data[:, 19]

        return inverted

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
        """Open a new position with realistic execution costs"""
        # Calculate position size
        position_value = self.equity * self.max_position_size

        # Apply spread + slippage (realistic execution)
        # Buying: pay ask price (mid + half spread) + slippage
        # Selling: get bid price (mid - half spread) - slippage
        half_spread = self.spread / 2
        if side == "long":
            # Buying at ask + slippage
            entry_price = self.current_price * (1 + half_spread + self.slippage)
        else:
            # Selling at bid - slippage
            entry_price = self.current_price * (1 - half_spread - self.slippage)

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
        """Close current position with realistic execution costs"""
        if self.position.side == "flat":
            return 0.0

        # Calculate exit price with spread + slippage
        # Closing long (selling): get bid price - slippage
        # Closing short (buying back): pay ask price + slippage
        half_spread = self.spread / 2
        if self.position.side == "long":
            # Selling at bid - slippage
            exit_price = self.current_price * (1 - half_spread - self.slippage)
            pnl = (exit_price - self.position.entry_price) / self.position.entry_price
        else:
            # Buying back at ask + slippage
            exit_price = self.current_price * (1 + half_spread + self.slippage)
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

        FIXED: NO LOOK-AHEAD BIAS - Only uses realized P&L and current observable data.
        This ensures training and live trading use the same information.
        All rewards scaled to roughly -1 to +1 range for stable value learning.
        """
        reward = 0.0

        # =================================================================
        # 1. REALIZED P&L REWARD (Primary signal - no look-ahead!)
        # =================================================================
        # Only reward based on actual realized returns from the step
        # This is the ONLY thing we can measure in live trading
        clamped_return = max(-0.05, min(0.05, step_return))  # Cap at ±5%
        reward += clamped_return * 10  # Scale: 1% move = 0.1 reward

        # =================================================================
        # 2. UNREALIZED P&L FEEDBACK (Observable in real-time)
        # =================================================================
        # Reward/penalize based on current unrealized P&L (no future data)
        if self.position.side != "flat":
            unrealized_pct = self.position.unrealized_pnl / self.position.size if self.position.size else 0
            # Clamp unrealized to prevent extreme values
            unrealized_pct = max(-0.03, min(0.03, unrealized_pct))
            reward += unrealized_pct * 3  # Smaller weight than realized

        # =================================================================
        # 3. TRADE EXECUTION COST (Discourages overtrading)
        # =================================================================
        if trade_executed:
            reward -= 0.02  # Small cost per trade to prevent churning

        # =================================================================
        # 4. WIN STREAK BONUS (Based on past trades only)
        # =================================================================
        if len(self.trade_history) >= 3:
            recent_trades = list(self.trade_history)[-3:]
            recent_wins = sum(1 for t in recent_trades if t.pnl > 0)
            if recent_wins == 3:
                reward += 0.1  # Bonus for 3 wins in a row
            elif recent_wins == 0:
                reward -= 0.08  # Penalty for 3 losses in a row

        # =================================================================
        # 5. SMART HOLDING (Observable metrics only)
        # =================================================================
        if self.position.side != "flat":
            holding_time = self.current_step - self.position.entry_time
            # Reward holding profitable positions
            if self.position.unrealized_pnl > 0 and holding_time > 5:
                reward += 0.02  # Small bonus for holding winners
            # Penalize holding losing positions too long
            elif self.position.unrealized_pnl < -self.position.size * 0.02 and holding_time > 10:
                reward -= 0.03  # Small penalty for holding losers

        # =================================================================
        # 6. RISK PENALTY (Observable drawdown)
        # =================================================================
        if len(self.returns_history) > 10:
            drawdown = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity else 0
            if drawdown > 0.15:
                reward -= 0.1  # Fixed penalty for large drawdown

        # =================================================================
        # 7. HOLD INCENTIVE (Prevent constant trading)
        # =================================================================
        if self.position.side == "flat" and not trade_executed:
            # Small reward for waiting when not in position
            # This teaches the model that it doesn't HAVE to trade every step
            reward += 0.005

        # Clamp total reward to prevent extreme values
        return max(-1.0, min(1.0, reward))

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

        # Calculate additional metrics
        win_pnls = [t.pnl for t in wins] if wins else [0]
        loss_pnls = [t.pnl for t in losses] if losses else [0]

        avg_win = sum(win_pnls) / len(win_pnls) if wins else 0
        avg_loss = abs(sum(loss_pnls) / len(loss_pnls)) if losses else 0
        largest_win = max(win_pnls) if wins else 0
        largest_loss = abs(min(loss_pnls)) if losses else 0

        # Count long vs short trades
        long_trades = sum(1 for t in self.trade_history if t.side == "long")
        short_trades = sum(1 for t in self.trade_history if t.side == "short")

        # Calculate Sortino ratio (only penalizes downside deviation)
        if len(self.returns_history) > 1:
            returns = np.array(list(self.returns_history))
            negative_returns = returns[returns < 0]
            downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 1e-8
            sortino = np.mean(returns) / (downside_std + 1e-8) * np.sqrt(252)
        else:
            sortino = 0.0

        # Calculate Calmar ratio (return / max drawdown)
        annual_return = float((self.equity - self.initial_balance) / self.initial_balance)
        calmar = annual_return / (max_drawdown + 1e-8) if max_drawdown > 0 else 0.0

        # Calculate win/loss streaks from trade history
        current_win_streak = 0
        current_loss_streak = 0
        best_win_streak = 0
        worst_loss_streak = 0

        for trade in self.trade_history:
            if trade.pnl > 0:
                current_win_streak += 1
                current_loss_streak = 0
                if current_win_streak > best_win_streak:
                    best_win_streak = current_win_streak
            else:
                current_loss_streak += 1
                current_win_streak = 0
                if current_loss_streak > worst_loss_streak:
                    worst_loss_streak = current_loss_streak

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
            "sortino_ratio": float(sortino),
            "max_drawdown": float(max_drawdown * 100),  # As percentage
            "calmar_ratio": float(calmar),
            "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else 0.0,
            "final_equity": float(self.equity),
            "return_pct": float((self.equity - self.initial_balance) / self.initial_balance * 100),
            "avg_win_amount": float(avg_win),
            "avg_loss_amount": float(avg_loss),
            "largest_win": float(largest_win),
            "largest_loss": float(largest_loss),
            "long_trades": int(long_trades),
            "short_trades": int(short_trades),
            "best_win_streak": int(best_win_streak),
            "worst_loss_streak": int(worst_loss_streak),
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
