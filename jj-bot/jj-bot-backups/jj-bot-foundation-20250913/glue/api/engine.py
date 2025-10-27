import sqlite3
import os
from pathlib import Path
from typing import Dict, List
import datetime

# Use consistent database path
DB_PATH = Path.home() / "jj-bot" / "data" / "trades.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection():
    """Get a new database connection for each operation"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
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
            pnl REAL DEFAULT 0.0
        )
        """)
        
        # Check if pnl column exists, add it if not
        cur.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cur.fetchall()]
        if 'pnl' not in columns:
            cur.execute("ALTER TABLE trades ADD COLUMN pnl REAL DEFAULT 0.0")
        
        conn.commit()
    print("🦍 Database initialized for JJ Gorilla")

def log_trade(trade):
    """Log a trade to the database"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO trades (timestamp, symbol, signal, last_price, vwap, pnl) 
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trade["timestamp"], 
            trade["symbol"], 
            trade["signal"], 
            trade["last_price"], 
            trade["vwap"], 
            trade.get("pnl", 0.0)
        ))
        conn.commit()

def get_trades(limit=50):
    """Get recent trades from database"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT timestamp, symbol, signal, last_price, vwap, pnl 
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
                "pnl": row[5]
            }
            for row in rows
        ]

def get_summary():
    """Get trading summary statistics"""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Total trades
        cur.execute("SELECT COUNT(*) FROM trades")
        total_trades = cur.fetchone()[0]
        
        # Total PnL
        cur.execute("SELECT SUM(pnl) FROM trades")
        total_pnl = cur.fetchone()[0] or 0.0
        
        # Winning trades
        cur.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
        winning_trades = cur.fetchone()[0]
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "winning_trades": winning_trades,
            "win_rate": win_rate
        }

def clear_all_trades():
    """Clear all trades from database"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM trades")
        conn.commit()
