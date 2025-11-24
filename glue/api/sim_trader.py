"""
Trading Bot with Strategy Engine & Learning
Generates trades based on technical analysis strategies
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
from modules.strategy.strategy_engine import StrategyEngine
from modules.learning.adaptive_strategy_selector import AdaptiveStrategySelector
from modules.database.connection import init_learning_db

# Database paths
DB_PATH = os.path.join(project_root, "data", "trades.db")
SYMBOLS_DB_PATH = os.path.join(project_root, "data", "symbols.db")

# Default base prices (updated as we trade)
BASE_PRICES = {
    'BTC': 45000, 'ETH': 2500, 'SOL': 100, 'BNB': 350, 'ADA': 0.50,
    'DOT': 7, 'LINK': 15, 'POL': 0.45, 'UNI': 6, 'AVAX': 35,
    'XRP': 0.65, 'DOGE': 0.08, 'TRX': 0.10, 'ATOM': 10,
    'LTC': 70, 'BCH': 250, 'XLM': 0.12, 'ETC': 20,
    'WBTC': 45000, 'SHIB': 0.00001
}

# Current prices (tracks live prices)
current_prices = {}

# Strategy engine instance
strategy_engine = None

# Adaptive strategy selector
adaptive_selector = None
current_strategy = "rsi_strategy"  # Track active strategy (will be updated from selector)

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
            strategy TEXT DEFAULT 'momentum',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add strategy column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT 'momentum'")
        print("✅ Added strategy column to trades table")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()
    print("✅ Database initialized")

def update_price(symbol):
    """Simulate realistic price movement for a symbol"""
    global current_prices

    # Initialize price if not exists
    if symbol not in current_prices:
        current_prices[symbol] = BASE_PRICES.get(symbol, 100)

    # Random walk with slight trend (realistic price movement)
    change_percent = random.uniform(-0.02, 0.02)  # ±2% movement
    new_price = current_prices[symbol] * (1 + change_percent)

    # Keep prices positive and reasonable
    new_price = max(new_price, 0.00001)

    current_prices[symbol] = new_price

    # Publish price update to strategy engine
    price_data = {
        "symbol": symbol,
        "price": new_price,
        "timestamp": datetime.now().isoformat(),
        "volume_24h": random.uniform(1000000, 10000000)
    }

    event_bus.publish("PRICE_UPDATE", price_data)

    return new_price

def generate_trade_from_signal(signal):
    """Generate trade from strategy signal"""
    if not signal or signal["action"] == "HOLD":
        return None

    symbol = signal["symbol"]
    last_price = signal["price"]
    vwap = last_price * (1 + random.uniform(-0.001, 0.001))  # Very close to last price

    # Calculate simulated P&L based on signal strength and randomness
    # Stronger signals tend to have better outcomes
    strength_bonus = signal["strength"] * 50  # Up to +50 for perfect signal
    base_pnl = random.uniform(-30, 70)  # Random component
    pnl = base_pnl + strength_bonus

    # Add some realism - not all signals work out
    if random.random() < 0.3:  # 30% chance signal doesn't work
        pnl = -abs(pnl) * 0.5

    timestamp = datetime.now().isoformat()

    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "signal": signal["action"],
        "last_price": last_price,
        "vwap": vwap,
        "pnl": pnl,
        "strategy": current_strategy,  # Use active strategy from adaptive selector
        "strategy_reason": ", ".join(signal["reason"][:2]) if signal.get("reason") else "N/A"
    }

def save_trade(trade):
    """Save trade to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (timestamp, symbol, signal, last_price, vwap, pnl, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade["timestamp"], trade["symbol"], trade["signal"],
              trade["last_price"], trade["vwap"], trade["pnl"], trade.get("strategy", "momentum")))

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
    """Main trading bot loop with strategy engine"""
    global strategy_engine, adaptive_selector, current_strategy

    print("🦍 JJ Gorilla Trading Bot starting...")
    print("🧠 Strategy engine: Enabled (RSI, SMA, MACD, Bollinger Bands)")
    print("🤖 Adaptive strategy: Enabled (switches to best performer)")
    print("⏰ Price updates every 5 seconds, trades based on signals")
    print()

    # Initialize database
    init_database()

    # Initialize strategy engine
    print("🚀 Starting strategy engine...")
    strategy_engine = StrategyEngine()
    strategy_engine.start()
    print("✅ Strategy engine started")

    # Initialize learning database
    print("🧠 Initializing learning database...")
    try:
        init_learning_db()
    except Exception as e:
        print(f"⚠️ Failed to initialize learning database: {e}")

    # Initialize adaptive strategy selector
    print("🧠 Initializing adaptive strategy selector...")
    try:
        adaptive_selector = AdaptiveStrategySelector(
            reevaluation_interval=10,  # Re-evaluate every 10 trades
            min_confidence=0.6,
            lookback_hours=24
        )
        # Get initial strategy from selector
        state = adaptive_selector.get_state()
        if state:
            current_strategy = state['current_strategy']
            print(f"✅ Adaptive strategy selector started (using: {current_strategy})")
        else:
            print("✅ Adaptive strategy selector started")
    except Exception as e:
        print(f"⚠️ Could not initialize adaptive selector: {e}")
        print("⚠️ Will use default 'momentum' strategy")
    print()

    # Load enabled symbols from database
    symbols = get_enabled_symbols()
    print(f"📊 Trading symbols: {', '.join(symbols)}")
    print()

    trade_count = 0
    last_symbol_refresh = time.time()
    last_signal_check = {}  # Track when we last checked each symbol
    SYMBOL_REFRESH_INTERVAL = 60  # Refresh symbols every 60 seconds
    SIGNAL_CHECK_INTERVAL = 20  # Check for signals every 20 seconds per symbol

    try:
        while True:
            # Refresh symbols periodically
            if time.time() - last_symbol_refresh > SYMBOL_REFRESH_INTERVAL:
                new_symbols = get_enabled_symbols()
                if new_symbols != symbols:
                    symbols = new_symbols
                    print(f"\n🔄 Symbols updated: {', '.join(symbols)}\n")
                last_symbol_refresh = time.time()

            # Update prices for all symbols
            for symbol in symbols:
                # Update price (feeds to strategy engine)
                new_price = update_price(symbol)

                # Check if enough time has passed to check for signals
                if symbol not in last_signal_check or \
                   time.time() - last_signal_check[symbol] > SIGNAL_CHECK_INTERVAL:

                    # Get signals from strategy engine
                    current_signals = strategy_engine.get_current_signals()

                    if symbol in current_signals:
                        signal = current_signals[symbol]

                        # Generate trade from signal
                        trade = generate_trade_from_signal(signal)

                        if trade:
                            # Save to database
                            if save_trade(trade):
                                trade_count += 1

                                # Publish to event bus
                                publish_trade(trade)

                                # Log trade with strategy reason
                                pnl_symbol = "+" if trade["pnl"] >= 0 else ""
                                reason = trade.get("strategy_reason", "N/A")
                                print(f"✅ {trade['signal']:4s} {trade['symbol']:6s} @ ${trade['last_price']:,.2f} | P&L: {pnl_symbol}${trade['pnl']:.2f} | [{current_strategy}] {reason} | Total: {trade_count}")

                                # Notify adaptive selector of new trade
                                if adaptive_selector:
                                    try:
                                        adaptive_selector.notify_trade()
                                    except Exception as e:
                                        print(f"⚠️ Failed to notify adaptive selector: {e}")

                                # Check if time to re-evaluate strategy
                                if adaptive_selector:
                                    try:
                                        selection = adaptive_selector.select_best_strategy()
                                        if selection and selection.get('switched'):
                                            old_strategy = current_strategy
                                            current_strategy = selection['strategy']
                                            confidence = selection.get('confidence', 0.0)
                                            print(f"\n🔄 STRATEGY SWITCHED: {old_strategy} → {current_strategy} (confidence: {confidence:.2%})\n")
                                    except Exception as e:
                                        print(f"⚠️ Strategy evaluation error: {e}")

                    last_signal_check[symbol] = time.time()

            # Wait 5 seconds between price update cycles
            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\n🛑 Bot stopped. Generated {trade_count} trades using strategy engine.")
        if strategy_engine:
            strategy_engine.stop()
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        if strategy_engine:
            strategy_engine.stop()

if __name__ == "__main__":
    run_simulator()
