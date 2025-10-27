#!/usr/bin/env python3
"""
Test Strategy Engine with Data Feed
This runs both modules together
"""

import time
import sys
from datetime import datetime

# Import both modules
from data_feed import DataFeedModule
from strategy import StrategyEngine
from event_bus import event_bus

def signal_handler(event):
    """Handle trading signals"""
    signal = event["data"]
    print(f"\n" + "="*50)
    print(f"🎯 TRADING SIGNAL GENERATED!")
    print(f"Symbol: {signal['symbol']}")
    print(f"Action: {signal['action']}")
    print(f"Price: ${signal['price']:.2f}")
    print(f"Strength: {signal['strength']:.1%}")
    print(f"Reasons:")
    for reason in signal['reason']:
        print(f"  • {reason}")
    print("="*50 + "\n")

def main():
    print("="*60)
    print("STRATEGY ENGINE TEST WITH LIVE DATA")
    print("="*60)
    print("This test runs both modules:")
    print("  • Module 1: Data Feed (gets real prices)")
    print("  • Module 2: Strategy Engine (analyzes & signals)")
    print("="*60 + "\n")
    
    # Subscribe to trading signals
    event_bus.subscribe("TRADING_SIGNAL", signal_handler)
    
    # Start data feed
    print("📡 Starting data feed...")
    feed = DataFeedModule()
    if not feed.start():
        print("❌ Failed to start data feed")
        return
    print("✅ Data feed running")
    
    # Start strategy engine
    print("🧠 Starting strategy engine...")
    strategy = StrategyEngine()
    if not strategy.start():
        print("❌ Failed to start strategy engine")
        return
    print("✅ Strategy engine running")
    
    print("\n" + "="*60)
    print("WAITING FOR TRADING SIGNALS...")
    print("The strategy needs about 30 seconds of price data")
    print("to calculate indicators and generate signals.")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        while True:
            # Show status every 20 seconds
            time.sleep(20)
            
            # Get current signals
            signals = strategy.get_current_signals()
            if signals:
                print(f"\n📊 Active signals for {len(signals)} symbols")
            
            # Show indicators for one symbol
            if strategy.indicators:
                symbol = list(strategy.indicators.keys())[0]
                if symbol != "last_update":
                    ind = strategy.indicators[symbol]
                    print(f"\n📈 {symbol} Indicators:")
                    print(f"  Price: ${ind.get('current_price', 0):.2f}")
                    if ind.get('rsi'):
                        print(f"  RSI: {ind['rsi']:.1f}")
                    if ind.get('sma_fast') and ind.get('sma_slow'):
                        print(f"  SMA Fast/Slow: {ind['sma_fast']:.2f}/{ind['sma_slow']:.2f}")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping modules...")
        strategy.stop()
        feed.stop()
        print("✅ Test complete")
        
        # Show summary
        history = strategy.get_signal_history()
        if history:
            print(f"\n📊 Generated {len(history)} signals during session")

if __name__ == "__main__":
    main()
