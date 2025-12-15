"""
Centralized Data Manager for JJ-Bot

This is the SINGLE SOURCE OF TRUTH for all bot data.
All components should use this module instead of direct file/db access.

Tables:
- trades: Complete trade history
- training_episodes: Training metrics per episode
- equity_snapshots: Equity curve data points
- bot_state: Runtime state (single row)
- model_versions: Trained model tracking
- open_positions: Current open positions
"""

import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading
import uuid

# Project root - this file is at modules/database/data_manager.py
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Single database for all data
DB_PATH = DATA_DIR / "jjbot.db"

# Thread-local storage for connections
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Get thread-local database connection"""
    if not hasattr(_local, 'connection') or _local.connection is None:
        _local.connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
        # Enable foreign keys and WAL mode for better concurrency
        _local.connection.execute("PRAGMA foreign_keys = ON")
        _local.connection.execute("PRAGMA journal_mode = WAL")
    return _local.connection


@contextmanager
def get_db():
    """Context manager for database operations with auto-commit"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e


def init_database():
    """Initialize database with all required tables"""
    with get_db() as conn:
        cur = conn.cursor()

        # 1. Trades table - complete trade history
        cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            size REAL NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            pnl REAL DEFAULT 0.0,
            pnl_pct REAL DEFAULT 0.0,
            fees REAL DEFAULT 0.0,
            slippage REAL DEFAULT 0.0,
            signal_source TEXT,
            exit_reason TEXT,
            model_version TEXT,
            strategy TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # 2. Training episodes table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS training_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            episode INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            symbol TEXT,
            total_reward REAL DEFAULT 0.0,
            avg_reward REAL DEFAULT 0.0,
            total_pnl REAL DEFAULT 0.0,
            trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            profit_factor REAL DEFAULT 0.0,
            max_drawdown REAL DEFAULT 0.0,
            sharpe_ratio REAL,
            policy_loss REAL,
            value_loss REAL,
            entropy REAL,
            learning_rate REAL,
            steps INTEGER DEFAULT 0,
            duration_seconds REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # 3. Equity snapshots table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS equity_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            equity REAL NOT NULL,
            cash REAL,
            positions_value REAL,
            daily_pnl REAL DEFAULT 0.0,
            total_pnl REAL DEFAULT 0.0,
            drawdown REAL DEFAULT 0.0,
            drawdown_pct REAL DEFAULT 0.0,
            peak_equity REAL,
            open_positions INTEGER DEFAULT 0,
            mode TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # 4. Bot state table (single row)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            equity REAL DEFAULT 0.0,
            peak_equity REAL DEFAULT 0.0,
            daily_pnl REAL DEFAULT 0.0,
            daily_start_equity REAL DEFAULT 0.0,
            total_pnl REAL DEFAULT 0.0,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            trading_iq INTEGER DEFAULT 0,
            expertise_level TEXT DEFAULT 'Untrained',
            training_sessions INTEGER DEFAULT 0,
            total_training_episodes INTEGER DEFAULT 0,
            total_training_trades INTEGER DEFAULT 0,
            last_training_date TEXT,
            current_model_version TEXT,
            avg_win_rate REAL DEFAULT 0.0,
            avg_profit_factor REAL DEFAULT 0.0,
            best_win_rate REAL DEFAULT 0.0,
            best_profit_factor REAL DEFAULT 0.0,
            mode TEXT DEFAULT 'paper',
            last_updated TEXT
        )
        """)

        # 5. Model versions table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS model_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            file_path TEXT,
            training_episodes INTEGER,
            training_session_id TEXT,
            final_iq INTEGER,
            final_win_rate REAL,
            final_profit_factor REAL,
            final_sharpe REAL,
            notes TEXT,
            is_active INTEGER DEFAULT 0
        )
        """)

        # 6. Open positions table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS open_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            side TEXT NOT NULL,
            size REAL NOT NULL,
            entry_price REAL NOT NULL,
            entry_time TEXT NOT NULL,
            current_price REAL,
            unrealized_pnl REAL DEFAULT 0.0,
            unrealized_pnl_pct REAL DEFAULT 0.0,
            stop_loss REAL,
            take_profit REAL,
            trailing_stop REAL,
            signal_source TEXT,
            model_version TEXT,
            last_updated TEXT
        )
        """)

        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_signal_source ON trades(signal_source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_training_episodes_session ON training_episodes(session_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_training_episodes_episode ON training_episodes(episode)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_equity_snapshots_timestamp ON equity_snapshots(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_equity_snapshots_mode ON equity_snapshots(mode)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(is_active)")

        # Insert default bot_state row if not exists
        cur.execute("SELECT COUNT(*) FROM bot_state")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO bot_state (id, equity, peak_equity, daily_start_equity, expertise_level, mode, last_updated)
                VALUES (1, 0.0, 0.0, 0.0, 'Untrained', 'paper', datetime('now'))
            """)

        print(f"[OK] Database initialized: {DB_PATH}")


