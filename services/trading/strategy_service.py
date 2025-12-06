"""
Strategy Service - Wraps the Strategy Engine as a managed service
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Any

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.base.service import BaseService
from modules.strategy.strategy_engine import StrategyEngine
from modules.event_bus import event_bus


class StrategyService(BaseService):
    """Service that wraps and manages the Strategy Engine"""

    def __init__(self):
        super().__init__(name="strategy_engine", auto_start=True)

        # Strategy engine instance
        self.engine = None

        # Configuration
        self.config = {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "sma_fast": 10,
            "sma_slow": 20,
            "min_signal_strength": 0.7
        }

        # Stats tracking
        self.stats = {
            "signals_generated": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "symbols_tracked": 0,
            "last_signal": None,
            "start_time": None
        }

        # Subscribe to trading signals for stats
        event_bus.subscribe("TRADING_SIGNAL", self._on_trading_signal)

    def _run(self):
        """Initialize and run the strategy engine"""
        print("🧠 Strategy Engine Service starting...")

        try:
            # Create and start the strategy engine
            self.engine = StrategyEngine()

            # Apply configuration
            if "rsi_oversold" in self.config:
                self.engine.rsi_oversold = self.config["rsi_oversold"]
            if "rsi_overbought" in self.config:
                self.engine.rsi_overbought = self.config["rsi_overbought"]
            if "sma_fast" in self.config:
                self.engine.sma_fast = self.config["sma_fast"]
            if "sma_slow" in self.config:
                self.engine.sma_slow = self.config["sma_slow"]

            # Start the engine
            if self.engine.start():
                self.stats["start_time"] = datetime.now().isoformat()
                print("[OK] Strategy Engine started successfully")
                print(f"   RSI Oversold: {self.engine.rsi_oversold}")
                print(f"   RSI Overbought: {self.engine.rsi_overbought}")
                print(f"   SMA Fast: {self.engine.sma_fast}")
                print(f"   SMA Slow: {self.engine.sma_slow}")

                # Keep service running
                while self.status == "running":
                    # Update stats
                    self.stats["symbols_tracked"] = len(self.engine.price_history)
                    time.sleep(1)
            else:
                print("[ERROR] Failed to start Strategy Engine")
                self.status = "stopped"

        except Exception as e:
            print(f"[ERROR] Strategy Engine error: {e}")
            self.status = "stopped"

    def _cleanup(self):
        """Cleanup when stopping"""
        if self.engine:
            try:
                self.engine.stop()
                print("[STOP] Strategy Engine stopped")
            except Exception as e:
                print(f"[WARNING] Error stopping engine: {e}")

    def _on_trading_signal(self, event: Dict):
        """Track trading signals for stats"""
        try:
            signal = event["data"]
            self.stats["signals_generated"] += 1
            self.stats["last_signal"] = {
                "symbol": signal.get("symbol"),
                "action": signal.get("action"),
                "strength": signal.get("strength"),
                "timestamp": datetime.now().isoformat()
            }

            if signal.get("action") == "BUY":
                self.stats["buy_signals"] += 1
            elif signal.get("action") == "SELL":
                self.stats["sell_signals"] += 1

        except Exception as e:
            print(f"[WARNING] Error tracking signal: {e}")

    def get_current_signals(self) -> Dict[str, Any]:
        """
        Get current trading signals from the engine

        Returns:
            Dictionary of current signals by symbol
        """
        if self.engine:
            return self.engine.get_current_signals()
        return {}

    def get_signal_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent signal history

        Args:
            limit: Maximum number of signals to return

        Returns:
            List of recent signals
        """
        if self.engine:
            return self.engine.get_signal_history(limit)
        return []

    def get_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Get technical indicators for a specific symbol

        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')

        Returns:
            Dictionary of indicators or empty dict if not found
        """
        if self.engine and symbol in self.engine.indicators:
            return self.engine.indicators[symbol]
        return {}

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Update strategy configuration

        Args:
            new_config: Dictionary of configuration values

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config.update(new_config)

            # Apply to running engine
            if self.engine:
                if "rsi_oversold" in new_config:
                    self.engine.rsi_oversold = new_config["rsi_oversold"]
                if "rsi_overbought" in new_config:
                    self.engine.rsi_overbought = new_config["rsi_overbought"]
                if "sma_fast" in new_config:
                    self.engine.sma_fast = new_config["sma_fast"]
                if "sma_slow" in new_config:
                    self.engine.sma_slow = new_config["sma_slow"]

            print(f"[OK] Strategy configuration updated: {new_config}")
            return True

        except Exception as e:
            print(f"[ERROR] Error updating config: {e}")
            return False
