"""
Database Connection Module

Provides thread-safe database connectivity and initialization for all JJ-Bot databases.
Uses thread-local storage for connection pooling to ensure safe concurrent access.
"""

import sqlite3
import os
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from datetime import datetime
import json

# Project root path (modules/database -> modules -> project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Backup directory for data safety
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Database paths - SINGLE SOURCE OF TRUTH
TRADES_DB_PATH = DATA_DIR / "trades.db"
PRICE_HISTORY_DB_PATH = DATA_DIR / "price_history.db"
LEARNING_DB_PATH = DATA_DIR / "learning.db"
SYMBOLS_DB_PATH = DATA_DIR / "symbols.db"
MARKET_DATA_CACHE_PATH = DATA_DIR / "market_data_cache.db"


class ThreadSafeConnectionPool:
    """
    Thread-safe SQLite connection pool using thread-local storage.

    Each thread gets its own connection, preventing thread safety issues.
    Connections are reused within the same thread for efficiency.
    """

    def __init__(self):
        self._local = threading.local()
        self._lock = threading.Lock()
        self._connections: Dict[int, Dict[str, sqlite3.Connection]] = {}

    def get_connection(self, db_path: Path) -> sqlite3.Connection:
        """
        Get a connection for the current thread.

        Args:
            db_path: Path to the database file

        Returns:
            sqlite3.Connection for the current thread
        """
        thread_id = threading.get_ident()
        db_key = str(db_path)

        # Check if we have a connection for this thread/db combo
        if not hasattr(self._local, 'connections'):
            self._local.connections = {}

        if db_key not in self._local.connections:
            # Create new connection for this thread
            conn = sqlite3.connect(
                str(db_path),
                check_same_thread=True,  # Safe because each thread has its own
                timeout=30.0,  # Wait up to 30 seconds for locks
                isolation_level=None  # Autocommit mode, we manage transactions manually
            )
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
            conn.execute("PRAGMA foreign_keys=ON")  # Enforce foreign keys
            self._local.connections[db_key] = conn

            # Track for cleanup
            with self._lock:
                if thread_id not in self._connections:
                    self._connections[thread_id] = {}
                self._connections[thread_id][db_key] = conn

        return self._local.connections[db_key]

    def close_thread_connections(self):
        """Close all connections for the current thread."""
        if hasattr(self._local, 'connections'):
            for conn in self._local.connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._local.connections.clear()

    def close_all_connections(self):
        """Close all connections across all threads."""
        with self._lock:
            for thread_conns in self._connections.values():
                for conn in thread_conns.values():
                    try:
                        conn.close()
                    except Exception:
                        pass
            self._connections.clear()


# Global connection pool
_connection_pool = ThreadSafeConnectionPool()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get a thread-safe database connection.

    Args:
        db_path: Path to database file (defaults to trades.db)

    Returns:
        sqlite3.Connection object (thread-local)
    """
    if db_path is None:
        db_path = TRADES_DB_PATH

    return _connection_pool.get_connection(db_path)


@contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """
    Context manager for database connections with automatic transaction handling.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades")

    Args:
        db_path: Path to database file (defaults to trades.db)

    Yields:
        sqlite3.Connection object
    """
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        raise e


@contextmanager
def get_db_cursor(db_path: Optional[Path] = None):
    """
    Context manager that provides a cursor with automatic cleanup.

    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM trades")
            rows = cursor.fetchall()

    Args:
        db_path: Path to database file

    Yields:
        sqlite3.Cursor object
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()