# ============================================================================
# BOT STATE OPERATIONS
# ============================================================================

def get_bot_state() -> Dict[str, Any]:
    """Get current bot state"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bot_state WHERE id = 1")
        row = cur.fetchone()
        if row:
            return dict(row)
        return {}


def update_bot_state(**kwargs) -> None:
    """Update bot state fields"""
    if not kwargs:
        return

    kwargs['last_updated'] = datetime.now().isoformat()

    with get_db() as conn:
        cur = conn.cursor()
        # Build SET clause
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())

        cur.execute(f"UPDATE bot_state SET {set_clause} WHERE id = 1", values)

        # If no rows updated, insert
        if cur.rowcount == 0:
            columns = ", ".join(["id"] + list(kwargs.keys()))
            placeholders = ", ".join(["1"] + ["?" for _ in kwargs])
            cur.execute(f"INSERT INTO bot_state ({columns}) VALUES ({placeholders})", values)


def reset_bot_state(initial_equity: float = 0.0) -> None:
    """Reset bot state to defaults"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM bot_state")
        cur.execute("""
            INSERT INTO bot_state (id, equity, peak_equity, daily_start_equity, expertise_level, mode, last_updated)
            VALUES (1, ?, ?, ?, 'Untrained', 'paper', datetime('now'))
        """, (initial_equity, initial_equity, initial_equity))


# ============================================================================
# TRADE OPERATIONS
# ============================================================================

def record_trade(
    symbol: str,
    side: str,
    size: float,
    entry_price: float,
    exit_price: float,
    entry_time: str,
    exit_time: str,
    pnl: float = 0.0,
    pnl_pct: float = 0.0,
    fees: float = 0.0,
    slippage: float = 0.0,
    signal_source: str = None,
    exit_reason: str = None,
    model_version: str = None,
    strategy: str = None,
    notes: str = None
) -> int:
    """Record a completed trade"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trades (
                symbol, side, size, entry_price, exit_price, entry_time, exit_time,
                pnl, pnl_pct, fees, slippage, signal_source, exit_reason,
                model_version, strategy, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, side, size, entry_price, exit_price, entry_time, exit_time,
            pnl, pnl_pct, fees, slippage, signal_source, exit_reason,
            model_version, strategy, notes
        ))

        trade_id = cur.lastrowid

        # Update bot state stats
        cur.execute("SELECT total_trades, winning_trades, losing_trades, total_pnl FROM bot_state WHERE id = 1")
        state = cur.fetchone()
        if state:
            new_total = state[0] + 1
            new_wins = state[1] + (1 if pnl > 0 else 0)
            new_losses = state[2] + (1 if pnl < 0 else 0)
            new_pnl = state[3] + pnl
            cur.execute("""
                UPDATE bot_state SET
                    total_trades = ?,
                    winning_trades = ?,
                    losing_trades = ?,
                    total_pnl = ?,
                    last_updated = datetime('now')
                WHERE id = 1
            """, (new_total, new_wins, new_losses, new_pnl))

        return trade_id


def get_trades(
    symbol: str = None,
    limit: int = 100,
    offset: int = 0,
    since: str = None,
    until: str = None,
    signal_source: str = None
) -> List[Dict[str, Any]]:
    """Get trade history with optional filters"""
    with get_db() as conn:
        cur = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if since:
            query += " AND exit_time >= ?"
            params.append(since)
        if until:
            query += " AND exit_time <= ?"
            params.append(until)
        if signal_source:
            query += " AND signal_source = ?"
            params.append(signal_source)

        query += " ORDER BY exit_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_trade_stats(since: str = None) -> Dict[str, Any]:
    """Get aggregated trade statistics"""
    with get_db() as conn:
        cur = conn.cursor()

        where_clause = ""
        params = []
        if since:
            where_clause = "WHERE exit_time >= ?"
            params.append(since)

        cur.execute(f"""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade,
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)) as gross_loss
            FROM trades
            {where_clause}
        """, params)

        row = cur.fetchone()
        if not row or row[0] == 0:
            return {
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                'total_pnl': 0, 'avg_pnl': 0, 'best_trade': 0, 'worst_trade': 0,
                'win_rate': 0, 'profit_factor': 0
            }

        stats = dict(row)
        stats['win_rate'] = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
        stats['profit_factor'] = (stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] > 0 else 0

        return stats


def clear_trades() -> int:
    """Clear all trades, return count deleted"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM trades")
        return count


