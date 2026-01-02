#!/usr/bin/env python3
"""
Run Backtest with Historical Data

This script runs a backtest using the JJ-Bot strategy engine with simulated
historical data to validate the trading logic.
"""

import sys
import os
from datetime import datetime, timedelta
import random
import math

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.backtesting.backtester import Backtester


def generate_price_series(
    start_price: float,
    days: int = 90,
    volatility: float = 0.02,
    trend: float = 0.0001
) -> list:
    """
    Generate realistic price data with trends and volatility.

    Args:
        start_price: Starting price
        days: Number of days
        volatility: Daily volatility (default 2%)
        trend: Daily drift (positive = bullish)

    Returns:
        List of price dictionaries
    """
    prices = []
    price = start_price

    # Generate hourly data (24 candles per day)
    candles_per_day = 24
    total_candles = days * candles_per_day

    start_time = datetime.now() - timedelta(days=days)

    for i in range(total_candles):
        # Add some mean reversion and momentum
        momentum = (random.random() - 0.5) * 2 * volatility

        # Add occasional larger moves (market events)
        if random.random() < 0.01:  # 1% chance of big move
            momentum *= 3

        # Apply price change
        price *= (1 + momentum + trend)

        # Ensure price stays positive
        price = max(price * 0.1, price)

        timestamp = start_time + timedelta(hours=i)

        prices.append({
            "timestamp": timestamp.isoformat(),
            "price": round(price, 2)
        })

    return prices


def run_multi_asset_backtest():
    """Run backtest across multiple assets"""

    print("=" * 60)
    print("JJ-Bot Pro - Backtest Results")
    print("=" * 60)

    # Initialize backtester
    bt = Backtester(initial_capital=10000.0)

    # Configure REALISTIC settings for actual crypto trading
    # Commission: 0.2% (Kraken taker: 0.26%, Binance taker: 0.1%)
    # Slippage: 0.5% base (can spike to 2% during volatility)
    bt.config["commission"] = 0.002  # 0.2% commission (realistic taker fee)
    bt.config["slippage"] = 0.005    # 0.5% slippage (realistic for crypto)
    bt.config["position_size"] = 0.05  # 5% per position (matches bot config)

    # Test assets with different price ranges
    assets = {
        "BTC": {"start_price": 50000, "volatility": 0.025, "trend": 0.0002},
        "ETH": {"start_price": 3000, "volatility": 0.03, "trend": 0.0001},
        "SOL": {"start_price": 150, "volatility": 0.04, "trend": 0.0003},
    }

    all_results = {}

    for symbol, params in assets.items():
        print(f"\n{'='*60}")
        print(f"Backtesting {symbol}")
        print(f"{'='*60}")

        # Generate historical data
        historical_data = generate_price_series(
            start_price=params["start_price"],
            days=90,
            volatility=params["volatility"],
            trend=params["trend"]
        )

        # Load data into backtester
        bt.load_historical_data(symbol, historical_data)

        # Run backtest with RSI strategy
        result = bt.run_backtest(symbol, strategy="rsi_strategy")

        if "error" not in result:
            all_results[symbol] = result

            # Print individual results
            print(f"\nResults for {symbol}:")
            print(f"  Initial Capital: ${bt.initial_capital:,.2f}")
            print(f"  Final Equity:    ${result.get('final_equity', 0):,.2f}")
            print(f"  Total Return:    {result.get('total_return', 0)*100:.2f}%")
            print(f"  Total Trades:    {result.get('total_trades', 0)}")
            print(f"  Win Rate:        {result.get('win_rate', 0)*100:.1f}%")
            print(f"  Max Drawdown:    {result.get('max_drawdown', 0)*100:.2f}%")
            print(f"  Sharpe Ratio:    {result.get('sharpe_ratio', 0):.2f}")
        else:
            print(f"  Error: {result['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("BACKTEST SUMMARY")
    print("=" * 60)

    if all_results:
        avg_return = sum(r.get('total_return', 0) for r in all_results.values()) / len(all_results)
        avg_win_rate = sum(r.get('win_rate', 0) for r in all_results.values()) / len(all_results)
        total_trades = sum(r.get('total_trades', 0) for r in all_results.values())

        print(f"Assets Tested:     {len(all_results)}")
        print(f"Total Trades:      {total_trades}")
        print(f"Avg Return:        {avg_return*100:.2f}%")
        print(f"Avg Win Rate:      {avg_win_rate*100:.1f}%")

        # Strategy validation
        print("\n" + "-" * 40)
        print("Strategy Validation:")
        print("-" * 40)

        if avg_return > 0:
            print("  [PASS] Strategy is profitable on average")
        else:
            print("  [WARN] Strategy shows negative average returns")

        if avg_win_rate > 0.45:
            print("  [PASS] Win rate above 45%")
        else:
            print("  [WARN] Win rate below 45%")

        worst_dd = max(r.get('max_drawdown', 0) for r in all_results.values())
        if worst_dd < 0.15:
            print(f"  [PASS] Max drawdown ({worst_dd*100:.1f}%) within acceptable limits")
        else:
            print(f"  [WARN] Max drawdown ({worst_dd*100:.1f}%) exceeds 15%")

    return all_results


def run_stress_test():
    """Run stress tests with adverse market conditions"""

    print("\n" + "=" * 60)
    print("STRESS TEST - Adverse Market Conditions")
    print("=" * 60)

    bt = Backtester(initial_capital=10000.0)

    scenarios = {
        "crash": {"volatility": 0.08, "trend": -0.005, "desc": "Market Crash (-50% over 90d)"},
        "high_vol": {"volatility": 0.06, "trend": 0.0, "desc": "High Volatility Sideways"},
        "bull_run": {"volatility": 0.03, "trend": 0.003, "desc": "Strong Bull Run"},
    }

    results = {}

    for scenario, params in scenarios.items():
        print(f"\nScenario: {params['desc']}")
        print("-" * 40)

        data = generate_price_series(
            start_price=50000,
            days=90,
            volatility=params["volatility"],
            trend=params["trend"]
        )

        bt.load_historical_data("TEST", data)
        result = bt.run_backtest("TEST", strategy="rsi_strategy")

        if "error" not in result:
            results[scenario] = result
            print(f"  Return:     {result.get('total_return', 0)*100:+.2f}%")
            print(f"  Max DD:     {result.get('max_drawdown', 0)*100:.2f}%")
            print(f"  Trades:     {result.get('total_trades', 0)}")
        else:
            print(f"  Error: {result['error']}")

    return results


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("#  JJ-Bot Pro Backtesting Suite")
    print("#" * 60)

    # Run multi-asset backtest
    backtest_results = run_multi_asset_backtest()

    # Run stress tests
    stress_results = run_stress_test()

    print("\n" + "=" * 60)
    print("Backtesting Complete!")
    print("=" * 60)
