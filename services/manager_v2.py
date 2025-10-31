"""
Service Manager V2 - Connected to real services
"""

import sys
import os
import json
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.trading.simulator_service import SimulatorService

class ServiceManager:
    """Enhanced Service Manager with real services"""
    
    def __init__(self, db_path: str = None):
        self.services = {}
        # Use data directory in project root if no path specified
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "jjbot.db")
        self.db_path = db_path
        self._init_database()
        self._init_services()
    
    def _init_database(self):
        """Initialize service state table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_states (
                name TEXT PRIMARY KEY,
                status TEXT,
                auto_start BOOLEAN,
                config TEXT,
                last_start TEXT,
                last_stop TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_services(self):
        """Initialize real service instances"""
        # Import all services
        from services.trading.simulator_service import SimulatorService
        from services.trading.market_feed_service import MarketFeedService
        from services.trading.analytics_service import AnalyticsService
        from services.trading.trading_bot_service import TradingBotService
        from services.trading.strategy_service import StrategyService

        # Create real service instances
        self.services = {
            "simulator": SimulatorService(),
            "market_feed": MarketFeedService(),
            "strategy_engine": StrategyService(),
            "analytics": AnalyticsService(),
            "trading_bot": TradingBotService()
        }

        # Sync with database
        for name, service in self.services.items():
            self._sync_service_state(name)
    
    def _sync_service_state(self, name: str):
        """Sync service state with database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT status FROM service_states WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        if not row:
            # Add to database
            cursor.execute(
                """INSERT INTO service_states 
                   (name, status, auto_start, config) 
                   VALUES (?, ?, ?, ?)""",
                (name, "stopped", self.services[name].auto_start, "{}")
            )
            conn.commit()
        
        conn.close()
    
    def start_service(self, name: str) -> Dict[str, Any]:
        """Start a real service"""
        if name not in self.services:
            return {"success": False, "message": f"Service {name} not found"}
        
        # Start the actual service
        result = self.services[name].start()
        
        if result["success"]:
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE service_states SET status = ?, last_start = ? WHERE name = ?",
                ("running", datetime.now().isoformat(), name)
            )
            conn.commit()
            conn.close()
        
        return result
    
    def stop_service(self, name: str) -> Dict[str, Any]:
        """Stop a real service"""
        if name not in self.services:
            return {"success": False, "message": f"Service {name} not found"}
        
        # Stop the actual service
        result = self.services[name].stop()
        
        if result["success"]:
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE service_states SET status = ?, last_stop = ? WHERE name = ?",
                ("stopped", datetime.now().isoformat(), name)
            )
            conn.commit()
            conn.close()
        
        return result
    
    def get_service_status(self, name: str) -> Dict[str, Any]:
        """Get real service status"""
        if name not in self.services:
            return {"error": f"Service {name} not found"}
        
        return self.services[name].get_status()
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get status of all real services"""
        return [
            self.get_service_status(name)
            for name in self.services
        ]

    def start_auto_services(self) -> List[str]:
        """
        Start all services marked with auto_start=True

        Returns:
            List of service names that were started
        """
        started = []
        for name, service in self.services.items():
            if service.auto_start and service.status != "running":
                result = self.start_service(name)
                if result.get("success"):
                    started.append(name)
        return started