# ============================================================================
# TRAINING EPISODE OPERATIONS
# ============================================================================

def start_training_session() -> str:
    """Start a new training session, return session ID"""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    return session_id


def record_training_episode(
    session_id: str,
    episode: int,
    symbol: str = None,
    total_reward: float = 0.0,
    avg_reward: float = 0.0,
    total_pnl: float = 0.0,
    trades: int = 0,
    wins: int = 0,
    losses: int = 0,
    win_rate: float = 0.0,
    profit_factor: float = 0.0,
    max_drawdown: float = 0.0,
    sharpe_ratio: float = None,
    policy_loss: float = None,
    value_loss: float = None,
    entropy: float = None,
    learning_rate: float = None,
    steps: int = 0,
    duration_seconds: float = None
) -> int:
    """Record metrics for a training episode"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO training_episodes (
                session_id, episode, timestamp, symbol,
                total_reward, avg_reward, total_pnl, trades, wins, losses,
                win_rate, profit_factor, max_drawdown, sharpe_ratio,
                policy_loss, value_loss, entropy, learning_rate, steps, duration_seconds
            ) VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, episode, symbol,
            total_reward, avg_reward, total_pnl, trades, wins, losses,
            win_rate, profit_factor, max_drawdown, sharpe_ratio,
            policy_loss, value_loss, entropy, learning_rate, steps, duration_seconds
        ))
        return cur.lastrowid


def get_training_episodes(
    session_id: str = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get training episodes, optionally filtered by session"""
    with get_db() as conn:
        cur = conn.cursor()

        if session_id:
            cur.execute("""
                SELECT * FROM training_episodes
                WHERE session_id = ?
                ORDER BY episode ASC
                LIMIT ? OFFSET ?
            """, (session_id, limit, offset))
        else:
            cur.execute("""
                SELECT * FROM training_episodes
                ORDER BY created_at DESC, episode ASC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        return [dict(row) for row in cur.fetchall()]


def get_training_sessions() -> List[Dict[str, Any]]:
    """Get summary of all training sessions"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                session_id,
                MIN(timestamp) as started_at,
                MAX(timestamp) as ended_at,
                COUNT(*) as episodes,
                MAX(episode) as max_episode,
                AVG(win_rate) as avg_win_rate,
                AVG(profit_factor) as avg_profit_factor,
                SUM(total_pnl) as total_pnl,
                AVG(total_reward) as avg_reward
            FROM training_episodes
            GROUP BY session_id
            ORDER BY started_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]


def get_latest_training_metrics() -> Dict[str, Any]:
    """Get the most recent training session's final metrics"""
    with get_db() as conn:
        cur = conn.cursor()
        # Get latest session
        cur.execute("""
            SELECT session_id FROM training_episodes
            ORDER BY created_at DESC LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return {}

        session_id = row[0]

        # Get final episode of that session
        cur.execute("""
            SELECT * FROM training_episodes
            WHERE session_id = ?
            ORDER BY episode DESC LIMIT 1
        """, (session_id,))

        row = cur.fetchone()
        if row:
            return dict(row)
        return {}


def clear_training_episodes() -> int:
    """Clear all training episodes, return count deleted"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM training_episodes")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM training_episodes")
        return count


# ============================================================================
# EQUITY SNAPSHOT OPERATIONS
# ============================================================================

