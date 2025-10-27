"""
Risk Manager Module for JJ-Bot
Manages position sizing, risk limits, and trade approval
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.base import BaseModule
from modules.event_bus import event_bus

class RiskManager(BaseModule):
    """Risk management and trade approval system"""
    
    def __init__(self, initial_balance: float = 10000.0):
        super().__init__("RiskManager")
        
        # Account settings
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.available_balance = initial_balance
        
        # Risk parameters
        self.max_risk_per_trade = 0.02  # 2% per trade
        self.max_daily_loss = 0.05  # 5% daily loss limit
        self.max_positions = 5  # Maximum concurrent positions
        self.min_win_rate = 0.3  # Minimum acceptable win rate
        
        # Position tracking
        self.open_positions = {}
        self.closed_trades = []
        self.daily_pnl = 0
        self.daily_trades = 0
        
        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        
        # Risk state
        self.risk_state = "NORMAL"  # NORMAL, CAUTION, LOCKED
        self.last_reset = datetime.now()
        
    def start(self) -> bool:
        """Start the risk manager"""
        try:
            self.status = "RUNNING"
            self.start_time = datetime.now().isoformat()
            
            # Subscribe to trading signals
            event_bus.subscribe("TRADING_SIGNAL", self.evaluate_signal)
            
            self.logger.info("Risk manager started")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the risk manager"""
        try:
            self.status = "STOPPED"
            self.logger.info("Risk manager stopped")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to stop: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check module health"""
        return {
            "healthy": self.status == "RUNNING" and self.risk_state != "LOCKED",
            "status": self.status,
            "risk_state": self.risk_state,
            "balance": self.current_balance,
            "open_positions": len(self.open_positions),
            "daily_pnl": self.daily_pnl,
            "win_rate": self.calculate_win_rate()
        }
    
    def evaluate_signal(self, event: Dict):
        """Evaluate a trading signal for risk approval"""
        signal = event["data"]
        
        # Create risk evaluation
        evaluation = {
            "signal": signal,
            "timestamp": datetime.now().isoformat(),
            "approved": False,
            "reasons": [],
            "position_size": 0,
            "risk_amount": 0
        }
        
        # Check if risk system is locked
        if self.risk_state == "LOCKED":
            evaluation["reasons"].append("Risk system locked due to daily loss limit")
            self.publish_evaluation(evaluation)
            return
        
        # Check daily loss limit
        if self.check_daily_loss_limit():
            evaluation["reasons"].append("Daily loss limit reached")
            self.lock_trading()
            self.publish_evaluation(evaluation)
            return
        
        # Check maximum positions
        if len(self.open_positions) >= self.max_positions:
            evaluation["reasons"].append(f"Maximum positions ({self.max_positions}) reached")
            self.publish_evaluation(evaluation)
            return
        
        # Check if we already have position in this symbol
        if signal["symbol"] in self.open_positions:
            evaluation["reasons"].append("Already have position in this symbol")
            self.publish_evaluation(evaluation)
            return
        
        # Check signal strength
        min_strength = 0.6
        if signal.get("strength", 0) < min_strength:
            evaluation["reasons"].append(f"Signal strength too low ({signal.get('strength', 0):.1%} < {min_strength:.1%})")
            self.publish_evaluation(evaluation)
            return
        
        # Calculate position size
        position_size = self.calculate_position_size(signal)
        
        if position_size == 0:
            evaluation["reasons"].append("Position size calculation failed")
            self.publish_evaluation(evaluation)
            return
        
        # Calculate risk amount
        risk_amount = position_size * signal["price"] * self.max_risk_per_trade
        
        # Check if risk amount exceeds limits
        if risk_amount > self.available_balance * self.max_risk_per_trade:
            evaluation["reasons"].append("Risk amount exceeds per-trade limit")
            self.publish_evaluation(evaluation)
            return
        
        # Check win rate (after 20 trades)
        if self.total_trades >= 20:
            win_rate = self.calculate_win_rate()
            if win_rate < self.min_win_rate:
                evaluation["reasons"].append(f"Win rate too low ({win_rate:.1%} < {self.min_win_rate:.1%})")
                evaluation["approved"] = False
                self.publish_evaluation(evaluation)
                return
        
        # APPROVED
        evaluation["approved"] = True
        evaluation["position_size"] = position_size
        evaluation["risk_amount"] = risk_amount
        evaluation["reasons"].append("All risk checks passed")
        
        # Update position tracking
        if signal["action"] == "BUY":
            self.open_position(signal, position_size, risk_amount)
        
        self.publish_evaluation(evaluation)
    
    def calculate_position_size(self, signal: Dict) -> float:
        """Calculate appropriate position size using Kelly Criterion"""
        # Simplified Kelly Criterion
        # f = (p * b - q) / b
        # where: p = win probability, q = loss probability, b = win/loss ratio
        
        win_rate = max(self.calculate_win_rate(), 0.5)  # Use 50% if no history
        avg_win = self.calculate_avg_win() or 100
        avg_loss = abs(self.calculate_avg_loss()) or 50
        
        if avg_loss == 0:
            return 0
        
        win_loss_ratio = avg_win / avg_loss
        
        # Kelly percentage
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # Apply Kelly with safety factor (use 25% of Kelly)
        kelly_safe = kelly * 0.25
        
        # Ensure within risk limits
        position_pct = min(kelly_safe, self.max_risk_per_trade)
        position_pct = max(position_pct, 0.001)  # Minimum position
        
        # Calculate position size in units
        position_value = self.available_balance * position_pct
        position_size = position_value / signal["price"]
        
        return position_size
    
    def open_position(self, signal: Dict, size: float, risk: float):
        """Record an open position"""
        self.open_positions[signal["symbol"]] = {
            "entry_price": signal["price"],
            "size": size,
            "risk": risk,
            "timestamp": datetime.now().isoformat(),
            "signal": signal
        }
        
        self.available_balance -= (size * signal["price"])
        self.daily_trades += 1
        
        print(f"📈 Position opened: {signal['symbol']} size={size:.4f} risk=${risk:.2f}")
    
    def close_position(self, symbol: str, exit_price: float):
        """Close a position and record P&L"""
        if symbol not in self.open_positions:
            return
        
        position = self.open_positions[symbol]
        pnl = (exit_price - position["entry_price"]) * position["size"]
        
        # Update statistics
        self.total_trades += 1
        self.total_pnl += pnl
        self.daily_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Record closed trade
        self.closed_trades.append({
            "symbol": symbol,
            "entry": position["entry_price"],
            "exit": exit_price,
            "size": position["size"],
            "pnl": pnl,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update balance
        self.current_balance += pnl
        self.available_balance += (position["size"] * exit_price)
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        print(f"📉 Position closed: {symbol} P&L=${pnl:.2f}")
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit exceeded"""
        max_daily_loss_amount = self.initial_balance * self.max_daily_loss
        return self.daily_pnl < -max_daily_loss_amount
    
    def lock_trading(self):
        """Lock trading due to risk limits"""
        self.risk_state = "LOCKED"
        print("🔒 TRADING LOCKED - Daily loss limit reached")
        event_bus.publish("RISK_ALERT", {
            "type": "TRADING_LOCKED",
            "reason": "Daily loss limit reached",
            "daily_pnl": self.daily_pnl
        })
    
    def reset_daily_limits(self):
        """Reset daily limits (call at start of new trading day)"""
        self.daily_pnl = 0
        self.daily_trades = 0
        self.risk_state = "NORMAL"
        self.last_reset = datetime.now()
        print("🔄 Daily limits reset")
    
    def calculate_win_rate(self) -> float:
        """Calculate win rate"""
        if self.total_trades == 0:
            return 0.5  # Default 50%
        return self.winning_trades / self.total_trades
    
    def calculate_avg_win(self) -> float:
        """Calculate average winning trade"""
        if not self.closed_trades:
            return 0
        
        wins = [t["pnl"] for t in self.closed_trades if t["pnl"] > 0]
        return sum(wins) / len(wins) if wins else 0
    
    def calculate_avg_loss(self) -> float:
        """Calculate average losing trade"""
        if not self.closed_trades:
            return 0
        
        losses = [t["pnl"] for t in self.closed_trades if t["pnl"] < 0]
        return sum(losses) / len(losses) if losses else 0
    
    def publish_evaluation(self, evaluation: Dict):
        """Publish risk evaluation result"""
        event_type = "TRADE_APPROVED" if evaluation["approved"] else "TRADE_REJECTED"
        event_bus.publish(event_type, evaluation)
        
        # Log the decision
        status = "✅ APPROVED" if evaluation["approved"] else "❌ REJECTED"
        print(f"{status}: {evaluation['signal']['symbol']} - {evaluation['reasons'][-1]}")
    
    def get_statistics(self) -> Dict:
        """Get risk statistics"""
        return {
            "balance": self.current_balance,
            "available": self.available_balance,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "open_positions": len(self.open_positions),
            "total_trades": self.total_trades,
            "win_rate": self.calculate_win_rate(),
            "risk_state": self.risk_state,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades
        }
