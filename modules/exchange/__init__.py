"""
Exchange Integration Module
Real exchange connections via CCXT
"""

from .ccxt_connector import (
    CCXTConnector,
    ExchangeType,
    ExchangeCredentials,
    OrderRequest,
    OrderResult,
    OrderType,
    OrderSide,
    OrderStatus,
    Ticker,
    OHLCV,
    OrderBook,
    create_connector,
)

from .live_data_feed import (
    LiveDataFeed,
    PriceUpdate,
    CandleUpdate,
    create_live_feed,
)

__all__ = [
    "CCXTConnector",
    "ExchangeType",
    "ExchangeCredentials",
    "OrderRequest",
    "OrderResult",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "Ticker",
    "OHLCV",
    "OrderBook",
    "create_connector",
    "LiveDataFeed",
    "PriceUpdate",
    "CandleUpdate",
    "create_live_feed",
]
