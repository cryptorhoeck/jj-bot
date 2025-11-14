"""
Trading Bot Service - Automated trading system
Integrates strategy engine, risk management, and execution
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Any

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.base.service import BaseService
from modules.event_bus import event_bus


class TradingBotService(BaseService):
    """Automated trading bot service"""

    def __init__(self):
        super().__init__(name="trading_bot", auto_start=True)

        # Configuration
        self.config = {
            "enabled": True,  # ENABLED: Bot will execute paper trades based on real analysis
            "paper_trading": True,  # Always use paper trading for safety
            "max_open_positions": 5,
            "risk_per_trade": 0.02,  # 2% risk per trade
            "symbols_to_trade": ["BTC", "ETH", "BNB", "SOL", "ADA"],
            "min_signal_strength": 0.7,  # Minimum signal strength (0-1)
            "cooldown_seconds": 300  # 5 minutes between trades on same symbol
        }

        # Stats tracking
        self.stats = {
            "trades_executed": 0,
            "trades_rejected": 0,
            "signals_received": 0,
            "signals_approved": 0,
            "open_positions": {},
            "last_trade_time": {},
            "total_pnl": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "last_signal": None,
            "last_trade": None,
            "bot_state": "idle"
        }

        # Internal state
        self.open_positions = {}
        self.last_trade_times = {}

        # Subscribe to trading signals and approvals
        event_bus.subscribe("TRADING_SIGNAL", self._on_trading_signal)
        event_bus.subscribe("TRADE_APPROVED", self._on_trade_approved)
        event_bus.subscribe("TRADE_REJECTED", self._on_trade_rejected)

    def _run(self):
        """Run the trading bot"""
        print("🤖 Trading Bot Service starting...")

        if not self.config["enabled"]:
            print("⚠️  Trading Bot is DISABLED by default for safety")
            print("   To enable: update config with {\"enabled\": true}")
            print("   Bot will listen for signals but not execute trades")

        if self.config["paper_trading"]:
            print("📝 Paper Trading Mode: ON (no real money at risk)")

        self.stats["bot_state"] = "monitoring"

        # Main bot loop - just stay alive and process events
        while self.status == "running":
            try:
                # Periodic health check
                self._check_positions()

                # Log status every 5 minutes
                time.sleep(300)
                if self.stats["signals_received"] > 0:
                    approval_rate = (self.stats["signals_approved"] /
                                   self.stats["signals_received"] * 100)
                    print(f"🤖 Bot Status: {self.stats['signals_received']} signals | "
                          f"{approval_rate:.1f}% approved | "
                          f"{self.stats['trades_executed']} executed")

            except Exception as e:
                print(f"❌ Trading Bot error: {e}")
                time.sleep(10)

    def _on_trading_signal(self, event: Dict):
        """Handle incoming trading signals"""
        try:
            signal = event["data"]
            self.stats["signals_received"] += 1
            self.stats["last_signal"] = signal

            symbol = signal.get("symbol")
            action = signal.get("action")
            strength = signal.get("strength", 0)

            # Check if bot is enabled
            if not self.config["enabled"]:
                return

            # Check if we should trade this symbol
            if symbol not in self.config["symbols_to_trade"]:
                return

            # Check signal strength
            if strength < self.config["min_signal_strength"]:
                print(f"⚠️  Signal {symbol} too weak: {strength:.1%}")
                return

            # Check cooldown
            if symbol in self.last_trade_times:
                time_since_last = (datetime.now() - self.last_trade_times[symbol]).total_seconds()
                if time_since_last < self.config["cooldown_seconds"]:
                    print(f"⏳ {symbol} in cooldown ({time_since_last:.0f}s)")
                    return

            # Check max positions
            if len(self.open_positions) >= self.config["max_open_positions"]:
                print(f"🔒 Max positions reached ({len(self.open_positions)}/{self.config['max_open_positions']})")
                return

            # Signal looks good - publish for risk evaluation
            print(f"✅ {symbol} {action} signal approved (strength: {strength:.1%})")
            self.stats["signals_approved"] += 1

            # In a real system, this would go to risk manager
            # For now, we'll simulate approval
            self._execute_trade(signal)

        except Exception as e:
            print(f"❌ Signal processing error: {e}")

    def _on_trade_approved(self, event: Dict):
        """Handle trade approval from risk manager"""
        try:
            approval = event["data"]
            signal = approval.get("signal")

            if approval.get("approved"):
                self._execute_trade(signal)
        except Exception as e:
            print(f"❌ Trade approval error: {e}")

    def _on_trade_rejected(self, event: Dict):
        """Handle trade rejection from risk manager"""
        try:
            rejection = event["data"]
            self.stats["trades_rejected"] += 1

            signal = rejection.get("signal")
            reasons = rejection.get("reasons", [])

            print(f"❌ Trade rejected: {signal.get('symbol')} - {', '.join(reasons)}")
        except Exception as e:
            print(f"❌ Trade rejection handling error: {e}")

    def _execute_trade(self, signal: Dict):
        """
        Execute a trade (paper trading)

        Args:
            signal: Trading signal dictionary
        """
        try:
            symbol = signal.get("symbol")
            action = signal.get("action")
            price = signal.get("price")
            strength = signal.get("strength", 0)

            # Simulated execution
            trade = {
                "symbol": symbol,
                "action": action,
                "price": price,
                "size": 1.0,  # Simplified - would calculate based on risk
                "timestamp": datetime.now().isoformat(),
                "signal_strength": strength,
                "status": "executed"
            }

            # Update stats
            self.stats["trades_executed"] += 1
            self.stats["last_trade"] = trade
            self.last_trade_times[symbol] = datetime.now()

            # Track open position
            if action == "BUY":
                self.open_positions[symbol] = {
                    "entry_price": price,
                    "size": trade["size"],
                    "entry_time": trade["timestamp"]
                }
                self.stats["open_positions"] = len(self.open_positions)

            elif action == "SELL" and symbol in self.open_positions:
                # Close position
                position = self.open_positions[symbol]
                pnl = (price - position["entry_price"]) * position["size"]

                self.stats["total_pnl"] += pnl
                if pnl > 0:
                    self.stats["win_count"] += 1
                else:
                    self.stats["loss_count"] += 1

                del self.open_positions[symbol]
                self.stats["open_positions"] = len(self.open_positions)

                # Publish trade executed event
                event_bus.publish("TRADE_EXECUTED", {
                    "symbol": symbol,
                    "action": action,
                    "price": price,
                    "pnl": pnl,
                    "timestamp": trade["timestamp"]
                })

                print(f"💰 {symbol} trade executed: {action} @ ${price:.2f} | "
                      f"PnL: ${pnl:.2f}")
            else:
                print(f"📝 {symbol} trade logged: {action} @ ${price:.2f}")

        except Exception as e:
            print(f"❌ Trade execution error: {e}")

    def _check_positions(self):
        """Check and update open positions"""
        try:
            # In a real system, this would check for stop losses, take profits, etc.
            # For now, just update the count
            self.stats["open_positions"] = len(self.open_positions)

        except Exception as e:
            print(f"❌ Position check error: {e}")

    def _cleanup(self):
        """Cleanup when stopping"""
        # Unsubscribe from events
        event_bus.unsubscribe("TRADING_SIGNAL", self._on_trading_signal)
        event_bus.unsubscribe("TRADE_APPROVED", self._on_trade_approved)
        event_bus.unsubscribe("TRADE_REJECTED", self._on_trade_rejected)

        print("🛑 Trading Bot Service stopped")

    def enable_trading(self):
        """Enable live trading (paper trading)"""
        self.config["enabled"] = True
        self.stats["bot_state"] = "active"
        print("✅ Trading Bot ENABLED")
        return {"success": True, "message": "Trading enabled"}

    def disable_trading(self):
        """Disable live trading"""
        self.config["enabled"] = False
        self.stats["bot_state"] = "monitoring"
        print("⏸️  Trading Bot DISABLED")
        return {"success": True, "message": "Trading disabled"}

    def get_open_positions(self) -> Dict[str, Dict]:
        """Get all open positions"""
        return self.open_positions.copy()

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Manually close a position

        Args:
            symbol: Symbol to close

        Returns:
            Result dictionary
        """
        if symbol not in self.open_positions:
            return {"success": False, "message": f"No open position for {symbol}"}

        # In a real system, would execute market order
        position = self.open_positions[symbol]
        del self.open_positions[symbol]

        print(f"📤 Manually closed {symbol} position")
        return {
            "success": True,
            "message": f"Closed {symbol} position",
            "position": position
        }
