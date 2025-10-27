#!/usr/bin/env python3
"""
Fixed Strategy Test - Shows signals properly
"""

import time
from datetime import datetime

from data_feed import DataFeedModule
from strategy import StrategyEngine
from event_bus import event_bus

# Track what we've seen
shown_signals = set()

def signal_handler(event):
    """Handle trading signals"""
    signal = event["data"]
    
    # Create unique key to avoid duplicates
    key = f"{signal['symbol']}_{signal['action']}_{signal['timestamp'][:16]}"
    
    if key not in shown_signals:
        shown_signals.add(key)
        print(f"\n" + "="*50)
        print(f"🚨 NEW TRADING SIGNAL!")
        print(f"Symbol: {signal['symbol']}")
        print(f"Action: {signal['action']}")
        print(f"Price: ${signal['price']:.2f}")
        print(f"Strength: {signal['strength']:.1%}")
        print(f"Reasons:")
        for reason in signal['reason']:
            print(f"  • {reason}")
        print("="*50)

def main():
    print("="*60)
    print("STRATEGY ENGINE - FIXED VERSION")
    print("="*60)
    
    # Subscribe to signals
    event_bus.subscribe("TRADING_SIGNAL", signal_handler)
    
    # Start modules
    print("Starting modules...")
    feed = DataFeedModule()
    strategy = StrategyEngine()
    
    feed.start()
    strategy.start()
    
    print("✅ Both modules running")
    print("\nWaiting for signals (need 20-30 seconds for first one)...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(10)
            
            # Show we're alive
            signals = strategy.get_current_signals()
            prices = feed.get_all_prices()
            
            if prices:
                # Show one price as heartbeat
                first_symbol = list(prices.keys())[0]
                price_data = prices[first_symbol]
                print(f"💓 {first_symbol.upper()}: ${price_data['price']:.2f}", end="\r")
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        strategy.stop()
        feed.stop()
        
        # Summary
        history = strategy.get_signal_history()
        print(f"\n📊 Summary: Generated {len(history)} signals")
        if history:
            print("\nLast 3 signals:")
            for sig in history[-3:]:
                print(f"  • {sig['action']} {sig['symbol']} @ ${sig['price']:.2f}")

if __name__ == "__main__":
    main()
