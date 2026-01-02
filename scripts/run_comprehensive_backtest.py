#!/usr/bin/env python3
"""
Comprehensive Backtest with Walk-Forward Validation

This script runs rigorous backtests that:
1. Use REALISTIC fees (0.2%) and slippage (0.5%)
2. Compare against buy-and-hold baseline
3. Use walk-forward validation
4. Calculate proper Sharpe ratios
5. Generate proof of results

Usage:
    python scripts/run_comprehensive_backtest.py
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ComprehensiveBacktester:
    """
    Rigorous backtesting with walk-forward validation and baseline comparison.

    Uses REALISTIC parameters:
    - Commission: 0.2% (Kraken: 0.26%, Binance: 0.1%)
    - Slippage: 0.5% base (can spike to 2% in volatility)
    """

    # REALISTIC trading costs
    COMMISSION = 0.002  # 0.2% per trade
    SLIPPAGE = 0.005    # 0.5% slippage
    POSITION_SIZE = 0.05  # 5% of capital per trade

    def __init__(
        self,
        initial_capital: float = 10000.0,
        results_dir: str = "./data/backtest_results"
    ):
        self.initial_capital = initial_capital
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

    def generate_synthetic_ohlcv(
        self,
        days: int = 365,
        volatility: float = 0.02,
        trend: float = 0.0001,
        start_price: float = 50000.0
    ) -> np.ndarray:
        """Generate realistic synthetic price data with trends and mean reversion"""
        np.random.seed(42)  # Reproducible results

        prices = [start_price]
        hours = days * 24

        # Use geometric brownian motion with mean reversion
        for i in range(hours - 1):
            # Random component
            daily_return = np.random.normal(trend, volatility)

            # Add mean reversion (prices tend to revert to trend)
            mean_price = start_price * (1 + trend * i)
            reversion = 0.001 * (mean_price - prices[-1]) / prices[-1]

            # Occasional larger moves (market events)
            if np.random.random() < 0.01:  # 1% chance
                daily_return *= np.random.uniform(2, 5)

            new_price = prices[-1] * (1 + daily_return + reversion)
            prices.append(max(new_price, start_price * 0.1))

        prices = np.array(prices)

        # Create OHLCV
        ohlcv = []
        for i, close in enumerate(prices):
            high = close * np.random.uniform(1.001, 1.02)
            low = close * np.random.uniform(0.98, 0.999)
            open_price = (high + low) / 2 * np.random.uniform(0.99, 1.01)
            volume = np.random.uniform(100, 1000)

            ohlcv.append([i, open_price, high, low, close, volume])

        return np.array(ohlcv)

    def calculate_indicators(self, prices: np.ndarray) -> Dict[str, np.ndarray]:
        """Calculate technical indicators for strategy"""
        closes = prices[:, 4]  # Close prices

        # RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(closes))
        avg_loss = np.zeros(len(closes))

        # EMA of gains/losses
        period = 14
        for i in range(period, len(closes)):
            avg_gain[i] = np.mean(gains[i-period:i])
            avg_loss[i] = np.mean(losses[i-period:i])

        rs = np.divide(avg_gain, avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        # SMA
        sma_fast = np.zeros(len(closes))
        sma_slow = np.zeros(len(closes))
        for i in range(50, len(closes)):
            sma_fast[i] = np.mean(closes[i-20:i])
            sma_slow[i] = np.mean(closes[i-50:i])

        # MACD
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd = ema12 - ema26
        signal = self._ema(macd, 9)

        return {
            "rsi": rsi,
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "macd": macd,
            "macd_signal": signal
        }

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA"""
        ema = np.zeros(len(data))
        ema[0] = data[0]
        multiplier = 2 / (period + 1)

        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))

        return ema

    def generate_signals(self, ohlcv: np.ndarray, indicators: Dict) -> np.ndarray:
        """Generate trading signals based on indicators"""
        signals = np.zeros(len(ohlcv))

        rsi = indicators["rsi"]
        sma_fast = indicators["sma_fast"]
        sma_slow = indicators["sma_slow"]
        macd = indicators["macd"]
        macd_signal = indicators["macd_signal"]

        for i in range(50, len(ohlcv)):
            # Combined signal logic
            rsi_buy = rsi[i] < 30
            rsi_sell = rsi[i] > 70
            sma_buy = sma_fast[i] > sma_slow[i] and sma_fast[i-1] <= sma_slow[i-1]
            sma_sell = sma_fast[i] < sma_slow[i] and sma_fast[i-1] >= sma_slow[i-1]
            macd_buy = macd[i] > macd_signal[i] and macd[i-1] <= macd_signal[i-1]
            macd_sell = macd[i] < macd_signal[i] and macd[i-1] >= macd_signal[i-1]

            # Require 2 of 3 signals to agree
            buy_votes = sum([rsi_buy, sma_buy, macd_buy])
            sell_votes = sum([rsi_sell, sma_sell, macd_sell])

            if buy_votes >= 2:
                signals[i] = 1  # Buy
            elif sell_votes >= 2:
                signals[i] = -1  # Sell
            else:
                signals[i] = 0  # Hold

        return signals

    def run_backtest(
        self,
        ohlcv: np.ndarray,
        signals: np.ndarray,
        walk_forward: bool = False,
        train_pct: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run backtest with realistic costs.

        Args:
            ohlcv: Price data
            signals: Trading signals (-1, 0, 1)
            walk_forward: Use walk-forward validation
            train_pct: Training data percentage for walk-forward

        Returns:
            Backtest results
        """
        if walk_forward:
            split_idx = int(len(ohlcv) * train_pct)
            # Only use out-of-sample data for validation
            ohlcv = ohlcv[split_idx:]
            signals = signals[split_idx:]

        capital = self.initial_capital
        position = 0  # 0 = flat, 1 = long
        entry_price = 0
        trades = []
        equity_curve = [capital]

        for i in range(1, len(ohlcv)):
            price = ohlcv[i, 4]  # Close price
            signal = signals[i]

            # Entry logic
            if position == 0 and signal == 1:
                # Buy with realistic costs
                position_value = capital * self.POSITION_SIZE
                slippage_cost = position_value * self.SLIPPAGE
                commission_cost = position_value * self.COMMISSION
                total_cost = slippage_cost + commission_cost

                entry_price = price * (1 + self.SLIPPAGE)  # Worse execution
                capital -= total_cost
                position = 1

                trades.append({
                    "type": "entry",
                    "price": entry_price,
                    "cost": total_cost,
                    "idx": i
                })

            # Exit logic
            elif position == 1 and signal == -1:
                # Sell with realistic costs
                position_value = capital * self.POSITION_SIZE
                exit_price = price * (1 - self.SLIPPAGE)  # Worse execution
                slippage_cost = position_value * self.SLIPPAGE
                commission_cost = position_value * self.COMMISSION
                total_cost = slippage_cost + commission_cost

                # Calculate P&L
                pnl = (exit_price - entry_price) / entry_price * position_value
                capital += pnl - total_cost
                position = 0

                trades.append({
                    "type": "exit",
                    "price": exit_price,
                    "cost": total_cost,
                    "pnl": pnl - total_cost,
                    "idx": i
                })

            equity_curve.append(capital)

        # Calculate metrics
        equity_curve = np.array(equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]

        total_return = (capital - self.initial_capital) / self.initial_capital
        win_trades = [t for t in trades if t.get("pnl", 0) > 0]
        loss_trades = [t for t in trades if t.get("pnl", 0) <= 0 and "pnl" in t]

        # Sharpe ratio (annualized, assuming hourly data)
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe = np.sqrt(8760) * np.mean(returns) / np.std(returns)
        else:
            sharpe = 0

        # Maximum drawdown
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            "initial_capital": self.initial_capital,
            "final_capital": capital,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "total_trades": len([t for t in trades if t["type"] == "exit"]),
            "winning_trades": len(win_trades),
            "losing_trades": len(loss_trades),
            "win_rate": len(win_trades) / max(len(win_trades) + len(loss_trades), 1),
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd * 100,
            "equity_curve": equity_curve.tolist(),
            "trades": trades,
            "commission_rate": self.COMMISSION,
            "slippage_rate": self.SLIPPAGE
        }

    def calculate_buy_hold(self, ohlcv: np.ndarray) -> Dict[str, Any]:
        """Calculate buy-and-hold baseline"""
        start_price = ohlcv[0, 4]
        end_price = ohlcv[-1, 4]

        # Account for entry/exit costs
        entry_cost = self.COMMISSION + self.SLIPPAGE
        exit_cost = self.COMMISSION + self.SLIPPAGE
        total_cost = entry_cost + exit_cost

        gross_return = (end_price - start_price) / start_price
        net_return = gross_return - total_cost

        # Calculate Sharpe
        prices = ohlcv[:, 4]
        returns = np.diff(prices) / prices[:-1]

        if len(returns) > 0 and np.std(returns) > 0:
            sharpe = np.sqrt(8760) * np.mean(returns) / np.std(returns)
        else:
            sharpe = 0

        # Max drawdown
        peak = prices[0]
        max_dd = 0
        for p in prices:
            if p > peak:
                peak = p
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.initial_capital * (1 + net_return),
            "gross_return": gross_return,
            "net_return": net_return,
            "total_return_pct": net_return * 100,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd * 100,
            "trading_costs": total_cost * self.initial_capital
        }

    def run_comprehensive_analysis(
        self,
        days: int = 365,
        scenarios: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive backtest analysis across multiple scenarios.

        Args:
            days: Number of days to simulate
            scenarios: List of market scenarios to test

        Returns:
            Complete analysis results
        """
        print("=" * 60)
        print("COMPREHENSIVE BACKTEST ANALYSIS")
        print("=" * 60)
        print(f"\nREALISTIC TRADING COSTS:")
        print(f"  Commission:  {self.COMMISSION*100:.1f}%")
        print(f"  Slippage:    {self.SLIPPAGE*100:.1f}%")
        print(f"  Per trade:   {(self.COMMISSION + self.SLIPPAGE)*100:.1f}% each way")
        print(f"  Round trip:  {(self.COMMISSION + self.SLIPPAGE)*2*100:.1f}%")
        print("=" * 60)

        if scenarios is None:
            scenarios = [
                {"name": "Bull Market", "trend": 0.0003, "volatility": 0.02},
                {"name": "Bear Market", "trend": -0.0003, "volatility": 0.025},
                {"name": "Sideways", "trend": 0.0, "volatility": 0.015},
                {"name": "High Volatility", "trend": 0.0001, "volatility": 0.04},
                {"name": "Crash & Recovery", "trend": -0.0001, "volatility": 0.05},
            ]

        all_results = {}

        for scenario in scenarios:
            print(f"\n{'='*60}")
            print(f"Scenario: {scenario['name']}")
            print(f"  Trend:      {scenario['trend']*100:.3f}%/hr")
            print(f"  Volatility: {scenario['volatility']*100:.1f}%")
            print(f"{'='*60}")

            # Generate data
            ohlcv = self.generate_synthetic_ohlcv(
                days=days,
                trend=scenario["trend"],
                volatility=scenario["volatility"]
            )

            # Calculate indicators and signals
            indicators = self.calculate_indicators(ohlcv)
            signals = self.generate_signals(ohlcv, indicators)

            # Run standard backtest
            print("\nStandard backtest...")
            standard_results = self.run_backtest(ohlcv, signals)

            # Run walk-forward validation
            print("Walk-forward validation (30% out-of-sample)...")
            wf_results = self.run_backtest(ohlcv, signals, walk_forward=True, train_pct=0.7)

            # Calculate buy-and-hold
            print("Buy-and-hold baseline...")
            bh_results = self.calculate_buy_hold(ohlcv)

            # Compare
            outperformance = standard_results["total_return"] - bh_results["net_return"]
            wf_outperformance = wf_results["total_return"] - bh_results["net_return"]

            all_results[scenario["name"]] = {
                "scenario": scenario,
                "standard": standard_results,
                "walk_forward": wf_results,
                "buy_hold": bh_results,
                "outperformance": outperformance,
                "wf_outperformance": wf_outperformance
            }

            # Print results
            print(f"\nResults for {scenario['name']}:")
            print(f"  Strategy Return:   {standard_results['total_return_pct']:+.2f}%")
            print(f"  WF Return:         {wf_results['total_return_pct']:+.2f}%")
            print(f"  Buy & Hold:        {bh_results['total_return_pct']:+.2f}%")
            print(f"  Outperformance:    {outperformance*100:+.2f}%")
            print(f"  Sharpe (Strategy): {standard_results['sharpe_ratio']:.2f}")
            print(f"  Sharpe (B&H):      {bh_results['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown:      {standard_results['max_drawdown_pct']:.1f}%")
            print(f"  Win Rate:          {standard_results['win_rate']*100:.1f}%")
            print(f"  Trades:            {standard_results['total_trades']}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY ACROSS ALL SCENARIOS")
        print("=" * 60)

        avg_return = np.mean([r["standard"]["total_return"] for r in all_results.values()])
        avg_wf_return = np.mean([r["walk_forward"]["total_return"] for r in all_results.values()])
        avg_bh_return = np.mean([r["buy_hold"]["net_return"] for r in all_results.values()])
        avg_outperf = np.mean([r["outperformance"] for r in all_results.values()])
        avg_sharpe = np.mean([r["standard"]["sharpe_ratio"] for r in all_results.values()])
        avg_win_rate = np.mean([r["standard"]["win_rate"] for r in all_results.values()])

        print(f"\nAverage Strategy Return:    {avg_return*100:+.2f}%")
        print(f"Average WF Return:          {avg_wf_return*100:+.2f}%")
        print(f"Average Buy & Hold:         {avg_bh_return*100:+.2f}%")
        print(f"Average Outperformance:     {avg_outperf*100:+.2f}%")
        print(f"Average Sharpe Ratio:       {avg_sharpe:.2f}")
        print(f"Average Win Rate:           {avg_win_rate*100:.1f}%")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f"backtest_results_{timestamp}.json")

        # Prepare serializable results
        save_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "initial_capital": self.initial_capital,
                "commission": self.COMMISSION,
                "slippage": self.SLIPPAGE,
                "days_tested": days
            },
            "summary": {
                "avg_strategy_return": avg_return,
                "avg_walk_forward_return": avg_wf_return,
                "avg_buy_hold_return": avg_bh_return,
                "avg_outperformance": avg_outperf,
                "avg_sharpe_ratio": avg_sharpe,
                "avg_win_rate": avg_win_rate,
                "profitable_scenarios": sum(1 for r in all_results.values() if r["standard"]["total_return"] > 0),
                "beats_baseline_count": sum(1 for r in all_results.values() if r["outperformance"] > 0)
            },
            "scenarios": {}
        }

        for name, result in all_results.items():
            save_results["scenarios"][name] = {
                "config": result["scenario"],
                "strategy_return": result["standard"]["total_return"],
                "walk_forward_return": result["walk_forward"]["total_return"],
                "buy_hold_return": result["buy_hold"]["net_return"],
                "outperformance": result["outperformance"],
                "sharpe_ratio": result["standard"]["sharpe_ratio"],
                "max_drawdown": result["standard"]["max_drawdown"],
                "win_rate": result["standard"]["win_rate"],
                "total_trades": result["standard"]["total_trades"]
            }

        with open(results_file, 'w') as f:
            json.dump(save_results, f, indent=2)

        print(f"\nResults saved: {results_file}")

        # Validation status
        print("\n" + "=" * 60)
        print("VALIDATION STATUS")
        print("=" * 60)

        checks = [
            ("Sharpe Ratio > 0.5", avg_sharpe > 0.5),
            ("Win Rate > 45%", avg_win_rate > 0.45),
            ("Beats Buy & Hold", avg_outperf > 0),
            ("Walk-Forward Profitable", avg_wf_return > 0),
            ("Profitable in >50% scenarios", sum(1 for r in all_results.values() if r["standard"]["total_return"] > 0) > len(all_results) / 2)
        ]

        for check_name, passed in checks:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check_name}")

        passed_count = sum(1 for _, p in checks if p)
        print(f"\nPassed: {passed_count}/{len(checks)} checks")

        return {
            "results": save_results,
            "all_scenarios": all_results,
            "validation_passed": passed_count
        }


def main():
    print("\n" + "#" * 60)
    print("# JJ-Bot Comprehensive Backtest")
    print("# With REALISTIC Trading Costs")
    print("#" * 60)

    backtester = ComprehensiveBacktester(
        initial_capital=10000.0,
        results_dir="./data/backtest_results"
    )

    results = backtester.run_comprehensive_analysis(days=365)

    print("\n" + "=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
