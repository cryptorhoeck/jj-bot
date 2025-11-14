"""
Backtesting API Endpoints
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.backtesting.backtester import Backtester
from modules.strategy.strategy_config import STRATEGY_METADATA

# Create router
router = APIRouter(prefix="/api/backtest", tags=["backtesting"])

# Global backtester instance
backtester = None


@router.get("/strategies")
async def get_available_strategies():
    """
    Get list of available trading strategies

    Returns:
        List of strategy metadata with names, descriptions, categories
    """
    return {
        "success": True,
        "strategies": STRATEGY_METADATA
    }


class BacktestRequest(BaseModel):
    """Request model for running a backtest"""
    symbol: str
    strategy: Optional[str] = "rsi_strategy"  # Strategy to use
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: Optional[float] = 10000.0
    commission: Optional[float] = 0.001
    slippage: Optional[float] = 0.0005
    position_size: Optional[float] = 0.1


class HistoricalDataRequest(BaseModel):
    """Request model for loading historical data"""
    symbol: str
    data: list  # List of price dictionaries


@router.post("/load-data")
async def load_historical_data(request: HistoricalDataRequest):
    """
    Load historical price data for backtesting

    Args:
        request: Historical data with symbol and price list

    Returns:
        Success status
    """
    global backtester

    try:
        # Initialize backtester if needed
        if backtester is None:
            backtester = Backtester()

        # Load data
        success = backtester.load_historical_data(request.symbol, request.data)

        if success:
            return {
                "success": True,
                "message": f"Loaded {len(request.data)} data points for {request.symbol}"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to load historical data")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """
    Run a backtest with the specified parameters

    Args:
        request: Backtest configuration

    Returns:
        Backtest results with metrics and trades
    """
    global backtester

    try:
        # Initialize backtester if needed, or use existing one with loaded data
        if backtester is None:
            backtester = Backtester(initial_capital=request.initial_capital)
        else:
            # Update capital for new backtest
            backtester.initial_capital = request.initial_capital

        # Apply configuration
        if request.commission:
            backtester.config["commission"] = request.commission
        if request.slippage:
            backtester.config["slippage"] = request.slippage
        if request.position_size:
            backtester.config["position_size"] = request.position_size

        # Run backtest with strategy parameter
        results = backtester.run_backtest(
            request.symbol,
            strategy=request.strategy,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        # Transform equity curve to simple array of values for frontend
        if "equity_curve" in results:
            # Convert from list of dicts to list of equity values
            results["equity_curve"] = [point["equity"] for point in results["equity_curve"]]

        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_backtest_results():
    """
    Get the most recent backtest results

    Returns:
        Last backtest results or error if none available
    """
    global backtester

    if backtester is None or not backtester.trades:
        raise HTTPException(status_code=404, detail="No backtest results available")

    try:
        # Transform equity curve to simple array for frontend
        equity_curve = [point["equity"] for point in backtester.equity_curve] if backtester.equity_curve else []

        return {
            "success": True,
            "trades": backtester.trades,
            "equity_curve": equity_curve,
            "metrics": backtester.metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_backtest_summary():
    """
    Get formatted summary of backtest results

    Returns:
        Text summary of backtest performance
    """
    global backtester

    if backtester is None or not backtester.trades:
        raise HTTPException(status_code=404, detail="No backtest results available")

    try:
        summary = backtester.get_trade_summary()
        return {
            "success": True,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-sample-data")
async def generate_sample_data(symbol: str = "BTC", days: int = 30):
    """
    Generate sample historical data for testing backtester with realistic patterns

    Creates data with:
    - Trending periods (bull/bear markets)
    - Volatility clusters
    - Occasional sharp moves
    - Patterns that trigger technical indicators

    Args:
        symbol: Cryptocurrency symbol
        days: Number of days of data to generate

    Returns:
        Generated sample data
    """
    import random

    try:
        # Generate realistic-looking price data with trends and volatility
        data = []
        base_price = 45000 if symbol == "BTC" else 2500
        current_price = base_price

        start_date = datetime.now() - timedelta(days=days)

        # Create market regimes (trending vs ranging)
        regime_length = 100  # Hours per regime
        trend_direction = random.choice([1, -1])  # 1 for uptrend, -1 for downtrend
        volatility = 0.03  # Base volatility

        for i in range(days * 24):  # Hourly data
            timestamp = start_date + timedelta(hours=i)

            # Change regime periodically
            if i % regime_length == 0:
                trend_direction = random.choice([1, -1, 0])  # 0 for ranging
                volatility = random.uniform(0.02, 0.05)  # Variable volatility

            # Generate price change
            if trend_direction == 0:
                # Ranging market - mean reversion
                change = random.uniform(-volatility, volatility)
            else:
                # Trending market - directional bias
                trend_strength = 0.003 * trend_direction
                noise = random.uniform(-volatility, volatility)
                change = trend_strength + noise

            # Add occasional sharp moves (10% chance)
            if random.random() < 0.10:
                spike = random.uniform(-0.05, 0.05)
                change += spike

            current_price *= (1 + change)

            # Prevent extreme prices
            current_price = max(base_price * 0.5, min(base_price * 2.0, current_price))

            data.append({
                "price": current_price,
                "timestamp": timestamp.isoformat(),
                "volume": random.uniform(1000, 5000) * (1 + abs(change) * 10)  # Higher volume on big moves
            })

        # Load into backtester
        global backtester
        if backtester is None:
            backtester = Backtester()

        backtester.load_historical_data(symbol, data)

        return {
            "success": True,
            "message": f"Generated {len(data)} sample data points for {symbol}",
            "data_points": len(data),
            "start_date": data[0]["timestamp"],
            "end_date": data[-1]["timestamp"],
            "price_range": {
                "min": round(min(d["price"] for d in data), 2),
                "max": round(max(d["price"] for d in data), 2),
                "start": round(data[0]["price"], 2),
                "end": round(data[-1]["price"], 2)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-csv")
async def upload_csv_data(symbol: str, csv_content: str):
    """
    Upload historical price data from CSV format

    Args:
        symbol: Symbol for the data
        csv_content: CSV data as string (columns: timestamp,price,volume)

    Returns:
        Success status and data loaded count
    """
    global backtester

    try:
        import csv
        from io import StringIO

        # Initialize backtester if needed
        if backtester is None:
            backtester = Backtester()

        # Parse CSV
        csv_reader = csv.DictReader(StringIO(csv_content))
        data = []

        for row in csv_reader:
            try:
                data.append({
                    "timestamp": row.get("timestamp", row.get("date", "")),
                    "price": float(row.get("price", row.get("close", 0))),
                    "volume": float(row.get("volume", 0))
                })
            except (ValueError, KeyError) as e:
                continue  # Skip invalid rows

        if len(data) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid data found in CSV. Expected columns: timestamp,price,volume"
            )

        # Load into backtester
        backtester.load_historical_data(symbol, data)

        return {
            "success": True,
            "message": f"Loaded {len(data)} data points for {symbol}",
            "data_points": len(data),
            "start_date": data[0]["timestamp"] if data else None,
            "end_date": data[-1]["timestamp"] if data else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-with-real-data")
async def run_backtest_with_real_data(
    symbol: str,
    strategy: Optional[str] = "rsi_strategy",
    timeframe: str = "1h",
    num_candles: int = 1000,
    source: str = "auto",
    initial_capital: float = 10000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    position_size: float = 0.1,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Run a backtest with real market data

    This endpoint automatically fetches historical data from the market data service
    and runs a backtest with the specified strategy.

    Args:
        symbol: Trading symbol (e.g., 'BTC', 'ETH', 'AAPL')
        strategy: Strategy to use (default: 'rsi_strategy')
        timeframe: Candle timeframe (1m, 5m, 1h, 1d, etc.)
        num_candles: Number of historical candles to fetch
        source: Data source ('kraken', 'yahoo', 'auto')
        initial_capital: Starting capital
        commission: Commission rate (default 0.1%)
        slippage: Slippage rate (default 0.05%)
        position_size: Position size as fraction of capital (default 10%)
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)

    Returns:
        Backtest results with performance metrics and trades

    Example:
        POST /api/backtest/run-with-real-data?symbol=BTC&strategy=rsi_strategy&timeframe=1h&num_candles=500
    """
    global backtester

    try:
        # Import data loader
        from modules.backtesting import backtest_data_loader

        # Fetch real market data
        print(f"📊 Fetching real market data for {symbol} ({timeframe})...")
        data_result = backtest_data_loader.load_data_for_backtest(
            symbol=symbol,
            timeframe=timeframe,
            num_candles=num_candles,
            source=source,
            start_date=start_date,
            end_date=end_date
        )

        if not data_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch market data: {data_result.get('error')}"
            )

        # Initialize backtester
        backtester = Backtester(initial_capital=initial_capital)
        backtester.config["commission"] = commission
        backtester.config["slippage"] = slippage
        backtester.config["position_size"] = position_size

        # Load data
        success = backtester.load_historical_data(symbol, data_result["data"])

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to load data into backtester"
            )

        print(f"✅ Loaded {len(data_result['data'])} candles from {data_result['metadata']['source']}")

        # Run backtest
        results = backtester.run_backtest(
            symbol,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date
        )

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        # Transform equity curve for frontend
        if "equity_curve" in results:
            results["equity_curve"] = [point["equity"] for point in results["equity_curve"]]

        # Add metadata about data source
        results["data_metadata"] = data_result["metadata"]

        return {
            "success": True,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
