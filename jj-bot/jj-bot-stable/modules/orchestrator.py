"""
Module Orchestrator for JJ-Bot
Connects and manages all trading modules
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Any

# Import all modules
from data_feed import DataFeedModule
from strategy import StrategyEngine
from risk import RiskManager
from event_bus import event_bus

class ModuleOrchestrator:
    """Manages and connects all trading modules"""
    
    def __init__(self):
        self.modules = {}
        self.running = False
        self.start_time = None
        
        # Statistics
        self.stats = {
            "prices_received": 0,
            "signals_generated": 0,
            "trades_approved": 0,
            "trades_rejected": 0
        }
        
    def initialize(self):
        """Initialize all modules"""
        print("🚀 Initializing Module Orchestrator...")
        
        # Create module instances
        self.modules["data_feed"] = DataFeedModule()
        self.modules["strategy"] = StrategyEngine()
        self.modules["risk"] = RiskManager(initial_balance=10000)
        
        # Set up event routing
        self._setup_event_routing()
        
        print("✅ All modules initialized")
        
    def _setup_event_routing(self):
        """Connect modules via events"""
        print("🔌 Setting up event routing...")
        
        # Data Feed -> Strategy
        def route_price_to_strategy(event):
            self.stats["prices_received"] += 1
            self.modules["strategy"].on_price_update(event)
        
        # Strategy -> Risk
        def route_signal_to_risk(event):
            self.stats["signals_generated"] += 1
            self.modules["risk"].evaluate_signal(event)
            
        # Risk -> Executor (future)
        def handle_approved_trade(event):
            self.stats["trades_approved"] += 1
            print(f"✅ Trade Approved: {event['data']['signal']['symbol']}")
            
        def handle_rejected_trade(event):
            self.stats["trades_rejected"] += 1
            print(f"❌ Trade Rejected: {event['data']['signal']['symbol']}")
        
        # Subscribe to events
        event_bus.subscribe("PRICE_UPDATE", route_price_to_strategy)
        event_bus.subscribe("TRADING_SIGNAL", route_signal_to_risk)
        event_bus.subscribe("TRADE_APPROVED", handle_approved_trade)
        event_bus.subscribe("TRADE_REJECTED", handle_rejected_trade)
        
        print("✅ Event routing configured")
    
    def start(self):
        """Start all modules in correct order"""
        print("\n🎯 Starting all modules...")
        
        # Start in dependency order
        if not self.modules["risk"].start():
            print("❌ Failed to start Risk Manager")
            return False
            
        if not self.modules["strategy"].start():
            print("❌ Failed to start Strategy Engine")
            return False
            
        if not self.modules["data_feed"].start():
            print("❌ Failed to start Data Feed")
            return False
        
        self.running = True
        self.start_time = datetime.now()
        
        print("✅ All modules running!")
        print("=" * 60)
        return True
    
    def stop(self):
        """Stop all modules"""
        print("\n⏹️ Stopping all modules...")
        
        self.running = False
        
        # Stop in reverse order
        self.modules["data_feed"].stop()
        self.modules["strategy"].stop()
        self.modules["risk"].stop()
        
        print("✅ All modules stopped")
    
    def get_status(self) -> Dict:
        """Get status of all modules"""
        status = {
            "running": self.running,
            "uptime": str(datetime.now() - self.start_time) if self.start_time else "0",
            "modules": {},
            "statistics": self.stats
        }
        
        for name, module in self.modules.items():
            status["modules"][name] = module.get_status()
        
        return status
    
    def get_health(self) -> Dict:
        """Check health of all modules"""
        health = {
            "overall": True,
            "modules": {}
        }
        
        for name, module in self.modules.items():
            module_health = module.health_check()
            health["modules"][name] = module_health
            if not module_health.get("healthy", False):
                health["overall"] = False
        
        return health

# Test the orchestrator
if __name__ == "__main__":
    print("="*60)
    print("MODULE ORCHESTRATOR TEST")
    print("="*60)
    
    # Create orchestrator
    orchestrator = ModuleOrchestrator()
    orchestrator.initialize()
    
    # Start everything
    if orchestrator.start():
        print("\n📊 System running. Press Ctrl+C to stop")
        print("Waiting for signals...\n")
        
        try:
            while True:
                time.sleep(30)
                
                # Show statistics
                print(f"\n📈 Statistics at {datetime.now().strftime('%H:%M:%S')}:")
                stats = orchestrator.stats
                print(f"  Prices: {stats['prices_received']}")
                print(f"  Signals: {stats['signals_generated']}")
                print(f"  Approved: {stats['trades_approved']}")
                print(f"  Rejected: {stats['trades_rejected']}")
                
                # Show health
                health = orchestrator.get_health()
                print(f"  System Health: {'✅' if health['overall'] else '❌'}")
                
        except KeyboardInterrupt:
            pass
        
        # Stop everything
        orchestrator.stop()
        
        # Final report
        print("\n" + "="*60)
        print("FINAL STATISTICS:")
        for key, value in orchestrator.stats.items():
            print(f"  {key}: {value}")
