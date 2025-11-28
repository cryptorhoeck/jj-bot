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

# Import risk manager
try:
    from modules.risk.risk_manager import risk_manager
    RISK_MANAGER_AVAILABLE = True
except ImportError:
    RISK_MANAGER_AVAILABLE = False
    print("⚠️ Risk manager not available - trading without risk limits!")

# Import AI inference service
try:
    from services.ai.inference_service import ai_inference_service
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False
    print("⚠️ AI inference service not available")


class TradingBotService(BaseService):
    """Automated trading bot service"""

    def __init__(self):
        super().__init__(name="trading_bot", auto_start=False)  # Disable auto-start to prevent API startup hang

        # Configuration
        self.config = {
            "enabled": True,  # ENABLED: Bot will execute paper trades based on real analysis
            "paper_trading": True,  # Always use paper trading for safety
            "max_open_positions": 5,
            "risk_per_trade": 0.02,  # 2% risk per trade
            "symbols_to_trade": ["BTC", "ETH", "BNB", "SOL", "ADA"],
            "min_signal_strength": 0.7,  # Minimum signal strength (0-1)
            "cooldown_seconds": 300,  # 5 minutes between trades on same symbol
            # AI Integration settings
            "use_ai_enhancement": True,  # Use AI to enhance trading signals
            "require_ai_confirmation": False,  # Require AI to confirm signals before executing
            "ai_min_confidence": 0.6,  # Minimum AI confidence to proceed
            "ai_weight_in_signal": 0.3  # Weight of AI confidence in final signal strength
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
            "bot_state": "idle",
            # AI-related stats
            "ai_enhanced_signals": 0,
            "ai_confirmed_signals": 0,
            "ai_rejected_signals": 0,
            "last_ai_analysis": None
        }

        # Internal state
        self.open_positions = {}
        self.last_trade_times = {}
        self.current_prices = {}  # Cache of real-time market prices

        # Subscribe to trading signals and approvals
        event_bus.subscribe("TRADING_SIGNAL", self._on_trading_signal)
        event_bus.subscribe("TRADE_APPROVED", self._on_trade_approved)
        event_bus.subscribe("TRADE_REJECTED", self._on_trade_rejected)
        event_bus.subscribe("PRICE_UPDATE", self._on_price_update)

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

    def _on_price_update(self, event: Dict):
        """Handle real-time price updates from market feed"""
        try:
            price_data = event["data"]
            symbol = price_data.get("symbol")
            price = price_data.get("price")

            if symbol and price:
                self.current_prices[symbol] = {
                    "price": price,
                    "change_24h": price_data.get("change_24h", 0),
                    "timestamp": price_data.get("timestamp"),
                    "volume_24h": price_data.get("volume_24h", 0)
                }
        except Exception as e:
            print(f"❌ Price update error: {e}")

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

            # AI Enhancement (if enabled and available)
            final_signal = signal.copy()
            ai_analysis = None

            if self.config["use_ai_enhancement"] and AI_SERVICE_AVAILABLE:
                try:
                    enhanced = ai_inference_service.enhance_signal(signal)
                    if enhanced:
                        self.stats["ai_enhanced_signals"] += 1
                        self.stats["last_ai_analysis"] = {
                            "timestamp": datetime.now().isoformat(),
                            "symbol": symbol,
                            "original_action": action,
                            "enhanced_action": enhanced.enhanced_action,
                            "ai_confidence": enhanced.ai_confidence,
                            "recommendation": enhanced.recommendation,
                            "reasoning": enhanced.reasoning
                        }

                        # Check AI confirmation if required
                        if self.config["require_ai_confirmation"]:
                            if enhanced.recommendation != "execute":
                                print(f"🤖 AI rejected {symbol} signal: {enhanced.reasoning}")
                                self.stats["ai_rejected_signals"] += 1
                                return

                            if enhanced.ai_confidence < self.config["ai_min_confidence"]:
                                print(f"🤖 AI confidence too low for {symbol}: {enhanced.ai_confidence:.1%}")
                                self.stats["ai_rejected_signals"] += 1
                                return

                        # Apply AI weight to signal strength
                        if enhanced.ai_confidence > 0:
                            ai_weight = self.config["ai_weight_in_signal"]
                            combined_strength = (
                                strength * (1 - ai_weight) +
                                enhanced.ai_confidence * ai_weight
                            )
                            final_signal["strength"] = combined_strength
                            final_signal["ai_enhanced"] = True
                            final_signal["ai_confidence"] = enhanced.ai_confidence
                            final_signal["ai_reasoning"] = enhanced.reasoning

                            self.stats["ai_confirmed_signals"] += 1
                            print(f"🤖 AI enhanced {symbol}: strength {strength:.1%} -> {combined_strength:.1%}")

                        ai_analysis = enhanced.to_dict()

                except Exception as ai_error:
                    print(f"⚠️  AI enhancement failed for {symbol}: {ai_error}")
                    # Continue without AI if it fails

            # Risk management checks
            if RISK_MANAGER_AVAILABLE:
                # Get current equity and drawdown (simplified - would query from DB)
                current_equity = 10000 + self.stats.get("total_pnl", 0)
                current_drawdown = 0  # Would calculate from trade history

                # Get recent trades for circuit breaker check
                recent_trades = []  # Would load from database

                # Check if we can trade
                risk_check = risk_manager.check_can_trade(
                    current_equity=current_equity,
                    current_drawdown=current_drawdown,
                    open_positions_count=len(self.open_positions),
                    recent_trades=recent_trades
                )

                if not risk_check["can_trade"]:
                    print(f"🛑 Risk check failed: {risk_check['reason']}")
                    self.stats["trades_rejected"] += 1
                    return

            # Signal looks good - publish for risk evaluation
            final_strength = final_signal.get("strength", strength)
            ai_note = " (AI enhanced)" if final_signal.get("ai_enhanced") else ""
            print(f"✅ {symbol} {action} signal approved (strength: {final_strength:.1%}){ai_note}")
            self.stats["signals_approved"] += 1

            # Execute trade with risk-based position sizing
            self._execute_trade(final_signal)

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
        Execute a trade (paper trading) using real market prices

        Args:
            signal: Trading signal dictionary
        """
        try:
            symbol = signal.get("symbol")
            action = signal.get("action")
            strength = signal.get("strength", 0)

            # Get current market price from real-time feed
            if symbol in self.current_prices:
                price = self.current_prices[symbol]["price"]
                print(f"📊 Using real market price for {symbol}: ${price:.2f}")
            else:
                # Fallback to signal price if no market data available yet
                price = signal.get("price")
                print(f"⚠️  No market data for {symbol}, using signal price: ${price:.2f}")

            # Calculate position size based on risk management
            if RISK_MANAGER_AVAILABLE:
                current_equity = 10000 + self.stats.get("total_pnl", 0)
                stop_loss_price = price * 0.98 if action == "BUY" else price * 1.02  # 2% stop loss

                position_calc = risk_manager.calculate_position_size(
                    current_equity=current_equity,
                    entry_price=price,
                    stop_loss_price=stop_loss_price
                )
                trade_size = position_calc["position_size"]
                print(f"💼 Position size: {trade_size} shares (${position_calc['position_value']:.2f})")
            else:
                trade_size = 1.0  # Default size

            # Execute trade
            trade = {
                "symbol": symbol,
                "action": action,
                "price": price,
                "size": trade_size,
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
        event_bus.unsubscribe("PRICE_UPDATE", self._on_price_update)

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
