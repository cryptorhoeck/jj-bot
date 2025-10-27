#!/usr/bin/env python3
"""
Check what the modules are actually doing
"""

import time
from data_feed import DataFeedModule
from strategy import StrategyEngine
from event_bus import event_bus

# Track events
price_count = 0
signal_count = 0

def price_counter(event):
    global price_count
    price_count += 1

def signal_counter(event):
    global signal_count
    signal_count += 1
    signal = event["data"]
    print(f"✅ Signal: {signal['action']} {signal['symbol']} - {signal['reason']}")

print("="*60)
print("MODULE DIAGNOSTIC CHECK")
print("="*60)

# Subscribe to events
event_bus.subscribe("PRICE_UPDATE", price_counter)
event_bus.subscribe("TRADING_SIGNAL", signal_counter)

# Start modules
feed = DataFeedModule()
strategy = StrategyEngine()

feed.start()
strategy.start()

print("Running 30-second diagnostic...\n")

# Check for 30 seconds
for i in range(6):
    time.sleep(5)
    prices = feed.get_all_prices()
    
    # Show sample price
    if prices:
        symbol = list(prices.keys())[0]
        print(f"Second {i*5}: Price updates: {price_count} | Signals: {signal_count}")
        print(f"  Sample: {symbol} = ${prices[symbol]['price']:.2f}")

# Final analysis
print("\n" + "="*60)
print("DIAGNOSTIC RESULTS:")
print(f"• Price updates received: {price_count}")
print(f"• Trading signals generated: {signal_count}")
print(f"• Symbols tracked: {len(feed.get_all_prices())}")

# Check strategy indicators
if strategy.indicators:
    symbol = list(strategy.indicators.keys())[0]
    if symbol != "last_update":
        ind = strategy.indicators[symbol]
        print(f"\nIndicator Check for {symbol}:")
        print(f"  RSI: {ind.get('rsi', 'Not calculated')}")
        print(f"  Has enough data: {len(strategy.price_history.get(symbol, [])) >= 20}")

if signal_count == 0:
    print("\n⚠️ No signals generated - this is NORMAL if:")
    print("  • Market is not moving much")
    print("  • Strategy is being cautious")
    print("  • Indicators are neutral")
else:
    print(f"\n✅ Module working correctly - {signal_count} signals generated")

feed.stop()
strategy.stop()
