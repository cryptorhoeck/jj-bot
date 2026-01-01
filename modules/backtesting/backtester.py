"""
Backtesting Engine - Test trading strategies on historical data
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.strategy.strategy_engine import StrategyEngine


class Backtester:
    """
    Backtesting engine for evaluating trading strategies on historical data
    """

    def __init__(self, initial_capital: float = 10000.0):
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital for backtest
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Strategy engine
        self.strategy = StrategyEngine()

        # Backtest results
        self.trades = []
        self.equity_curve = []
        self.positions = {}  # symbol -> position info

        # Performance metrics
        self.metrics = {}

        # Configuration - REALISTIC VALUES for actual trading
        # Commission: 0.2% (Kraken taker: 0.26%, Binance taker: 0.1%)
        # Slippage: 0.5% base (can spike to 2% during volatility)
        self.config = {
            "commission": 0.002,  # 0.2% per trade (realistic taker fee)
            "slippage": 0.005,    # 0.5% slippage (realistic for crypto)
            "position_size": 0.1   # 10% of capital per position
        }

        # Active strategy type
        self.active_strategy = "combined"

    def _configure_strategy(self, strategy: str):
        """
        Configure strategy engine based on selected strategy type

        Args:
            strategy: Strategy name from STRATEGY_METADATA
        """
        # Default parameters
        if strategy == "rsi_strategy":
            self.strategy.rsi_oversold = 30
            self.strategy.rsi_overbought = 70
            self.active_strategy = "rsi"
        elif strategy == "sma_crossover":
            self.strategy.sma_fast = 20
            self.strategy.sma_slow = 50
            self.active_strategy = "sma"
        elif strategy == "macd":
            self.active_strategy = "macd"
        elif strategy == "bollinger_bands":
            self.active_strategy = "bollinger"
        elif strategy == "stochastic":
            self.active_strategy = "stochastic"
        elif strategy == "ichimoku":
            self.active_strategy = "ichimoku"
        elif strategy == "adx":
            self.active_strategy = "adx"
        elif strategy == "supertrend":
            self.active_strategy = "supertrend"
        elif strategy == "combined_indicators":
            self.active_strategy = "combined"
        else:
            # Default to RSI
            self.active_strategy = "rsi"

    def _generate_strategy_signal(self, symbol: str, price: float) -> Optional[Dict]:
        """
        Generate trading signal based on active strategy

        Args:
            symbol: Symbol to analyze
            price: Current price

        Returns:
            Signal dictionary with action, reason, and strength
        """
        # Use StrategyEngine's analysis but filter based on active strategy
        self.strategy.analyze_symbol(symbol)
        full_signal = self.strategy.current_signals.get(symbol)

        if not full_signal:
            return None

        # For strategy-specific approaches, we'll use the full combined signal
        # but adjust the naming/reasoning based on the active strategy
        # In a full implementation, you'd have separate strategy classes

        # Return the signal as-is for now (all strategies use combined indicators)
        return full_signal

    def load_historical_data(self, symbol: str, data: List[Dict]) -> bool:
        """
        Load historical price data for a symbol

        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            data: List of price dictionaries with keys: price, timestamp, volume

        Returns:
            True if loaded successfully
        """
        try:
            if not data:
                return False

            # Add to strategy engine's price history
            if symbol not in self.strategy.price_history:
                self.strategy.price_history[symbol] = []

            self.strategy.price_history[symbol] = data
            return True

        except Exception as e:
            print(f"❌ Error loading data for {symbol}: {e}")
            return False

    def run_backtest(self, symbol: str, strategy: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Run backtest on historical data

        Args:
            symbol: Cryptocurrency symbol
            strategy: Strategy to use (e.g., 'rsi_strategy', 'sma_crossover', etc.)
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Dictionary of backtest results
        """
        print(f"🔄 Running backtest for {symbol} with strategy: {strategy or 'combined'}...")

        # Configure strategy parameters based on selected strategy
        self._configure_strategy(strategy or "rsi_strategy")

        if symbol not in self.strategy.price_history:
            return {"error": f"No historical data for {symbol}"}

        history = self.strategy.price_history[symbol]

        # Filter by date range if provided
        if start_date or end_date:
            history = self._filter_by_date(history, start_date, end_date)

        if len(history) < self.strategy.sma_slow:
            return {"error": "Insufficient historical data"}

        # Reset state
        self.trades = []
        self.equity_curve = []
        self.current_capital = self.initial_capital
        self.positions = {}

        # Initialize equity curve
        self.equity_curve.append({
            "timestamp": history[0]["timestamp"],
            "equity": self.current_capital,
            "cash": self.current_capital,
            "positions_value": 0
        })

        # Simulate trading through historical data
        for i in range(self.strategy.sma_slow, len(history)):
            # Get current price point
            current = history[i]
            timestamp = current["timestamp"]
            price = current["price"]

            # Generate signal using active strategy
            signal = self._generate_strategy_signal(symbol, price)

            if signal:
                # Execute trade based on signal
                if signal["action"] == "BUY" and symbol not in self.positions:
                    self._execute_buy(symbol, price, timestamp, signal)
                elif signal["action"] == "SELL" and symbol in self.positions:
                    self._execute_sell(symbol, price, timestamp, signal)

            # Update equity curve
            positions_value = self._calculate_positions_value(price if symbol in self.positions else 0)
            equity = self.current_capital + positions_value

            self.equity_curve.append({
                "timestamp": timestamp,
                "equity": equity,
                "cash": self.current_capital,
                "positions_value": positions_value
            })

        # Close any open positions at end
        if symbol in self.positions:
            final_price = history[-1]["price"]
            self._execute_sell(symbol, final_price, history[-1]["timestamp"],
                             {"reason": ["End of backtest"]})

        # Calculate performance metrics
        self.metrics = self._calculate_metrics()

        print(f"[OK] Backtest complete: {len(self.trades)} trades executed")

        return {
            "symbol": symbol,
            "start_date": history[0]["timestamp"],
            "end_date": history[-1]["timestamp"],
            "initial_capital": self.initial_capital,
            "final_capital": self.equity_curve[-1]["equity"],
            "total_return": ((self.equity_curve[-1]["equity"] / self.initial_capital) - 1) * 100,
            "total_trades": len(self.trades),
            "metrics": self.metrics,
            "trades": self.trades,
            "equity_curve": self.equity_curve
        }

    def _execute_buy(self, symbol: str, price: float, timestamp: str, signal: Dict):
        """Execute a buy order in backtest"""
        # Calculate position size
        position_value = self.current_capital * self.config["position_size"]
        price_with_slippage = price * (1 + self.config["slippage"])
        quantity = position_value / price_with_slippage
        commission = position_value * self.config["commission"]

        # Check if we have enough capital
        total_cost = position_value + commission
        if total_cost > self.current_capital:
            return

        # Open position
        self.positions[symbol] = {
            "quantity": quantity,
            "entry_price": price_with_slippage,
            "entry_time": timestamp,
            "entry_signal": signal
        }

        # Update capital
        self.current_capital -= total_cost

        # Record trade
        self.trades.append({
            "symbol": symbol,
            "action": "BUY",
            "price": price_with_slippage,
            "quantity": quantity,
            "timestamp": timestamp,
            "commission": commission,
            "reason": signal.get("reason", [])
        })

    def _execute_sell(self, symbol: str, price: float, timestamp: str, signal: Dict):
        """Execute a sell order in backtest"""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        price_with_slippage = price * (1 - self.config["slippage"])
        quantity = position["quantity"]
        proceeds = quantity * price_with_slippage
        commission = proceeds * self.config["commission"]

        # Calculate P&L
        entry_value = quantity * position["entry_price"]
        pnl = proceeds - entry_value - commission
        pnl_percent = (pnl / entry_value) * 100

        # Update capital
        self.current_capital += proceeds - commission

        # Record trade
        self.trades.append({
            "symbol": symbol,
            "action": "SELL",
            "price": price_with_slippage,
            "quantity": quantity,
            "timestamp": timestamp,
            "commission": commission,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "hold_time": self._calculate_hold_time(position["entry_time"], timestamp),
            "reason": signal.get("reason", [])
        })

        # Close position
        del self.positions[symbol]

    def _calculate_positions_value(self, current_price: float) -> float:
        """Calculate current value of all open positions"""
        total_value = 0
        for symbol, position in self.positions.items():
            total_value += position["quantity"] * current_price
        return total_value

    def _calculate_hold_time(self, entry_time: str, exit_time: str) -> str:
        """Calculate time held in position"""
        try:
            entry = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            exit = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            delta = exit - entry
            hours = delta.total_seconds() / 3600
            return f"{hours:.1f}h"
        except:
            return "Unknown"

    def _filter_by_date(self, history: List[Dict], start_date: Optional[str],
                        end_date: Optional[str]) -> List[Dict]:
        """Filter historical data by date range"""
        filtered = history

        if start_date:
            filtered = [h for h in filtered
                       if h["timestamp"] >= start_date]

        if end_date:
            filtered = [h for h in filtered
                       if h["timestamp"] <= end_date]

        return filtered

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not self.trades:
            return {
                "win_rate": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "total_wins": 0,
                "total_losses": 0,
                "avg_win": 0,
                "avg_loss": 0
            }

        # Separate winning and losing trades
        completed_trades = [t for t in self.trades if t["action"] == "SELL"]
        winning_trades = [t for t in completed_trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in completed_trades if t.get("pnl", 0) <= 0]

        # Basic metrics
        total_wins = len(winning_trades)
        total_losses = len(losing_trades)
        win_rate = (total_wins / len(completed_trades) * 100) if completed_trades else 0

        # Profit metrics
        total_profit = sum(t.get("pnl", 0) for t in winning_trades)
        total_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

        avg_win = (total_profit / total_wins) if total_wins > 0 else 0
        avg_loss = (total_loss / total_losses) if total_losses > 0 else 0

        # Drawdown
        max_drawdown = self._calculate_max_drawdown()

        # Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "total_profit": total_profit,
            "total_loss": total_loss
        }

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage"""
        if len(self.equity_curve) < 2:
            return 0

        peak = self.equity_curve[0]["equity"]
        max_dd = 0

        for point in self.equity_curve:
            equity = point["equity"]
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if len(self.equity_curve) < 2:
            return 0

        # Calculate returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i-1]["equity"]
            curr_equity = self.equity_curve[i]["equity"]
            ret = (curr_equity - prev_equity) / prev_equity
            returns.append(ret)

        if not returns:
            return 0

        # Sharpe ratio = (mean return - risk free rate) / std dev of returns
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        sharpe = (mean_return - risk_free_rate) / std_return

        # Annualize (assuming daily data)
        sharpe_annualized = sharpe * np.sqrt(365)

        return sharpe_annualized

    def get_trade_summary(self) -> str:
        """Get a formatted summary of backtest results"""
        if not self.metrics:
            return "No backtest results available"

        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║              BACKTEST RESULTS SUMMARY                         ║
╠══════════════════════════════════════════════════════════════╣
║ Initial Capital:     ${self.initial_capital:,.2f}
║ Final Equity:        ${self.equity_curve[-1]["equity"]:,.2f}
║ Total Return:        {((self.equity_curve[-1]["equity"] / self.initial_capital) - 1) * 100:.2f}%
║
║ Total Trades:        {len(self.trades)}
║ Winning Trades:      {self.metrics['total_wins']}
║ Losing Trades:       {self.metrics['total_losses']}
║ Win Rate:            {self.metrics['win_rate']:.2f}%
║
║ Total Profit:        ${self.metrics['total_profit']:,.2f}
║ Total Loss:          ${self.metrics['total_loss']:,.2f}
║ Profit Factor:       {self.metrics['profit_factor']:.2f}
║
║ Average Win:         ${self.metrics['avg_win']:,.2f}
║ Average Loss:        ${self.metrics['avg_loss']:,.2f}
║
║ Max Drawdown:        {self.metrics['max_drawdown']:.2f}%
║ Sharpe Ratio:        {self.metrics['sharpe_ratio']:.2f}
╚══════════════════════════════════════════════════════════════╝
"""
        return summary
