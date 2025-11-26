"""
Trading Environment for Reinforcement Learning
OpenAI Gym compatible environment for training RL agents
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import logging


logger = logging.getLogger(__name__)


class Action(Enum):
    """Trading actions"""
    HOLD = 0
    BUY = 1
    SELL = 2
    CLOSE = 3  # Close current position


@dataclass
class Position:
    """Current trading position"""
    side: str  # "long", "short", or "flat"
    entry_price: float = 0.0
    size: float = 0.0
    unrealized_pnl: float = 0.0
    entry_time: int = 0


@dataclass
class TradeResult:
    """Result of a completed trade"""
    entry_price: float
    exit_price: float
    side: str
    size: float
    pnl: float
    pnl_pct: float
    holding_period: int
    timestamp: int


class TradingEnvironment:
    """
    Reinforcement Learning Environment for Trading

    State Space:
    - Price features (returns, volatility, momentum)
    - Technical indicators (RSI, MACD, BB)
    - Position info (side, unrealized P&L, holding time)
    - Account info (equity, drawdown)

    Action Space:
    - 0: Hold
    - 1: Buy/Long
    - 2: Sell/Short
    - 3: Close position

    Reward:
    - Realized P&L on trade close
    - Risk-adjusted returns (Sharpe-like)
    - Penalties for excessive trading
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        max_position_size: float = 0.1,  # 10% of equity
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.0005,  # 0.05%
        lookback_window: int = 50,
        max_steps: int = 10000,
        reward_scaling: float = 1.0,
        risk_penalty: float = 0.1,
        trade_penalty: float = 0.0001,
    ):
        self.initial_balance = initial_balance
        self.max_position_size = max_position_size
        self.commission = commission
        self.slippage = slippage
        self.lookback_window = lookback_window
        self.max_steps = max_steps
        self.reward_scaling = reward_scaling
        self.risk_penalty = risk_penalty
        self.trade_penalty = trade_penalty

        # State dimensions
        self.n_features = 20  # Price/indicator features
        self.n_position_features = 4  # Position state
        self.n_account_features = 3  # Account state

        self.observation_space_dim = (
            self.lookback_window * self.n_features +
            self.n_position_features +
            self.n_account_features
        )
        self.action_space_dim = 4  # HOLD, BUY, SELL, CLOSE

        self.reset()

    def reset(self, price_data: Optional[np.ndarray] = None) -> np.ndarray:
        """Reset environment to initial state"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.peak_equity = self.initial_balance

        self.position = Position(side="flat")
        self.trade_history: List[TradeResult] = []

        self.current_step = 0
        self.done = False

        # Price data: shape (n_steps, n_features)
        if price_data is not None:
            self.price_data = price_data
        else:
            # Generate dummy data for testing
            self.price_data = self._generate_dummy_data()

        self.prices = self.price_data[:, 0]  # First column is close price
        self.current_price = self.prices[self.lookback_window]

        # Performance tracking
        self.returns_history = deque(maxlen=100)
        self.equity_history = [self.initial_balance]

        return self._get_observation()

    def _generate_dummy_data(self) -> np.ndarray:
        """Generate dummy price data for testing"""
        n_steps = self.max_steps + self.lookback_window
        n_features = self.n_features

        # Random walk prices
        returns = np.random.randn(n_steps) * 0.02
        prices = 100 * np.exp(np.cumsum(returns))

        # Create feature matrix
        data = np.zeros((n_steps, n_features))
        data[:, 0] = prices  # Close price

        # Simple derived features
        for i in range(1, n_features):
            lag = min(i, 20)
            data[lag:, i] = np.diff(prices[:n_steps - lag + 1], n=1) / prices[:-lag]

        return data

    def _get_observation(self) -> np.ndarray:
        """Build observation vector from current state"""
        obs = []

        # Price/indicator features (lookback window)
        start_idx = max(0, self.current_step)
        end_idx = self.current_step + self.lookback_window

        if end_idx > len(self.price_data):
            end_idx = len(self.price_data)
            start_idx = end_idx - self.lookback_window

        window_data = self.price_data[start_idx:end_idx]

        # Normalize price features
        price_mean = np.mean(window_data[:, 0])
        price_std = np.std(window_data[:, 0]) + 1e-8

        normalized_prices = (window_data[:, 0] - price_mean) / price_std
        obs.extend(normalized_prices.flatten())

        # Add other features (already returns/normalized)
        for i in range(1, min(self.n_features, window_data.shape[1])):
            feature = window_data[:, i]
            feature = np.clip(feature, -5, 5)  # Clip extreme values
            obs.extend(feature.flatten())

        # Pad if needed
        while len(obs) < self.lookback_window * self.n_features:
            obs.append(0.0)

        # Position features
        position_encoding = {
            "flat": 0.0,
            "long": 1.0,
            "short": -1.0
        }
        obs.append(position_encoding.get(self.position.side, 0.0))

        # Unrealized P&L (normalized)
        unrealized_pnl_pct = self.position.unrealized_pnl / self.initial_balance
        obs.append(np.clip(unrealized_pnl_pct, -1, 1))

        # Holding time (normalized)
        holding_time = (self.current_step - self.position.entry_time) / 100
        obs.append(np.clip(holding_time, 0, 1))

        # Position size (normalized)
        obs.append(self.position.size / self.initial_balance if self.initial_balance else 0)

        # Account features
        equity_change = (self.equity - self.initial_balance) / self.initial_balance
        obs.append(np.clip(equity_change, -1, 1))

        drawdown = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity else 0
        obs.append(np.clip(drawdown, 0, 1))

        # Recent return volatility
        if len(self.returns_history) > 0:
            recent_vol = np.std(list(self.returns_history))
            obs.append(np.clip(recent_vol * 10, 0, 1))
        else:
            obs.append(0.0)

        return np.array(obs, dtype=np.float32)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute action and return (observation, reward, done, info)
        """
        if self.done:
            return self._get_observation(), 0.0, True, {}

        self.current_step += 1
        prev_equity = self.equity

        # Get current price
        price_idx = min(self.current_step + self.lookback_window, len(self.prices) - 1)
        self.current_price = self.prices[price_idx]

        # Execute action
        reward = 0.0
        trade_executed = False

        action_enum = Action(action)

        if action_enum == Action.BUY:
            if self.position.side == "flat":
                # Open long position
                self._open_position("long")
                trade_executed = True
            elif self.position.side == "short":
                # Close short, open long
                reward += self._close_position()
                self._open_position("long")
                trade_executed = True

        elif action_enum == Action.SELL:
            if self.position.side == "flat":
                # Open short position
                self._open_position("short")
                trade_executed = True
            elif self.position.side == "long":
                # Close long, open short
                reward += self._close_position()
                self._open_position("short")
                trade_executed = True

        elif action_enum == Action.CLOSE:
            if self.position.side != "flat":
                reward += self._close_position()
                trade_executed = True

        # Update unrealized P&L
        self._update_position_pnl()

        # Update equity
        self.equity = self.balance + self.position.unrealized_pnl
        self.peak_equity = max(self.peak_equity, self.equity)

        # Calculate step return
        step_return = (self.equity - prev_equity) / prev_equity if prev_equity else 0
        self.returns_history.append(step_return)
        self.equity_history.append(self.equity)

        # Calculate reward
        reward += self._calculate_reward(step_return, trade_executed)

        # Check termination conditions
        self.done = self._check_done()

        info = {
            "equity": self.equity,
            "balance": self.balance,
            "position": self.position.side,
            "unrealized_pnl": self.position.unrealized_pnl,
            "n_trades": len(self.trade_history),
            "step": self.current_step,
        }

        return self._get_observation(), reward, self.done, info

    def _open_position(self, side: str):
        """Open a new position"""
        # Calculate position size
        position_value = self.equity * self.max_position_size

        # Apply slippage
        if side == "long":
            entry_price = self.current_price * (1 + self.slippage)
        else:
            entry_price = self.current_price * (1 - self.slippage)

        # Deduct commission
        commission_cost = position_value * self.commission
        self.balance -= commission_cost

        self.position = Position(
            side=side,
            entry_price=entry_price,
            size=position_value,
            unrealized_pnl=0.0,
            entry_time=self.current_step
        )

    def _close_position(self) -> float:
        """Close current position and return realized P&L"""
        if self.position.side == "flat":
            return 0.0

        # Calculate exit price with slippage
        if self.position.side == "long":
            exit_price = self.current_price * (1 - self.slippage)
            pnl = (exit_price - self.position.entry_price) / self.position.entry_price
        else:
            exit_price = self.current_price * (1 + self.slippage)
            pnl = (self.position.entry_price - exit_price) / self.position.entry_price

        realized_pnl = pnl * self.position.size

        # Deduct commission
        commission_cost = self.position.size * self.commission
        realized_pnl -= commission_cost

        # Update balance
        self.balance += realized_pnl

        # Record trade
        trade = TradeResult(
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            side=self.position.side,
            size=self.position.size,
            pnl=realized_pnl,
            pnl_pct=pnl * 100,
            holding_period=self.current_step - self.position.entry_time,
            timestamp=self.current_step
        )
        self.trade_history.append(trade)

        # Reset position
        self.position = Position(side="flat")

        return realized_pnl

    def _update_position_pnl(self):
        """Update unrealized P&L for current position"""
        if self.position.side == "flat":
            self.position.unrealized_pnl = 0.0
            return

        if self.position.side == "long":
            pnl = (self.current_price - self.position.entry_price) / self.position.entry_price
        else:
            pnl = (self.position.entry_price - self.current_price) / self.position.entry_price

        self.position.unrealized_pnl = pnl * self.position.size

    def _calculate_reward(self, step_return: float, trade_executed: bool) -> float:
        """
        Calculate reward for the current step

        Components:
        1. P&L reward (scaled)
        2. Risk penalty (drawdown, volatility)
        3. Trade penalty (discourage overtrading)
        """
        reward = 0.0

        # P&L component
        reward += step_return * self.reward_scaling * 100

        # Risk penalty
        if len(self.returns_history) > 10:
            volatility = np.std(list(self.returns_history))
            drawdown = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity else 0

            # Penalize high volatility and drawdown
            reward -= volatility * self.risk_penalty
            reward -= drawdown * self.risk_penalty

        # Trade penalty (discourage churning)
        if trade_executed:
            reward -= self.trade_penalty

        return reward

    def _check_done(self) -> bool:
        """Check if episode should terminate"""
        # Max steps reached
        if self.current_step >= self.max_steps - 1:
            return True

        # Out of data
        if self.current_step + self.lookback_window >= len(self.prices) - 1:
            return True

        # Bankruptcy
        if self.equity <= self.initial_balance * 0.5:  # Lost 50%
            return True

        return False

    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics for the episode"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
            }

        wins = [t for t in self.trade_history if t.pnl > 0]
        losses = [t for t in self.trade_history if t.pnl < 0]

        total_pnl = sum(t.pnl for t in self.trade_history)
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 1

        # Calculate Sharpe ratio
        if len(self.returns_history) > 1:
            returns = np.array(list(self.returns_history))
            sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Calculate max drawdown
        equity_array = np.array(self.equity_history)
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak
        max_drawdown = np.max(drawdown)

        return {
            "total_trades": len(self.trade_history),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / len(self.trade_history) if self.trade_history else 0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(self.trade_history),
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "profit_factor": gross_profit / gross_loss if gross_loss else 0,
            "final_equity": self.equity,
            "return_pct": (self.equity - self.initial_balance) / self.initial_balance * 100,
        }

    def render(self, mode: str = "human"):
        """Render current state (for debugging)"""
        print(f"\n=== Step {self.current_step} ===")
        print(f"Price: ${self.current_price:.2f}")
        print(f"Position: {self.position.side}")
        print(f"Unrealized P&L: ${self.position.unrealized_pnl:.2f}")
        print(f"Balance: ${self.balance:.2f}")
        print(f"Equity: ${self.equity:.2f}")
        print(f"Trades: {len(self.trade_history)}")
