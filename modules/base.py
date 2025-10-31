"""
Base Module for JJ-Bot
Provides common functionality for all trading modules
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Base class for all JJ-Bot modules"""

    def __init__(self, name: str):
        """
        Initialize base module

        Args:
            name: Name of the module
        """
        self.name = name
        self.status = "STOPPED"
        self.start_time: Optional[str] = None
        self.error_count = 0
        self.last_error: Optional[str] = None

        # Setup logging
        self.logger = logging.getLogger(f"jjbot.{name}")
        self.logger.setLevel(logging.INFO)

        # Create console handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                f'%(asctime)s - {name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @abstractmethod
    def start(self) -> bool:
        """
        Start the module

        Returns:
            True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the module

        Returns:
            True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check module health

        Returns:
            Dictionary with health status information
        """
        pass

    def log_error(self, message: str):
        """
        Log an error and track error count

        Args:
            message: Error message to log
        """
        self.error_count += 1
        self.last_error = message
        self.logger.error(message)

    def log_info(self, message: str):
        """
        Log an info message

        Args:
            message: Info message to log
        """
        self.logger.info(message)

    def log_warning(self, message: str):
        """
        Log a warning message

        Args:
            message: Warning message to log
        """
        self.logger.warning(message)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current module status

        Returns:
            Dictionary with module status information
        """
        return {
            "name": self.name,
            "status": self.status,
            "start_time": self.start_time,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "health": self.health_check()
        }

    def reset_errors(self):
        """Reset error tracking"""
        self.error_count = 0
        self.last_error = None
        self.logger.info("Error count reset")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', status='{self.status}')>"
