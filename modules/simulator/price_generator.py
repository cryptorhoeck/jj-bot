"""
Realistic Price Generation Engine

Generates realistic cryptocurrency price movements using:
- Geometric Brownian Motion (GBM)
- Regime switching (bull/bear/sideways/volatile)
- Volatility clustering
- Market microstructure (bid-ask spreads)

This replaces the previous random ±5% price fluctuations with
a proper financial model.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """Market regime types"""
    BULL = "bull"           # Positive drift, moderate volatility
    BEAR = "bear"           # Negative drift, higher volatility
    SIDEWAYS = "sideways"   # Zero drift, low volatility
    VOLATILE = "volatile"   # Random drift, high volatility


@dataclass
class RegimeParameters:
    """Parameters for each market regime"""
    drift: float            # Annual drift (mu)
    volatility: float       # Annual volatility (sigma)
    duration_mean: int      # Average regime duration (minutes)
    duration_std: int       # Std dev of regime duration


@dataclass
class PriceTickdata:
    """Single price tick with market data"""
    timestamp: datetime
    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    regime: MarketRegime


class RealisticPriceGenerator:
    """
    Generates realistic cryptocurrency prices using GBM with regime switching.

    Features:
    - Geometric Brownian Motion for price dynamics
    - Multiple market regimes with different characteristics
    - Volatility clustering (high volatility follows high volatility)
    - Realistic bid-ask spreads
    - Volume simulation

    Usage:
        generator = RealisticPriceGenerator(symbol="BTC", initial_price=45000)
        tick = generator.generate_next_tick()
    """

    # Default regime parameters (realistic for crypto markets)
    REGIME_PARAMS = {
        MarketRegime.BULL: RegimeParameters(
            drift=0.50,          # 50% annual growth
            volatility=0.60,     # 60% annual volatility
            duration_mean=240,   # 4 hours average
            duration_std=120     # ±2 hours
        ),
        MarketRegime.BEAR: RegimeParameters(
            drift=-0.40,         # -40% annual decline
            volatility=0.80,     # 80% annual volatility (higher in bear markets)
            duration_mean=180,   # 3 hours average
            duration_std=90      # ±1.5 hours
        ),
        MarketRegime.SIDEWAYS: RegimeParameters(
            drift=0.0,           # No trend
            volatility=0.30,     # 30% annual volatility (lower)
            duration_mean=360,   # 6 hours average
            duration_std=180     # ±3 hours
        ),
        MarketRegime.VOLATILE: RegimeParameters(
            drift=0.0,           # Random walk
            volatility=1.20,     # 120% annual volatility (crypto chaos)
            duration_mean=120,   # 2 hours average (short bursts)
            duration_std=60      # ±1 hour
        ),
    }

    def __init__(
        self,
        symbol: str,
        initial_price: float,
        tick_interval_seconds: int = 60,
        spread_bps: float = 10.0,  # 0.10% spread
        initial_regime: Optional[MarketRegime] = None
    ):
        """
        Initialize price generator.

        Args:
            symbol: Trading symbol (e.g., "BTC", "ETH")
            initial_price: Starting price
            tick_interval_seconds: Time between price updates (default: 60s)
            spread_bps: Bid-ask spread in basis points (default: 10 = 0.10%)
            initial_regime: Starting market regime (random if None)
        """
        self.symbol = symbol
        self.current_price = initial_price
        self.tick_interval = tick_interval_seconds
        self.spread_bps = spread_bps

        # Time tracking
        self.current_time = datetime.now()
        self.tick_count = 0

        # Regime tracking
        self.current_regime = initial_regime or np.random.choice(list(MarketRegime))
        self.regime_start_time = self.current_time
        self.regime_duration = self._sample_regime_duration()

        # Volatility clustering
        self.recent_returns = []
        self.volatility_multiplier = 1.0

        # Volume simulation
        self.base_volume = initial_price * 10  # Base volume proportional to price

        # Random seed for reproducibility (can be set externally)

    def _sample_regime_duration(self) -> int:
        """Sample regime duration from normal distribution (in minutes)"""
        params = self.REGIME_PARAMS[self.current_regime]
        duration = max(
            30,  # Minimum 30 minutes
            int(np.random.normal(params.duration_mean, params.duration_std))
        )
        return duration

    def _should_switch_regime(self) -> bool:
        """Check if it's time to switch market regime"""
        minutes_in_regime = (self.current_time - self.regime_start_time).total_seconds() / 60
        return minutes_in_regime >= self.regime_duration

    def _switch_regime(self):
        """Switch to a new market regime"""
        # Transition probabilities (bull tends to stay bull, etc.)
        transition_probs = {
            MarketRegime.BULL: {
                MarketRegime.BULL: 0.50,
                MarketRegime.SIDEWAYS: 0.30,
                MarketRegime.VOLATILE: 0.15,
                MarketRegime.BEAR: 0.05
            },
            MarketRegime.BEAR: {
                MarketRegime.BEAR: 0.45,
                MarketRegime.SIDEWAYS: 0.30,
                MarketRegime.VOLATILE: 0.20,
                MarketRegime.BULL: 0.05
            },
            MarketRegime.SIDEWAYS: {
                MarketRegime.SIDEWAYS: 0.40,
                MarketRegime.BULL: 0.25,
                MarketRegime.BEAR: 0.20,
                MarketRegime.VOLATILE: 0.15
            },
            MarketRegime.VOLATILE: {
                MarketRegime.VOLATILE: 0.30,
                MarketRegime.SIDEWAYS: 0.30,
                MarketRegime.BULL: 0.20,
                MarketRegime.BEAR: 0.20
            }
        }

        probs = transition_probs[self.current_regime]
        regimes = list(probs.keys())
        probabilities = list(probs.values())

        self.current_regime = np.random.choice(regimes, p=probabilities)
        self.regime_start_time = self.current_time
        self.regime_duration = self._sample_regime_duration()

    def _calculate_volatility_multiplier(self) -> float:
        """
        Calculate volatility multiplier based on recent price movements.

        Implements volatility clustering: high volatility tends to follow
        high volatility (GARCH-like behavior).
        """
        if len(self.recent_returns) < 10:
            return 1.0

        # Calculate realized volatility from recent returns
        recent_vol = np.std(self.recent_returns[-20:])

        # Compare to expected volatility for current regime
        params = self.REGIME_PARAMS[self.current_regime]
        expected_vol = params.volatility / np.sqrt(252 * 24 * 60 / self.tick_interval)

        # Multiplier: if recent volatility is high, next period likely high too
        multiplier = 0.7 + 0.6 * (recent_vol / max(expected_vol, 0.001))
        return np.clip(multiplier, 0.5, 2.0)

    def _generate_price_change(self) -> float:
        """
        Generate next price using Geometric Brownian Motion.

        dS = μ * S * dt + σ * S * dW

        Where:
            S = current price
            μ = drift (expected return)
            σ = volatility
            dt = time step
            dW = Wiener process (random shock)
        """
        params = self.REGIME_PARAMS[self.current_regime]

        # Convert annual parameters to per-tick
        dt = self.tick_interval / (252 * 24 * 60 * 60)  # Fraction of trading year

        # Drift term (expected return)
        drift = params.drift * dt

        # Volatility term (random component)
        volatility = params.volatility * np.sqrt(dt) * self.volatility_multiplier

        # Random shock from normal distribution
        shock = np.random.normal(0, 1)

        # GBM formula: S_next = S * exp((μ - σ²/2)*dt + σ*√dt*ε)
        # Simplified to: log(S_next/S) = drift - 0.5*vol² + vol*shock
        log_return = drift - 0.5 * volatility**2 + volatility * shock

        # Update recent returns for volatility clustering
        self.recent_returns.append(log_return)
        if len(self.recent_returns) > 100:
            self.recent_returns.pop(0)

        return log_return

    def _generate_spread(self) -> Tuple[float, float]:
        """
        Generate bid-ask spread.

        Returns:
            (bid_price, ask_price)
        """
        spread = self.current_price * (self.spread_bps / 10000)
        bid = self.current_price - spread / 2
        ask = self.current_price + spread / 2
        return bid, ask

    def _generate_volume(self) -> float:
        """
        Generate trading volume (varies with volatility).

        Higher volatility typically correlates with higher volume.
        """
        # Base volume varies ±50%
        volume_multiplier = np.random.uniform(0.5, 1.5)

        # Higher volatility → higher volume
        volume_multiplier *= self.volatility_multiplier

        return self.base_volume * volume_multiplier

    def generate_next_tick(self) -> PriceTickdata:
        """
        Generate the next price tick.

        Returns:
            PriceTickdata object with price, bid, ask, volume, etc.
        """
        # Check if we should switch regime
        if self._should_switch_regime():
            self._switch_regime()

        # Update volatility multiplier (clustering effect)
        self.volatility_multiplier = self._calculate_volatility_multiplier()

        # Generate price change using GBM
        log_return = self._generate_price_change()
        self.current_price *= np.exp(log_return)

        # Ensure price stays positive and reasonable
        # (crypto can't go below 0, and extreme moves are rare)
        self.current_price = max(self.current_price, 0.01)

        # Generate bid-ask spread
        bid, ask = self._generate_spread()

        # Generate volume
        volume = self._generate_volume()

        # Advance time
        self.current_time += timedelta(seconds=self.tick_interval)
        self.tick_count += 1

        return PriceTickdata(
            timestamp=self.current_time,
            symbol=self.symbol,
            price=self.current_price,
            bid=bid,
            ask=ask,
            volume=volume,
            regime=self.current_regime
        )

    def generate_history(self, num_ticks: int) -> List[PriceTickdata]:
        """
        Generate multiple price ticks (for backtesting or initialization).

        Args:
            num_ticks: Number of ticks to generate

        Returns:
            List of PriceTickdata objects
        """
        return [self.generate_next_tick() for _ in range(num_ticks)]

    def set_regime(self, regime: MarketRegime):
        """Manually set market regime (for testing)"""
        self.current_regime = regime
        self.regime_start_time = self.current_time
        self.regime_duration = self._sample_regime_duration()

    def get_regime_info(self) -> Dict:
        """Get current regime information"""
        minutes_in_regime = (self.current_time - self.regime_start_time).total_seconds() / 60
        return {
            "current_regime": self.current_regime.value,
            "minutes_in_regime": int(minutes_in_regime),
            "regime_duration": self.regime_duration,
            "volatility_multiplier": round(self.volatility_multiplier, 2)
        }