def record_equity_snapshot(
    equity: float,
    cash: float = None,
    positions_value: float = None,
    daily_pnl: float = 0.0,
    total_pnl: float = 0.0,
    drawdown: float = 0.0,
    drawdown_pct: float = 0.0,
    peak_equity: float = None,
    open_positions: int = 0,
    mode: str = None
) -> int:
    """Record an equity snapshot for equity curve"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO equity_snapshots (
                timestamp, equity, cash, positions_value, daily_pnl, total_pnl,
                drawdown, drawdown_pct, peak_equity, open_positions, mode
            ) VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            equity, cash, positions_value, daily_pnl, total_pnl,
            drawdown, drawdown_pct, peak_equity, open_positions, mode
        ))
        return cur.lastrowid


def get_equity_curve(
    since: str = None,
    until: str = None,
    mode: str = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Get equity curve data points"""
    with get_db() as conn:
        cur = conn.cursor()

        query = "SELECT * FROM equity_snapshots WHERE 1=1"
        params = []

        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        if until:
            query += " AND timestamp <= ?"
            params.append(until)
        if mode:
            query += " AND mode = ?"
            params.append(mode)

        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def clear_equity_snapshots() -> int:
    """Clear all equity snapshots, return count deleted"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM equity_snapshots")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM equity_snapshots")
        return count


# ============================================================================
# POSITION OPERATIONS
# ============================================================================

def save_position(
    symbol: str,
    side: str,
    size: float,
    entry_price: float,
    entry_time: str,
    current_price: float = None,
    unrealized_pnl: float = 0.0,
    unrealized_pnl_pct: float = 0.0,
    stop_loss: float = None,
    take_profit: float = None,
    trailing_stop: float = None,
    signal_source: str = None,
    model_version: str = None
) -> None:
    """Save or update an open position"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO open_positions (
                symbol, side, size, entry_price, entry_time, current_price,
                unrealized_pnl, unrealized_pnl_pct, stop_loss, take_profit,
                trailing_stop, signal_source, model_version, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            symbol, side, size, entry_price, entry_time, current_price,
            unrealized_pnl, unrealized_pnl_pct, stop_loss, take_profit,
            trailing_stop, signal_source, model_version
        ))


def get_positions() -> List[Dict[str, Any]]:
    """Get all open positions"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM open_positions ORDER BY entry_time DESC")
        return [dict(row) for row in cur.fetchall()]


def get_position(symbol: str) -> Optional[Dict[str, Any]]:
    """Get a specific position by symbol"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM open_positions WHERE symbol = ?", (symbol,))
        row = cur.fetchone()
        return dict(row) if row else None


def remove_position(symbol: str) -> bool:
    """Remove a position (when closed)"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM open_positions WHERE symbol = ?", (symbol,))
        return cur.rowcount > 0


def clear_positions() -> int:
    """Clear all positions, return count deleted"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM open_positions")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM open_positions")
        return count


# ============================================================================
# MODEL VERSION OPERATIONS
# ============================================================================

