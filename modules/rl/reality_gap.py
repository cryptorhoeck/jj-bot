"""
Reality Gap Mitigation Module

This module bridges the gap between backtesting/training and real trading by:
1. Dynamic slippage simulation based on volatility
2. Randomized execution delays
3. Historical stress testing against real market crashes
4. Monte Carlo simulation for robustness testing

Key insight: Backtests are always optimistic. This module makes training
more pessimistic to produce strategies that survive real markets.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)


@dataclass
class SlippageModel:
    """
    Realistic slippage model that varies with market conditions.

    Real-world slippage depends on:
    - Order size relative to liquidity
    - Market volatility (higher vol = more slippage)
    - Time of day (less liquidity = more slippage)
    - Market direction (selling into a falling market = more slippage)
    """
    base_slippage: float = 0.001  # 0.1% minimum
    volatility_multiplier: float = 0.5  # How much volatility affects slippage
    size_impact: float = 0.1  # Impact of large orders
    random_factor_range: Tuple[float, float] = (0.5, 2.0)  # Randomization range

    def calculate_slippage(
        self,
        price: float,
        side: str,  # 'buy' or 'sell'
        volatility: float,  # Current market volatility (e.g., ATR/price)
        order_size_pct: float = 0.1,  # Order size as % of typical volume
        price_momentum: float = 0.0,  # Recent price direction
    ) -> float:
        """
        Calculate realistic slippage for a trade.

        Returns slippage as a decimal (0.003 = 0.3%)
        """
        # Base slippage
        slippage = self.base_slippage

        # Volatility component (higher volatility = more slippage)
        vol_component = volatility * self.volatility_multiplier
        slippage += vol_component

        # Size impact (larger orders move the market more)
        if order_size_pct > 0.05:  # Orders > 5% of volume
            size_component = (order_size_pct - 0.05) * self.size_impact
            slippage += size_component

        # Momentum impact (trading against momentum = more slippage)
        # If buying and price is falling, or selling and price is rising
        if (side == 'buy' and price_momentum < 0) or (side == 'sell' and price_momentum > 0):
            momentum_penalty = abs(price_momentum) * 0.1
            slippage += momentum_penalty

        # Random factor (market microstructure noise)
        random_mult = random.uniform(*self.random_factor_range)
        slippage *= random_mult

        # Cap at reasonable maximum (5%)
        return min(slippage, 0.05)

    def apply_slippage(
        self,
        price: float,
        side: str,
        volatility: float = 0.02,
        order_size_pct: float = 0.1,
        price_momentum: float = 0.0,
    ) -> float:
        """Apply slippage to get execution price"""
        slippage = self.calculate_slippage(
            price, side, volatility, order_size_pct, price_momentum
        )

        if side == 'buy':
            return price * (1 + slippage)  # Pay more when buying
        else:
            return price * (1 - slippage)  # Receive less when selling


@dataclass
class ExecutionModel:
    """
    Models realistic order execution including:
    - Latency (price can move between decision and execution)
    - Partial fills (large orders may not fill completely)
    - Requotes/rejections
    """
    latency_ms_range: Tuple[int, int] = (50, 500)  # 50-500ms typical
    partial_fill_probability: float = 0.05  # 5% chance of partial fill
    rejection_probability: float = 0.02  # 2% chance of rejection
    price_move_per_100ms: float = 0.0005  # 0.05% price move per 100ms

    def simulate_execution(
        self,
        intended_price: float,
        side: str,
        volatility: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Simulate order execution with realistic delays and fills.

        Returns dict with:
        - executed: bool
        - execution_price: float
        - fill_ratio: float (1.0 = full fill)
        - latency_ms: int
        - slipped_price: float
        """
        # Simulate latency
        latency_ms = random.randint(*self.latency_ms_range)

        # Check for rejection
        if random.random() < self.rejection_probability:
            return {
                'executed': False,
                'execution_price': 0.0,
                'fill_ratio': 0.0,
                'latency_ms': latency_ms,
                'rejection_reason': 'market_moved'
            }

        # Calculate price movement during latency
        price_move_pct = (latency_ms / 100) * self.price_move_per_100ms * volatility * 10
        # Random direction, biased against trader
        if side == 'buy':
            price_move = random.uniform(0, price_move_pct)  # Price goes up
        else:
            price_move = -random.uniform(0, price_move_pct)  # Price goes down

        slipped_price = intended_price * (1 + price_move)

        # Determine fill ratio
        if random.random() < self.partial_fill_probability:
            fill_ratio = random.uniform(0.5, 0.95)
        else:
            fill_ratio = 1.0

        return {
            'executed': True,
            'execution_price': slipped_price,
            'fill_ratio': fill_ratio,
            'latency_ms': latency_ms,
            'slipped_price': slipped_price
        }


