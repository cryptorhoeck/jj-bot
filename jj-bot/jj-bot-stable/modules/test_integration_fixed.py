#!/usr/bin/env python3
"""
Fixed Integration - Forces modules to communicate
"""

import time
import threading
from datetime import datetime

# Import modules
from data_feed import DataFeedModule
from strategy import StrategyEngine
from risk import RiskManager
from event_bus import event_bus

# Global stats
stats = {
    "prices": 0,
    "signals": 0,
    "approved": 0,
    "rejected": 0
}

def main():
    print("="*60)
    print("INTEGRATION TEST - FIXED VERSION")
    print("="*60)
    
    # Create modules
    print("Creating modules...")
    feed = DataFeedModule()
    strategy = StrategyEngine()
    risk = RiskManager(10000)
    
    # CRITICAL: Set up connections BEFORE starting
    print("Connecting modules...")
    
    # Count events for debugging
    def count_price(event):
        stats["prices"] += 1
        # MANUALLY route to strategy
        strategy.on_price_update(event)
        
    def count_signal(event):
        stats["signals"] += 1
        print(f"📍 Signal: {event['data']['action']} {event['data']['symbol']}")
        # MANUALLY route to risk
        risk.evaluate_signal(event)
        
    def count_approved(event):
        stats["approved"] += 1
        print(f"✅ APPROVED: {event['data']['signal']['symbol']}")
        
    def count_rejected(event):
        stats["rejected"] += 1
        print(f"❌ REJECTED: {event['data']['signal']['symbol']} - {event['data']['reasons']}")
    
    # Subscribe with our routing functions
    event_bus.subscribe("PRICE_UPDATE", count_price)
    event_bus.subscribe("TRADING_SIGNAL", count_signal)
    event_bus.subscribe("TRADE_APPROVED", count_approved)
    event_bus.subscribe("TRADE_REJECTED", count_rejected)
    
    # Start modules
    print("Starting modules...")
    feed.start()
    strategy.start()
    risk.start()
    
    print("✅ All modules started")
    print("="*60)
    print("Waiting for activity...")
    print("(First signals take 30-60 seconds)")
    print("="*60 + "\n")
    
    try:
        while True:
            time.sleep(10)
            
            # Force check if feed is working
            prices = feed.get_all_prices()
            if prices and stats["prices"] == 0:
                print("⚠️ Feed has prices but events not flowing!")
                print("Forcing manual price event...")
                # Force emit a price event
                for symbol, price_data in prices.items():
                    event_bus.publish("PRICE_UPDATE", price_data)
                    break
            
            # Status update
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Prices: {stats['prices']} | Signals: {stats['signals']} | Approved: {stats['approved']} | Rejected: {stats['rejected']}")
            
    except KeyboardInterrupt:
        print("\nStopping...")
        feed.stop()
        strategy.stop()
        risk.stop()
        
        print("\nFinal Stats:", stats)

if __name__ == "__main__":
    main()
