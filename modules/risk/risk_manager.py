"""
Risk Management Module

Implements comprehensive risk controls:
- Position sizing based on account equity and risk per trade
- Max drawdown stops
- Circuit breakers for rapid losses
- Risk limits and exposure management
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import sys
import os

# Add parent to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


@dataclass
class RiskLimits:
    """Risk management configuration"""
    max_risk_per_trade: float = 0.02  # 2% of account per trade
    max_total_exposure: float = 0.20  # 20% of account in open positions
    max_drawdown_pct: float = 0.10  # 10% maximum drawdown before stop
    max_daily_loss: float = 500.0  # Maximum daily loss in dollars
    max_open_positions: int = 5  # Maximum concurrent positions
    position_size_method: str = "fixed_risk"  # or "kelly", "equal_weight"
    min_risk_reward_ratio: float = 1.5  # Minimum R:R for trade entry
    circuit_breaker_loss_count: int = 3  # Consecutive losses to trigger breaker
    circuit_breaker_cooldown_minutes: int = 60  # Minutes to wait after breaker


class RiskManager:
    """
    Manages all risk-related decisions for trading
    """

    def __init__(self, config: Optional[RiskLimits] = None):
        """
        Initialize risk manager

        Args:
            config: Risk limits configuration
        """
        self.config = config or RiskLimits()
        self.circuit_breaker_active = False
        self.circuit_breaker_until: Optional[datetime] = None
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()

    def check_can_trade(
        self,
        current_equity: float,
        current_drawdown: float,
        open_positions_count: int,
        recent_trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if trading is allowed based on current risk state

        Args:
            current_equity: Current account equity
            current_drawdown: Current drawdown amount
            open_positions_count: Number of open positions
            recent_trades: List of recent trades for circuit breaker check

        Returns:
            Dictionary with can_trade flag and reason if blocked
        """
        # Reset daily stats if new day
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date

        # Calculate daily PnL
        today_trades = [
            t for t in recent_trades
            if datetime.fromisoformat(t.get('timestamp', '')).date() == current_date
        ]
        self.daily_pnl = sum(t.get('pnl', 0) for t in today_trades)

        # Check 1: Circuit breaker
        if self.circuit_breaker_active:
            if datetime.now() < self.circuit_breaker_until:
                return {
                    "can_trade": False,
                    "reason": f"Circuit breaker active until {self.circuit_breaker_until.strftime('%H:%M')}",
                    "code": "CIRCUIT_BREAKER"
                }
            else:
                # Reset circuit breaker
                self.circuit_breaker_active = False
                self.circuit_breaker_until = None
                self.consecutive_losses = 0

        # Check 2: Max drawdown
        drawdown_pct = (current_drawdown / current_equity) if current_equity > 0 else 0
        if drawdown_pct >= self.config.max_drawdown_pct:
            return {
                "can_trade": False,
                "reason": f"Max drawdown exceeded: {drawdown_pct*100:.1f}% >= {self.config.max_drawdown_pct*100:.1f}%",
                "code": "MAX_DRAWDOWN"
            }

        # Check 3: Daily loss limit
        if abs(self.daily_pnl) >= self.config.max_daily_loss:
            return {
                "can_trade": False,
                "reason": f"Daily loss limit reached: ${abs(self.daily_pnl):.2f} >= ${self.config.max_daily_loss:.2f}",
                "code": "DAILY_LOSS_LIMIT"
            }

        # Check 4: Max open positions
        if open_positions_count >= self.config.max_open_positions:
            return {
                "can_trade": False,
                "reason": f"Max open positions reached: {open_positions_count} >= {self.config.max_open_positions}",
                "code": "MAX_POSITIONS"
            }

        # Check 5: Consecutive losses (circuit breaker trigger)
        if len(recent_trades) >= self.config.circuit_breaker_loss_count:
            recent_pnls = [t.get('pnl', 0) for t in recent_trades[-self.config.circuit_breaker_loss_count:]]
            if all(pnl < 0 for pnl in recent_pnls):
                self._activate_circuit_breaker()
                return {
                    "can_trade": False,
                    "reason": f"Circuit breaker activated after {self.config.circuit_breaker_loss_count} consecutive losses",
                    "code": "CIRCUIT_BREAKER_TRIGGERED"
                }

        return {
            "can_trade": True,
            "reason": "All risk checks passed",
            "code": "OK"
        }

    def calculate_position_size(
        self,
        current_equity: float,
        entry_price: float,
        stop_loss_price: float,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate appropriate position size based on risk management rules

        Args:
            current_equity: Current account equity
            entry_price: Planned entry price
            stop_loss_price: Stop loss price
            method: Position sizing method (overrides config)

        Returns:
            Dictionary with position size and risk metrics
        """
        method = method or self.config.position_size_method

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            return {
                "position_size": 0,
                "position_value": 0,
                "risk_amount": 0,
                "reason": "Invalid stop loss - risk per share is zero"
            }

        # Maximum risk amount based on account equity
        max_risk_amount = current_equity * self.config.max_risk_per_trade

        if method == "fixed_risk":
            # Risk a fixed percentage of equity
            shares = int(max_risk_amount / risk_per_share)

        elif method == "equal_weight":
            # Equal weight across max positions
            position_value = current_equity / self.config.max_open_positions
            shares = int(position_value / entry_price)

        elif method == "kelly":
            # Simplified Kelly Criterion (requires win rate and avg win/loss)
            # For now, use conservative 0.25 Kelly
            shares = int((max_risk_amount * 0.25) / risk_per_share)

        else:
            shares = int(max_risk_amount / risk_per_share)

        # Calculate actual position metrics
        position_value = shares * entry_price
        actual_risk = shares * risk_per_share
        risk_pct = (actual_risk / current_equity * 100) if current_equity > 0 else 0

        # Check exposure limits
        exposure_pct = (position_value / current_equity * 100) if current_equity > 0 else 0
        if exposure_pct > self.config.max_total_exposure * 100:
            # Scale down position
            max_position_value = current_equity * self.config.max_total_exposure
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
            actual_risk = shares * risk_per_share
            risk_pct = (actual_risk / current_equity * 100) if current_equity > 0 else 0

        return {
            "position_size": shares,
            "position_value": round(position_value, 2),
            "risk_amount": round(actual_risk, 2),
            "risk_pct": round(risk_pct, 2),
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "risk_per_share": round(risk_per_share, 2),
            "method": method
        }

    def validate_trade(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validate if a trade meets risk/reward criteria

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional)

        Returns:
            Dictionary with validation result and metrics
        """
        risk = abs(entry_price - stop_loss)

        if take_profit is None:
            return {
                "is_valid": True,
                "reason": "No take profit specified - manual exit",
                "risk_reward_ratio": None
            }

        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0

        is_valid = risk_reward_ratio >= self.config.min_risk_reward_ratio

        return {
            "is_valid": is_valid,
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "risk": round(risk, 2),
            "reward": round(reward, 2),
            "reason": "Valid R:R ratio" if is_valid else f"R:R {risk_reward_ratio:.2f} < minimum {self.config.min_risk_reward_ratio}"
        }

    def record_trade_result(self, pnl: float):
        """
        Record trade result for circuit breaker tracking

        Args:
            pnl: Trade profit/loss
        """
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self.daily_pnl += pnl

    def _activate_circuit_breaker(self):
        """Activate circuit breaker and set cooldown"""
        self.circuit_breaker_active = True
        self.circuit_breaker_until = datetime.now() + timedelta(
            minutes=self.config.circuit_breaker_cooldown_minutes
        )
        print(f"⚠️ CIRCUIT BREAKER ACTIVATED until {self.circuit_breaker_until.strftime('%H:%M:%S')}")

    def get_risk_status(self, current_equity: float, current_drawdown: float) -> Dict[str, Any]:
        """
        Get current risk management status

        Args:
            current_equity: Current account equity
            current_drawdown: Current drawdown amount

        Returns:
            Risk status dictionary
        """
        drawdown_pct = (current_drawdown / current_equity * 100) if current_equity > 0 else 0

        return {
            "circuit_breaker_active": self.circuit_breaker_active,
            "circuit_breaker_until": self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": round(self.daily_pnl, 2),
            "current_drawdown_pct": round(drawdown_pct, 2),
            "max_drawdown_pct": self.config.max_drawdown_pct * 100,
            "risk_per_trade_pct": self.config.max_risk_per_trade * 100,
            "max_open_positions": self.config.max_open_positions,
            "max_daily_loss": self.config.max_daily_loss,
            "daily_loss_remaining": round(self.config.max_daily_loss - abs(self.daily_pnl), 2)
        }


# Create global risk manager instance
risk_manager = RiskManager()
