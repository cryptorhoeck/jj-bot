"""
Standalone Trade Simulator
Generates simulated trades and publishes them to the event bus
"""

import sys
import os
import time
import random
import sqlite3
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from modules.event_bus import event_bus

# Database paths
DB_PATH = os.path.join(project_root, "data", "trades.db")
SYMBOLS_DB_PATH = os.path.join(project_root, "data", "symbols.db")

# Default base prices (will be updated from market data)
BASE_PRICES = {
    'BTC': 45000, 'ETH': 2500, 'SOL': 100, 'BNB': 350, 'ADA': 0.50,
    'DOT': 7, 'LINK': 15, 'MATIC': 0.80, 'UNI': 6, 'AVAX': 35,
    'XRP': 0.65, 'DOGE': 0.08, 'AVAX': 35, 'TRX': 0.10, 'ATOM': 10,
    'LTC': 70, 'BCH': 250, 'UNI': 6, 'XLM': 0.12, 'ETC': 20,
    'WBTC': 45000, 'SHIB': 0.00001
}

def get_enabled_symbols():
    """Get enabled symbols from the symbols database"""
    try:
        if not os.path.exists(SYMBOLS_DB_PATH):
            print("⚠️ Symbols database not found, using defaults")
            return ['BTC', 'ETH', 'SOL']

        conn = sqlite3.connect(SYMBOLS_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT symbol FROM symbols WHERE enabled = 1 ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]

        conn.close()

        if not symbols:
            print("⚠️ No enabled symbols found, using defaults")
            return ['BTC', 'ETH', 'SOL']

        print(f"✅ Loaded {len(symbols)} enabled symbols from database")
        return symbols
    except Exception as e:
        print(f"⚠️ Error loading symbols from database: {e}")
        return ['BTC', 'ETH', 'SOL']

def init_database():
    """Initialize the trades database"""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create trades table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            last_price REAL NOT NULL,
            vwap REAL NOT NULL,
            pnl REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized")

def generate_trade(symbols):
    """Generate a single simulated trade"""
    # Random symbol from enabled symbols
    symbol = random.choice(symbols)
    base_price = BASE_PRICES.get(symbol, 100)  # Default to 100 if not in BASE_PRICES

    # Random price variation (±5%)
    last_price = base_price * (1 + random.uniform(-0.05, 0.05))
    vwap = last_price * (1 + random.uniform(-0.02, 0.02))

    # Random signal (70% BUY, 30% SELL for more activity)
    signal = random.choice(['BUY', 'BUY', 'BUY', 'SELL'])

    # Random P&L (-50 to +100, skewed positive)
    pnl = random.uniform(-50, 100)

    # Current timestamp
    timestamp = datetime.now().isoformat()

    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "signal": signal,
        "last_price": last_price,
        "vwap": vwap,
        "pnl": pnl
    }

def save_trade(trade):
    """Save trade to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (timestamp, symbol, signal, last_price, vwap, pnl)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (trade["timestamp"], trade["symbol"], trade["signal"],
              trade["last_price"], trade["vwap"], trade["pnl"]))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Failed to save trade: {e}")
        return False

def publish_trade(trade):
    """Publish trade to event bus"""
    try:
        event_bus.publish("TRADE_EXECUTED", trade)
        return True
    except Exception as e:
        print(f"⚠️ Failed to publish trade: {e}")
        return False

def run_simulator():
    """Main simulator loop"""
    print("🦍 JJ Gorilla Trading Bot starting...")
    print("⏰ Trade interval: 10-30 seconds")
    print()

    # Initialize database
    init_database()

    # Load enabled symbols from database
    symbols = get_enabled_symbols()
    print(f"📊 Trading symbols: {', '.join(symbols)}")
    print()

    trade_count = 0
    last_symbol_refresh = time.time()
    SYMBOL_REFRESH_INTERVAL = 60  # Refresh symbols every 60 seconds

    try:
        while True:
            # Refresh symbols periodically
            if time.time() - last_symbol_refresh > SYMBOL_REFRESH_INTERVAL:
                new_symbols = get_enabled_symbols()
                if new_symbols != symbols:
                    symbols = new_symbols
                    print(f"\n🔄 Symbols updated: {', '.join(symbols)}\n")
                last_symbol_refresh = time.time()

            # Generate trade using current enabled symbols
            trade = generate_trade(symbols)

            # Save to database
            if save_trade(trade):
                trade_count += 1

                # Publish to event bus
                publish_trade(trade)

                # Log trade
                pnl_symbol = "+" if trade["pnl"] >= 0 else ""
                print(f"✅ {trade['signal']:4s} {trade['symbol']:6s} @ ${trade['last_price']:,.2f} | P&L: {pnl_symbol}${trade['pnl']:.2f} | Total: {trade_count}")

            # Random wait between 10-30 seconds
            wait_time = random.randint(10, 30)
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print(f"\n🛑 Bot stopped. Generated {trade_count} trades.")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")

if __name__ == "__main__":
    run_simulator()
