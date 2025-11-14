"""
Portfolio Performance Tracker

Track and analyze trading performance with comprehensive metrics
"""

import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime


class PerformanceTracker:
    """Track and calculate portfolio performance metrics"""

    def __init__(self, initial_capital: float = 10000.0):
        """
        Initialize performance tracker

        Args:
            initial_capital: Starting capital
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []
        self.equity_curve = [initial_capital]
        self.timestamps = [datetime.now()]

    def add_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        entry_time: Optional[datetime] = None,
        exit_time: Optional[datetime] = None,
        fees: float = 0.0,
        trade_type: str = "long"
    ) -> Dict[str, Any]:
        """
        Add a completed trade to the tracker

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            exit_price: Exit price
            quantity: Position size
            entry_time: Entry timestamp
            exit_time: Exit timestamp
            fees: Trading fees
            trade_type: 'long' or 'short'

        Returns:
            Trade result dictionary
        """
        # Calculate P&L
        if trade_type == "long":
            pnl = (exit_price - entry_price) * quantity - fees
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # short
            pnl = (entry_price - exit_price) * quantity - fees
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Update capital
        self.current_capital += pnl

        # Record trade
        trade = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'entry_time': entry_time or datetime.now(),
            'exit_time': exit_time or datetime.now(),
            'fees': fees,
            'trade_type': trade_type,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'is_win': pnl > 0
        }

        self.trades.append(trade)

        # Update equity curve
        self.equity_curve.append(self.current_capital)
        self.timestamps.append(trade['exit_time'])

        return trade

    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """
        Get equity curve data

        Returns:
            List of equity points with timestamps
        """
        return [
            {
                'timestamp': ts.isoformat() if isinstance(ts, datetime) else ts,
                'equity': equity,
                'return_pct': ((equity - self.initial_capital) / self.initial_capital) * 100
            }
            for ts, equity in zip(self.timestamps, self.equity_curve)
        ]

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics

        Returns:
            Dictionary of performance metrics
        """
        if not self.trades:
            return {
                'success': False,
                'error': 'No trades to analyze'
            }

        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['is_win']]
        losing_trades = [t for t in self.trades if not t['is_win']]

        num_wins = len(winning_trades)
        num_losses = len(losing_trades)

        # Basic metrics
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100

        win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0

        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Sharpe ratio (simplified - assumes daily returns)
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0

        # Maximum drawdown
        peak = self.equity_curve[0]
        max_dd = 0
        max_dd_pct = 0

        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak) * 100 if peak > 0 else 0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * abs(avg_loss))

        # Best and worst trades
        best_trade = max(self.trades, key=lambda t: t['pnl'])
        worst_trade = min(self.trades, key=lambda t: t['pnl'])

        # Consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in self.trades:
            if trade['is_win']:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        return {
            'success': True,
            'overview': {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'total_pnl': total_pnl,
                'total_return_pct': total_return,
                'total_trades': total_trades
            },
            'win_loss': {
                'win_rate': win_rate,
                'num_wins': num_wins,
                'num_losses': num_losses,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'max_consecutive_wins': max_consecutive_wins,
                'max_consecutive_losses': max_consecutive_losses
            },
            'risk_metrics': {
                'max_drawdown': max_dd,
                'max_drawdown_pct': max_dd_pct,
                'sharpe_ratio': sharpe_ratio
            },
            'best_worst': {
                'best_trade': {
                    'symbol': best_trade['symbol'],
                    'pnl': best_trade['pnl'],
                    'pnl_pct': best_trade['pnl_pct'],
                    'entry_price': best_trade['entry_price'],
                    'exit_price': best_trade['exit_price']
                },
                'worst_trade': {
                    'symbol': worst_trade['symbol'],
                    'pnl': worst_trade['pnl'],
                    'pnl_pct': worst_trade['pnl_pct'],
                    'entry_price': worst_trade['entry_price'],
                    'exit_price': worst_trade['exit_price']
                }
            }
        }

    def get_trade_distribution(self) -> Dict[str, Any]:
        """
        Get distribution of trade results

        Returns:
            Trade distribution data
        """
        if not self.trades:
            return {'success': False, 'error': 'No trades'}

        pnl_values = [t['pnl'] for t in self.trades]
        pnl_pct_values = [t['pnl_pct'] for t in self.trades]

        # Create bins for histogram
        bins = [-100, -10, -5, -2, 0, 2, 5, 10, 100]
        histogram, _ = np.histogram(pnl_pct_values, bins=bins)

        return {
            'success': True,
            'distribution': {
                'bins': bins,
                'counts': histogram.tolist(),
                'labels': [
                    '< -10%', '-10% to -5%', '-5% to -2%', '-2% to 0%',
                    '0% to 2%', '2% to 5%', '5% to 10%', '> 10%'
                ]
            },
            'statistics': {
                'mean_pnl': np.mean(pnl_values),
                'median_pnl': np.median(pnl_values),
                'std_pnl': np.std(pnl_values),
                'mean_pnl_pct': np.mean(pnl_pct_values),
                'median_pnl_pct': np.median(pnl_pct_values),
                'std_pnl_pct': np.std(pnl_pct_values)
            }
        }

    def get_monthly_performance(self) -> Dict[str, Any]:
        """
        Get performance broken down by month

        Returns:
            Monthly performance data
        """
        if not self.trades:
            return {'success': False, 'error': 'No trades'}

        monthly_data = {}

        for trade in self.trades:
            exit_time = trade['exit_time']
            month_key = exit_time.strftime('%Y-%m') if isinstance(exit_time, datetime) else 'Unknown'

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'pnl': 0,
                    'trades': 0,
                    'wins': 0,
                    'losses': 0
                }

            monthly_data[month_key]['pnl'] += trade['pnl']
            monthly_data[month_key]['trades'] += 1

            if trade['is_win']:
                monthly_data[month_key]['wins'] += 1
            else:
                monthly_data[month_key]['losses'] += 1

        # Convert to list and calculate percentages
        monthly_list = []
        for month, data in sorted(monthly_data.items()):
            win_rate = (data['wins'] / data['trades']) * 100 if data['trades'] > 0 else 0
            monthly_list.append({
                'month': month,
                'pnl': data['pnl'],
                'trades': data['trades'],
                'wins': data['wins'],
                'losses': data['losses'],
                'win_rate': win_rate
            })

        return {
            'success': True,
            'monthly_performance': monthly_list
        }

    def reset(self, initial_capital: Optional[float] = None):
        """Reset the tracker"""
        if initial_capital is not None:
            self.initial_capital = initial_capital

        self.current_capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = [datetime.now()]


