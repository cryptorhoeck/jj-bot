"""
Service Manager - Central control for all services
"""

import sys
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ServiceManager:
    """Manages all JJ-Bot services"""
    
    def __init__(self, db_path: str = "jjbot.db"):
        self.services = {}
        self.db_path = db_path
        self._init_database()
        self._load_services()
    
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
    
    def _load_services(self):
        """Load and register all services"""
        # This will be populated as we create services
        # For now, create placeholders
        
        service_configs = [
            {"name": "simulator", "type": "trading", "auto_start": False},
            {"name": "market_feed", "type": "core", "auto_start": True},
            {"name": "analytics", "type": "core", "auto_start": True},
            {"name": "trading_bot", "type": "trading", "auto_start": False},
        ]
        
        for config in service_configs:
            self._register_service(config)
    
    def _register_service(self, config: Dict[str, Any]):
        """Register a service"""
        name = config["name"]
        
        # Check if service exists in DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM service_states WHERE name = ?",
            (name,)
        )
        
        if not cursor.fetchone():
            # Add to database
            cursor.execute(
                """INSERT INTO service_states 
                   (name, status, auto_start, config) 
                   VALUES (?, ?, ?, ?)""",
                (name, "stopped", config.get("auto_start", False), "{}")
            )
            conn.commit()
        
        conn.close()
        
        # Add to memory (placeholder for now)
        self.services[name] = {
            "type": config["type"],
            "auto_start": config.get("auto_start", False),
            "status": "stopped"
        }
    
    def start_service(self, name: str) -> Dict[str, Any]:
        """Start a specific service"""
        if name not in self.services:
            return {"success": False, "message": f"Service {name} not found"}
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE service_states SET status = ?, last_start = ? WHERE name = ?",
            ("running", datetime.now().isoformat(), name)
        )
        conn.commit()
        conn.close()
        
        self.services[name]["status"] = "running"
        
        return {"success": True, "message": f"{name} started"}
    
    def stop_service(self, name: str) -> Dict[str, Any]:
        """Stop a specific service"""
        if name not in self.services:
            return {"success": False, "message": f"Service {name} not found"}
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE service_states SET status = ?, last_stop = ? WHERE name = ?",
            ("stopped", datetime.now().isoformat(), name)
        )
        conn.commit()
        conn.close()
        
        self.services[name]["status"] = "stopped"
        
        return {"success": True, "message": f"{name} stopped"}
    
    def get_service_status(self, name: str) -> Dict[str, Any]:
        """Get status of a specific service"""
        if name not in self.services:
            return {"error": f"Service {name} not found"}
        
        return {
            "name": name,
            "status": self.services[name]["status"],
            "type": self.services[name]["type"],
            "auto_start": self.services[name]["auto_start"]
        }
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get status of all services"""
        return [
            self.get_service_status(name) 
            for name in self.services
        ]
    
    def start_auto_services(self) -> List[str]:
        """Start all auto-start services"""
        started = []
        for name, service in self.services.items():
            if service["auto_start"] and service["status"] != "running":
                self.start_service(name)
                started.append(name)
        return started
