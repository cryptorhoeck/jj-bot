#!/usr/bin/env python3
"""
JJ-Bot Trade Simulator
Generates simulated trades for testing
"""

import asyncio
import random
import time
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from api.engine import log_trade
except ImportError:
    print("Error: Could not import engine. Make sure you're in the virtual environment")
    sys.exit(1)

# Trading pairs
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT']

# Trade types
ACTIONS = ['BUY', 'SELL']

async def generate_trade():
    """Generate a single random trade"""
    symbol = random.choice(SYMBOLS)
    action = random.choice(ACTIONS)
    
    # Generate realistic price based on symbol
    base_prices = {
        'BTCUSDT': 45000,
        'ETHUSDT': 2500,
        'BNBUSDT': 300,
        'ADAUSDT': 0.50,
        'DOGEUSDT': 0.08
    }
    
    base_price = base_prices.get(symbol, 100)
    price = base_price * (1 + random.uniform(-0.05, 0.05))
    
    quantity = random.uniform(0.001, 1.0)
    
    # Calculate P&L (simplified)
    if action == 'SELL':
        pnl = random.uniform(-50, 100)  # Random P&L for sells
    else:
        pnl = 0  # No P&L on buys
    
    trade = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'action': action,
        'quantity': round(quantity, 4),
        'price': round(price, 2),
        'pnl': round(pnl, 2)
    }
    
    return trade

async def run_simulator():
    """Run the trade simulator"""
    print("🎮 JJ-Bot Trade Simulator Started")
    print("Generating trades every 2-5 seconds...")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    
    trade_count = 0
    total_pnl = 0
    
    try:
        while True:
            # Generate trade
            trade = await generate_trade()
            trade_count += 1
            total_pnl += trade['pnl']
            
            # Log trade to database
            try:
                log_trade(
                    trade['symbol'],
                    trade['action'],
                    trade['quantity'],
                    trade['price'],
                    trade['pnl']
                )
                
                # Display trade
                print(f"Trade #{trade_count}: {trade['action']} {trade['quantity']} {trade['symbol']} @ ${trade['price']}")
                print(f"  P&L: ${trade['pnl']:.2f} | Total P&L: ${total_pnl:.2f}")
                
            except Exception as e:
                print(f"Error logging trade: {e}")
            
            # Wait random time
            await asyncio.sleep(random.uniform(2, 5))
            
    except KeyboardInterrupt:
        print("\n" + "-" * 40)
        print(f"Simulator stopped. Generated {trade_count} trades")
        print(f"Final P&L: ${total_pnl:.2f}")

if __name__ == "__main__":
    asyncio.run(run_simulator())
