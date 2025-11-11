"""
Strategy Performance Tracker

Tracks and analyzes performance metrics for each trading strategy.
Calculates win rate, profit factor, Sharpe ratio, max drawdown, etc.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.database.connection import get_db_connection, TRADES_DB_PATH, LEARNING_DB_PATH


class StrategyPerformanceTracker:
    """
    Tracks performance metrics for trading strategies.

    Calculates:
    - Win rate
    - Profit factor
    - Sharpe ratio
    - Maximum drawdown
    - Total trades
    - Total P&L
    """

    def __init__(self):
        """Initialize strategy performance tracker."""
        self.trades_db = TRADES_DB_PATH
        self.learning_db = LEARNING_DB_PATH

    def get_strategy_metrics(
        self,
        strategy_name: str,
        period_hours: int = 24
    ) -> Dict:
        """
        Get performance metrics for a strategy over a time period.

        Args:
            strategy_name: Name of the strategy
            period_hours: Time period in hours to analyze

        Returns:
            Dict with performance metrics
        """
        start_time = (datetime.now() - timedelta(hours=period_hours)).isoformat()

        with get_db_connection(self.trades_db) as conn:
            cur = conn.cursor()

            # Get all trades for this strategy in the period
            cur.execute("""
                SELECT pnl, timestamp
                FROM trades
                WHERE strategy = ?
                AND timestamp >= ?
                AND pnl IS NOT NULL
                ORDER BY timestamp ASC
            """, (strategy_name, start_time))

            trades = cur.fetchall()

        if not trades:
            return self._empty_metrics(strategy_name, period_hours)

        # Calculate metrics
        pnls = [t[0] for t in trades]
        total_trades = len(pnls)
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        # Win rate
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        # Profit factor
        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        # Total P&L
        total_pnl = sum(pnls)

        # Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio(pnls)

        # Maximum drawdown
        max_drawdown = self._calculate_max_drawdown(pnls)

        return {
            'strategy_name': strategy_name,
            'period_hours': period_hours,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'total_pnl': round(total_pnl, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'avg_win': round(sum(winning_trades) / len(winning_trades), 2) if winning_trades else 0,
            'avg_loss': round(sum(losing_trades) / len(losing_trades), 2) if losing_trades else 0
        }

    def get_all_strategies_performance(
        self,
        period_hours: int = 24
    ) -> List[Dict]:
        """
        Get performance metrics for all strategies.

        Args:
            period_hours: Time period in hours

        Returns:
            List of performance dicts, sorted by total P&L
        """
        start_time = (datetime.now() - timedelta(hours=period_hours)).isoformat()

        # Get list of all strategies that have trades
        with get_db_connection(self.trades_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT strategy
                FROM trades
                WHERE timestamp >= ?
                AND strategy IS NOT NULL
            """, (start_time,))

            strategies = [row[0] for row in cur.fetchall()]

        # Get metrics for each strategy
        all_metrics = []
        for strategy in strategies:
            metrics = self.get_strategy_metrics(strategy, period_hours)
            all_metrics.append(metrics)

        # Sort by total P&L
        all_metrics.sort(key=lambda x: x['total_pnl'], reverse=True)

        return all_metrics

    def recommend_strategy(self, period_hours: int = 24) -> Optional[Dict]:
        """
        Recommend best performing strategy based on composite score.

        Score = (win_rate * 0.3) + (profit_factor * 0.3) + (sharpe * 0.2) + (pnl * 0.2)

        Args:
            period_hours: Time period to analyze

        Returns:
            Dict with recommended strategy and confidence score
        """
        all_performance = self.get_all_strategies_performance(period_hours)

        if not all_performance:
            return None

        # Calculate composite scores
        for metrics in all_performance:
            # Normalize components to 0-100 scale
            win_rate_score = metrics['win_rate']  # Already 0-100
            profit_factor_score = min(metrics['profit_factor'] * 10, 100)  # Scale PF to 0-100
            sharpe_score = min(metrics['sharpe_ratio'] * 20, 100)  # Scale Sharpe to 0-100
            pnl_score = min(metrics['total_pnl'], 100)  # Cap at 100

            # Weighted composite score
            composite_score = (
                win_rate_score * 0.3 +
                profit_factor_score * 0.3 +
                sharpe_score * 0.2 +
                pnl_score * 0.2
            )

            metrics['composite_score'] = round(composite_score, 2)

        # Sort by composite score
        all_performance.sort(key=lambda x: x['composite_score'], reverse=True)

        best = all_performance[0]

        return {
            'strategy': best['strategy_name'],
            'confidence': best['composite_score'] / 100,  # Convert to 0-1
            'metrics': best
        }

    def save_performance_snapshot(self, strategy_name: str, period_hours: int = 24):
        """
        Save current performance metrics to learning database.

        Args:
            strategy_name: Strategy to snapshot
            period_hours: Period to analyze
        """
        metrics = self.get_strategy_metrics(strategy_name, period_hours)

        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO strategy_performance (
                    strategy_name, timestamp, total_trades, winning_trades,
                    losing_trades, total_pnl, win_rate, profit_factor,
                    sharpe_ratio, max_drawdown
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strategy_name,
                datetime.now().isoformat(),
                metrics['total_trades'],
                metrics['winning_trades'],
                metrics['losing_trades'],
                metrics['total_pnl'],
                metrics['win_rate'],
                metrics['profit_factor'],
                metrics['sharpe_ratio'],
                metrics['max_drawdown']
            ))
            conn.commit()

    def _calculate_sharpe_ratio(self, pnls: List[float]) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted returns).

        Sharpe = mean(returns) / std(returns)

        Args:
            pnls: List of P&L values

        Returns:
            Sharpe ratio
        """
        if len(pnls) < 2:
            return 0.0

        import statistics

        mean_return = statistics.mean(pnls)
        std_return = statistics.stdev(pnls)

        if std_return == 0:
            return 0.0

        return mean_return / std_return

    def _calculate_max_drawdown(self, pnls: List[float]) -> float:
        """
        Calculate maximum drawdown (largest peak-to-trough decline).

        Args:
            pnls: List of P&L values

        Returns:
            Maximum drawdown (negative value)
        """
        if not pnls:
            return 0.0

        # Calculate cumulative P&L
        cumulative = []
        total = 0
        for pnl in pnls:
            total += pnl
            cumulative.append(total)

        # Find max drawdown
        peak = cumulative[0]
        max_dd = 0

        for value in cumulative:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd

        return -max_dd  # Return as negative

    def _empty_metrics(self, strategy_name: str, period_hours: int) -> Dict:
        """Return empty metrics dict."""
        return {
            'strategy_name': strategy_name,
            'period_hours': period_hours,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_pnl': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
