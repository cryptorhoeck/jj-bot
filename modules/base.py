"""
Base Module Class for JJ-Bot
All modules inherit from this
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseModule(ABC):
    """Base class for all JJ-Bot modules"""
    
    def __init__(self, name: str):
        self.name = name
        self.status = "STOPPED"
        self.start_time = None
        self.error_count = 0
        self.last_error = None
        self.config = {}
        
        # Setup logging
        self.logger = logging.getLogger(name)
        handler = logging.FileHandler(f'logs/{name}.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    @abstractmethod
    def start(self) -> bool:
        """Start the module"""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Stop the module"""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check module health"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status"""
        return {
            "name": self.name,
            "status": self.status,
            "start_time": self.start_time,
            "error_count": self.error_count,
            "last_error": self.last_error
        }
    
    def log_error(self, error: str):
        """Log an error"""
        self.error_count += 1
        self.last_error = {
            "message": error,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.error(error)
