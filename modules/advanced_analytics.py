"""
Advanced Analytics Module
Provides sophisticated performance metrics for trading strategies
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    # Returns
    total_return: float
    annualized_return: float
    average_return: float

    # Risk metrics
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Drawdown metrics
    max_drawdown: float
    max_drawdown_duration: int  # days
    current_drawdown: float

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float

    # Other metrics
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    expectancy: float


class AdvancedAnalytics:
    """
    Advanced analytics for trading performance
    Calculates various risk and performance metrics
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize analytics

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_returns(self, equity_curve: pd.Series) -> pd.Series:
        """
        Calculate returns from equity curve

        Args:
            equity_curve: Series of equity values over time

        Returns:
            Series of returns
        """
        return equity_curve.pct_change().fillna(0)

    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe ratio

        Args:
            returns: Series of returns
            periods_per_year: Number of periods per year (252 for daily)

        Returns:
            Sharpe ratio
        """
        if len(returns) < 2 or returns.std() == 0:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / periods_per_year)
        sharpe = np.sqrt(periods_per_year) * (excess_returns.mean() / returns.std())

        return float(sharpe)

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino ratio (focuses on downside volatility)

        Args:
            returns: Series of returns
            periods_per_year: Number of periods per year

        Returns:
            Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        # Downside returns (only negative returns)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / periods_per_year)
        sortino = np.sqrt(periods_per_year) * (
            excess_returns.mean() / downside_returns.std()
        )

        return float(sortino)

    def calculate_max_drawdown(
        self,
        equity_curve: pd.Series
    ) -> Tuple[float, int]:
        """
        Calculate maximum drawdown and duration

        Args:
            equity_curve: Series of equity values

        Returns:
            Tuple of (max_drawdown_pct, duration_in_days)
        """
        if len(equity_curve) < 2:
            return 0.0, 0

        # Calculate running maximum
        running_max = equity_curve.expanding().max()

        # Calculate drawdown
        drawdown = (equity_curve - running_max) / running_max

        # Find maximum drawdown
        max_dd = float(drawdown.min())

        # Calculate drawdown duration
        dd_duration = 0
        current_duration = 0

        for dd in drawdown:
            if dd < 0:
                current_duration += 1
                dd_duration = max(dd_duration, current_duration)
            else:
                current_duration = 0

        return max_dd, dd_duration

    def calculate_calmar_ratio(
        self,
        returns: pd.Series,
        equity_curve: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Calmar ratio (return / max drawdown)

        Args:
            returns: Series of returns
            equity_curve: Series of equity values
            periods_per_year: Number of periods per year

        Returns:
            Calmar ratio
        """
        if len(returns) < 2:
            return 0.0

        # Annualized return
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        periods = len(returns)
        years = periods / periods_per_year
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Max drawdown
        max_dd, _ = self.calculate_max_drawdown(equity_curve)

        if max_dd == 0:
            return 0.0

        calmar = annualized_return / abs(max_dd)
        return float(calmar)

    def calculate_trade_statistics(
        self,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate trade statistics

        Args:
            trades: List of trade dictionaries with 'pnl' field

        Returns:
            Dictionary of trade statistics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'expectancy': 0.0,
            }

        # Extract PnL values
        pnls = [float(trade.get('pnl', 0)) for trade in trades]

        # Separate wins and losses
        wins = [pnl for pnl in pnls if pnl > 0]
        losses = [pnl for pnl in pnls if pnl < 0]

        # Calculate statistics
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Averages
        average_win = np.mean(wins) if wins else 0
        average_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0

        # Expectancy
        expectancy = (win_rate * average_win) + ((1 - win_rate) * average_loss)

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'average_win': float(average_win),
            'average_loss': float(average_loss),
            'largest_win': float(largest_win),
            'largest_loss': float(largest_loss),
            'expectancy': float(expectancy),
        }

    def calculate_all_metrics(
        self,
        equity_curve: pd.Series,
        trades: List[Dict[str, Any]],
        periods_per_year: int = 252
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics

        Args:
            equity_curve: Series of equity values over time
            trades: List of trade dictionaries
            periods_per_year: Number of periods per year

        Returns:
            PerformanceMetrics object with all metrics
        """
        if len(equity_curve) < 2:
            # Return empty metrics
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                average_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0,
                current_drawdown=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                average_win=0.0,
                average_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                expectancy=0.0,
            )

        # Calculate returns
        returns = self.calculate_returns(equity_curve)

        # Return metrics
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        periods = len(returns)
        years = periods / periods_per_year
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        average_return = float(returns.mean())

        # Risk metrics
        volatility = float(returns.std() * np.sqrt(periods_per_year))
        sharpe = self.calculate_sharpe_ratio(returns, periods_per_year)
        sortino = self.calculate_sortino_ratio(returns, periods_per_year)
        calmar = self.calculate_calmar_ratio(returns, equity_curve, periods_per_year)

        # Drawdown metrics
        max_dd, dd_duration = self.calculate_max_drawdown(equity_curve)
        current_dd = float(
            (equity_curve.iloc[-1] - equity_curve.max()) / equity_curve.max()
        )

        # Trade statistics
        trade_stats = self.calculate_trade_statistics(trades)

        return PerformanceMetrics(
            total_return=float(total_return),
            annualized_return=float(annualized_return),
            average_return=average_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration=dd_duration,
            current_drawdown=current_dd,
            total_trades=trade_stats['total_trades'],
            winning_trades=trade_stats['winning_trades'],
            losing_trades=trade_stats['losing_trades'],
            win_rate=trade_stats['win_rate'],
            profit_factor=trade_stats['profit_factor'],
            average_win=trade_stats['average_win'],
            average_loss=trade_stats['average_loss'],
            largest_win=trade_stats['largest_win'],
            largest_loss=trade_stats['largest_loss'],
            expectancy=trade_stats['expectancy'],
        )

    def generate_performance_report(
        self,
        metrics: PerformanceMetrics
    ) -> str:
        """
        Generate a formatted performance report

        Args:
            metrics: PerformanceMetrics object

        Returns:
            Formatted string report
        """
        report = f"""
═══════════════════════════════════════════════════════
               PERFORMANCE REPORT
═══════════════════════════════════════════════════════

RETURN METRICS
───────────────────────────────────────────────────────
Total Return:           {metrics.total_return:>12.2%}
Annualized Return:      {metrics.annualized_return:>12.2%}
Average Return:         {metrics.average_return:>12.4%}

RISK METRICS
───────────────────────────────────────────────────────
Volatility (Annual):    {metrics.volatility:>12.2%}
Sharpe Ratio:           {metrics.sharpe_ratio:>12.2f}
Sortino Ratio:          {metrics.sortino_ratio:>12.2f}
Calmar Ratio:           {metrics.calmar_ratio:>12.2f}

DRAWDOWN METRICS
───────────────────────────────────────────────────────
Maximum Drawdown:       {metrics.max_drawdown:>12.2%}
Max DD Duration:        {metrics.max_drawdown_duration:>12} days
Current Drawdown:       {metrics.current_drawdown:>12.2%}

TRADE STATISTICS
───────────────────────────────────────────────────────
Total Trades:           {metrics.total_trades:>12}
Winning Trades:         {metrics.winning_trades:>12}
Losing Trades:          {metrics.losing_trades:>12}
Win Rate:               {metrics.win_rate:>12.2%}
Profit Factor:          {metrics.profit_factor:>12.2f}

TRADE PERFORMANCE
───────────────────────────────────────────────────────
Average Win:            ${metrics.average_win:>11.2f}
Average Loss:           ${metrics.average_loss:>11.2f}
Largest Win:            ${metrics.largest_win:>11.2f}
Largest Loss:           ${metrics.largest_loss:>11.2f}
Expectancy:             ${metrics.expectancy:>11.2f}

═══════════════════════════════════════════════════════
"""
        return report


if __name__ == "__main__":
    # Test analytics with sample data
    print("Testing Advanced Analytics...\n")

    # Create sample equity curve
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 252)  # Daily returns
    equity = [10000]

    for r in returns:
        equity.append(equity[-1] * (1 + r))

    equity_curve = pd.Series(equity)

    # Create sample trades
    trades = []
    for i in range(100):
        pnl = np.random.normal(10, 50)
        trades.append({'pnl': pnl, 'symbol': 'BTC', 'timestamp': datetime.now()})

    # Calculate metrics
    analytics = AdvancedAnalytics(risk_free_rate=0.02)
    metrics = analytics.calculate_all_metrics(equity_curve, trades, periods_per_year=252)

    # Print report
    report = analytics.generate_performance_report(metrics)
    print(report)

    print("✅ Advanced analytics test complete!")
