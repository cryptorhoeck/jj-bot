"""
Price History Module

Stores and retrieves price data for analysis, indicators, and regime detection.
Provides multi-timeframe aggregation and efficient querying.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.database.connection import get_db_connection, PRICE_HISTORY_DB_PATH


class PriceHistory:
    """
    Manages price history storage and retrieval.

    Features:
    - Store tick-by-tick price data
    - Multi-timeframe aggregation (1m, 5m, 15m, 1h, 4h, 1d)
    - Efficient range queries
    - Automatic cleanup of old data
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize price history manager.

        Args:
            db_path: Path to price history database (defaults to PRICE_HISTORY_DB_PATH)
        """
        self.db_path = db_path or PRICE_HISTORY_DB_PATH

    def add_price_tick(
        self,
        symbol: str,
        price: float,
        volume: float = 0.0,
        timestamp: Optional[datetime] = None
    ):
        """
        Add a price tick to history.

        Args:
            symbol: Trading symbol (e.g., "BTC", "ETH")
            price: Price value
            volume: Trading volume
            timestamp: Tick timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO price_ticks (timestamp, symbol, price, volume)
                VALUES (?, ?, ?, ?)
            """, (timestamp.isoformat(), symbol, price, volume))
            conn.commit()

    def add_price_ticks_batch(self, ticks: List[Dict]):
        """
        Add multiple price ticks in batch.

        Args:
            ticks: List of dicts with keys: symbol, price, volume, timestamp
        """
        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            for tick in ticks:
                timestamp = tick.get('timestamp', datetime.now())
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)

                cur.execute("""
                    INSERT INTO price_ticks (timestamp, symbol, price, volume)
                    VALUES (?, ?, ?, ?)
                """, (
                    timestamp.isoformat(),
                    tick['symbol'],
                    tick['price'],
                    tick.get('volume', 0.0)
                ))
            conn.commit()

    def get_recent_prices(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get most recent prices for a symbol.

        Args:
            symbol: Trading symbol
            limit: Maximum number of prices to return

        Returns:
            List of price dicts (timestamp, price, volume)
        """
        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, price, volume
                FROM price_ticks
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, limit))

            rows = cur.fetchall()
            return [
                {
                    'timestamp': row[0],
                    'price': row[1],
                    'volume': row[2]
                }
                for row in reversed(rows)  # Reverse to get chronological order
            ]

    def get_price_range(
        self,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get prices within a time range.

        Args:
            symbol: Trading symbol
            start_time: Start of range
            end_time: End of range (defaults to now)

        Returns:
            List of price dicts
        """
        if end_time is None:
            end_time = datetime.now()

        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, price, volume
                FROM price_ticks
                WHERE symbol = ?
                AND timestamp >= ?
                AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (symbol, start_time.isoformat(), end_time.isoformat()))

            rows = cur.fetchall()
            return [
                {
                    'timestamp': row[0],
                    'price': row[1],
                    'volume': row[2]
                }
                for row in rows
            ]

    def get_price_array(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[float]:
        """
        Get price values as simple array (for indicator calculations).

        Args:
            symbol: Trading symbol
            limit: Number of prices

        Returns:
            List of price values (chronological order)
        """
        prices_data = self.get_recent_prices(symbol, limit)
        return [p['price'] for p in prices_data]

    def get_ohlc(
        self,
        symbol: str,
        timeframe_minutes: int = 5,
        periods: int = 100
    ) -> List[Dict]:
        """
        Get OHLC (Open, High, Low, Close) candles.

        Args:
            symbol: Trading symbol
            timeframe_minutes: Candle timeframe in minutes (1, 5, 15, 60, 240, 1440)
            periods: Number of candles to return

        Returns:
            List of OHLC dicts
        """
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=timeframe_minutes * periods * 2)  # Get extra data

        # Get raw price ticks
        ticks = self.get_price_range(symbol, start_time, end_time)

        if not ticks:
            return []

        # Aggregate into OHLC candles
        candles = []
        current_candle = None
        candle_start = None

        for tick in ticks:
            tick_time = datetime.fromisoformat(tick['timestamp'])

            # Calculate which candle this tick belongs to
            candle_timestamp = tick_time.replace(
                minute=(tick_time.minute // timeframe_minutes) * timeframe_minutes,
                second=0,
                microsecond=0
            )

            # Start new candle if needed
            if candle_start != candle_timestamp:
                if current_candle:
                    candles.append(current_candle)

                current_candle = {
                    'timestamp': candle_timestamp.isoformat(),
                    'open': tick['price'],
                    'high': tick['price'],
                    'low': tick['price'],
                    'close': tick['price'],
                    'volume': tick['volume']
                }
                candle_start = candle_timestamp
            else:
                # Update current candle
                current_candle['high'] = max(current_candle['high'], tick['price'])
                current_candle['low'] = min(current_candle['low'], tick['price'])
                current_candle['close'] = tick['price']
                current_candle['volume'] += tick['volume']

        # Add final candle
        if current_candle:
            candles.append(current_candle)

        # Return requested number of periods
        return candles[-periods:]

    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Remove price data older than specified days.

        Args:
            days_to_keep: Number of days of history to keep
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM price_ticks
                WHERE timestamp < ?
            """, (cutoff_time.isoformat(),))
            deleted = cur.rowcount
            conn.commit()

        print(f"🧹 Cleaned up {deleted} old price ticks (older than {days_to_keep} days)")

    def get_statistics(self, symbol: str, hours: int = 24) -> Dict:
        """
        Get price statistics for a symbol over time period.

        Args:
            symbol: Trading symbol
            hours: Time period in hours

        Returns:
            Dict with statistics (min, max, avg, volatility, etc.)
        """
        start_time = datetime.now() - timedelta(hours=hours)
        prices_data = self.get_price_range(symbol, start_time)

        if not prices_data:
            return {
                'symbol': symbol,
                'period_hours': hours,
                'count': 0
            }

        prices = [p['price'] for p in prices_data]

        # Calculate statistics
        import statistics

        return {
            'symbol': symbol,
            'period_hours': hours,
            'count': len(prices),
            'min': min(prices),
            'max': max(prices),
            'mean': statistics.mean(prices),
            'median': statistics.median(prices),
            'stdev': statistics.stdev(prices) if len(prices) > 1 else 0,
            'first_price': prices[0],
            'last_price': prices[-1],
            'change': prices[-1] - prices[0],
            'change_pct': ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0
        }
