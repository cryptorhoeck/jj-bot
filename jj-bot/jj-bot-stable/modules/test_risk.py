#!/usr/bin/env python3
"""
Test Risk Manager Module
"""

import time
from datetime import datetime
from risk import RiskManager
from event_bus import event_bus

def main():
    print("="*60)
    print("RISK MANAGER TEST")
    print("="*60)
    
    # Create risk manager
    risk = RiskManager(initial_balance=10000)
    
    print(f"Initial Balance: ${risk.initial_balance}")
    print(f"Max Risk Per Trade: {risk.max_risk_per_trade:.1%}")
    print(f"Max Daily Loss: {risk.max_daily_loss:.1%}")
    print(f"Max Positions: {risk.max_positions}")
    print()
    
    # Start risk manager
    risk.start()
    print("✅ Risk manager started\n")
    
    # Simulate some trading signals
    test_signals = [
        {"symbol": "BITCOIN", "action": "BUY", "price": 45000, "strength": 0.7, "reason": ["Test signal 1"]},
        {"symbol": "ETHEREUM", "action": "BUY", "price": 2500, "strength": 0.8, "reason": ["Test signal 2"]},
        {"symbol": "BITCOIN", "action": "BUY", "price": 45100, "strength": 0.9, "reason": ["Duplicate position"]},
        {"symbol": "CARDANO", "action": "BUY", "price": 0.5, "strength": 0.4, "reason": ["Weak signal"]},
        {"symbol": "DOGECOIN", "action": "BUY", "price": 0.08, "strength": 0.75, "reason": ["Test signal 3"]},
    ]
    
    print("Sending test signals to risk manager...\n")
    
    for signal in test_signals:
        # Publish as event
        event_bus.publish("TRADING_SIGNAL", signal)
        time.sleep(1)
    
    print("\n" + "="*60)
    print("RISK STATISTICS:")
    stats = risk.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Simulate closing a position
    print("\n" + "="*60)
    print("Simulating position close...")
    risk.close_position("BITCOIN", 46000)  # Close with profit
    
    print("\nFinal Statistics:")
    stats = risk.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    risk.stop()
    print("\n✅ Test complete")

if __name__ == "__main__":
    main()
