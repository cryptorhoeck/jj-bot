"""
Data Loader for Backtesting

Fetches real historical OHLCV data for backtesting from cached market data service
"""

import sys
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.data import cached_market_data_service


class BacktestDataLoader:
    """Load historical data for backtesting from real market sources"""

    def __init__(self):
        self.data_service = cached_market_data_service

    def load_data_for_backtest(
        self,
        symbol: str,
        timeframe: str = "1h",
        num_candles: int = 1000,
        source: str = "auto",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Load historical data optimized for backtesting

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETH', 'AAPL')
            timeframe: Timeframe for candles (1m, 5m, 1h, 1d, etc.)
            num_candles: Number of candles to fetch (default 1000)
            source: Data source ('kraken', 'yahoo', 'auto')
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)

        Returns:
            Dict with:
                - success: bool
                - symbol: str
                - data: List of price dicts for backtester
                - metadata: Additional information
        """
        try:
            # Fetch OHLCV data from cached service
            result = self.data_service.get_ohlcv(
                symbol=symbol,
                source=source,
                timeframe=timeframe,
                num_candles=num_candles,
                force_refresh=False  # Use cache when possible
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to fetch data")
                }

            candles = result["candles"]

            if not candles:
                return {
                    "success": False,
                    "error": "No candle data available"
                }

            # Convert OHLCV candles to backtester format
            # Backtester expects: {price, timestamp, volume, high, low, open, close}
            backtester_data = []

            for candle in candles:
                # Convert timestamp from unix seconds to ISO string
                timestamp = datetime.fromtimestamp(candle["time"]).isoformat()

                # Filter by date range if specified
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    break

                backtester_data.append({
                    "timestamp": timestamp,
                    "price": candle["close"],  # Use close as primary price
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle.get("volume", 0)
                })

            if not backtester_data:
                return {
                    "success": False,
                    "error": "No data in specified date range"
                }

            return {
                "success": True,
                "symbol": symbol,
                "data": backtester_data,
                "metadata": {
                    "source": result.get("source", "unknown"),
                    "timeframe": timeframe,
                    "num_candles": len(backtester_data),
                    "from_cache": result.get("from_cache", False),
                    "cache_age": result.get("cache_age"),
                    "start_date": backtester_data[0]["timestamp"],
                    "end_date": backtester_data[-1]["timestamp"],
                    "price_range": {
                        "high": max(c["high"] for c in backtester_data),
                        "low": min(c["low"] for c in backtester_data),
                        "start": backtester_data[0]["close"],
                        "end": backtester_data[-1]["close"]
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error loading backtest data: {str(e)}"
            }

    def load_multiple_symbols(
        self,
        symbols: List[str],
        timeframe: str = "1h",
        num_candles: int = 1000,
        source: str = "auto"
    ) -> Dict[str, Dict]:
        """
        Load data for multiple symbols

        Args:
            symbols: List of symbols to load
            timeframe: Timeframe for all symbols
            num_candles: Number of candles for each symbol
            source: Data source

        Returns:
            Dict mapping symbol to result dict
        """
        results = {}

        for symbol in symbols:
            print(f"Loading backtest data for {symbol}...")
            results[symbol] = self.load_data_for_backtest(
                symbol=symbol,
                timeframe=timeframe,
                num_candles=num_candles,
                source=source
            )

            if results[symbol]["success"]:
                print(f"  ✅ Loaded {results[symbol]['metadata']['num_candles']} candles")
            else:
                print(f"  ❌ Failed: {results[symbol].get('error')}")

        return results

    def get_optimal_timeframe_for_period(self, days: int) -> str:
        """
        Get optimal timeframe based on backtest period

        Args:
            days: Number of days to backtest

        Returns:
            Recommended timeframe string
        """
        if days <= 1:
            return "5m"
        elif days <= 7:
            return "15m"
        elif days <= 30:
            return "1h"
        elif days <= 90:
            return "4h"
        else:
            return "1d"

    def estimate_candles_needed(self, days: int, timeframe: str) -> int:
        """
        Estimate number of candles needed for a given period

        Args:
            days: Number of days
            timeframe: Timeframe string

        Returns:
            Estimated number of candles
        """
        intervals_per_day = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "30m": 48,
            "1h": 24,
            "4h": 6,
            "1d": 1,
            "1w": 1 / 7
        }

        interval_count = intervals_per_day.get(timeframe, 24)
        return int(days * interval_count * 1.1)  # 10% buffer

    def preload_data_for_symbols(
        self,
        symbols: List[str],
        timeframes: List[str] = ["1h", "1d"],
        num_candles: int = 1000
    ) -> Dict:
        """
        Preload and cache data for multiple symbols and timeframes

        Useful for preparing data before running multiple backtests

        Args:
            symbols: List of symbols
            timeframes: List of timeframes to preload
            num_candles: Number of candles per timeframe

        Returns:
            Statistics about preloaded data
        """
        stats = {
            "symbols_processed": 0,
            "timeframes_processed": 0,
            "total_candles": 0,
            "errors": []
        }

        for symbol in symbols:
            for timeframe in timeframes:
                result = self.load_data_for_backtest(
                    symbol=symbol,
                    timeframe=timeframe,
                    num_candles=num_candles
                )

                if result["success"]:
                    stats["total_candles"] += result["metadata"]["num_candles"]
                    stats["timeframes_processed"] += 1
                    print(f"✅ Preloaded {symbol} {timeframe}: {result['metadata']['num_candles']} candles")
                else:
                    stats["errors"].append(f"{symbol}/{timeframe}: {result.get('error')}")
                    print(f"❌ Failed {symbol} {timeframe}: {result.get('error')}")

            stats["symbols_processed"] += 1

        return stats


# Singleton instance
backtest_data_loader = BacktestDataLoader()
