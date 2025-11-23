"""
CCXT Exchange Connector - Real exchange integration for live trading
Supports multiple exchanges with unified API
"""

import ccxt
import ccxt.pro as ccxtpro
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


logger = logging.getLogger(__name__)


class ExchangeType(Enum):
    BINANCE = "binance"
    BINANCE_US = "binanceus"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    KUCOIN = "kucoin"
    BYBIT = "bybit"
    OKX = "okx"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"


@dataclass
class ExchangeCredentials:
    """Exchange API credentials"""
    api_key: str
    secret: str
    password: Optional[str] = None  # Some exchanges require this
    sandbox: bool = True  # Default to sandbox/testnet for safety


@dataclass
class OrderRequest:
    """Order request parameters"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    params: Dict = field(default_factory=dict)


@dataclass
class OrderResult:
    """Order execution result"""
    order_id: str
    symbol: str
    side: str
    order_type: str
    amount: float
    price: float
    cost: float
    filled: float
    remaining: float
    status: OrderStatus
    fee: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw: Dict = field(default_factory=dict)


@dataclass
class Ticker:
    """Real-time ticker data"""
    symbol: str
    bid: float
    ask: float
    last: float
    high: float
    low: float
    volume: float
    change_24h: float
    change_pct: float
    timestamp: datetime


@dataclass
class OHLCV:
    """Candlestick data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class OrderBook:
    """Order book snapshot"""
    symbol: str
    bids: List[List[float]]  # [[price, amount], ...]
    asks: List[List[float]]
    timestamp: datetime


