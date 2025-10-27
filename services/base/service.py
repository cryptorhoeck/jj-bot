"""
Base Service Class - Foundation for all services
"""

import os
import sys
import time
import json
import threading
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

class BaseService(ABC):
    """Base class for all JJ-Bot services"""
    
    def __init__(self, name: str, auto_start: bool = False):
        self.name = name
        self.auto_start = auto_start
        self.status = "stopped"
        self.process = None
        self.thread = None
        self.start_time = None
        self.config = {}
        self.stats = {}
        
    @abstractmethod
    def _run(self):
        """Service-specific run logic - override this"""
        pass
    
    def start(self) -> Dict[str, Any]:
        """Start the service"""
        if self.status == "running":
            return {"success": False, "message": f"{self.name} already running"}
        
        try:
            self.status = "starting"
            self.start_time = datetime.now()
            
            # Run service in thread
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            
            time.sleep(1)  # Give it a moment to start
            self.status = "running"
            
            return {
                "success": True, 
                "message": f"{self.name} started",
                "start_time": self.start_time.isoformat()
            }
            
        except Exception as e:
            self.status = "error"
            return {"success": False, "message": str(e)}
    
    def stop(self) -> Dict[str, Any]:
        """Stop the service"""
        if self.status != "running":
            return {"success": False, "message": f"{self.name} not running"}
        
        try:
            self.status = "stopping"
            
            # Service-specific cleanup
            self._cleanup()
            
            self.status = "stopped"
            self.start_time = None
            
            return {"success": True, "message": f"{self.name} stopped"}
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _cleanup(self):
        """Override for service-specific cleanup"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        uptime = None
        if self.start_time and self.status == "running":
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "name": self.name,
            "status": self.status,
            "auto_start": self.auto_start,
            "uptime": uptime,
            "config": self.config,
            "stats": self.stats
        }
    
    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update service configuration"""
        self.config.update(config)
        return {"success": True, "config": self.config}