class StressTestScenarios:
    """
    Historical crash scenarios for stress testing trading strategies.

    Each scenario represents a real market crash with:
    - Date range
    - Price path (daily returns)
    - Volatility spike
    - Liquidity conditions
    """

    SCENARIOS = {
        'covid_crash_2020': {
            'name': 'COVID-19 Crash (March 2020)',
            'description': 'BTC dropped 50%+ in 24 hours',
            'duration_days': 7,
            'max_drawdown': 0.50,  # 50% drop
            'volatility_spike': 5.0,  # 5x normal volatility
            'liquidity_factor': 0.3,  # 30% normal liquidity
            'daily_returns': [-0.08, -0.25, -0.15, -0.10, 0.05, 0.08, 0.12],
        },
        'crypto_crash_may_2021': {
            'name': 'China Ban Crash (May 2021)',
            'description': 'BTC dropped 50% over 2 weeks',
            'duration_days': 14,
            'max_drawdown': 0.55,
            'volatility_spike': 4.0,
            'liquidity_factor': 0.4,
            'daily_returns': [-0.05, -0.12, -0.08, -0.03, 0.02, -0.10, -0.15,
                             -0.05, 0.03, -0.08, -0.04, 0.05, 0.08, 0.10],
        },
        'ftx_collapse_2022': {
            'name': 'FTX Collapse (November 2022)',
            'description': 'Exchange collapse caused 25% drop',
            'duration_days': 10,
            'max_drawdown': 0.30,
            'volatility_spike': 3.5,
            'liquidity_factor': 0.2,  # Very low liquidity
            'daily_returns': [-0.05, -0.12, -0.10, -0.05, -0.03, 0.02, 0.03, 0.05, 0.02, 0.01],
        },
        'flash_crash': {
            'name': 'Generic Flash Crash',
            'description': 'Sudden 20% drop and recovery',
            'duration_days': 3,
            'max_drawdown': 0.25,
            'volatility_spike': 8.0,  # Extreme volatility
            'liquidity_factor': 0.1,  # Almost no liquidity
            'daily_returns': [-0.20, 0.10, 0.08],
        },
        'bear_market_grind': {
            'name': 'Prolonged Bear Market',
            'description': 'Slow bleed over 30 days',
            'duration_days': 30,
            'max_drawdown': 0.40,
            'volatility_spike': 1.5,  # Slightly elevated
            'liquidity_factor': 0.7,
            'daily_returns': [-0.02] * 20 + [0.01] * 10,  # Mostly down
        },
    }

    @classmethod
    def get_scenario(cls, name: str) -> Dict:
        """Get a specific crash scenario"""
        return cls.SCENARIOS.get(name, {})

    @classmethod
    def list_scenarios(cls) -> List[str]:
        """List available scenarios"""
        return list(cls.SCENARIOS.keys())

    @classmethod
    def generate_stress_data(
        cls,
        scenario_name: str,
        base_price: float = 50000.0,
        n_features: int = 20,
    ) -> np.ndarray:
        """
        Generate synthetic price data for a stress scenario.

        Returns feature array similar to training data format.
        """
        scenario = cls.SCENARIOS.get(scenario_name)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        daily_returns = scenario['daily_returns']
        n_days = len(daily_returns)

        # Generate minute-level data (1440 minutes per day)
        candles_per_day = 60  # Hourly candles for efficiency
        n_candles = n_days * candles_per_day

        prices = [base_price]
        for day_idx, day_return in enumerate(daily_returns):
            # Distribute daily return across candles with noise
            candle_return = day_return / candles_per_day
            vol_spike = scenario['volatility_spike']

            for _ in range(candles_per_day):
                noise = np.random.normal(0, 0.01 * vol_spike)
                new_price = prices[-1] * (1 + candle_return + noise)
                prices.append(max(new_price, 1.0))  # Floor at $1

        prices = np.array(prices[1:])  # Remove initial price

        # Build feature array (simplified version)
        features = np.zeros((len(prices), n_features), dtype=np.float32)
        features[:, 0] = prices  # Close price

        # Returns
        features[1:, 1] = np.diff(prices) / prices[:-1]

        # Volatility (rolling 20-period std)
        for i in range(20, len(prices)):
            features[i, 3] = np.std(features[i-20:i, 1]) * vol_spike

        # RSI (simplified)
        features[:, 4] = 0.3  # Oversold during crash

        return features


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy robustness testing.

    Runs thousands of simulations with randomized:
    - Entry/exit timing (±few candles)
    - Slippage amounts
    - Fee variations
    - Partial fills

    Produces distribution of outcomes rather than single backtest result.
    """

    def __init__(
        self,
        n_simulations: int = 1000,
        timing_jitter_candles: int = 3,
        slippage_range: Tuple[float, float] = (0.001, 0.005),
        fee_range: Tuple[float, float] = (0.001, 0.003),
        fill_rate_range: Tuple[float, float] = (0.8, 1.0),
    ):
        self.n_simulations = n_simulations
        self.timing_jitter_candles = timing_jitter_candles
        self.slippage_range = slippage_range
        self.fee_range = fee_range
        self.fill_rate_range = fill_rate_range

        self.results: List[Dict] = []

    def run_simulation(
        self,
        trades: List[Dict],  # List of trade signals: {'time': t, 'side': 'buy/sell', 'price': p}
        price_data: np.ndarray,  # Price array
        initial_capital: float = 10000.0,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation on a set of trade signals.

        Returns distribution of outcomes.
        """
        results = []

        for sim in range(self.n_simulations):
            # Randomize parameters for this simulation
            slippage = random.uniform(*self.slippage_range)
            fee = random.uniform(*self.fee_range)
            fill_rate = random.uniform(*self.fill_rate_range)

            # Simulate trades
            capital = initial_capital
            position = 0.0
            entry_price = 0.0

            for trade in trades:
                # Apply timing jitter
                jitter = random.randint(-self.timing_jitter_candles, self.timing_jitter_candles)
                exec_time = max(0, min(len(price_data) - 1, trade['time'] + jitter))
                exec_price = price_data[exec_time]

                # Apply slippage
                if trade['side'] == 'buy':
                    exec_price *= (1 + slippage)
                else:
                    exec_price *= (1 - slippage)

                # Apply fees
                fee_cost = capital * 0.1 * fee  # 10% position, fee applied

                # Apply fill rate
                actual_fill = fill_rate

                if trade['side'] == 'buy' and position == 0:
                    position = capital * 0.1 * actual_fill / exec_price
                    entry_price = exec_price
                    capital -= fee_cost
                elif trade['side'] == 'sell' and position > 0:
                    pnl = position * (exec_price - entry_price)
                    capital += pnl - fee_cost
                    position = 0.0

            # Close any open position at end
            if position > 0:
                final_price = price_data[-1] * (1 - slippage)
                pnl = position * (final_price - entry_price)
                capital += pnl

            results.append({
                'final_capital': capital,
                'return_pct': (capital - initial_capital) / initial_capital * 100,
                'slippage_used': slippage,
                'fee_used': fee,
            })

        self.results = results
        return self._analyze_results(results, initial_capital)

    def _analyze_results(self, results: List[Dict], initial_capital: float) -> Dict[str, Any]:
        """Analyze Monte Carlo results"""
        returns = [r['return_pct'] for r in results]

        return {
            'n_simulations': len(results),
            'mean_return': np.mean(returns),
            'std_return': np.std(returns),
            'median_return': np.median(returns),
            'min_return': np.min(returns),
            'max_return': np.max(returns),
            'percentile_5': np.percentile(returns, 5),
            'percentile_25': np.percentile(returns, 25),
            'percentile_75': np.percentile(returns, 75),
            'percentile_95': np.percentile(returns, 95),
            'probability_profit': sum(1 for r in returns if r > 0) / len(returns),
            'probability_loss_10pct': sum(1 for r in returns if r < -10) / len(returns),
            'expected_value': np.mean(returns),
            'value_at_risk_95': np.percentile(returns, 5),  # 5th percentile = 95% VaR
        }