class CCXTConnector:
    """
    Unified exchange connector using CCXT library
    Supports REST API and WebSocket connections
    """

    # Exchange-specific configurations
    EXCHANGE_CONFIGS = {
        ExchangeType.BINANCE: {
            "has_websocket": True,
            "testnet_url": "https://testnet.binance.vision",
            "rate_limit": 1200,  # requests per minute
            "default_type": "spot",
        },
        ExchangeType.BINANCE_US: {
            "has_websocket": True,
            "rate_limit": 1200,
            "default_type": "spot",
        },
        ExchangeType.COINBASE: {
            "has_websocket": True,
            "rate_limit": 600,
            "default_type": "spot",
        },
        ExchangeType.KRAKEN: {
            "has_websocket": True,
            "rate_limit": 600,
            "default_type": "spot",
        },
        ExchangeType.KUCOIN: {
            "has_websocket": True,
            "rate_limit": 600,
            "default_type": "spot",
        },
        ExchangeType.BYBIT: {
            "has_websocket": True,
            "rate_limit": 600,
            "default_type": "spot",
        },
    }

    def __init__(
        self,
        exchange_type: ExchangeType,
        credentials: Optional[ExchangeCredentials] = None,
        sandbox: bool = True
    ):
        self.exchange_type = exchange_type
        self.credentials = credentials
        self.sandbox = sandbox
        self.exchange: Optional[ccxt.Exchange] = None
        self.ws_exchange: Optional[ccxtpro.Exchange] = None
        self._ws_callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        self._ws_tasks: List[asyncio.Task] = []

    async def connect(self) -> bool:
        """Initialize exchange connection"""
        try:
            exchange_id = self.exchange_type.value
            exchange_class = getattr(ccxt, exchange_id)

            config = {
                "enableRateLimit": True,
                "options": {
                    "defaultType": self.EXCHANGE_CONFIGS.get(
                        self.exchange_type, {}
                    ).get("default_type", "spot")
                }
            }

            if self.credentials:
                config["apiKey"] = self.credentials.api_key
                config["secret"] = self.credentials.secret
                if self.credentials.password:
                    config["password"] = self.credentials.password

            if self.sandbox:
                config["sandbox"] = True

            self.exchange = exchange_class(config)

            # Load markets
            await asyncio.to_thread(self.exchange.load_markets)

            logger.info(f"Connected to {exchange_id} ({'sandbox' if self.sandbox else 'live'})")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to exchange: {e}")
            return False

    async def connect_websocket(self) -> bool:
        """Initialize WebSocket connection for real-time data"""
        try:
            exchange_id = self.exchange_type.value

            if not hasattr(ccxtpro, exchange_id):
                logger.warning(f"WebSocket not supported for {exchange_id}")
                return False

            ws_class = getattr(ccxtpro, exchange_id)

            config = {
                "enableRateLimit": True,
            }

            if self.credentials:
                config["apiKey"] = self.credentials.api_key
                config["secret"] = self.credentials.secret
                if self.credentials.password:
                    config["password"] = self.credentials.password

            if self.sandbox:
                config["sandbox"] = True

            self.ws_exchange = ws_class(config)
            self._running = True

            logger.info(f"WebSocket connected to {exchange_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            return False

    async def disconnect(self):
        """Close all connections"""
        self._running = False

        for task in self._ws_tasks:
            task.cancel()

        if self.ws_exchange:
            await self.ws_exchange.close()

        if self.exchange:
            self.exchange.close()

        logger.info("Exchange connections closed")

    # ========== Market Data Methods ==========

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current ticker for symbol"""
        try:
            if not self.exchange:
                await self.connect()

            ticker = await asyncio.to_thread(
                self.exchange.fetch_ticker, symbol
            )

            return Ticker(
                symbol=symbol,
                bid=ticker.get("bid", 0),
                ask=ticker.get("ask", 0),
                last=ticker.get("last", 0),
                high=ticker.get("high", 0),
                low=ticker.get("low", 0),
                volume=ticker.get("baseVolume", 0),
                change_24h=ticker.get("change", 0),
                change_pct=ticker.get("percentage", 0),
                timestamp=datetime.fromtimestamp(ticker["timestamp"] / 1000) if ticker.get("timestamp") else datetime.now()
            )

        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    async def get_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Ticker]:
        """Get tickers for multiple symbols"""
        try:
            if not self.exchange:
                await self.connect()

            tickers = await asyncio.to_thread(
                self.exchange.fetch_tickers, symbols
            )

            result = {}
            for symbol, ticker in tickers.items():
                result[symbol] = Ticker(
                    symbol=symbol,
                    bid=ticker.get("bid", 0),
                    ask=ticker.get("ask", 0),
                    last=ticker.get("last", 0),
                    high=ticker.get("high", 0),
                    low=ticker.get("low", 0),
                    volume=ticker.get("baseVolume", 0),
                    change_24h=ticker.get("change", 0),
                    change_pct=ticker.get("percentage", 0),
                    timestamp=datetime.fromtimestamp(ticker["timestamp"] / 1000) if ticker.get("timestamp") else datetime.now()
                )
            return result

        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return {}

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[int] = None
    ) -> List[OHLCV]:
        """Get historical OHLCV data"""
        try:
            if not self.exchange:
                await self.connect()

            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol, timeframe, since, limit
            )

            return [
                OHLCV(
                    timestamp=datetime.fromtimestamp(candle[0] / 1000),
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5]
                )
                for candle in ohlcv
            ]

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []

    async def get_order_book(
        self,
        symbol: str,
        limit: int = 20
    ) -> Optional[OrderBook]:
        """Get current order book"""
        try:
            if not self.exchange:
                await self.connect()

            book = await asyncio.to_thread(
                self.exchange.fetch_order_book, symbol, limit
            )

            return OrderBook(
                symbol=symbol,
                bids=book.get("bids", []),
                asks=book.get("asks", []),
                timestamp=datetime.fromtimestamp(book["timestamp"] / 1000) if book.get("timestamp") else datetime.now()
            )

        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            return None

    # ========== WebSocket Streaming Methods ==========

    def on_ticker(self, callback: Callable[[Ticker], None]):
        """Register callback for ticker updates"""
        if "ticker" not in self._ws_callbacks:
            self._ws_callbacks["ticker"] = []
        self._ws_callbacks["ticker"].append(callback)

    def on_ohlcv(self, callback: Callable[[str, OHLCV], None]):
        """Register callback for OHLCV updates"""
        if "ohlcv" not in self._ws_callbacks:
            self._ws_callbacks["ohlcv"] = []
        self._ws_callbacks["ohlcv"].append(callback)

    def on_order_book(self, callback: Callable[[OrderBook], None]):
        """Register callback for order book updates"""
        if "orderbook" not in self._ws_callbacks:
            self._ws_callbacks["orderbook"] = []
        self._ws_callbacks["orderbook"].append(callback)

    def on_trade(self, callback: Callable[[Dict], None]):
        """Register callback for trade updates"""
        if "trade" not in self._ws_callbacks:
            self._ws_callbacks["trade"] = []
        self._ws_callbacks["trade"].append(callback)

    async def subscribe_ticker(self, symbols: List[str]):
        """Subscribe to real-time ticker updates"""
        if not self.ws_exchange:
            await self.connect_websocket()

        async def ticker_loop():
            while self._running:
                try:
                    for symbol in symbols:
                        ticker = await self.ws_exchange.watch_ticker(symbol)

                        ticker_obj = Ticker(
                            symbol=symbol,
                            bid=ticker.get("bid", 0),
                            ask=ticker.get("ask", 0),
                            last=ticker.get("last", 0),
                            high=ticker.get("high", 0),
                            low=ticker.get("low", 0),
                            volume=ticker.get("baseVolume", 0),
                            change_24h=ticker.get("change", 0),
                            change_pct=ticker.get("percentage", 0),
                            timestamp=datetime.now()
                        )

                        for callback in self._ws_callbacks.get("ticker", []):
                            try:
                                callback(ticker_obj)
                            except Exception as e:
                                logger.error(f"Ticker callback error: {e}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Ticker stream error: {e}")
                    await asyncio.sleep(1)

        task = asyncio.create_task(ticker_loop())
        self._ws_tasks.append(task)

    async def subscribe_ohlcv(self, symbol: str, timeframe: str = "1m"):
        """Subscribe to real-time OHLCV updates"""
        if not self.ws_exchange:
            await self.connect_websocket()

        async def ohlcv_loop():
            while self._running:
                try:
                    ohlcv = await self.ws_exchange.watch_ohlcv(symbol, timeframe)

                    if ohlcv:
                        latest = ohlcv[-1]
                        candle = OHLCV(
                            timestamp=datetime.fromtimestamp(latest[0] / 1000),
                            open=latest[1],
                            high=latest[2],
                            low=latest[3],
                            close=latest[4],
                            volume=latest[5]
                        )

                        for callback in self._ws_callbacks.get("ohlcv", []):
                            try:
                                callback(symbol, candle)
                            except Exception as e:
                                logger.error(f"OHLCV callback error: {e}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"OHLCV stream error: {e}")
                    await asyncio.sleep(1)

        task = asyncio.create_task(ohlcv_loop())
        self._ws_tasks.append(task)

    async def subscribe_order_book(self, symbol: str, limit: int = 20):
        """Subscribe to real-time order book updates"""
        if not self.ws_exchange:
            await self.connect_websocket()

        async def orderbook_loop():
            while self._running:
                try:
                    book = await self.ws_exchange.watch_order_book(symbol, limit)

                    orderbook = OrderBook(
                        symbol=symbol,
                        bids=book.get("bids", [])[:limit],
                        asks=book.get("asks", [])[:limit],
                        timestamp=datetime.now()
                    )

                    for callback in self._ws_callbacks.get("orderbook", []):
                        try:
                            callback(orderbook)
                        except Exception as e:
                            logger.error(f"OrderBook callback error: {e}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"OrderBook stream error: {e}")
                    await asyncio.sleep(1)

        task = asyncio.create_task(orderbook_loop())
        self._ws_tasks.append(task)

    # ========== Trading Methods ==========

    async def create_order(self, order: OrderRequest) -> Optional[OrderResult]:
        """Create a new order"""
        try:
            if not self.exchange:
                await self.connect()

            if not self.credentials:
                logger.error("Cannot create order without credentials")
                return None

            # Build order parameters
            params = order.params.copy()

            # Add stop loss / take profit if supported
            if order.stop_loss:
                params["stopLoss"] = {"triggerPrice": order.stop_loss}
            if order.take_profit:
                params["takeProfit"] = {"triggerPrice": order.take_profit}

            result = await asyncio.to_thread(
                self.exchange.create_order,
                order.symbol,
                order.order_type.value,
                order.side.value,
                order.amount,
                order.price,
                params
            )

            return OrderResult(
                order_id=result["id"],
                symbol=result["symbol"],
                side=result["side"],
                order_type=result["type"],
                amount=result["amount"],
                price=result.get("price", 0) or result.get("average", 0),
                cost=result.get("cost", 0),
                filled=result.get("filled", 0),
                remaining=result.get("remaining", 0),
                status=OrderStatus(result["status"]),
                fee=result.get("fee"),
                timestamp=datetime.fromtimestamp(result["timestamp"] / 1000) if result.get("timestamp") else datetime.now(),
                raw=result
            )

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an open order"""
        try:
            if not self.exchange:
                await self.connect()

            await asyncio.to_thread(
                self.exchange.cancel_order, order_id, symbol
            )
            return True

        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False

    async def get_order(self, order_id: str, symbol: str) -> Optional[OrderResult]:
        """Get order status"""
        try:
            if not self.exchange:
                await self.connect()

            result = await asyncio.to_thread(
                self.exchange.fetch_order, order_id, symbol
            )

            return OrderResult(
                order_id=result["id"],
                symbol=result["symbol"],
                side=result["side"],
                order_type=result["type"],
                amount=result["amount"],
                price=result.get("price", 0) or result.get("average", 0),
                cost=result.get("cost", 0),
                filled=result.get("filled", 0),
                remaining=result.get("remaining", 0),
                status=OrderStatus(result["status"]),
                fee=result.get("fee"),
                raw=result
            )

        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """Get all open orders"""
        try:
            if not self.exchange:
                await self.connect()

            orders = await asyncio.to_thread(
                self.exchange.fetch_open_orders, symbol
            )

            return [
                OrderResult(
                    order_id=o["id"],
                    symbol=o["symbol"],
                    side=o["side"],
                    order_type=o["type"],
                    amount=o["amount"],
                    price=o.get("price", 0),
                    cost=o.get("cost", 0),
                    filled=o.get("filled", 0),
                    remaining=o.get("remaining", 0),
                    status=OrderStatus(o["status"]),
                    raw=o
                )
                for o in orders
            ]

        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    # ========== Account Methods ==========

    async def get_balance(self) -> Dict[str, Dict]:
        """Get account balances"""
        try:
            if not self.exchange:
                await self.connect()

            if not self.credentials:
                return {}

            balance = await asyncio.to_thread(self.exchange.fetch_balance)

            return {
                "total": balance.get("total", {}),
                "free": balance.get("free", {}),
                "used": balance.get("used", {}),
            }

        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}

    async def get_positions(self) -> List[Dict]:
        """Get open positions (for margin/futures)"""
        try:
            if not self.exchange:
                await self.connect()

            if not self.credentials:
                return []

            if hasattr(self.exchange, "fetch_positions"):
                positions = await asyncio.to_thread(self.exchange.fetch_positions)
                return positions
            return []

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    # ========== Utility Methods ==========

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol/market information"""
        if self.exchange and symbol in self.exchange.markets:
            return self.exchange.markets[symbol]
        return None

    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols"""
        if self.exchange:
            return list(self.exchange.markets.keys())
        return []

    def format_symbol(self, base: str, quote: str = "USDT") -> str:
        """Format symbol for this exchange"""
        return f"{base}/{quote}"

    async def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Get funding rate for perpetual contracts"""
        try:
            if not self.exchange:
                await self.connect()

            if hasattr(self.exchange, "fetch_funding_rate"):
                rate = await asyncio.to_thread(
                    self.exchange.fetch_funding_rate, symbol
                )
                return rate
            return None

        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return None


# Convenience function to create connector
def create_connector(
    exchange: str,
    api_key: Optional[str] = None,
    secret: Optional[str] = None,
    password: Optional[str] = None,
    sandbox: bool = True
) -> CCXTConnector:
    """Factory function to create exchange connector"""

    exchange_type = ExchangeType(exchange.lower())

    credentials = None
    if api_key and secret:
        credentials = ExchangeCredentials(
            api_key=api_key,
            secret=secret,
            password=password,
            sandbox=sandbox
        )

    return CCXTConnector(exchange_type, credentials, sandbox)
