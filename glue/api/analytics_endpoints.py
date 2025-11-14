"""
Analytics API Endpoints

Provides RESTful endpoints for performance tracking and analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, List
from pydantic import BaseModel
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.analytics import PerformanceTracker, analyze_backtest_results, compare_strategies
from modules.backtesting import backtester

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# === Request/Response Models ===

class TradeInput(BaseModel):
    """Single trade input"""
    symbol: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    fees: float = 0.0
    trade_type: str = "long"


class PerformanceAnalysisRequest(BaseModel):
    """Request for performance analysis"""
    initial_capital: float = 10000.0
    trades: List[TradeInput]


class StrategyComparisonRequest(BaseModel):
    """Request for strategy comparison"""
    strategies: Dict[str, Dict]  # strategy_name -> backtest_results


# === Endpoints ===

@router.post("/analyze")
async def analyze_performance(request: PerformanceAnalysisRequest):
    """
    Analyze trading performance from a list of trades

    Calculates comprehensive metrics including:
    - Win rate, profit factor, expectancy
    - Sharpe ratio, maximum drawdown
    - Equity curve
    - Trade distribution
    - Monthly performance breakdown

    Request body:
    {
        "initial_capital": 10000,
        "trades": [
            {
                "symbol": "BTC",
                "entry_price": 50000,
                "exit_price": 52000,
                "quantity": 0.1,
                "fees": 10,
                "trade_type": "long"
            }
        ]
    }

    Returns:
        Comprehensive performance analysis

    Example:
    - POST /api/analytics/analyze
    """
    try:
        tracker = PerformanceTracker(initial_capital=request.initial_capital)

        # Add all trades
        for trade in request.trades:
            tracker.add_trade(
                symbol=trade.symbol,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                quantity=trade.quantity,
                fees=trade.fees,
                trade_type=trade.trade_type
            )

        # Calculate metrics
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/{run_id}/analysis")
async def analyze_backtest(run_id: str):
    """
    Analyze a saved backtest run

    Retrieves backtest results and calculates performance metrics

    Args:
        run_id: Backtest run identifier

    Returns:
        Performance analysis of the backtest

    Example:
    - GET /api/analytics/backtest/abc123/analysis
    """
    try:
        # In a real implementation, this would load from a database
        # For now, return a helpful message
        return {
            'success': False,
            'error': 'Backtest result storage not yet implemented',
            'note': 'Use POST /api/analytics/analyze with backtest results directly'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-strategies")
async def compare_strategies_endpoint(request: StrategyComparisonRequest):
    """
    Compare performance of multiple trading strategies

    Analyzes multiple backtest results and provides side-by-side comparison

    Request body:
    {
        "strategies": {
            "SMA_Crossover": {
                "initial_capital": 10000,
                "trades": [...]
            },
            "RSI_Strategy": {
                "initial_capital": 10000,
                "trades": [...]
            }
        }
    }

    Returns:
        Comparison metrics for all strategies

    Example:
    - POST /api/analytics/compare-strategies
    """
    try:
        comparison = compare_strategies(request.strategies)

        return {
            'success': True,
            'comparison': comparison['comparison'],
            'num_strategies': len(request.strategies)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equity-curve/simulate")
async def simulate_equity_curve(
    initial_capital: float = Query(10000, description="Starting capital"),
    avg_return_pct: float = Query(1.0, description="Average return per trade (%)"),
    std_return_pct: float = Query(2.0, description="Standard deviation of returns (%)"),
    num_trades: int = Query(100, description="Number of trades to simulate"),
    win_rate: float = Query(60, description="Win rate percentage")
):
    """
    Simulate an equity curve with specified parameters

    Useful for understanding expected performance characteristics

    Examples:
    - /api/analytics/equity-curve/simulate?initial_capital=10000&avg_return_pct=1.5&num_trades=200
    - /api/analytics/equity-curve/simulate?win_rate=65&std_return_pct=3.0
    """
    try:
        import numpy as np

        tracker = PerformanceTracker(initial_capital=initial_capital)

        # Simulate trades
        for i in range(num_trades):
            # Determine if win or loss
            is_win = np.random.random() < (win_rate / 100)

            # Generate return
            if is_win:
                return_pct = abs(np.random.normal(avg_return_pct, std_return_pct))
            else:
                return_pct = -abs(np.random.normal(avg_return_pct, std_return_pct))

            # Simulate trade
            entry_price = 100
            exit_price = entry_price * (1 + return_pct / 100)
            quantity = tracker.current_capital * 0.1 / entry_price  # Use 10% of capital

            tracker.add_trade(
                symbol='SIM',
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                trade_type='long'
            )

        # Get results
        metrics = tracker.calculate_metrics()
        equity_curve = tracker.get_equity_curve()

        return {
            'success': True,
            'simulation_params': {
                'initial_capital': initial_capital,
                'avg_return_pct': avg_return_pct,
                'std_return_pct': std_return_pct,
                'num_trades': num_trades,
                'win_rate': win_rate
            },
            'metrics': metrics,
            'equity_curve': equity_curve
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics-info")
async def get_metrics_info():
    """
    Get information about available performance metrics

    Returns descriptions of all calculated metrics

    Example:
    - GET /api/analytics/metrics-info
    """
    return {
        'success': True,
        'metrics': {
            'overview': {
                'initial_capital': 'Starting capital amount',
                'current_capital': 'Final capital after all trades',
                'total_pnl': 'Total profit/loss in absolute terms',
                'total_return_pct': 'Total return as percentage of initial capital',
                'total_trades': 'Number of completed trades'
            },
            'win_loss': {
                'win_rate': 'Percentage of winning trades',
                'num_wins': 'Number of winning trades',
                'num_losses': 'Number of losing trades',
                'avg_win': 'Average profit of winning trades',
                'avg_loss': 'Average loss of losing trades',
                'profit_factor': 'Gross profit / Gross loss',
                'expectancy': 'Average expected profit per trade',
                'max_consecutive_wins': 'Longest winning streak',
                'max_consecutive_losses': 'Longest losing streak'
            },
            'risk_metrics': {
                'max_drawdown': 'Largest peak-to-trough decline in absolute terms',
                'max_drawdown_pct': 'Largest peak-to-trough decline as percentage',
                'sharpe_ratio': 'Risk-adjusted return (higher is better, >1 is good, >2 is excellent)'
            },
            'best_worst': {
                'best_trade': 'Trade with highest profit',
                'worst_trade': 'Trade with largest loss'
            }
        },
        'formulas': {
            'win_rate': '(Number of Wins / Total Trades) * 100',
            'profit_factor': 'Gross Profit / Absolute Gross Loss',
            'expectancy': '(Win Rate * Avg Win) - (Loss Rate * Avg Loss)',
            'sharpe_ratio': '(Mean Return / Std Dev of Returns) * sqrt(252)',
            'max_drawdown_pct': '((Peak Equity - Current Equity) / Peak Equity) * 100'
        }
    }


@router.get("/status")
async def get_analytics_status():
    """
    Get analytics module status

    Returns information about analytics capabilities

    Example:
    - GET /api/analytics/status
    """
    return {
        'success': True,
        'status': 'operational',
        'capabilities': {
            'performance_analysis': True,
            'equity_curves': True,
            'trade_distribution': True,
            'monthly_breakdown': True,
            'strategy_comparison': True,
            'risk_metrics': True
        },
        'supported_metrics': [
            'win_rate', 'profit_factor', 'sharpe_ratio',
            'max_drawdown', 'expectancy', 'total_return'
        ],
        'endpoints': [
            'POST /api/analytics/analyze',
            'GET /api/analytics/backtest/{run_id}/analysis',
            'POST /api/analytics/compare-strategies',
            'GET /api/analytics/equity-curve/simulate',
            'GET /api/analytics/metrics-info',
            'GET /api/analytics/status'
        ]
    }