def backup_table(db_path: Path, table_name: str) -> Optional[str]:
    """
    Create a backup of a table before destructive operations.

    Args:
        db_path: Path to the database
        table_name: Name of the table to backup

    Returns:
        Path to backup file, or None if backup failed
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"{table_name}_{timestamp}.json"

        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # Convert to list of dicts
        columns = [description[0] for description in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]

        with open(backup_file, 'w') as f:
            json.dump({
                'table': table_name,
                'timestamp': timestamp,
                'row_count': len(data),
                'data': data
            }, f, indent=2, default=str)

        print(f"💾 Backed up {len(data)} rows from {table_name} to {backup_file}")
        return str(backup_file)

    except Exception as e:
        print(f"⚠️ Backup failed for {table_name}: {e}")
        return None


def safe_delete(db_path: Path, table_name: str, where_clause: str = "", params: tuple = ()) -> int:
    """
    Safely delete rows with automatic backup.

    Args:
        db_path: Path to the database
        table_name: Name of the table
        where_clause: Optional WHERE clause (without 'WHERE' keyword)
        params: Parameters for the WHERE clause

    Returns:
        Number of rows deleted
    """
    # Create backup first
    backup_file = backup_table(db_path, table_name)
    if backup_file is None:
        raise RuntimeError(f"Cannot delete from {table_name}: backup failed")

    # Perform delete with transaction
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        if where_clause:
            sql = f"DELETE FROM {table_name} WHERE {where_clause}"
            cursor.execute(sql, params)
        else:
            cursor.execute(f"DELETE FROM {table_name}")

        deleted = cursor.rowcount
        print(f"🗑️ Deleted {deleted} rows from {table_name}")
        return deleted


def init_trades_db():
    """
    Initialize trades database with proper schema.

    Creates tables and adds missing columns for backward compatibility.
    """
    conn = get_connection(TRADES_DB_PATH)
    cur = conn.cursor()

    try:
        conn.execute("BEGIN")

        # Create trades table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            last_price REAL NOT NULL,
            vwap REAL,
            pnl REAL DEFAULT 0.0,
            strategy TEXT DEFAULT 'rsi_strategy',
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            side TEXT,
            source TEXT DEFAULT 'simulator',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Check and add missing columns for backward compatibility
        cur.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cur.fetchall()]

        migrations = []

        column_migrations = [
            ('pnl', "ALTER TABLE trades ADD COLUMN pnl REAL DEFAULT 0.0"),
            ('strategy', "ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT 'rsi_strategy'"),
            ('entry_price', "ALTER TABLE trades ADD COLUMN entry_price REAL"),
            ('exit_price', "ALTER TABLE trades ADD COLUMN exit_price REAL"),
            ('quantity', "ALTER TABLE trades ADD COLUMN quantity REAL"),
            ('side', "ALTER TABLE trades ADD COLUMN side TEXT"),
            ('source', "ALTER TABLE trades ADD COLUMN source TEXT DEFAULT 'simulator'"),
            ('created_at', "ALTER TABLE trades ADD COLUMN created_at TEXT DEFAULT ''"),
        ]

        for col_name, sql in column_migrations:
            if col_name not in columns:
                cur.execute(sql)
                migrations.append(col_name)

        # Create indexes for common queries
        indexes = [
            ("idx_trades_timestamp", "trades(timestamp)"),
            ("idx_trades_symbol", "trades(symbol)"),
            ("idx_trades_strategy", "trades(strategy)"),
            ("idx_trades_strategy_timestamp", "trades(strategy, timestamp)"),
            ("idx_trades_symbol_timestamp", "trades(symbol, timestamp)"),
            ("idx_trades_pnl", "trades(pnl)"),
        ]

        for idx_name, idx_columns in indexes:
            cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_columns}")

        conn.execute("COMMIT")

        if migrations:
            print(f"✅ Trades DB migrated: Added columns {migrations}")
        else:
            print("✅ Trades DB initialized")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Failed to initialize trades DB: {e}")
        raise


def init_price_history_db():
    """Initialize price history database for storing tick data."""
    conn = get_connection(PRICE_HISTORY_DB_PATH)
    cur = conn.cursor()

    try:
        conn.execute("BEGIN")

        # Price ticks table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS price_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            volume REAL,
            bid REAL,
            ask REAL,
            source TEXT DEFAULT 'kraken',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # OHLCV candles table for historical data
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL,
            source TEXT DEFAULT 'kraken',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(symbol, timeframe, timestamp)
        )
        """)

        # Indexes for fast lookups
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_ticks_symbol_timestamp
        ON price_ticks(symbol, timestamp)
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_timestamp
        ON ohlcv_candles(symbol, timeframe, timestamp)
        """)

        conn.execute("COMMIT")
        print("✅ Price history DB initialized")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Failed to initialize price history DB: {e}")
        raise


def init_learning_db():
    """Initialize learning database for strategy performance tracking."""
    conn = get_connection(LEARNING_DB_PATH)
    cur = conn.cursor()

    try:
        conn.execute("BEGIN")

        # Strategy performance table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS strategy_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0.0,
            win_rate REAL DEFAULT 0.0,
            profit_factor REAL DEFAULT 0.0,
            sharpe_ratio REAL DEFAULT 0.0,
            max_drawdown REAL DEFAULT 0.0,
            avg_trade_duration REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Strategy selector state table (singleton)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS strategy_selector_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_strategy TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            trades_since_switch INTEGER DEFAULT 0,
            last_switch_timestamp TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Market regime table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS market_regime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            regime TEXT NOT NULL,
            trend_strength REAL,
            volatility REAL,
            momentum REAL,
            symbol TEXT DEFAULT 'BTC',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Strategy recommendations history
        cur.execute("""
        CREATE TABLE IF NOT EXISTS strategy_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            recommended_strategy TEXT NOT NULL,
            previous_strategy TEXT,
            confidence REAL,
            reason TEXT,
            market_regime TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Indexes
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategy_performance_name_timestamp
        ON strategy_performance(strategy_name, timestamp)
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_market_regime_timestamp
        ON market_regime(timestamp)
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategy_recommendations_timestamp
        ON strategy_recommendations(timestamp)
        """)

        conn.execute("COMMIT")
        print("✅ Learning DB initialized")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Failed to initialize learning DB: {e}")
        raise


def init_symbols_db():
    """Initialize symbols database for tracking enabled trading pairs."""
    conn = get_connection(SYMBOLS_DB_PATH)
    cur = conn.cursor()

    try:
        conn.execute("BEGIN")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            coingecko_id TEXT,
            kraken_pair TEXT,
            yahoo_symbol TEXT,
            enabled INTEGER DEFAULT 1,
            asset_type TEXT DEFAULT 'crypto',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Insert default symbols if empty
        cur.execute("SELECT COUNT(*) FROM symbols")
        if cur.fetchone()[0] == 0:
            default_symbols = [
                ('BTC', 'Bitcoin', 'bitcoin', 'XXBTZUSD', None, 1, 'crypto'),
                ('ETH', 'Ethereum', 'ethereum', 'XETHZUSD', None, 1, 'crypto'),
                ('SOL', 'Solana', 'solana', 'SOLUSD', None, 1, 'crypto'),
                ('XRP', 'Ripple', 'ripple', 'XXRPZUSD', None, 1, 'crypto'),
                ('ADA', 'Cardano', 'cardano', 'ADAUSD', None, 1, 'crypto'),
                ('DOGE', 'Dogecoin', 'dogecoin', 'XDGUSD', None, 1, 'crypto'),
                ('AVAX', 'Avalanche', 'avalanche-2', 'AVAXUSD', None, 1, 'crypto'),
                ('DOT', 'Polkadot', 'polkadot', 'DOTUSD', None, 1, 'crypto'),
                ('LINK', 'Chainlink', 'chainlink', 'LINKUSD', None, 1, 'crypto'),
                ('UNI', 'Uniswap', 'uniswap', 'UNIUSD', None, 1, 'crypto'),
                ('ATOM', 'Cosmos', 'cosmos', 'ATOMUSD', None, 1, 'crypto'),
                ('LTC', 'Litecoin', 'litecoin', 'XLTCZUSD', None, 1, 'crypto'),
            ]

            cur.executemany("""
                INSERT INTO symbols (symbol, name, coingecko_id, kraken_pair, yahoo_symbol, enabled, asset_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, default_symbols)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbols_symbol ON symbols(symbol)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbols_enabled ON symbols(enabled)")

        conn.execute("COMMIT")
        print("✅ Symbols DB initialized")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Failed to initialize symbols DB: {e}")
        raise


def init_all_databases():
    """Initialize all JJ-Bot databases."""
    init_trades_db()
    init_price_history_db()
    init_learning_db()
    init_symbols_db()
    print("✅ All databases initialized")


def cleanup_connections():
    """Cleanup all database connections (call on shutdown)."""
    _connection_pool.close_all_connections()
    print("✅ Database connections closed")


# Export commonly used functions and paths
__all__ = [
    # Connection functions
    'get_connection',
    'get_db_connection',
    'get_db_cursor',
    'cleanup_connections',
    # Safety functions
    'backup_table',
    'safe_delete',
    # Init functions
    'init_trades_db',
    'init_price_history_db',
    'init_learning_db',
    'init_symbols_db',
    'init_all_databases',
    # Database paths - SINGLE SOURCE OF TRUTH
    'TRADES_DB_PATH',
    'PRICE_HISTORY_DB_PATH',
    'LEARNING_DB_PATH',
    'SYMBOLS_DB_PATH',
    'MARKET_DATA_CACHE_PATH',
    'DATA_DIR',
    'BACKUP_DIR',
    'PROJECT_ROOT',
]