def apply_realistic_costs(
    env_config: Dict,
    pessimism_level: str = 'moderate'
) -> Dict:
    """
    Apply realistic cost parameters to training environment.

    Pessimism levels:
    - 'optimistic': Best-case (dangerous for live trading)
    - 'moderate': Reasonable real-world estimate
    - 'pessimistic': Worst-case (safest for live trading)
    """
    cost_profiles = {
        'optimistic': {
            'commission': 0.001,  # 0.1%
            'slippage': 0.001,    # 0.1%
            'spread': 0.0005,     # 0.05%
        },
        'moderate': {
            'commission': 0.002,  # 0.2%
            'slippage': 0.003,    # 0.3%
            'spread': 0.001,      # 0.1%
        },
        'pessimistic': {
            'commission': 0.003,  # 0.3%
            'slippage': 0.005,    # 0.5%
            'spread': 0.002,      # 0.2%
        },
    }

    profile = cost_profiles.get(pessimism_level, cost_profiles['moderate'])

    env_config.update(profile)

    # Log the total round-trip cost
    total_cost = (profile['commission'] + profile['slippage'] + profile['spread']) * 2
    logger.info(f"Training with {pessimism_level} costs: {total_cost*100:.2f}% round-trip")

    return env_config


class WalkForwardValidator:
    """
    Walk-forward validation for strategy robustness.

    Instead of a single train/test split, uses rolling windows:
    1. Train on Period 1, Test on Period 2
    2. Train on Period 1+2, Test on Period 3
    3. Train on Period 1+2+3, Test on Period 4
    ...

    This tests how well the strategy adapts to changing markets.
    """

    def __init__(
        self,
        n_folds: int = 5,
        train_ratio: float = 0.7,
        min_train_samples: int = 1000,
    ):
        self.n_folds = n_folds
        self.train_ratio = train_ratio
        self.min_train_samples = min_train_samples
        self.fold_results: List[Dict] = []

    def create_folds(self, data: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Create walk-forward validation folds.

        Returns list of (train_data, test_data) tuples.
        """
        n_samples = len(data)
        folds = []

        # Calculate fold size
        fold_size = n_samples // (self.n_folds + 1)

        for fold in range(self.n_folds):
            # Expanding window: train on all previous data
            train_end = (fold + 1) * fold_size
            test_start = train_end
            test_end = test_start + fold_size

            if train_end < self.min_train_samples:
                continue
            if test_end > n_samples:
                test_end = n_samples

            train_data = data[:train_end]
            test_data = data[test_start:test_end]

            folds.append((train_data, test_data))

            logger.debug(f"Fold {fold+1}: Train[0:{train_end}] ({len(train_data)}), "
                        f"Test[{test_start}:{test_end}] ({len(test_data)})")

        return folds

    def summarize_results(self) -> Dict[str, Any]:
        """Summarize walk-forward validation results"""
        if not self.fold_results:
            return {}

        returns = [r.get('return_pct', 0) for r in self.fold_results]
        win_rates = [r.get('win_rate', 0) for r in self.fold_results]

        return {
            'n_folds': len(self.fold_results),
            'mean_return': np.mean(returns),
            'std_return': np.std(returns),
            'min_return': np.min(returns),
            'max_return': np.max(returns),
            'mean_win_rate': np.mean(win_rates),
            'consistency': sum(1 for r in returns if r > 0) / len(returns),  # % profitable folds
            'fold_details': self.fold_results,
        }


# Convenience functions for easy use

def get_realistic_slippage(
    price: float,
    side: str,
    volatility: float = 0.02,
) -> float:
    """Quick function to get realistic slippage-adjusted price"""
    model = SlippageModel()
    return model.apply_slippage(price, side, volatility)


def run_stress_test(
    strategy_func,  # Function that takes price data and returns trades
    scenario_name: str = 'covid_crash_2020',
    initial_capital: float = 10000.0,
) -> Dict[str, Any]:
    """
    Run a strategy through a historical crash scenario.

    Args:
        strategy_func: Function(price_data) -> List[trades]
        scenario_name: Name of crash scenario
        initial_capital: Starting capital

    Returns:
        Performance metrics during the crash
    """
    scenario = StressTestScenarios.get_scenario(scenario_name)
    if not scenario:
        return {'error': f'Unknown scenario: {scenario_name}'}

    # Generate stress data
    stress_data = StressTestScenarios.generate_stress_data(scenario_name)

    # Run strategy
    try:
        trades = strategy_func(stress_data[:, 0])  # Pass price data

        # Simulate with high slippage/low liquidity
        slippage = 0.005 * scenario['volatility_spike']  # Elevated slippage

        capital = initial_capital
        position = 0.0
        entry_price = 0.0
        max_capital = initial_capital
        max_drawdown = 0.0

        for trade in trades:
            exec_price = stress_data[trade['time'], 0]

            if trade['side'] == 'buy':
                exec_price *= (1 + slippage)
                position = capital * 0.1 / exec_price
                entry_price = exec_price
            elif trade['side'] == 'sell' and position > 0:
                exec_price *= (1 - slippage)
                pnl = position * (exec_price - entry_price)
                capital += pnl
                position = 0.0

            max_capital = max(max_capital, capital)
            drawdown = (max_capital - capital) / max_capital
            max_drawdown = max(max_drawdown, drawdown)

        return {
            'scenario': scenario_name,
            'scenario_description': scenario['description'],
            'initial_capital': initial_capital,
            'final_capital': capital,
            'return_pct': (capital - initial_capital) / initial_capital * 100,
            'max_drawdown_pct': max_drawdown * 100,
            'scenario_max_drawdown': scenario['max_drawdown'] * 100,
            'survived': capital > initial_capital * 0.5,  # Survived if lost <50%
        }
    except Exception as e:
        return {
            'scenario': scenario_name,
            'error': str(e),
            'survived': False,
        }


# Export all classes and functions
__all__ = [
    'SlippageModel',
    'ExecutionModel',
    'StressTestScenarios',
    'MonteCarloSimulator',
    'WalkForwardValidator',
    'apply_realistic_costs',
    'get_realistic_slippage',
    'run_stress_test',
]