def register_model_version(
    version: str,
    file_path: str,
    training_episodes: int = None,
    training_session_id: str = None,
    final_iq: int = None,
    final_win_rate: float = None,
    final_profit_factor: float = None,
    final_sharpe: float = None,
    notes: str = None,
    is_active: bool = True
) -> int:
    """Register a new model version"""
    with get_db() as conn:
        cur = conn.cursor()

        # Deactivate all other models if this one is active
        if is_active:
            cur.execute("UPDATE model_versions SET is_active = 0")

        cur.execute("""
            INSERT INTO model_versions (
                version, created_at, file_path, training_episodes, training_session_id,
                final_iq, final_win_rate, final_profit_factor, final_sharpe, notes, is_active
            ) VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            version, file_path, training_episodes, training_session_id,
            final_iq, final_win_rate, final_profit_factor, final_sharpe, notes, 1 if is_active else 0
        ))

        # Update bot_state with current model
        if is_active:
            cur.execute("UPDATE bot_state SET current_model_version = ? WHERE id = 1", (version,))

        return cur.lastrowid


def get_active_model_version() -> Optional[Dict[str, Any]]:
    """Get the currently active model version"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM model_versions WHERE is_active = 1 LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None


def get_model_versions(limit: int = 20) -> List[Dict[str, Any]]:
    """Get all model versions"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM model_versions ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]


def clear_model_versions() -> int:
    """Clear all model version records, return count deleted"""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM model_versions")
        count = cur.fetchone()[0]
        cur.execute("DELETE FROM model_versions")
        return count


# ============================================================================
# RESET OPERATIONS
# ============================================================================

def reset_all_data(initial_equity: float = 0.0) -> Dict[str, int]:
    """
    Reset ALL data - complete fresh start.
    Returns count of deleted records per table.
    """
    counts = {}

    with get_db() as conn:
        cur = conn.cursor()

        # Clear all tables
        for table in ['trades', 'training_episodes', 'equity_snapshots', 'open_positions', 'model_versions']:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {table}")

        # Reset bot_state
        cur.execute("DELETE FROM bot_state")
        cur.execute("""
            INSERT INTO bot_state (id, equity, peak_equity, daily_start_equity, expertise_level, mode, last_updated)
            VALUES (1, ?, ?, ?, 'Untrained', 'paper', datetime('now'))
        """, (initial_equity, initial_equity, initial_equity))
        counts['bot_state'] = 1

    return counts


def reset_trading_data(initial_equity: float = 0.0) -> Dict[str, int]:
    """
    Reset trading data only - keeps training history and IQ.
    Returns count of deleted records per table.
    """
    counts = {}

    with get_db() as conn:
        cur = conn.cursor()

        # Clear trading tables only
        for table in ['trades', 'equity_snapshots', 'open_positions']:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {table}")

        # Reset equity but keep IQ and training history
        cur.execute("""
            UPDATE bot_state SET
                equity = ?,
                peak_equity = ?,
                daily_pnl = 0.0,
                daily_start_equity = ?,
                total_pnl = 0.0,
                total_trades = 0,
                winning_trades = 0,
                losing_trades = 0,
                last_updated = datetime('now')
            WHERE id = 1
        """, (initial_equity, initial_equity, initial_equity))

    return counts


def reset_training_data() -> Dict[str, int]:
    """
    Reset training data only - keeps trade history.
    Returns count of deleted records per table.
    """
    counts = {}

    with get_db() as conn:
        cur = conn.cursor()

        # Clear training tables
        for table in ['training_episodes', 'model_versions']:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {table}")

        # Reset training-related fields in bot_state
        cur.execute("""
            UPDATE bot_state SET
                trading_iq = 0,
                expertise_level = 'Untrained',
                training_sessions = 0,
                total_training_episodes = 0,
                total_training_trades = 0,
                last_training_date = NULL,
                current_model_version = NULL,
                avg_win_rate = 0.0,
                avg_profit_factor = 0.0,
                best_win_rate = 0.0,
                best_profit_factor = 0.0,
                last_updated = datetime('now')
            WHERE id = 1
        """)

    return counts


# ============================================================================
# MIGRATION HELPERS
# ============================================================================

def migrate_from_json(json_path: str) -> Dict[str, int]:
    """
    Migrate data from old bot_state.json format to SQLite.
    Returns count of migrated records.
    """
    counts = {'trades': 0, 'state': 0}

    if not os.path.exists(json_path):
        return counts

    try:
        with open(json_path) as f:
            data = json.load(f)

        with get_db() as conn:
            cur = conn.cursor()

            # Migrate bot state
            if 'stats' in data:
                stats = data['stats']
                cur.execute("""
                    UPDATE bot_state SET
                        equity = ?,
                        peak_equity = ?,
                        daily_pnl = ?,
                        daily_start_equity = ?,
                        total_trades = ?,
                        winning_trades = ?,
                        total_pnl = ?,
                        trading_iq = ?,
                        expertise_level = ?,
                        training_sessions = ?,
                        total_training_episodes = ?,
                        total_training_trades = ?,
                        last_training_date = ?,
                        avg_win_rate = ?,
                        avg_profit_factor = ?,
                        last_updated = datetime('now')
                    WHERE id = 1
                """, (
                    data.get('equity', 0),
                    data.get('peak_equity', 0),
                    data.get('daily_pnl', 0),
                    data.get('daily_start_equity', 0),
                    stats.get('total_trades', 0),
                    stats.get('winning_trades', 0),
                    stats.get('total_pnl', 0),
                    stats.get('trading_iq', 0),
                    stats.get('expertise_level', 'Untrained'),
                    stats.get('training_sessions', 0),
                    stats.get('total_training_episodes', 0),
                    stats.get('total_training_trades', 0),
                    stats.get('last_training_date'),
                    stats.get('avg_win_rate', 0),
                    stats.get('avg_profit_factor', 0)
                ))
                counts['state'] = 1

            # Migrate trade history
            if 'trade_history' in data:
                for trade in data['trade_history']:
                    cur.execute("""
                        INSERT INTO trades (
                            symbol, side, size, entry_price, exit_price,
                            entry_time, exit_time, pnl, pnl_pct, signal_source, exit_reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.get('symbol'),
                        trade.get('side'),
                        trade.get('size', 0),
                        trade.get('entry_price', 0),
                        trade.get('exit_price', 0),
                        trade.get('entry_time'),
                        trade.get('exit_time'),
                        trade.get('pnl', 0),
                        trade.get('pnl_pct', 0),
                        trade.get('signal_source'),
                        trade.get('exit_reason')
                    ))
                    counts['trades'] += 1

        print(f"[OK] Migrated from JSON: {counts}")
        return counts

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return counts


# Initialize database on module load
init_database()
