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
        # Initialize backtester with config
        backtester = Backtester(initial_capital=request.initial_capital)

        # Apply configuration
        if request.commission:
            backtester.config["commission"] = request.commission
        if request.slippage:
            backtester.config["slippage"] = request.slippage
        if request.position_size:
            backtester.config["position_size"] = request.position_size

        # Run backtest
        results = backtester.run_backtest(
            request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

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
        return {
            "success": True,
            "trades": backtester.trades,
            "equity_curve": backtester.equity_curve,
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
    Generate sample historical data for testing backtester

    Args:
        symbol: Cryptocurrency symbol
        days: Number of days of data to generate

    Returns:
        Generated sample data
    """
    import random

    try:
        # Generate realistic-looking price data
        data = []
        base_price = 45000 if symbol == "BTC" else 2500
        current_price = base_price

        start_date = datetime.now() - timedelta(days=days)

        for i in range(days * 24):  # Hourly data
            timestamp = start_date + timedelta(hours=i)

            # Add some random walk
            change = random.uniform(-0.02, 0.02)
            current_price *= (1 + change)

            data.append({
                "price": current_price,
                "timestamp": timestamp.isoformat(),
                "volume": random.uniform(1000, 5000)
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
            "end_date": data[-1]["timestamp"]
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
