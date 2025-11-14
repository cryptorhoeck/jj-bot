"""
Walk-Forward Analysis for Strategy Optimization
Prevents overfitting by using rolling in-sample/out-of-sample windows
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import itertools


@dataclass
class WalkForwardWindow:
    """Configuration for a walk-forward window"""
    in_sample_start: datetime
    in_sample_end: datetime
    out_sample_start: datetime
    out_sample_end: datetime
    window_number: int


@dataclass
class WalkForwardResult:
    """Results from a walk-forward analysis"""
    window_number: int
    in_sample_metrics: Dict[str, float]
    out_sample_metrics: Dict[str, float]
    optimal_params: Dict[str, Any]
    trades_in_sample: int
    trades_out_sample: int


class WalkForwardAnalyzer:
    """
    Performs walk-forward analysis on trading strategies
    """

    def __init__(
        self,
        in_sample_days: int = 180,
        out_sample_days: int = 60,
        anchored: bool = False
    ):
        """
        Initialize walk-forward analyzer

        Args:
            in_sample_days: Days for in-sample (training) period
            out_sample_days: Days for out-of-sample (testing) period
            anchored: If True, in-sample window starts from beginning (anchored)
                     If False, rolling window that moves forward
        """
        self.in_sample_days = in_sample_days
        self.out_sample_days = out_sample_days
        self.anchored = anchored

    def generate_windows(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[WalkForwardWindow]:
        """
        Generate walk-forward windows

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            List of WalkForwardWindow objects
        """
        windows = []
        window_num = 1

        if self.anchored:
            # Anchored walk-forward: in-sample always starts from beginning
            out_sample_start = start_date + timedelta(days=self.in_sample_days)

            while out_sample_start < end_date:
                out_sample_end = out_sample_start + timedelta(days=self.out_sample_days)

                if out_sample_end > end_date:
                    out_sample_end = end_date

                windows.append(WalkForwardWindow(
                    in_sample_start=start_date,
                    in_sample_end=out_sample_start,
                    out_sample_start=out_sample_start,
                    out_sample_end=out_sample_end,
                    window_number=window_num
                ))

                out_sample_start = out_sample_end
                window_num += 1

        else:
            # Rolling walk-forward: both windows move forward
            current_start = start_date

            while current_start < end_date:
                in_sample_end = current_start + timedelta(days=self.in_sample_days)

                if in_sample_end > end_date:
                    break

                out_sample_start = in_sample_end
                out_sample_end = out_sample_start + timedelta(days=self.out_sample_days)

                if out_sample_end > end_date:
                    out_sample_end = end_date

                windows.append(WalkForwardWindow(
                    in_sample_start=current_start,
                    in_sample_end=in_sample_end,
                    out_sample_start=out_sample_start,
                    out_sample_end=out_sample_end,
                    window_number=window_num
                ))

                # Move to next window
                current_start = out_sample_end
                window_num += 1

        return windows

    def optimize_parameters(
        self,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        backtest_func: Callable,
        metric: str = 'sharpe_ratio'
    ) -> Tuple[Dict[str, Any], float]:
        """
        Optimize strategy parameters using grid search

        Args:
            data: Market data for in-sample period
            param_grid: Dictionary of parameters and their possible values
            backtest_func: Function that runs backtest and returns metrics
            metric: Metric to optimize (sharpe_ratio, total_return, etc.)

        Returns:
            Tuple of (optimal_params, best_metric_value)
        """
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        param_combinations = list(itertools.product(*param_values))

        best_params = None
        best_metric_value = float('-inf')

        # Test each parameter combination
        for param_combo in param_combinations:
            params = dict(zip(param_names, param_combo))

            try:
                # Run backtest with these parameters
                result = backtest_func(data, params)

                # Get metric value
                metric_value = result.get(metric, float('-inf'))

                # Update best if better
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_params = params

            except Exception as e:
                # Skip this combination if it fails
                print(f"⚠️ Parameter combination failed: {params} - {e}")
                continue

        return best_params or {}, best_metric_value

    def run_walk_forward(
        self,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        backtest_func: Callable,
        optimization_metric: str = 'sharpe_ratio'
    ) -> List[WalkForwardResult]:
        """
        Run complete walk-forward analysis

        Args:
            data: Full market data DataFrame with datetime index
            param_grid: Parameter grid for optimization
            backtest_func: Backtesting function
            optimization_metric: Metric to optimize on in-sample data

        Returns:
            List of WalkForwardResult objects
        """
        # Get date range from data
        start_date = data.index[0]
        end_date = data.index[-1]

        # Generate windows
        windows = self.generate_windows(start_date, end_date)

        results = []

        for window in windows:
            print(f"\n🔍 Processing Window {window.window_number}")
            print(f"  In-Sample:  {window.in_sample_start.date()} to {window.in_sample_end.date()}")
            print(f"  Out-Sample: {window.out_sample_start.date()} to {window.out_sample_end.date()}")

            # Split data
            in_sample_data = data[
                (data.index >= window.in_sample_start) &
                (data.index < window.in_sample_end)
            ]

            out_sample_data = data[
                (data.index >= window.out_sample_start) &
                (data.index < window.out_sample_end)
            ]

            # Optimize parameters on in-sample data
            print(f"  Optimizing parameters...")
            optimal_params, best_metric = self.optimize_parameters(
                in_sample_data,
                param_grid,
                backtest_func,
                optimization_metric
            )

            print(f"  Optimal params: {optimal_params}")
            print(f"  In-sample {optimization_metric}: {best_metric:.4f}")

            # Run in-sample backtest with optimal parameters
            in_sample_result = backtest_func(in_sample_data, optimal_params)

            # Test on out-of-sample data
            print(f"  Testing on out-of-sample...")
            out_sample_result = backtest_func(out_sample_data, optimal_params)

            print(f"  Out-sample {optimization_metric}: {out_sample_result.get(optimization_metric, 0):.4f}")

            # Store results
            results.append(WalkForwardResult(
                window_number=window.window_number,
                in_sample_metrics=in_sample_result,
                out_sample_metrics=out_sample_result,
                optimal_params=optimal_params,
                trades_in_sample=in_sample_result.get('total_trades', 0),
                trades_out_sample=out_sample_result.get('total_trades', 0)
            ))

        return results

    def analyze_results(
        self,
        results: List[WalkForwardResult]
    ) -> Dict[str, Any]:
        """
        Analyze walk-forward results

        Args:
            results: List of WalkForwardResult objects

        Returns:
            Dictionary with aggregate statistics
        """
        if not results:
            return {}

        # Extract metrics
        in_sample_returns = [r.in_sample_metrics.get('total_return', 0) for r in results]
        out_sample_returns = [r.out_sample_metrics.get('total_return', 0) for r in results]

        in_sample_sharpe = [r.in_sample_metrics.get('sharpe_ratio', 0) for r in results]
        out_sample_sharpe = [r.out_sample_metrics.get('sharpe_ratio', 0) for r in results]

        # Calculate aggregate statistics
        analysis = {
            'total_windows': len(results),
            'in_sample': {
                'avg_return': np.mean(in_sample_returns),
                'avg_sharpe': np.mean(in_sample_sharpe),
                'std_return': np.std(in_sample_returns),
                'win_rate': sum(1 for r in in_sample_returns if r > 0) / len(in_sample_returns),
            },
            'out_sample': {
                'avg_return': np.mean(out_sample_returns),
                'avg_sharpe': np.mean(out_sample_sharpe),
                'std_return': np.std(out_sample_returns),
                'win_rate': sum(1 for r in out_sample_returns if r > 0) / len(out_sample_returns),
            },
            'degradation': {
                'return_degradation': np.mean(in_sample_returns) - np.mean(out_sample_returns),
                'sharpe_degradation': np.mean(in_sample_sharpe) - np.mean(out_sample_sharpe),
            },
            'consistency': {
                'return_correlation': np.corrcoef(in_sample_returns, out_sample_returns)[0, 1]
                    if len(in_sample_returns) > 1 else 0,
            }
        }

        return analysis

    def generate_report(
        self,
        results: List[WalkForwardResult],
        analysis: Dict[str, Any]
    ) -> str:
        """
        Generate formatted walk-forward analysis report

        Args:
            results: List of WalkForwardResult objects
            analysis: Aggregated analysis from analyze_results()

        Returns:
            Formatted string report
        """
        report = f"""
