#!/usr/bin/env python3
"""
Stress Test Script

Tests the trained model against historical crash scenarios to evaluate
robustness and survival probability.

Usage:
    python scripts/stress_test.py --model models/ppo_agent.pt
    python scripts/stress_test.py --scenario covid_crash_2020
    python scripts/stress_test.py --all  # Run all scenarios
"""

import sys
import os
import argparse
import json
from datetime import datetime
from typing import Dict, List, Any
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.rl.reality_gap import (
    StressTestScenarios,
    MonteCarloSimulator,
    SlippageModel,
)
from modules.rl.ppo_agent import PPOAgent


def load_model(model_path: str) -> PPOAgent:
    """Load trained PPO agent"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    # Get state/action dims from the model file
    import torch
    checkpoint = torch.load(model_path, map_location='cpu')

    # Infer dimensions from checkpoint
    if 'policy_net.0.weight' in checkpoint:
        state_dim = checkpoint['policy_net.0.weight'].shape[1]
        action_dim = checkpoint['policy_net.4.weight'].shape[0]
    else:
        # Default dimensions
        state_dim = 1007  # 50*20 + 4 + 3
        action_dim = 4

    agent = PPOAgent(state_dim=state_dim, action_dim=action_dim)
    agent.load(model_path)
    return agent


def run_scenario_test(
    agent: PPOAgent,
    scenario_name: str,
    initial_capital: float = 10000.0,
    n_monte_carlo: int = 100,
) -> Dict[str, Any]:
    """
    Run a stress test scenario with Monte Carlo simulation.

    Returns detailed results including survival rate and drawdown statistics.
    """
    scenario = StressTestScenarios.get_scenario(scenario_name)
    if not scenario:
        return {'error': f'Unknown scenario: {scenario_name}'}

    print(f"\n{'='*60}")
    print(f"STRESS TEST: {scenario['name']}")
    print(f"{'='*60}")
    print(f"Description: {scenario['description']}")
    print(f"Duration: {scenario['duration_days']} days")
    print(f"Max Drawdown: {scenario['max_drawdown']*100:.1f}%")
    print(f"Volatility Spike: {scenario['volatility_spike']}x normal")
    print(f"Liquidity: {scenario['liquidity_factor']*100:.0f}% normal")
    print()

    # Generate stress scenario data
    stress_data = StressTestScenarios.generate_stress_data(
        scenario_name,
        base_price=50000.0,
        n_features=20
    )

    prices = stress_data[:, 0]

    # Run Monte Carlo simulations
    print(f"Running {n_monte_carlo} Monte Carlo simulations...")

    results = []
    slippage_model = SlippageModel(
        base_slippage=0.002 * scenario['volatility_spike'],  # Higher slippage in crash
        volatility_multiplier=1.0,
    )

    for sim in range(n_monte_carlo):
        capital = initial_capital
        position = 0.0
        entry_price = 0.0
        max_capital = initial_capital
        max_drawdown = 0.0
        trades = 0

        # Build state for agent
        lookback = 50

        for t in range(lookback, len(prices)):
            # Build observation (simplified)
            window = stress_data[t-lookback:t]
            obs = []

            # Normalize prices
            price_mean = np.mean(window[:, 0])
            price_std = np.std(window[:, 0]) + 1e-8
            normalized_prices = (window[:, 0] - price_mean) / price_std
            obs.extend(normalized_prices)

            # Add other features
            for i in range(1, min(20, window.shape[1])):
                feature = np.clip(window[:, i], -5, 5)
                obs.extend(feature)

            # Pad to expected size
            while len(obs) < 50 * 20:
                obs.append(0.0)

            # Position features
            pos_enc = 1.0 if position > 0 else (-1.0 if position < 0 else 0.0)
            obs.append(pos_enc)

            # Unrealized P&L
            if position > 0:
                unrealized = (prices[t] - entry_price) / entry_price
            else:
                unrealized = 0.0
            obs.append(np.clip(unrealized, -1, 1))

            # Holding time, position size
            obs.append(0.1)  # Normalized holding time
            obs.append(0.1 if position > 0 else 0.0)

            # Account features
            equity_change = (capital - initial_capital) / initial_capital
            obs.append(np.clip(equity_change, -1, 1))

            drawdown = (max_capital - capital) / max_capital if max_capital > 0 else 0
            obs.append(np.clip(drawdown, 0, 1))

            obs.append(0.02)  # Recent volatility

            obs = np.array(obs, dtype=np.float32)

            # Get agent action
            action, _, _ = agent.select_action(obs, training=False)

            current_price = prices[t]

            # Execute action with realistic slippage
            if action == 1 and position == 0:  # BUY
                slippage = slippage_model.calculate_slippage(
                    current_price, 'buy',
                    volatility=0.05 * scenario['volatility_spike']
                )
                exec_price = current_price * (1 + slippage)
                position = capital * 0.1 / exec_price
                entry_price = exec_price
                capital -= capital * 0.002  # Commission
                trades += 1

            elif action == 2 and position > 0:  # SELL
                slippage = slippage_model.calculate_slippage(
                    current_price, 'sell',
                    volatility=0.05 * scenario['volatility_spike']
                )
                exec_price = current_price * (1 - slippage)
                pnl = position * (exec_price - entry_price)
                capital += pnl
                capital -= capital * 0.002  # Commission
                position = 0.0
                trades += 1

            elif action == 3 and position > 0:  # CLOSE
                slippage = slippage_model.calculate_slippage(
                    current_price, 'sell',
                    volatility=0.05 * scenario['volatility_spike']
                )
                exec_price = current_price * (1 - slippage)
                pnl = position * (exec_price - entry_price)
                capital += pnl
                capital -= capital * 0.002  # Commission
                position = 0.0
                trades += 1

            # Update equity with unrealized
            if position > 0:
                equity = capital + position * (current_price - entry_price)
            else:
                equity = capital

            max_capital = max(max_capital, equity)
            current_dd = (max_capital - equity) / max_capital if max_capital > 0 else 0
            max_drawdown = max(max_drawdown, current_dd)

        # Close any remaining position
        if position > 0:
            final_price = prices[-1] * (1 - 0.005)  # Slippage on exit
            pnl = position * (final_price - entry_price)
            capital += pnl

        results.append({
            'final_capital': capital,
            'return_pct': (capital - initial_capital) / initial_capital * 100,
            'max_drawdown': max_drawdown * 100,
            'trades': trades,
            'survived': capital > initial_capital * 0.5,  # Lost less than 50%
        })

    # Analyze results
    returns = [r['return_pct'] for r in results]
    drawdowns = [r['max_drawdown'] for r in results]
    survival_rate = sum(1 for r in results if r['survived']) / len(results)

    analysis = {
        'scenario': scenario_name,
        'scenario_name': scenario['name'],
        'description': scenario['description'],
        'n_simulations': n_monte_carlo,
        'initial_capital': initial_capital,
        'results': {
            'mean_return': np.mean(returns),
            'std_return': np.std(returns),
            'median_return': np.median(returns),
            'min_return': np.min(returns),
            'max_return': np.max(returns),
            'percentile_5': np.percentile(returns, 5),
            'percentile_95': np.percentile(returns, 95),
            'mean_max_drawdown': np.mean(drawdowns),
            'worst_drawdown': np.max(drawdowns),
            'survival_rate': survival_rate,
            'probability_profit': sum(1 for r in returns if r > 0) / len(returns),
        }
    }

    # Print results
    print("RESULTS:")
    print(f"  Survival Rate:     {survival_rate*100:.1f}%")
    print(f"  Mean Return:       {np.mean(returns):+.2f}%")
    print(f"  Median Return:     {np.median(returns):+.2f}%")
    print(f"  Worst Case:        {np.min(returns):+.2f}%")
    print(f"  Best Case:         {np.max(returns):+.2f}%")
    print(f"  5th Percentile:    {np.percentile(returns, 5):+.2f}%")
    print(f"  95th Percentile:   {np.percentile(returns, 95):+.2f}%")
    print(f"  Mean Max Drawdown: {np.mean(drawdowns):.1f}%")
    print(f"  Worst Drawdown:    {np.max(drawdowns):.1f}%")
    print(f"  Probability Profit:{sum(1 for r in returns if r > 0)/len(returns)*100:.1f}%")

    # Verdict
    print()
    if survival_rate >= 0.9 and np.mean(returns) > -10:
        print("VERDICT: [PASS] Strategy shows good crash resilience")
    elif survival_rate >= 0.7:
        print("VERDICT: [CAUTION] Strategy survives but needs improvement")
    else:
        print("VERDICT: [FAIL] Strategy vulnerable to crashes - needs work")

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Stress test trading model against crash scenarios")
    parser.add_argument("--model", "-m", type=str, default="models/ppo_agent.pt",
                       help="Path to trained model")
    parser.add_argument("--scenario", "-s", type=str, default=None,
                       help="Specific scenario to test")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Run all scenarios")
    parser.add_argument("--monte-carlo", "-n", type=int, default=100,
                       help="Number of Monte Carlo simulations")
    parser.add_argument("--capital", "-c", type=float, default=10000.0,
                       help="Initial capital")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="Save results to JSON file")

    args = parser.parse_args()

    print("=" * 60)
    print("JJ-BOT STRESS TEST")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Monte Carlo Runs: {args.monte_carlo}")
    print(f"Initial Capital: ${args.capital:,.2f}")

    # Load model
    try:
        agent = load_model(args.model)
        print(f"Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        print("\nRunning with random actions for demonstration...")
        agent = None

    # Determine scenarios to run
    if args.all:
        scenarios = StressTestScenarios.list_scenarios()
    elif args.scenario:
        scenarios = [args.scenario]
    else:
        # Default: run the most important crash scenarios
        scenarios = ['covid_crash_2020', 'ftx_collapse_2022', 'flash_crash']

    print(f"\nScenarios to test: {', '.join(scenarios)}")

    # Run tests
    all_results = []

    for scenario in scenarios:
        if agent:
            result = run_scenario_test(
                agent, scenario,
                initial_capital=args.capital,
                n_monte_carlo=args.monte_carlo
            )
        else:
            # Demo mode with fake results
            result = {
                'scenario': scenario,
                'note': 'Demo mode - no model loaded',
                'survival_rate': 0.0,
            }

        all_results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("STRESS TEST SUMMARY")
    print("=" * 60)

    passed = 0
    for result in all_results:
        if 'error' in result:
            status = "ERROR"
        elif result.get('results', {}).get('survival_rate', 0) >= 0.7:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"

        print(f"  {result.get('scenario_name', result['scenario'])}: {status}")

    print()
    print(f"Overall: {passed}/{len(all_results)} scenarios passed")

    if passed == len(all_results):
        print("\n[SUCCESS] Model shows good resilience across all crash scenarios!")
    elif passed >= len(all_results) // 2:
        print("\n[CAUTION] Model survives some crashes but vulnerable to others")
    else:
        print("\n[WARNING] Model needs significant work on crash resilience")

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'model': args.model,
                'n_simulations': args.monte_carlo,
                'results': all_results,
                'summary': {
                    'passed': passed,
                    'total': len(all_results),
                }
            }, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
