#!/usr/bin/env python3
"""
Working Trading System - Direct connections, no event bus issues
"""

import time
import threading
import requests
from datetime import datetime

# Import module cores directly
from data_feed.data_feed import DataFeedModule
from strategy.strategy_engine import StrategyEngine  
from risk.risk_manager import RiskManager

class WorkingTradingSystem:
    """A trading system that actually works"""
    
    def __init__(self):
        # Create modules
        self.feed = DataFeedModule()
        self.strategy = StrategyEngine()
        self.risk = RiskManager(10000)
        
        # Stats
        self.stats = {
            "prices": 0,
            "signals": 0,
            "approved": 0,
            "rejected": 0
        }
        
        # Override the feed's process_data to directly call strategy
        original_process = self.feed.process_data
        def new_process(data):
            original_process(data)
            # Direct connection - bypass event bus
            for symbol, price_data in data.items():
                self.stats["prices"] += 1
                formatted = {
                    "data": {
                        "symbol": symbol.upper(),
                        "price": price_data.get("usd", 0),
                        "change_24h": price_data.get("usd_24h_change", 0),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                # Direct call to strategy
                self.strategy.on_price_update(formatted)
                
                # Check for signals
                if symbol.upper() in self.strategy.current_signals:
                    signal = self.strategy.current_signals[symbol.upper()]
                    self.stats["signals"] += 1
                    print(f"\n🎯 SIGNAL: {signal['action']} {symbol.upper()} @ ${signal['price']:.2f}")
                    
                    # Direct call to risk
                    risk_eval = {"data": signal}
                    self.risk.evaluate_signal(risk_eval)
                    
                    # Check risk decision
                    if self.risk.open_positions.get(symbol.upper()):
                        self.stats["approved"] += 1
                        print(f"✅ APPROVED by risk manager")
                    else:
                        self.stats["rejected"] += 1
                        print(f"❌ REJECTED by risk manager")
        
        self.feed.process_data = new_process
    
    def start(self):
        """Start the complete system"""
        print("🚀 Starting Working Trading System...")
        
        # Start modules
        self.feed.start()
        self.strategy.start()
        self.risk.start()
        
        print("✅ System running!")
        print("="*60)
        
    def run(self):
        """Run the system"""
        self.start()
        
        print("Waiting for market data and signals...")
        print("(First signals take 30-60 seconds)\n")
        
        try:
            while True:
                time.sleep(10)
                
                # Status
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Prices: {self.stats['prices']} | "
                      f"Signals: {self.stats['signals']} | "
                      f"Approved: {self.stats['approved']} | "
                      f"Rejected: {self.stats['rejected']}")
                
                # Show a sample price
                prices = self.feed.get_all_prices()
                if prices:
                    symbol = list(prices.keys())[0]
                    print(f"  📊 {symbol}: ${prices[symbol]['price']:.2f}")
                    
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.feed.stop()
            self.strategy.stop()
            self.risk.stop()
            
            print("\n" + "="*60)
            print("FINAL RESULTS:")
            print(f"  Total Prices Processed: {self.stats['prices']}")
            print(f"  Trading Signals Generated: {self.stats['signals']}")
            print(f"  Trades Approved: {self.stats['approved']}")
            print(f"  Trades Rejected: {self.stats['rejected']}")
            
            # Risk stats
            risk_stats = self.risk.get_statistics()
            print(f"\nRisk Manager Stats:")
            print(f"  Balance: ${risk_stats['balance']:.2f}")
            print(f"  Win Rate: {risk_stats['win_rate']:.1%}")

if __name__ == "__main__":
    print("="*60)
    print("WORKING TRADING SYSTEM")
    print("="*60)
    print("This bypasses event bus issues with direct connections")
    print("="*60 + "\n")
    
    system = WorkingTradingSystem()
    system.run()
