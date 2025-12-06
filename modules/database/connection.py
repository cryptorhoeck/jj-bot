"""
Database Connection Module

Provides database connectivity and initialization for all JJ-Bot databases.
Extends the existing database pattern from engine.py.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, List
from contextlib import contextmanager

# Project root path (modules/database -> modules -> project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database paths
TRADES_DB_PATH = DATA_DIR / "trades.db"
PRICE_HISTORY_DB_PATH = DATA_DIR / "price_history.db"
LEARNING_DB_PATH = DATA_DIR / "learning.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get a database connection.

    Args:
        db_path: Path to database file (defaults to trades.db)

    Returns:
        sqlite3.Connection object
    """
    if db_path is None:
        db_path = TRADES_DB_PATH

    return sqlite3.connect(str(db_path), check_same_thread=False)


@contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """
    Context manager for database connections.

    Automatically handles connection cleanup.

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
        yield conn
    finally:
        conn.close()


def init_trades_db():
    """
    Initialize trades database with proper schema.

    Creates tables and adds missing columns for backward compatibility.
    """
    with get_db_connection(TRADES_DB_PATH) as conn:
        cur = conn.cursor()

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
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Check and add missing columns for backward compatibility
        cur.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cur.fetchall()]

        migrations = []

        if 'pnl' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN pnl REAL DEFAULT 0.0")
            migrations.append("pnl")

        if 'strategy' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT 'rsi_strategy'")
            migrations.append("strategy")

        if 'entry_price' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN entry_price REAL")
            migrations.append("entry_price")

        if 'exit_price' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN exit_price REAL")
            migrations.append("exit_price")

        if 'created_at' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN created_at TEXT DEFAULT ''")
            migrations.append("created_at")

        # Create indexes for common queries
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_timestamp
        ON trades(timestamp)
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_symbol
        ON trades(symbol)
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_strategy
        ON trades(strategy)
        """)

        # Composite index for strategy performance queries (strategy + timestamp range)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_strategy_timestamp
        ON trades(strategy, timestamp)
        """)

        conn.commit()

        if migrations:
            print(f"[OK] Trades DB migrated: Added columns {migrations}")
        else:
            print("[OK] Trades DB initialized")


def init_price_history_db():
    """Initialize price history database for storing tick data."""
    with get_db_connection(PRICE_HISTORY_DB_PATH) as conn:
        cur = conn.cursor()

        # Price ticks table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS price_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            volume REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Index for fast lookups
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_ticks_symbol_timestamp
        ON price_ticks(symbol, timestamp)
        """)

        conn.commit()
        print("[OK] Price history DB initialized")


def init_learning_db():
    """Initialize learning database for strategy performance tracking."""
    with get_db_connection(LEARNING_DB_PATH) as conn:
        cur = conn.cursor()

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
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Strategy selector state table
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

        conn.commit()
        print("[OK] Learning DB initialized")


def init_all_databases():
    """Initialize all JJ-Bot databases."""
    init_trades_db()
    init_price_history_db()
    init_learning_db()
    print("[OK] All databases initialized")


# Export commonly used functions
__all__ = [
    'get_connection',
    'get_db_connection',
    'init_trades_db',
    'init_price_history_db',
    'init_learning_db',
    'init_all_databases',
    'TRADES_DB_PATH',
    'PRICE_HISTORY_DB_PATH',
    'LEARNING_DB_PATH'
]
