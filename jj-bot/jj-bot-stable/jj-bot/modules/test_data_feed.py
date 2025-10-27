#!/usr/bin/env python3
"""
Test script for Data Feed Module
Run this to test the module independently
"""

import time
import sys
from datetime import datetime

# Import the module
from data_feed import DataFeedModule
from event_bus import event_bus

def price_handler(event):
    """Handle price update events"""
    data = event["data"]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"{data['symbol']}: ${data['price']:.2f} "
          f"({data['change_24h']:+.2f}%)")

def alert_handler(event):
    """Handle price alerts"""
    data = event["data"]
    print(f"⚠️ ALERT: {data['message']}")

def main():
    print("=" * 50)
    print("DATA FEED MODULE TEST")
    print("=" * 50)
    
    # Subscribe to events
    event_bus.subscribe("PRICE_UPDATE", price_handler)
    event_bus.subscribe("PRICE_ALERT", alert_handler)
    
    # Create and start module
    feed = DataFeedModule()
    
    print("\n▶️ Starting data feed...")
    if feed.start():
        print("✅ Data feed started successfully")
    else:
        print("❌ Failed to start data feed")
        return
    
    print("\n📊 Fetching live market data...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Run for a while
        while True:
            time.sleep(10)
            
            # Check health
            health = feed.health_check()
            print(f"\n💚 Health: {health}")
            
            # Get all prices
            prices = feed.get_all_prices()
            if prices:
                print(f"📈 Tracking {len(prices)} symbols")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping data feed...")
        feed.stop()
        print("✅ Test complete")

if __name__ == "__main__":
    main()
