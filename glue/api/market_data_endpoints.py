"""
Market Data API Endpoints - OHLCV data with caching

Provides RESTful endpoints for accessing market data:
- Real-time and historical OHLCV data
- Automatic caching and cache management
- Multiple data sources (Kraken, Yahoo Finance)
- Cache statistics and preloading
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from modules.data import cached_market_data_service, market_data_cache

router = APIRouter()


# === Request/Response Models ===

class OHLCVRequest(BaseModel):
    symbol: str
    source: str = "auto"  # kraken, yahoo, or auto
    timeframe: str = "1h"
    num_candles: int = 200
    force_refresh: bool = False


class PreloadCacheRequest(BaseModel):
    symbols: List[str]
    sources: Optional[List[str]] = None
    timeframes: Optional[List[str]] = None


# === Endpoints ===

@router.get("/market-data/ohlcv/{symbol}")
async def get_ohlcv_data(
    symbol: str,
    source: str = Query("auto", description="Data source: kraken, yahoo, or auto"),
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M"),
    num_candles: int = Query(200, description="Number of candles to return"),
    force_refresh: bool = Query(False, description="Force API fetch even if cache is fresh")
):
    """
    Get OHLCV (Open, High, Low, Close, Volume) data for a symbol

    Uses intelligent caching:
    - Returns cached data if fresh
    - Fetches from API if cache is stale
    - Falls back to generated data if API fails

    Examples:
    - /market-data/ohlcv/BTC?timeframe=1h&num_candles=100
    - /market-data/ohlcv/AAPL?source=yahoo&timeframe=1d&num_candles=365
    - /market-data/ohlcv/ETH?force_refresh=true
    """
    try:
        result = cached_market_data_service.get_ohlcv(
            symbol=symbol,
            source=source,
            timeframe=timeframe,
            num_candles=num_candles,
            force_refresh=force_refresh
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to fetch data"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-data/ohlcv")
async def get_ohlcv_data_post(request: OHLCVRequest):
    """
    Get OHLCV data (POST version for complex requests)

    Request body:
    {
        "symbol": "BTC",
        "source": "kraken",
        "timeframe": "1h",
        "num_candles": 200,
        "force_refresh": false
    }
    """
    try:
        result = cached_market_data_service.get_ohlcv(
            symbol=request.symbol,
            source=request.source,
            timeframe=request.timeframe,
            num_candles=request.num_candles,
            force_refresh=request.force_refresh
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to fetch data"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/price/{symbol}")
async def get_current_price(
    symbol: str,
    source: str = Query("auto", description="Data source: kraken, yahoo, or auto")
):
    """
    Get current price for a symbol

    Examples:
    - /market-data/price/BTC
    - /market-data/price/AAPL?source=yahoo
    """
    try:
        result = cached_market_data_service.get_current_price(symbol, source)

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to fetch price"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-data/cache/preload")
async def preload_cache(request: PreloadCacheRequest):
    """
    Preload cache with data for multiple symbols

    Request body:
    {
        "symbols": ["BTC", "ETH", "AAPL", "TSLA"],
        "sources": ["kraken", "yahoo"],  // optional
        "timeframes": ["1h", "1d"]       // optional
    }

    This endpoint is useful for:
    - Initial cache warming
    - Scheduled cache updates
    - Preparing data for offline use
    """
    try:
        stats = cached_market_data_service.preload_cache(
            symbols=request.symbols,
            sources=request.sources,
            timeframes=request.timeframes
        )

        return {
            "success": True,
            "message": f"Preloaded {stats['candles_cached']} candles for {stats['symbols_processed']} symbols",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics

    Returns:
    - Total candles cached
    - Unique symbols
    - Candles by source
    - Database size
    - Oldest and newest data timestamps
    """
    try:
        stats = cached_market_data_service.get_cache_stats()
        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/cache/info/{symbol}")
async def get_cache_info(
    symbol: str,
    source: str = Query("auto", description="Data source: kraken, yahoo, or auto"),
    timeframe: str = Query("1h", description="Timeframe")
):
    """
    Get cache information for a specific symbol/source/timeframe

    Returns cache metadata including:
    - Last fetch timestamp
    - Last candle timestamp
    - Candle count
    - Fetch count
    - Cache age
    """
    if source == 'auto':
        source = cached_market_data_service._detect_source(symbol)

    try:
        info = market_data_cache.get_cache_info(symbol, source, timeframe)

        if info:
            cache_age = market_data_cache.get_cache_age(symbol, source, timeframe)
            return {
                "success": True,
                "symbol": symbol,
                "source": source,
                "timeframe": timeframe,
                "info": info,
                "cache_age_seconds": cache_age,
                "is_fresh": market_data_cache.is_cache_fresh(symbol, source, timeframe)
            }
        else:
            return {
                "success": False,
                "message": "No cached data found",
                "symbol": symbol,
                "source": source,
                "timeframe": timeframe
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/market-data/cache/clear")
async def clear_cache(
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    source: Optional[str] = Query(None, description="Optional source filter"),
    timeframe: Optional[str] = Query(None, description="Optional timeframe filter"),
    older_than_days: Optional[int] = Query(None, description="Delete data older than X days")
):
    """
    Clear cached data based on filters

    Examples:
    - /market-data/cache/clear?older_than_days=7  (clear data older than 7 days)
    - /market-data/cache/clear?symbol=BTC  (clear all BTC data)
    - /market-data/cache/clear?source=kraken&timeframe=1h  (clear kraken 1h data)
    """
    try:
        older_than_seconds = older_than_days * 86400 if older_than_days else None

        deleted = market_data_cache.clear_cache(
            symbol=symbol,
            source=source,
            timeframe=timeframe,
            older_than_seconds=older_than_seconds
        )

        return {
            "success": True,
            "message": f"Deleted {deleted} candles",
            "deleted_count": deleted
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-data/cache/vacuum")
async def vacuum_cache():
    """
    Optimize cache database (reclaim space after deletions)

    This runs the VACUUM command on SQLite to:
    - Reclaim disk space from deleted records
    - Optimize database performance
    - Defragment the database file
    """
    try:
        market_data_cache.vacuum()
        return {
            "success": True,
            "message": "Cache database optimized"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/sources")
async def get_supported_sources():
    """
    Get list of supported data sources and symbols

    Returns information about:
    - Available data sources
    - Supported symbols per source
    - Supported timeframes
    """
    return {
        "success": True,
        "sources": {
            "kraken": {
                "name": "Kraken",
                "type": "crypto",
                "supported_symbols": ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "POL"],
                "supported_timeframes": ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
            },
            "yahoo": {
                "name": "Yahoo Finance",
                "type": "stocks",
                "supported_symbols": "All stock tickers (AAPL, TSLA, SPY, etc.)",
                "supported_timeframes": ["1m", "5m", "15m", "30m", "1h", "1d", "1w", "1M"]
            }
        },
        "cache_ttl": cached_market_data_service.cache_ttl
    }
