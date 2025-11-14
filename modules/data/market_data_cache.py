"""
Market Data Cache - Database caching layer for OHLCV data

Provides intelligent caching of historical market data to:
- Reduce API calls and avoid rate limits
- Speed up data retrieval
- Enable offline operation
- Store data from multiple sources (Kraken, Yahoo Finance)
"""

import sqlite3
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

# Project root path
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database path for market data cache
MARKET_DATA_CACHE_DB_PATH = DATA_DIR / "market_data_cache.db"


class MarketDataCache:
    """Caching layer for OHLCV market data"""

    def __init__(self):
        self.db_path = MARKET_DATA_CACHE_DB_PATH
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema for market data caching"""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # OHLCV candles table - stores all historical candle data
            cur.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                vwap REAL,
                trades INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(symbol, source, timeframe, timestamp)
            )
            """)

            # Create indexes for fast lookups
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_timestamp
            ON ohlcv_candles(symbol, timeframe, timestamp DESC)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlcv_source
            ON ohlcv_candles(source)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp
            ON ohlcv_candles(timestamp DESC)
            """)

            # Cache metadata table - tracks cache freshness and statistics
            cur.execute("""
            CREATE TABLE IF NOT EXISTS cache_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                last_fetch_timestamp INTEGER NOT NULL,
                last_candle_timestamp INTEGER NOT NULL,
                candle_count INTEGER DEFAULT 0,
                fetch_count INTEGER DEFAULT 0,
                last_error TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(symbol, source, timeframe)
            )
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_metadata_symbol_source_timeframe
            ON cache_metadata(symbol, source, timeframe)
            """)

            conn.commit()
            print("✅ Market data cache DB initialized")

    def store_candles(self, symbol: str, source: str, timeframe: str, candles: List[Dict]) -> int:
        """
        Store OHLCV candles in the cache

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETHUSD', 'AAPL')
            source: Data source ('kraken', 'yahoo', 'coingecko', 'generated')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            candles: List of candle dicts with keys: time, open, high, low, close, volume

        Returns:
            Number of candles inserted (duplicates are ignored)
        """
        if not candles:
            return 0

        with self._get_connection() as conn:
            cur = conn.cursor()
            inserted = 0

            for candle in candles:
                try:
                    cur.execute("""
                    INSERT OR REPLACE INTO ohlcv_candles
                    (symbol, source, timeframe, timestamp, open, high, low, close, volume, vwap, trades, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        symbol.upper(),
                        source.lower(),
                        timeframe,
                        int(candle['time']),
                        float(candle['open']),
                        float(candle['high']),
                        float(candle['low']),
                        float(candle['close']),
                        float(candle.get('volume', 0)),
                        float(candle.get('vwap', 0)) if candle.get('vwap') else None,
                        int(candle.get('count', 0)) if candle.get('count') else None
                    ))
                    inserted += 1
                except sqlite3.Error as e:
                    print(f"⚠️  Error inserting candle: {e}")
                    continue

            # Update metadata
            if candles:
                last_candle_time = max(int(c['time']) for c in candles)
                cur.execute("""
                INSERT OR REPLACE INTO cache_metadata
                (symbol, source, timeframe, last_fetch_timestamp, last_candle_timestamp, candle_count, fetch_count, updated_at)
                VALUES (
                    ?, ?, ?, ?, ?,
                    COALESCE((SELECT candle_count FROM cache_metadata WHERE symbol=? AND source=? AND timeframe=?), 0) + ?,
                    COALESCE((SELECT fetch_count FROM cache_metadata WHERE symbol=? AND source=? AND timeframe=?), 0) + 1,
                    datetime('now')
                )
                """, (
                    symbol.upper(), source.lower(), timeframe,
                    int(time.time()), last_candle_time,
                    symbol.upper(), source.lower(), timeframe, inserted,
                    symbol.upper(), source.lower(), timeframe
                ))

            conn.commit()
            return inserted

    def get_candles(
        self,
        symbol: str,
        source: str,
        timeframe: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        Retrieve candles from cache

        Args:
            symbol: Trading symbol
            source: Data source
            timeframe: Timeframe
            start_time: Optional start timestamp (inclusive)
            end_time: Optional end timestamp (inclusive)
            limit: Maximum number of candles to return (default 500)

        Returns:
            List of candle dicts sorted by timestamp ascending
        """
        with self._get_connection() as conn:
            cur = conn.cursor()

            query = """
            SELECT timestamp as time, open, high, low, close, volume, vwap, trades
            FROM ohlcv_candles
            WHERE symbol = ? AND source = ? AND timeframe = ?
            """
            params = [symbol.upper(), source.lower(), timeframe]

            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(int(start_time))

            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(int(end_time))

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

            candles = []
            for row in rows:
                candle = dict(row)
                # Remove None values
                candle = {k: v for k, v in candle.items() if v is not None}
                candles.append(candle)

            # Return in chronological order (oldest first)
            return list(reversed(candles))

    def get_latest_candle(self, symbol: str, source: str, timeframe: str) -> Optional[Dict]:
        """Get the most recent candle from cache"""
        candles = self.get_candles(symbol, source, timeframe, limit=1)
        return candles[0] if candles else None

    def get_cache_info(self, symbol: str, source: str, timeframe: str) -> Optional[Dict]:
        """
        Get cache metadata for a symbol/source/timeframe combination

        Returns:
            Dict with cache info or None if not cached
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT * FROM cache_metadata
            WHERE symbol = ? AND source = ? AND timeframe = ?
            """, (symbol.upper(), source.lower(), timeframe))

            row = cur.fetchone()
            return dict(row) if row else None

    def is_cache_fresh(
        self,
        symbol: str,
        source: str,
        timeframe: str,
        max_age_seconds: int = 3600
    ) -> bool:
        """
        Check if cached data is still fresh

        Args:
            symbol: Trading symbol
            source: Data source
            timeframe: Timeframe
            max_age_seconds: Maximum age in seconds before cache is stale (default 1 hour)

        Returns:
            True if cache exists and is fresh, False otherwise
        """
        info = self.get_cache_info(symbol, source, timeframe)
        if not info:
            return False

        age = int(time.time()) - info['last_fetch_timestamp']
        return age < max_age_seconds

    def get_cache_age(self, symbol: str, source: str, timeframe: str) -> Optional[int]:
        """
        Get the age of cached data in seconds

        Returns:
            Age in seconds or None if not cached
        """
        info = self.get_cache_info(symbol, source, timeframe)
        if not info:
            return None

        return int(time.time()) - info['last_fetch_timestamp']

    def clear_cache(
        self,
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        timeframe: Optional[str] = None,
        older_than_seconds: Optional[int] = None
    ) -> int:
        """
        Clear cached data based on filters

        Args:
            symbol: Optional symbol filter
            source: Optional source filter
            timeframe: Optional timeframe filter
            older_than_seconds: Optional age filter (delete data older than X seconds)

        Returns:
            Number of candles deleted
        """
        with self._get_connection() as conn:
            cur = conn.cursor()

            query = "DELETE FROM ohlcv_candles WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())

            if source:
                query += " AND source = ?"
                params.append(source.lower())

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            if older_than_seconds:
                cutoff_time = int(time.time()) - older_than_seconds
                query += " AND timestamp < ?"
                params.append(cutoff_time)

            cur.execute(query, params)
            deleted = cur.rowcount

            # Clear metadata if all candles for a symbol/source/timeframe are deleted
            if symbol and source and timeframe:
                cur.execute("""
                DELETE FROM cache_metadata
                WHERE symbol = ? AND source = ? AND timeframe = ?
                AND NOT EXISTS (
                    SELECT 1 FROM ohlcv_candles
                    WHERE symbol = ? AND source = ? AND timeframe = ?
                )
                """, (symbol.upper(), source.lower(), timeframe, symbol.upper(), source.lower(), timeframe))

            conn.commit()
            return deleted

    def get_statistics(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dict with overall cache statistics
        """
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Total candles
            cur.execute("SELECT COUNT(*) as total FROM ohlcv_candles")
            total_candles = cur.fetchone()['total']

            # Candles by source
            cur.execute("""
            SELECT source, COUNT(*) as count
            FROM ohlcv_candles
            GROUP BY source
            """)
            by_source = {row['source']: row['count'] for row in cur.fetchall()}

            # Cached symbols
            cur.execute("SELECT COUNT(DISTINCT symbol) as count FROM ohlcv_candles")
            unique_symbols = cur.fetchone()['count']

            # Database size
            cur.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cur.fetchone()['size']

            # Oldest and newest data
            cur.execute("SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM ohlcv_candles")
            time_range = cur.fetchone()

            return {
                "total_candles": total_candles,
                "unique_symbols": unique_symbols,
                "candles_by_source": by_source,
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / 1024 / 1024, 2),
                "oldest_timestamp": time_range['oldest'],
                "newest_timestamp": time_range['newest'],
                "oldest_date": datetime.fromtimestamp(time_range['oldest']).isoformat() if time_range['oldest'] else None,
                "newest_date": datetime.fromtimestamp(time_range['newest']).isoformat() if time_range['newest'] else None
            }

    def vacuum(self):
        """Optimize database by running VACUUM (reclaim space after deletions)"""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            print("✅ Database optimized (VACUUM completed)")


# Singleton instance
market_data_cache = MarketDataCache()
