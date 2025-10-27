#!/usr/bin/env python3
"""
Fixed test script that actually shows prices
"""

import time
import sys
from datetime import datetime

from data_feed import DataFeedModule
from event_bus import event_bus

def price_handler(event):
    """Handle price update events"""
    data = event["data"]
    print(f"💰 {data['symbol']}: ${data['price']:.2f} ({data['change_24h']:+.2f}%)")

def main():
    print("=" * 50)
    print("DATA FEED MODULE TEST - FIXED")
    print("=" * 50)
    
    # Subscribe to events
    event_bus.subscribe("PRICE_UPDATE", price_handler)
    
    # Create and start module
    feed = DataFeedModule()
    
    print("\n▶️ Starting data feed...")
    if feed.start():
        print("✅ Data feed started")
    else:
        print("❌ Failed to start")
        return
    
    print("\n📊 Waiting for prices...\n")
    
    try:
        while True:
            # Wait for prices to update
            time.sleep(2)
            
            # Force show current prices
            prices = feed.get_all_prices()
            if prices:
                print("\n" + "=" * 30)
                print("CURRENT PRICES:")
                print("=" * 30)
                for symbol, data in prices.items():
                    print(f"💰 {symbol.upper()}: ${data['price']:.2f} ({data['change_24h']:+.2f}%)")
                print("=" * 30)
            
            # Wait before next update
            time.sleep(8)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping...")
        feed.stop()
        print("✅ Done")

if __name__ == "__main__":
    main()
