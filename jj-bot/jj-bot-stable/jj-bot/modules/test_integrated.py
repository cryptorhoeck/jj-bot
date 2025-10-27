#!/usr/bin/env python3
"""
Fixed integration - ensures modules communicate
"""

import time
from data_feed import DataFeedModule
from strategy import StrategyEngine
from event_bus import event_bus

# Debug counters
events_seen = {"prices": 0, "signals": 0}

def debug_price(event):
    events_seen["prices"] += 1
    print(f"📡 Price received: {event['data']['symbol']} = ${event['data']['price']:.2f}")

def debug_signal(event):
    events_seen["signals"] += 1
    signal = event["data"]
    print(f"\n🎯 SIGNAL: {signal['action']} {signal['symbol']}")
    print(f"   Reasons: {', '.join(signal['reason'])}")
    print(f"   Strength: {signal['strength']:.1%}\n")

print("="*60)
print("INTEGRATION TEST - FIXED")
print("="*60)

# Subscribe BEFORE starting modules
print("Setting up event listeners...")
event_bus.subscribe("PRICE_UPDATE", debug_price)
event_bus.subscribe("TRADING_SIGNAL", debug_signal)

# Start modules
print("Starting modules...")
feed = DataFeedModule()
strategy = StrategyEngine()

# Make sure strategy is subscribed
event_bus.subscribe("PRICE_UPDATE", strategy.on_price_update)

feed.start()
strategy.start()

print("Running for 60 seconds to see communication...\n")

try:
    for i in range(12):
        time.sleep(5)
        print(f"[{i*5}s] Events - Prices: {events_seen['prices']}, Signals: {events_seen['signals']}")
        
        # Force a manual check
        if events_seen["prices"] == 0 and i > 1:
            print("⚠️ No events flowing - checking modules...")
            print(f"   Feed status: {feed.get_status()}")
            print(f"   Strategy status: {strategy.get_status()}")
            
except KeyboardInterrupt:
    pass

print("\n" + "="*60)
print(f"RESULTS: {events_seen['prices']} prices, {events_seen['signals']} signals")

if events_seen["prices"] == 0:
    print("❌ MODULES NOT COMMUNICATING - Need to fix event bus")
else:
    print("✅ Modules communicating properly")

feed.stop()
strategy.stop()
