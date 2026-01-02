import sqlite3
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import datetime

# Use project-relative database path (cross-platform compatible)
# Path: glue/api/engine.py -> glue/api -> glue -> project root
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
DB_PATH: Path = PROJECT_ROOT / "data" / "trades.db"
STATE_PATH: Path = PROJECT_ROOT / "data" / "bot_state.json"
CONFIG_PATH: Path = PROJECT_ROOT / "config" / "bot_config.json"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_saved_state() -> Optional[Dict[str, Any]]:
    """Load saved bot state from bot_state.json"""
    try:
        if STATE_PATH.exists():
            with open(STATE_PATH, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def get_config() -> Optional[Dict[str, Any]]:
    """Load bot config from bot_config.json"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

@contextmanager
def get_connection() -> sqlite3.Connection:
    """
    Get a database connection with context manager support

    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    """Initialize database with proper schema including PnL column"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            signal TEXT,
            last_price REAL,
            vwap REAL,
            pnl REAL DEFAULT 0.0,
            strategy TEXT DEFAULT 'unknown'
        )
        """)

        # Check if columns exist, add them if not
        cur.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cur.fetchall()]
        if 'pnl' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN pnl REAL DEFAULT 0.0")
        if 'strategy' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT 'unknown'")

        conn.commit()
    print("[GORILLA] Database initialized for JJ Gorilla")

def log_trade(trade: Dict[str, Any]) -> None:
    """
    Log a trade to the database

    Args:
        trade: Dictionary containing trade data with keys:
               timestamp, symbol, signal, last_price, vwap, pnl, strategy
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO trades (timestamp, symbol, signal, last_price, vwap, pnl, strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            trade["timestamp"],
            trade["symbol"],
            trade["signal"],
            trade["last_price"],
            trade["vwap"],
            trade.get("pnl", 0.0),
            trade.get("strategy", "unknown")
        ))
        conn.commit()

def get_trades(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent trades from database

    Args:
        limit: Maximum number of trades to return

    Returns:
        List of trade dictionaries
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT timestamp, symbol, signal, last_price, vwap, pnl, strategy
        FROM trades
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        return [
            {
                "timestamp": row[0],
                "symbol": row[1],
                "signal": row[2],
                "last_price": row[3],
                "vwap": row[4],
                "pnl": row[5],
                "strategy": row[6] if len(row) > 6 else "unknown"
            }
            for row in rows
        ]

def get_summary() -> Dict[str, Any]:
    """
    Get comprehensive trading summary statistics with real-time position tracking

    Returns:
        Dictionary containing summary statistics including:
        total_trades, total_pnl, avg_pnl, winning_trades, win_rate,
        open_positions, current_equity, max_drawdown, profit_factor
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # Total trades
        cur.execute("SELECT COUNT(*) FROM trades")
        total_trades = cur.fetchone()[0]

        # Total PnL
        cur.execute("SELECT SUM(pnl) FROM trades WHERE pnl IS NOT NULL")
        total_pnl = cur.fetchone()[0] or 0.0

        # Average PnL per trade
        cur.execute("SELECT AVG(pnl) FROM trades WHERE pnl IS NOT NULL")
        avg_pnl = cur.fetchone()[0] or 0.0

        # Winning trades
        cur.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
        winning_trades = cur.fetchone()[0]

        # Losing trades
        cur.execute("SELECT COUNT(*) FROM trades WHERE pnl < 0")
        losing_trades = cur.fetchone()[0]

        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Average win
        cur.execute("SELECT AVG(pnl) FROM trades WHERE pnl > 0")
        avg_win = cur.fetchone()[0] or 0.0

        # Average loss
        cur.execute("SELECT AVG(pnl) FROM trades WHERE pnl < 0")
        avg_loss = cur.fetchone()[0] or 0.0

        # Profit factor (total wins / abs(total losses))
        cur.execute("SELECT SUM(pnl) FROM trades WHERE pnl > 0")
        total_wins = cur.fetchone()[0] or 0.0
        cur.execute("SELECT SUM(pnl) FROM trades WHERE pnl < 0")
        total_losses = abs(cur.fetchone()[0] or 0.0)
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0

        # Max drawdown calculation (cumulative PnL approach)
        cur.execute("SELECT pnl FROM trades ORDER BY id ASC")
        pnls = [row[0] for row in cur.fetchall() if row[0] is not None]

        max_drawdown = 0.0
        if pnls:
            cumulative = []
            total = 0
            for pnl in pnls:
                total += pnl
                cumulative.append(total)

            peak = cumulative[0]
            for value in cumulative:
                if value > peak:
                    peak = value
                dd = peak - value
                if dd > max_drawdown:
                    max_drawdown = dd

        # Get open positions (trades without matching exit)
        # This assumes trades come in pairs: entry (BUY) and exit (SELL) for each symbol
        cur.execute("""
            SELECT symbol, COUNT(*) as trade_count, SUM(pnl) as position_pnl
            FROM trades
            WHERE signal IN ('BUY', 'SELL')
            GROUP BY symbol
            HAVING trade_count % 2 = 1
        """)
        open_positions_rows = cur.fetchall()
        open_positions = {
            row[0]: {
                "symbol": row[0],
                "trades": row[1],
                "unrealized_pnl": row[2] or 0.0
            }
            for row in open_positions_rows
        }

        # Get initial_capital from config
        config = get_config()
        starting_capital = 10000.0  # fallback default
        if config:
            starting_capital = config.get("initial_capital", 10000.0)

        # Try to get equity from centralized database first (source of truth)
        saved_state = None  # Initialize for later use
        try:
            from modules.database import data_manager
            bot_state = data_manager.get_bot_state()
            if bot_state and bot_state.get("equity", 0) > 0:
                current_equity = bot_state["equity"]
            else:
                # No database state - use config's initial_capital + PnL
                current_equity = starting_capital + total_pnl
        except Exception:
            # Fallback to JSON state if database unavailable
            saved_state = get_saved_state()
            if saved_state and "equity" in saved_state:
                current_equity = saved_state["equity"]
            else:
                current_equity = starting_capital + total_pnl

        # Load saved state for IQ/training stats if not already loaded
        if saved_state is None:
            saved_state = get_saved_state()

        # Get latest trade timestamp
        cur.execute("SELECT MAX(timestamp) FROM trades")
        latest_trade = cur.fetchone()[0]

        # Calculate return percentage from equity vs starting capital
        return_pct = round(((current_equity - starting_capital) / starting_capital * 100), 2) if starting_capital > 0 else 0.0

        result = {
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_drawdown, 2),
            "open_positions": open_positions,
            "open_positions_count": len(open_positions),
            "starting_capital": starting_capital,
            "current_equity": round(current_equity, 2),
            "return_pct": return_pct,
            "latest_trade": latest_trade
        }

        # Include IQ and training stats from saved state if available
        if saved_state:
            if "trading_iq" in saved_state:
                result["trading_iq"] = saved_state["trading_iq"]
            if "expertise_level" in saved_state:
                result["expertise_level"] = saved_state["expertise_level"]
            if "training_history" in saved_state:
                result["training_history"] = saved_state["training_history"]

        return result

