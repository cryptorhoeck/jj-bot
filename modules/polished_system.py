#!/usr/bin/env python3
"""
Polished Trading System - Production Ready
Top 20 Cryptos with Enhanced Features
"""

import os
import time
import json
from datetime import datetime
from typing import Dict

# Import enhanced modules
from data_feed.enhanced_feed import EnhancedDataFeed
from strategy.enhanced_strategy import EnhancedStrategy
from risk.risk_manager import RiskManager

class PolishedTradingSystem:
    """Production-ready trading system"""
    
    def __init__(self):
        print("Initializing Polished Trading System...")
        
        # Create enhanced modules
        self.feed = EnhancedDataFeed()
        self.strategy = EnhancedStrategy()
        self.risk = RiskManager(initial_balance=10000)
        
        # System stats
        self.start_time = None
        self.stats = {
            "uptime": 0,
            "prices_processed": 0,
            "signals_generated": 0,
            "trades_approved": 0,
            "trades_rejected": 0,
            "top_gainer": None,
            "top_loser": None
        }
        
        # Connect modules
        self._connect_modules()
        
    def _connect_modules(self):
        """Wire modules together"""
        # Override feed's process method to route to strategy
        original_process = self.feed.process_batch_data
        
        def enhanced_process(data):
            original_process(data)
            
            # Route each price to strategy
            for coin_id, coin_data in data.items():
                self.stats["prices_processed"] += 1
                
                # Create event format
                event = {
                    "data": {
                        "symbol": self.feed.SYMBOL_MAP.get(coin_id, coin_id.upper()),
                        "price": coin_data.get("usd", 0),
                        "change_24h": coin_data.get("usd_24h_change", 0),
                        "volume": coin_data.get("usd_24h_vol", 0),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                # Send to strategy
                self.strategy.on_price_update(event)
                
                # Check for signals
                symbol = event["data"]["symbol"]
                if symbol in self.strategy.current_signals:
                    signal = self.strategy.current_signals[symbol]
                    self.stats["signals_generated"] += 1
                    
                    print(f"\n🎯 SIGNAL GENERATED:")
                    print(f"  Symbol: {symbol}")
                    print(f"  Action: {signal['action']}")
                    print(f"  Price: ${signal['price']:.2f}")
                    print(f"  Confidence: {signal.get('confidence', 0):.1%}")
                    print(f"  Reasons: {', '.join(signal['reason'])}")
                    
                    # Send to risk manager
                    self.risk.evaluate_signal({"data": signal})
                    
                    # Track approvals
                    if symbol in self.risk.open_positions:
                        self.stats["trades_approved"] += 1
                    else:
                        self.stats["trades_rejected"] += 1
        
        self.feed.process_batch_data = enhanced_process
    
    def start(self):
        """Start the system"""
        self.start_time = datetime.now()
        
        print("\n" + "="*60)
        print("STARTING POLISHED TRADING SYSTEM")
        print("="*60)
        print(f"Tracking: Top 20 Cryptocurrencies by Market Cap")
        print(f"Update Interval: 30 seconds")
        print(f"Initial Balance: ${self.risk.initial_balance:,.2f}")
        print("="*60 + "\n")
        
        # Start modules
        self.feed.start()
        self.strategy.start()
        self.risk.start()
        
        print("✅ All systems operational\n")
        
    def display_status(self):
        """Display system status"""
        uptime = (datetime.now() - self.start_time).seconds if self.start_time else 0
        
        # Get market summary
        market = self.feed.get_market_summary()
        movers = self.feed.get_top_movers(3)
        
        print("\n" + "="*60)
        print(f"SYSTEM STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        print(f"Uptime: {uptime//60}m {uptime%60}s")
        print(f"Coins Tracked: {market.get('coins_tracked', 0)}")
        print(f"Avg Market Change: {market.get('average_change_24h', 0):.2f}%")
        
        print(f"\nActivity:")
        print(f"  Prices Processed: {self.stats['prices_processed']}")
        print(f"  Signals Generated: {self.stats['signals_generated']}")
        print(f"  Trades Approved: {self.stats['trades_approved']}")
        print(f"  Trades Rejected: {self.stats['trades_rejected']}")
        
        if movers.get("gainers"):
            print(f"\nTop Gainers:")
            for coin in movers["gainers"][:3]:
                print(f"  {coin['symbol']}: +{coin['change_24h']:.2f}% (${coin['price']:.2f})")
        
        if movers.get("losers"):
            print(f"\nTop Losers:")
            for coin in movers["losers"][:3]:
                print(f"  {coin['symbol']}: {coin['change_24h']:.2f}% (${coin['price']:.2f})")
        
        # Risk stats
        risk_stats = self.risk.get_statistics()
        print(f"\nPortfolio:")
        print(f"  Balance: ${risk_stats['balance']:.2f}")
        print(f"  P&L: ${risk_stats['total_pnl']:.2f}")
        print(f"  Open Positions: {risk_stats['open_positions']}")
        
    def run(self):
        """Run the system"""
        self.start()
        
        try:
            while True:
                time.sleep(30)
                self.display_status()
            self.write_status() if hasattr(self, "write_status") else None
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.stop()
    
    def stop(self):
        """Stop the system"""
        self.feed.stop()
        self.strategy.stop()
        self.risk.stop()
        
        print("\n" + "="*60)
        print("FINAL REPORT")
        print("="*60)
        print(f"Total Runtime: {(datetime.now() - self.start_time).seconds}s")
        print(f"Prices Processed: {self.stats['prices_processed']}")
        print(f"Signals Generated: {self.stats['signals_generated']}")
        print(f"Success Rate: {self.stats['trades_approved']}/{self.stats['signals_generated']}")
        
        risk_stats = self.risk.get_statistics()
        print(f"\nFinal Portfolio:")
        print(f"  Starting: ${self.risk.initial_balance:.2f}")
        print(f"  Ending: ${risk_stats['balance']:.2f}")
        print(f"  Total P&L: ${risk_stats['total_pnl']:.2f}")
        print(f"  Win Rate: {risk_stats['win_rate']:.1%}")

if __name__ == "__main__":
    system = PolishedTradingSystem()
    system.run()

    def update_status_file(self):
        """Write status to file for dashboard"""
        import json
        status = {
            "running": True,
            "last_update": datetime.now().isoformat(),
            "coins_tracked": len(self.feed.price_cache) if self.feed else 0,
            "signals_today": self.stats.get("signals_generated", 0)
        }
        with open("../data/module_status.json", "w") as f:
            json.dump(status, f)

    def update_status_file(self):
        """Write status to file for dashboard"""
        import json
        status = {
            "running": True,
            "last_update": datetime.now().isoformat(),
            "coins_tracked": len(self.feed.price_cache) if self.feed else 0,
            "signals_today": self.stats.get("signals_generated", 0)
        }
        with open("../data/module_status.json", "w") as f:
            json.dump(status, f)

# Add status update to the run method
def write_status(self):
    """Actually write the status"""
    import json
    status_data = {
        "running": True,
        "last_update": datetime.now().isoformat(),
        "coins_tracked": len(self.feed.price_cache) if self.feed else 0,
        "signals_today": self.stats.get("signals_generated", 0)
    }
    try:
        # Use relative path from project root
        status_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "module_status.json")
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        with open(status_file, "w") as f:
            json.dump(status_data, f)
        print(f"📝 Status written: {status_data['coins_tracked']} coins tracked")
    except Exception as e:
        print(f"❌ Could not write status: {e}")