═══════════════════════════════════════════════════════
           WALK-FORWARD ANALYSIS REPORT
═══════════════════════════════════════════════════════

Configuration:
  In-Sample Period:  {self.in_sample_days} days
  Out-Sample Period: {self.out_sample_days} days
  Method:            {'Anchored' if self.anchored else 'Rolling'}
  Total Windows:     {analysis['total_windows']}

───────────────────────────────────────────────────────
IN-SAMPLE PERFORMANCE
───────────────────────────────────────────────────────
Average Return:      {analysis['in_sample']['avg_return']:>12.2%}
Average Sharpe:      {analysis['in_sample']['avg_sharpe']:>12.2f}
Std Dev Return:      {analysis['in_sample']['std_return']:>12.2%}
Win Rate:            {analysis['in_sample']['win_rate']:>12.2%}

───────────────────────────────────────────────────────
OUT-OF-SAMPLE PERFORMANCE
───────────────────────────────────────────────────────
Average Return:      {analysis['out_sample']['avg_return']:>12.2%}
Average Sharpe:      {analysis['out_sample']['avg_sharpe']:>12.2f}
Std Dev Return:      {analysis['out_sample']['std_return']:>12.2%}
Win Rate:            {analysis['out_sample']['win_rate']:>12.2%}

───────────────────────────────────────────────────────
DEGRADATION ANALYSIS
───────────────────────────────────────────────────────
Return Degradation:  {analysis['degradation']['return_degradation']:>12.2%}
Sharpe Degradation:  {analysis['degradation']['sharpe_degradation']:>12.2f}
Consistency:         {analysis['consistency']['return_correlation']:>12.2f}

───────────────────────────────────────────────────────
WINDOW DETAILS
───────────────────────────────────────────────────────
"""

        for result in results:
            report += f"""
Window {result.window_number}:
  In-Sample:  Return {result.in_sample_metrics.get('total_return', 0):>7.2%}  Sharpe {result.in_sample_metrics.get('sharpe_ratio', 0):>6.2f}  Trades {result.trades_in_sample}
  Out-Sample: Return {result.out_sample_metrics.get('total_return', 0):>7.2%}  Sharpe {result.out_sample_metrics.get('sharpe_ratio', 0):>6.2f}  Trades {result.trades_out_sample}
  Parameters: {result.optimal_params}
"""

        report += "\n═══════════════════════════════════════════════════════\n"

        return report


if __name__ == "__main__":
    print("Walk-Forward Analysis Module")
    print("For testing, import and use with actual market data")
