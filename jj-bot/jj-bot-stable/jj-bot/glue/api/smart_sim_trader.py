#!/usr/bin/env python3
"""
Smart Trade Simulator with Real Trading Logic
"""

import asyncio
import random
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.engine import log_trade
from api.trading_engine import trading_engine

# Trading pairs with realistic price ranges
SYMBOLS = {
    'BTCUSDT': {'base': 45000, 'volatility': 0.02},
    'ETHUSDT': {'base': 2500, 'volatility': 0.03},
    'BNBUSDT': {'base': 300, 'volatility': 0.025},
    'ADAUSDT': {'base': 0.50, 'volatility': 0.04},
    'DOGEUSDT': {'base': 0.08, 'volatility': 0.05}
}

async def generate_market_price(symbol: str, last_price: float = None) -> float:
    """Generate realistic market price with random walk"""
    config = SYMBOLS[symbol]
    
    if last_price is None:
        last_price = config['base']
    
    # Random walk with mean reversion
    change_percent = random.gauss(0, config['volatility'])
    new_price = last_price * (1 + change_percent)
    
    # Mean reversion force
    reversion_force = (config['base'] - new_price) / config['base'] * 0.01
    new_price = new_price * (1 + reversion_force)
    
    return round(new_price, 2)

async def run_smart_simulator():
    """Run the smart trade simulator"""
    print("🧠 Smart JJ-Bot Trade Simulator Started")
    print("Using technical indicators for decisions")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    
    trade_count = 0
    total_pnl = 0
    last_prices = {}
    
    # Initialize price history with some data
    print("Building initial price history...")
    for symbol in SYMBOLS:
        for _ in range(30):
            price = await generate_market_price(symbol)
            trading_engine.update_price_history(symbol, price)
            last_prices[symbol] = price
    
    print("Price history built. Starting trading...")
    print("-" * 40)
    
    try:
        while True:
            # Pick a random symbol
            symbol = random.choice(list(SYMBOLS.keys()))
            
            # Generate new market price
            current_price = await generate_market_price(
                symbol, 
                last_prices.get(symbol)
            )
            last_prices[symbol] = current_price
            
            # Get trading signal
            signal = trading_engine.generate_signal(symbol, current_price)
            
            # Only trade on BUY/SELL signals with good confidence
            if signal['action'] in ['BUY', 'SELL'] and signal['confidence'] > 0.5:
                # Execute trade
                trade = trading_engine.execute_trade(signal)
                
                trade_count += 1
                total_pnl += trade['pnl']
                
                # Log to database
                try:
                    log_trade(trade)
                    
                    # Display trade
                    print(f"Trade #{trade_count}: {trade['signal']} {symbol} @ ${trade['last_price']}")
                    print(f"  Reason: {trade['reason']}")
                    print(f"  Confidence: {trade['confidence']:.1%}")
                    print(f"  P&L: ${trade['pnl']:.2f} | Total P&L: ${total_pnl:.2f}")
                    print("-" * 40)
                    
                except Exception as e:
                    print(f"Error logging trade: {e}")
            
            # Wait before next analysis
            await asyncio.sleep(random.uniform(3, 7))
            
    except KeyboardInterrupt:
        print("\n" + "=" * 40)
        print(f"Simulator stopped after {trade_count} trades")
        print(f"Final P&L: ${total_pnl:.2f}")
        avg_pnl = total_pnl / trade_count if trade_count > 0 else 0
        print(f"Average P&L per trade: ${avg_pnl:.2f}")

if __name__ == "__main__":
    asyncio.run(run_smart_simulator())