# Utility functions for backtesting results analysis

def analyze_backtest_results(backtest_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze backtest results and generate performance metrics

    Args:
        backtest_results: Results from backtester

    Returns:
        Performance analysis
    """
    tracker = PerformanceTracker(
        initial_capital=backtest_results.get('initial_capital', 10000)
    )

    # Add all trades from backtest
    for trade in backtest_results.get('trades', []):
        tracker.add_trade(
            symbol=trade.get('symbol', 'UNKNOWN'),
            entry_price=trade.get('entry_price', 0),
            exit_price=trade.get('exit_price', 0),
            quantity=trade.get('quantity', 0),
            entry_time=trade.get('entry_time'),
            exit_time=trade.get('exit_time'),
            fees=trade.get('fees', 0),
            trade_type=trade.get('type', 'long')
        )

    # Calculate all metrics
    metrics = tracker.calculate_metrics()
    equity_curve = tracker.get_equity_curve()
    distribution = tracker.get_trade_distribution()
    monthly = tracker.get_monthly_performance()

    return {
        'success': True,
        'metrics': metrics,
        'equity_curve': equity_curve,
        'distribution': distribution,
        'monthly_performance': monthly
    }


def compare_strategies(
    strategy_results: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compare multiple strategy results

    Args:
        strategy_results: Dictionary of strategy_name -> backtest_results

    Returns:
        Comparison data
    """
    comparison = {}

    for strategy_name, results in strategy_results.items():
        analysis = analyze_backtest_results(results)

        if analysis['success'] and analysis['metrics']['success']:
            metrics = analysis['metrics']

            comparison[strategy_name] = {
                'total_return': metrics['overview']['total_return_pct'],
                'win_rate': metrics['win_loss']['win_rate'],
                'profit_factor': metrics['win_loss']['profit_factor'],
                'sharpe_ratio': metrics['risk_metrics']['sharpe_ratio'],
                'max_drawdown': metrics['risk_metrics']['max_drawdown_pct'],
                'total_trades': metrics['overview']['total_trades'],
                'expectancy': metrics['win_loss']['expectancy']
            }

    return {
        'success': True,
        'comparison': comparison
    }
