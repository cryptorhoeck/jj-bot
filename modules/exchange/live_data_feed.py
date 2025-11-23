"""
Live Data Feed Service - Real-time market data from exchanges
Replaces simulated prices with actual exchange data
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json

from .ccxt_connector import (
    CCXTConnector, ExchangeType, Ticker, OHLCV, OrderBook, create_connector
)


logger = logging.getLogger(__name__)


@dataclass
class PriceUpdate:
    """Standardized price update event"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    change_pct: float
    timestamp: datetime
    source: str  # exchange name


@dataclass
class CandleUpdate:
    """Real-time candle update"""
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    is_closed: bool  # True if candle is complete


class LiveDataFeed:
    """
    Real-time market data feed using exchange websockets

    Features:
    - Multiple exchange support
    - Automatic reconnection
    - Price aggregation from multiple sources
    - Historical data caching
    - Event-driven callbacks
    """

    def __init__(
        self,
        exchange: str = "binance",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        sandbox: bool = True
    ):
        self.exchange_name = exchange
        self.connector = create_connector(exchange, api_key, secret, sandbox=sandbox)
        self.sandbox = sandbox

        # Data storage
        self._price_cache: Dict[str, PriceUpdate] = {}
        self._candle_cache: Dict[str, Dict[str, deque]] = {}  # symbol -> timeframe -> candles
        self._orderbook_cache: Dict[str, OrderBook] = {}

        # Callbacks
        self._price_callbacks: List[Callable[[PriceUpdate], None]] = []
        self._candle_callbacks: List[Callable[[CandleUpdate], None]] = []
        self._orderbook_callbacks: List[Callable[[OrderBook], None]] = []

        # State
        self._running = False
        self._subscribed_symbols: List[str] = []
        self._subscribed_timeframes: Dict[str, List[str]] = {}  # symbol -> timeframes

        # Settings
        self.max_candle_history = 1000
        self.reconnect_delay = 5  # seconds

    async def start(self, symbols: List[str], timeframes: List[str] = ["1m", "5m", "1h"]):
        """Start the live data feed"""
        logger.info(f"Starting live data feed for {len(symbols)} symbols on {self.exchange_name}")

        # Connect to exchange
        connected = await self.connector.connect()
        if not connected:
            logger.error("Failed to connect to exchange")
            return False

        ws_connected = await self.connector.connect_websocket()
        if not ws_connected:
            logger.warning("WebSocket not available, falling back to REST polling")

        self._running = True
        self._subscribed_symbols = symbols

        # Initialize candle cache
        for symbol in symbols:
            self._candle_cache[symbol] = {}
            self._subscribed_timeframes[symbol] = timeframes
            for tf in timeframes:
                self._candle_cache[symbol][tf] = deque(maxlen=self.max_candle_history)

        # Register internal callbacks
        self.connector.on_ticker(self._handle_ticker)
        self.connector.on_ohlcv(self._handle_ohlcv)
        self.connector.on_order_book(self._handle_orderbook)

        # Subscribe to streams
        if ws_connected:
            await self.connector.subscribe_ticker(symbols)
            for symbol in symbols:
                for tf in timeframes:
                    await self.connector.subscribe_ohlcv(symbol, tf)
        else:
            # Start REST polling as fallback
            asyncio.create_task(self._poll_prices(symbols))

        # Load initial historical data
        await self._load_historical_data(symbols, timeframes)

        logger.info("Live data feed started successfully")
        return True

    async def stop(self):
        """Stop the data feed"""
        self._running = False
        await self.connector.disconnect()
        logger.info("Live data feed stopped")

    async def _load_historical_data(self, symbols: List[str], timeframes: List[str]):
        """Load historical candles for each symbol/timeframe"""
        for symbol in symbols:
            for tf in timeframes:
                try:
                    candles = await self.connector.get_ohlcv(symbol, tf, limit=500)
                    for candle in candles:
                        self._candle_cache[symbol][tf].append(candle)
                    logger.debug(f"Loaded {len(candles)} historical candles for {symbol} {tf}")
                except Exception as e:
                    logger.error(f"Error loading historical data for {symbol} {tf}: {e}")

    async def _poll_prices(self, symbols: List[str], interval: float = 1.0):
        """Poll prices via REST API (fallback when websocket unavailable)"""
        while self._running:
            try:
                tickers = await self.connector.get_tickers(symbols)
                for symbol, ticker in tickers.items():
                    price_update = PriceUpdate(
                        symbol=symbol,
                        price=ticker.last,
                        bid=ticker.bid,
                        ask=ticker.ask,
                        volume_24h=ticker.volume,
                        change_24h=ticker.change_24h,
                        change_pct=ticker.change_pct,
                        timestamp=ticker.timestamp,
                        source=self.exchange_name
                    )
                    self._price_cache[symbol] = price_update
                    self._emit_price(price_update)

            except Exception as e:
                logger.error(f"Price polling error: {e}")

            await asyncio.sleep(interval)

    def _handle_ticker(self, ticker: Ticker):
        """Handle incoming ticker update from websocket"""
        price_update = PriceUpdate(
            symbol=ticker.symbol,
            price=ticker.last,
            bid=ticker.bid,
            ask=ticker.ask,
            volume_24h=ticker.volume,
            change_24h=ticker.change_24h,
            change_pct=ticker.change_pct,
            timestamp=ticker.timestamp,
            source=self.exchange_name
        )
        self._price_cache[ticker.symbol] = price_update
        self._emit_price(price_update)

    def _handle_ohlcv(self, symbol: str, candle: OHLCV):
        """Handle incoming OHLCV update"""
        # Determine timeframe from context (simplified - in production track per-subscription)
        for tf in self._subscribed_timeframes.get(symbol, []):
            if symbol in self._candle_cache and tf in self._candle_cache[symbol]:
                # Check if this updates existing candle or is new
                cache = self._candle_cache[symbol][tf]
                is_closed = False

                if cache and cache[-1].timestamp == candle.timestamp:
                    # Update existing candle
                    cache[-1] = candle
                else:
                    # New candle
                    cache.append(candle)
                    is_closed = len(cache) > 1

                candle_update = CandleUpdate(
                    symbol=symbol,
                    timeframe=tf,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                    timestamp=candle.timestamp,
                    is_closed=is_closed
                )
                self._emit_candle(candle_update)

    def _handle_orderbook(self, orderbook: OrderBook):
        """Handle incoming order book update"""
        self._orderbook_cache[orderbook.symbol] = orderbook
        self._emit_orderbook(orderbook)

    # ========== Event Emission ==========

    def _emit_price(self, update: PriceUpdate):
        """Emit price update to all callbacks"""
        for callback in self._price_callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Price callback error: {e}")

    def _emit_candle(self, update: CandleUpdate):
        """Emit candle update to all callbacks"""
        for callback in self._candle_callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Candle callback error: {e}")

    def _emit_orderbook(self, orderbook: OrderBook):
        """Emit orderbook update to all callbacks"""
        for callback in self._orderbook_callbacks:
            try:
                callback(orderbook)
            except Exception as e:
                logger.error(f"Orderbook callback error: {e}")

    # ========== Public API ==========

    def on_price(self, callback: Callable[[PriceUpdate], None]):
        """Register callback for price updates"""
        self._price_callbacks.append(callback)

    def on_candle(self, callback: Callable[[CandleUpdate], None]):
        """Register callback for candle updates"""
        self._candle_callbacks.append(callback)

    def on_orderbook(self, callback: Callable[[OrderBook], None]):
        """Register callback for orderbook updates"""
        self._orderbook_callbacks.append(callback)

    def get_price(self, symbol: str) -> Optional[PriceUpdate]:
        """Get latest price for symbol"""
        return self._price_cache.get(symbol)

    def get_prices(self) -> Dict[str, PriceUpdate]:
        """Get all cached prices"""
        return self._price_cache.copy()

    def get_candles(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[OHLCV]:
        """Get cached candles for symbol"""
        if symbol in self._candle_cache and timeframe in self._candle_cache[symbol]:
            candles = list(self._candle_cache[symbol][timeframe])
            return candles[-limit:] if limit else candles
        return []

    def get_orderbook(self, symbol: str) -> Optional[OrderBook]:
        """Get cached orderbook for symbol"""
        return self._orderbook_cache.get(symbol)

    def get_spread(self, symbol: str) -> Optional[float]:
        """Get bid-ask spread for symbol"""
        price = self._price_cache.get(symbol)
        if price and price.bid and price.ask:
            return (price.ask - price.bid) / price.ask * 100  # as percentage
        return None

    def get_mid_price(self, symbol: str) -> Optional[float]:
        """Get mid price (average of bid/ask)"""
        price = self._price_cache.get(symbol)
        if price and price.bid and price.ask:
            return (price.bid + price.ask) / 2
        return None

    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[datetime] = None
    ) -> List[OHLCV]:
        """Fetch historical candles from exchange"""
        since_ts = int(since.timestamp() * 1000) if since else None
        return await self.connector.get_ohlcv(symbol, timeframe, limit, since_ts)

    # ========== Order Book Analysis ==========

    def get_orderbook_imbalance(self, symbol: str, depth: int = 10) -> Optional[float]:
        """
        Calculate order book imbalance
        Returns: -1 (sell pressure) to +1 (buy pressure)
        """
        orderbook = self._orderbook_cache.get(symbol)
        if not orderbook:
            return None

        bid_volume = sum(level[1] for level in orderbook.bids[:depth])
        ask_volume = sum(level[1] for level in orderbook.asks[:depth])

        total = bid_volume + ask_volume
        if total == 0:
            return 0

        return (bid_volume - ask_volume) / total

    def get_vwap(self, symbol: str, depth: int = 20) -> Optional[Dict[str, float]]:
        """
        Calculate Volume-Weighted Average Price from order book
        """
        orderbook = self._orderbook_cache.get(symbol)
        if not orderbook:
            return None

        # Bid VWAP
        bid_value = sum(level[0] * level[1] for level in orderbook.bids[:depth])
        bid_volume = sum(level[1] for level in orderbook.bids[:depth])
        bid_vwap = bid_value / bid_volume if bid_volume else 0

        # Ask VWAP
        ask_value = sum(level[0] * level[1] for level in orderbook.asks[:depth])
        ask_volume = sum(level[1] for level in orderbook.asks[:depth])
        ask_vwap = ask_value / ask_volume if ask_volume else 0

        return {
            "bid_vwap": bid_vwap,
            "ask_vwap": ask_vwap,
            "mid_vwap": (bid_vwap + ask_vwap) / 2
        }

    def get_large_orders(
        self,
        symbol: str,
        threshold_multiplier: float = 3.0
    ) -> Dict[str, List[Dict]]:
        """
        Detect large orders (walls) in order book
        """
        orderbook = self._orderbook_cache.get(symbol)
        if not orderbook:
            return {"bids": [], "asks": []}

        # Calculate average order size
        all_sizes = [level[1] for level in orderbook.bids + orderbook.asks]
        avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 0
        threshold = avg_size * threshold_multiplier

        large_bids = [
            {"price": level[0], "size": level[1]}
            for level in orderbook.bids
            if level[1] > threshold
        ]

        large_asks = [
            {"price": level[0], "size": level[1]}
            for level in orderbook.asks
            if level[1] > threshold
        ]

        return {"bids": large_bids, "asks": large_asks}


# Factory function
def create_live_feed(
    exchange: str = "binance",
    api_key: Optional[str] = None,
    secret: Optional[str] = None,
    sandbox: bool = True
) -> LiveDataFeed:
    """Create a live data feed instance"""
    return LiveDataFeed(exchange, api_key, secret, sandbox)