def clear_all_trades() -> None:
    """Clear all trades from database"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM trades")
        conn.commit()

def clear_trades() -> None:
    """Clear all trades from the database"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM trades")
        conn.commit()
        return True

def get_equity_curve(starting_capital: float = 10000.0) -> List[Dict[str, Any]]:
    """
    Calculate equity curve over time

    Args:
        starting_capital: Initial capital amount

    Returns:
        List of equity points with timestamp and equity value
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, pnl
            FROM trades
            WHERE pnl IS NOT NULL
            ORDER BY timestamp ASC
        """)

        rows = cur.fetchall()
        equity_curve = []
        current_equity = starting_capital

        for row in rows:
            current_equity += row[1]  # Add PnL
            equity_curve.append({
                "timestamp": row[0],
                "equity": round(current_equity, 2),
                "pnl": round(row[1], 2)
            })

        return equity_curve

def get_open_positions() -> List[Dict[str, Any]]:
    """
    Get detailed information about currently open positions

    Returns:
        List of open position details
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # Get all trades and track which positions are open
        cur.execute("""
            SELECT id, timestamp, symbol, signal, last_price, entry_price, pnl, created_at
            FROM trades
            ORDER BY timestamp ASC
        """)

        all_trades = cur.fetchall()

        # Track positions per symbol
        positions = {}

        for trade in all_trades:
            trade_id, timestamp, symbol, signal, last_price, entry_price, pnl, created_at = trade

            if symbol not in positions:
                positions[symbol] = {
                    "symbol": symbol,
                    "entry_time": timestamp,
                    "entry_price": entry_price or last_price,
                    "current_price": last_price,
                    "unrealized_pnl": pnl or 0.0,
                    "trade_count": 0,
                    "is_open": False,
                    "created_at": created_at
                }

            positions[symbol]["trade_count"] += 1
            positions[symbol]["current_price"] = last_price

            # Simple logic: odd number of trades means position is open
            positions[symbol]["is_open"] = (positions[symbol]["trade_count"] % 2 == 1)

        # Return only open positions
        open_positions = [
            {
                **pos,
                "unrealized_pnl": round(pos["unrealized_pnl"], 2),
                "entry_price": round(pos["entry_price"], 2),
                "current_price": round(pos["current_price"], 2),
                "pnl_pct": round(
                    ((pos["current_price"] - pos["entry_price"]) / pos["entry_price"] * 100), 2
                ) if pos["entry_price"] > 0 else 0.0
            }
            for pos in positions.values()
            if pos["is_open"]
        ]

        return open_positions