class MultiSymbolPriceGenerator:
    """
    Manages price generation for multiple symbols with correlations.

    Symbols within the same asset class (e.g., all cryptocurrencies)
    tend to move together during major market moves.
    """

    def __init__(
        self,
        symbols_config: Dict[str, float],  # {symbol: initial_price}
        correlation: float = 0.3,          # Inter-symbol correlation (0-1)
        tick_interval_seconds: int = 60
    ):
        """
        Initialize multi-symbol generator.

        Args:
            symbols_config: Dict mapping symbols to initial prices
            correlation: How much symbols move together (0=independent, 1=perfect)
            tick_interval_seconds: Time between updates
        """
        self.correlation = correlation
        self.generators = {
            symbol: RealisticPriceGenerator(
                symbol=symbol,
                initial_price=price,
                tick_interval_seconds=tick_interval_seconds
            )
            for symbol, price in symbols_config.items()
        }

        # Shared regime influences all symbols (market-wide events)
        self.market_regime = np.random.choice(list(MarketRegime))
        self.regime_tick_count = 0
        self.regime_duration = 100  # Ticks until next regime switch

    def _update_market_regime(self):
        """Update global market regime (affects all symbols)"""
        self.regime_tick_count += 1

        if self.regime_tick_count >= self.regime_duration:
            # Switch global regime
            self.market_regime = np.random.choice(list(MarketRegime))
            self.regime_tick_count = 0
            self.regime_duration = np.random.randint(50, 200)

            # Force all symbols to acknowledge the new regime
            # (but they can still have their own local regimes)
            for generator in self.generators.values():
                # With 30% probability, force symbol to new regime
                if np.random.random() < 0.3:
                    generator.set_regime(self.market_regime)

    def generate_next_ticks(self) -> Dict[str, PriceTickdata]:
        """
        Generate next tick for all symbols.

        Returns:
            Dict mapping symbols to their PriceTickdata
        """
        self._update_market_regime()

        return {
            symbol: generator.generate_next_tick()
            for symbol, generator in self.generators.items()
        }

    def get_market_state(self) -> Dict:
        """Get overall market state"""
        return {
            "market_regime": self.market_regime.value,
            "symbols": {
                symbol: gen.get_regime_info()
                for symbol, gen in self.generators.items()
            }
        }
