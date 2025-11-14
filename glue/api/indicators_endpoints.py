"""
Technical Indicators API Endpoints

Provides RESTful endpoints for calculating technical indicators:
- MACD, Bollinger Bands, Fibonacci levels
- RSI, SMA, EMA, ATR
- Stochastic Oscillator, OBV, VWAP
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from modules.analysis import indicators
from modules.data import cached_market_data_service

router = APIRouter()


# === Request/Response Models ===

class IndicatorRequest(BaseModel):
    """Request model for indicator calculation"""
    symbol: str
    source: str = "auto"
    timeframe: str = "1h"
    num_candles: int = 200
    indicator: str  # macd, bollinger, rsi, etc.
    params: dict = {}  # Optional parameters for the indicator


# === Endpoints ===

@router.get("/indicators/all/{symbol}")
async def get_all_indicators(
    symbol: str,
    source: str = Query("auto", description="Data source: kraken, yahoo, or auto"),
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w"),
    num_candles: int = Query(200, description="Number of candles")
):
    """
    Get all available technical indicators for a symbol

    Returns a comprehensive set of indicators:
    - MACD (12, 26, 9)
    - Bollinger Bands (20, 2)
    - RSI (14)
    - SMA (20, 50, 200)
    - EMA (12, 26)
    - ATR (14)
    - Stochastic Oscillator (14, 3, 3)

    Example: /indicators/all/BTC?timeframe=1h&num_candles=200
    """
    try:
        # Fetch OHLCV data
        ohlcv_result = cached_market_data_service.get_ohlcv(
            symbol=symbol,
            source=source,
            timeframe=timeframe,
            num_candles=num_candles
        )

        if not ohlcv_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

        candles = ohlcv_result["candles"]
        if not candles:
            raise HTTPException(status_code=404, detail="No candle data available")

        # Extract price data
        close_prices = [c["close"] for c in candles]
        high_prices = [c["high"] for c in candles]
        low_prices = [c["low"] for c in candles]
        open_prices = [c["open"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        # Calculate all indicators
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "num_candles": len(candles),
            "indicators": {}
        }

        # MACD
        macd_data = indicators.macd(close_prices)
        result["indicators"]["macd"] = macd_data

        # Bollinger Bands
        bb_data = indicators.bollinger_bands(close_prices)
        result["indicators"]["bollinger_bands"] = bb_data

        # RSI
        rsi_data = indicators.rsi(close_prices, 14)
        result["indicators"]["rsi"] = rsi_data

        # Moving Averages
        result["indicators"]["sma_20"] = indicators.sma(close_prices, 20)
        result["indicators"]["sma_50"] = indicators.sma(close_prices, 50)
        result["indicators"]["sma_200"] = indicators.sma(close_prices, 200)
        result["indicators"]["ema_12"] = indicators.ema(close_prices, 12)
        result["indicators"]["ema_26"] = indicators.ema(close_prices, 26)

        # ATR
        atr_data = indicators.atr(high_prices, low_prices, close_prices)
        result["indicators"]["atr"] = atr_data

        # Stochastic Oscillator
        stoch_data = indicators.stochastic_oscillator(high_prices, low_prices, close_prices)
        result["indicators"]["stochastic"] = stoch_data

        # Volume indicators
        result["indicators"]["obv"] = indicators.obv(close_prices, volumes)
        result["indicators"]["vwap"] = indicators.vwap(high_prices, low_prices, close_prices, volumes)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/macd/{symbol}")
async def get_macd(
    symbol: str,
    source: str = Query("auto"),
    timeframe: str = Query("1h"),
    num_candles: int = Query(200),
    fast_period: int = Query(12),
    slow_period: int = Query(26),
    signal_period: int = Query(9)
):
    """
    Get MACD indicator for a symbol

    Parameters:
    - fast_period: Fast EMA period (default 12)
    - slow_period: Slow EMA period (default 26)
    - signal_period: Signal line period (default 9)

    Returns:
    - macd_line: MACD line values
    - signal_line: Signal line values
    - histogram: MACD histogram values
    """
    try:
        ohlcv_result = cached_market_data_service.get_ohlcv(
            symbol=symbol, source=source, timeframe=timeframe, num_candles=num_candles
        )

        if not ohlcv_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

        close_prices = [c["close"] for c in ohlcv_result["candles"]]
        macd_data = indicators.macd(close_prices, fast_period, slow_period, signal_period)

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "macd",
            "data": macd_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/bollinger/{symbol}")
async def get_bollinger_bands(
    symbol: str,
    source: str = Query("auto"),
    timeframe: str = Query("1h"),
    num_candles: int = Query(200),
    period: int = Query(20),
    std_dev: float = Query(2.0)
):
    """
    Get Bollinger Bands for a symbol

    Parameters:
    - period: Moving average period (default 20)
    - std_dev: Number of standard deviations (default 2.0)

    Returns:
    - upper_band: Upper Bollinger Band
    - middle_band: Middle band (SMA)
    - lower_band: Lower Bollinger Band
    - bandwidth: Bandwidth percentage
    """
    try:
        ohlcv_result = cached_market_data_service.get_ohlcv(
            symbol=symbol, source=source, timeframe=timeframe, num_candles=num_candles
        )

        if not ohlcv_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

        close_prices = [c["close"] for c in ohlcv_result["candles"]]
        bb_data = indicators.bollinger_bands(close_prices, period, std_dev)

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "bollinger_bands",
            "data": bb_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/fibonacci/{symbol}")
async def get_fibonacci_levels(
    symbol: str,
    source: str = Query("auto"),
    timeframe: str = Query("1d"),
    num_candles: int = Query(100),
    trend: str = Query("uptrend", description="uptrend or downtrend")
):
    """
    Get Fibonacci retracement levels for a symbol

    Calculates Fibonacci levels based on the highest and lowest prices
    in the specified period.

    Parameters:
    - trend: "uptrend" or "downtrend" (determines direction of levels)

    Returns Fibonacci levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
    """
    try:
        ohlcv_result = cached_market_data_service.get_ohlcv(
            symbol=symbol, source=source, timeframe=timeframe, num_candles=num_candles
        )

        if not ohlcv_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

        candles = ohlcv_result["candles"]
        high_prices = [c["high"] for c in candles]
        low_prices = [c["low"] for c in candles]

        swing_high = max(high_prices)
        swing_low = min(low_prices)

        fib_levels = indicators.fibonacci_retracement(swing_high, swing_low, trend)

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "fibonacci_retracement",
            "swing_high": swing_high,
            "swing_low": swing_low,
            "trend": trend,
            "levels": fib_levels
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/rsi/{symbol}")
async def get_rsi(
    symbol: str,
    source: str = Query("auto"),
    timeframe: str = Query("1h"),
    num_candles: int = Query(200),
    period: int = Query(14)
):
    """
    Get RSI (Relative Strength Index) for a symbol

    Parameters:
    - period: RSI period (default 14)

    Returns RSI values (0-100)
    """
    try:
        ohlcv_result = cached_market_data_service.get_ohlcv(
            symbol=symbol, source=source, timeframe=timeframe, num_candles=num_candles
        )

        if not ohlcv_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

        close_prices = [c["close"] for c in ohlcv_result["candles"]]
        rsi_data = indicators.rsi(close_prices, period)

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "rsi",
            "period": period,
            "data": rsi_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/atr/{symbol}")
async def get_atr(
    symbol: str,
    source: str = Query("auto"),
    timeframe: str = Query("1h"),
    num_candles: int = Query(200),
    period: int = Query(14)
):
    """
    Get ATR (Average True Range) for a symbol

    ATR measures volatility

    Parameters:
    - period: ATR period (default 14)
    """
    try:
        ohlcv_result = cached_market_data_service.get_ohlcv(
            symbol=symbol, source=source, timeframe=timeframe, num_candles=num_candles
        )

        if not ohlcv_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch OHLCV data")

        candles = ohlcv_result["candles"]
        high_prices = [c["high"] for c in candles]
        low_prices = [c["low"] for c in candles]
        close_prices = [c["close"] for c in candles]

        atr_data = indicators.atr(high_prices, low_prices, close_prices, period)

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator": "atr",
            "period": period,
            "data": atr_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/available")
async def get_available_indicators():
    """
    Get list of all available indicators

    Returns information about each indicator including:
    - Name
    - Description
    - Parameters
    - Typical use cases
    """
    return {
        "success": True,
        "indicators": {
            "macd": {
                "name": "MACD",
                "full_name": "Moving Average Convergence Divergence",
                "description": "Trend-following momentum indicator",
                "parameters": {
                    "fast_period": {"default": 12, "description": "Fast EMA period"},
                    "slow_period": {"default": 26, "description": "Slow EMA period"},
                    "signal_period": {"default": 9, "description": "Signal line period"}
                },
                "use_cases": ["Trend identification", "Momentum analysis", "Signal generation"]
            },
            "bollinger_bands": {
                "name": "Bollinger Bands",
                "description": "Volatility bands around a moving average",
                "parameters": {
                    "period": {"default": 20, "description": "Moving average period"},
                    "std_dev": {"default": 2.0, "description": "Number of standard deviations"}
                },
                "use_cases": ["Volatility analysis", "Overbought/oversold conditions", "Squeeze detection"]
            },
            "fibonacci": {
                "name": "Fibonacci Retracement",
                "description": "Key support/resistance levels based on Fibonacci ratios",
                "parameters": {
                    "trend": {"default": "uptrend", "description": "Trend direction (uptrend/downtrend)"}
                },
                "use_cases": ["Support/resistance identification", "Retracement targets", "Extension targets"]
            },
            "rsi": {
                "name": "RSI",
                "full_name": "Relative Strength Index",
                "description": "Momentum oscillator (0-100)",
                "parameters": {
                    "period": {"default": 14, "description": "RSI period"}
                },
                "use_cases": ["Overbought/oversold detection", "Divergence analysis", "Momentum measurement"]
            },
            "atr": {
                "name": "ATR",
                "full_name": "Average True Range",
                "description": "Volatility indicator",
                "parameters": {
                    "period": {"default": 14, "description": "ATR period"}
                },
                "use_cases": ["Volatility measurement", "Stop-loss placement", "Position sizing"]
            },
            "stochastic": {
                "name": "Stochastic Oscillator",
                "description": "Momentum indicator comparing closing price to price range",
                "parameters": {
                    "period": {"default": 14, "description": "Lookback period"},
                    "smooth_k": {"default": 3, "description": "%K smoothing period"},
                    "smooth_d": {"default": 3, "description": "%D smoothing period"}
                },
                "use_cases": ["Overbought/oversold detection", "Divergence analysis"]
            },
            "obv": {
                "name": "OBV",
                "full_name": "On-Balance Volume",
                "description": "Volume-based momentum indicator",
                "use_cases": ["Volume trend analysis", "Confirmation of price moves"]
            },
            "vwap": {
                "name": "VWAP",
                "full_name": "Volume Weighted Average Price",
                "description": "Average price weighted by volume",
                "use_cases": ["Intraday trading benchmark", "Trade execution reference"]
            }
        }
    }
