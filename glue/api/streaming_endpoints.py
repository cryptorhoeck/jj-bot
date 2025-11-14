"""
Market Streaming API Endpoints

Provides RESTful endpoints for controlling real-time market data streams
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.streaming.market_stream_service import market_stream_service

router = APIRouter(prefix="/api/stream", tags=["streaming"])


# === Request/Response Models ===

class StreamConfigRequest(BaseModel):
    """Request model for configuring the stream"""
    symbols: Optional[List[str]] = None
    exchange: Optional[str] = None  # 'kraken' or 'binance'


# === Endpoints ===

@router.post("/start")
async def start_market_stream(config: Optional[StreamConfigRequest] = None):
    """
    Start the real-time market data stream

    Optionally configure symbols and exchange before starting

    Request body (optional):
    {
        "symbols": ["BTC", "ETH", "SOL"],
        "exchange": "kraken"
    }

    Examples:
    - POST /api/stream/start
    - POST /api/stream/start {"symbols": ["BTC", "ETH"], "exchange": "binance"}
    """
    try:
        # Apply configuration if provided
        if config:
            if config.symbols:
                market_stream_service.set_symbols(config.symbols)
            if config.exchange:
                market_stream_service.set_exchange(config.exchange)

        # Start the stream
        await market_stream_service.start()

        return {
            "success": True,
            "message": "Market stream started",
            "config": {
                "exchange": market_stream_service.exchange,
                "symbols": market_stream_service.symbols
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_market_stream():
    """
    Stop the real-time market data stream

    Example:
    - POST /api/stream/stop
    """
    try:
        await market_stream_service.stop()

        return {
            "success": True,
            "message": "Market stream stopped"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure")
async def configure_stream(config: StreamConfigRequest):
    """
    Configure the market stream settings

    Request body:
    {
        "symbols": ["BTC", "ETH", "SOL"],
        "exchange": "kraken"
    }

    Note: Stream must be restarted for changes to take effect

    Example:
    - POST /api/stream/configure {"symbols": ["BTC", "ETH", "ADA"], "exchange": "binance"}
    """
    try:
        if config.symbols:
            market_stream_service.set_symbols(config.symbols)

        if config.exchange:
            market_stream_service.set_exchange(config.exchange)

        return {
            "success": True,
            "message": "Stream configuration updated",
            "config": {
                "exchange": market_stream_service.exchange,
                "symbols": market_stream_service.symbols
            },
            "note": "Restart the stream for changes to take effect"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_stream_status():
    """
    Get current status of the market stream

    Returns:
    - running: boolean indicating if stream is active
    - exchange: current exchange ('kraken' or 'binance')
    - symbols: list of subscribed symbols
    - stats: detailed statistics

    Example:
    - GET /api/stream/status
    """
    try:
        return {
            "success": True,
            "status": market_stream_service.get_stats()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices")
async def get_latest_prices():
    """
    Get latest real-time prices for all subscribed symbols

    Returns current prices from the WebSocket stream cache

    Example:
    - GET /api/stream/prices
    """
    try:
        prices = market_stream_service.get_latest_prices()

        return {
            "success": True,
            "prices": prices,
            "timestamp": market_stream_service.stream.stats.get("last_update")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price/{symbol}")
async def get_symbol_price(symbol: str):
    """
    Get latest real-time price for a specific symbol

    Args:
        symbol: Trading symbol (e.g., BTC, ETH, SOL)

    Returns:
        Latest price data from WebSocket stream

    Example:
    - GET /api/stream/price/BTC
    """
    try:
        price_data = market_stream_service.stream.get_latest_price(symbol.upper())

        if not price_data:
            return {
                "success": False,
                "message": f"No price data available for {symbol}",
                "note": "Symbol may not be subscribed in the stream"
            }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "data": price_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-symbol/{symbol}")
async def add_symbol_to_stream(symbol: str):
    """
    Add a new symbol to the stream

    Args:
        symbol: Trading symbol to add (e.g., BTC, ETH)

    Note: Stream must be restarted for the symbol to be added

    Example:
    - POST /api/stream/add-symbol/DOGE
    """
    try:
        symbol = symbol.upper()

        if symbol in market_stream_service.symbols:
            return {
                "success": True,
                "message": f"{symbol} already in stream",
                "symbols": market_stream_service.symbols
            }

        market_stream_service.symbols.append(symbol)

        return {
            "success": True,
            "message": f"Added {symbol} to stream",
            "symbols": market_stream_service.symbols,
            "note": "Restart the stream for changes to take effect"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove-symbol/{symbol}")
async def remove_symbol_from_stream(symbol: str):
    """
    Remove a symbol from the stream

    Args:
        symbol: Trading symbol to remove

    Note: Stream must be restarted for the symbol to be removed

    Example:
    - DELETE /api/stream/remove-symbol/DOGE
    """
    try:
        symbol = symbol.upper()

        if symbol not in market_stream_service.symbols:
            return {
                "success": False,
                "message": f"{symbol} not in stream",
                "symbols": market_stream_service.symbols
            }

        market_stream_service.symbols.remove(symbol)

        return {
            "success": True,
            "message": f"Removed {symbol} from stream",
            "symbols": market_stream_service.symbols,
            "note": "Restart the stream for changes to take effect"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restart")
async def restart_stream():
    """
    Restart the market stream

    Useful for applying configuration changes

    Example:
    - POST /api/stream/restart
    """
    try:
        # Stop if running
        if market_stream_service.running:
            await market_stream_service.stop()

        # Start with current config
        await market_stream_service.start()

        return {
            "success": True,
            "message": "Stream restarted",
            "config": {
                "exchange": market_stream_service.exchange,
                "symbols": market_stream_service.symbols
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-exchanges")
async def get_supported_exchanges():
    """
    Get list of supported exchanges

    Returns information about available WebSocket exchanges

    Example:
    - GET /api/stream/supported-exchanges
    """
    return {
        "success": True,
        "exchanges": {
            "kraken": {
                "name": "Kraken",
                "supported": True,
                "symbols": ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC"],
                "features": ["ticker", "real-time pricing", "auto-reconnect"]
            },
            "binance": {
                "name": "Binance",
                "supported": True,
                "symbols": ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC"],
                "features": ["ticker", "real-time pricing", "auto-reconnect", "higher update frequency"]
            }
        },
        "default": "kraken"
    }
