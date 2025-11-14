"""
Analytics Module

Performance tracking and analysis for trading strategies
"""

from .performance_tracker import (
    PerformanceTracker,
    analyze_backtest_results,
    compare_strategies
)

__all__ = [
    'PerformanceTracker',
    'analyze_backtest_results',
    'compare_strategies'
]
