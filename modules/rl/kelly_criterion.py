"""
Kelly Criterion Position Sizing

Calculates optimal position size based on historical trade performance.
Inspired by Renaissance Technologies' approach via Elwyn Berlekamp.

Features:
- Binary Kelly for discrete win/loss outcomes
- Continuous Kelly for portfolio returns
- Fractional Kelly for reduced volatility (half/quarter Kelly)
- Regime-based Kelly adjustment
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class KellyFraction(float, Enum):
    """Standard Kelly fractions for different risk tolerances"""
    FULL = 1.0
    THREE_QUARTER = 0.75
    HALF = 0.5
    QUARTER = 0.25
    TENTH = 0.1


@dataclass
class KellyResult:
    """Result of Kelly Criterion calculation"""
    kelly: float  # Optimal fraction (0-1)
    kelly_pct: float  # As percentage
    win_rate: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    expectancy: float  # Expected value per trade
    recommended_position: str
    regime_multiplier: float = 1.0
    adjusted_kelly: float = 0.0


class KellyCriterion:
    """
    Kelly Criterion calculator for optimal position sizing.

    Supports both binary outcomes (trades) and continuous returns (portfolio).
    Includes regime-based adjustments for risk management.

    Reference: Kelly, J.L. (1956) "A New Interpretation of Information Rate"
    """

    def __init__(
        self,
        kelly_fraction: float = 0.5,
        max_position: float = 0.25,
        min_trades_required: int = 10,
    ):
        """
        Initialize Kelly calculator.

        Parameters
        ----------
        kelly_fraction : float
            Fraction of Kelly to use (0.5 = half Kelly, 1.0 = full Kelly)
            Half Kelly is recommended as it significantly reduces volatility
            while only slightly reducing expected growth rate.
        max_position : float
            Maximum position size as fraction of capital (safety cap)
        min_trades_required : int
            Minimum trades needed for reliable Kelly calculation
        """
        self.kelly_fraction = kelly_fraction
        self.max_position = max_position
        self.min_trades_required = min_trades_required

    def binary_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """
        Calculate Kelly fraction for binary outcomes.

        Formula: f* = W - (1-W)/R

        Where:
            f* = Optimal fraction of capital to bet
            W  = Probability of winning (0-1)
            R  = Win/Loss ratio (avg_win / avg_loss)

        Parameters
        ----------
        win_rate : float
            Probability of winning (0-1)
        avg_win : float
            Average winning trade return (positive value)
        avg_loss : float
            Average losing trade return (positive value, not negative)

        Returns
        -------
        float
            Optimal position size as fraction of capital
        """
        if avg_loss <= 0 or avg_win <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        # Win/loss ratio
        R = avg_win / avg_loss

        # Kelly formula: f* = W - (1-W)/R
        kelly = win_rate - (1 - win_rate) / R

        # Apply fraction and cap
        kelly = kelly * self.kelly_fraction
        kelly = max(0, min(kelly, self.max_position))

        return kelly

    def continuous_kelly(
        self,
        mean_return: float,
        std_return: float,
        risk_free_rate: float = 0.0,
    ) -> float:
        """
        Calculate Kelly fraction for continuous returns (stocks/crypto).

        Formula: f* = (μ - r) / σ²

        Where:
            f* = Optimal fraction
            μ  = Mean return (expected return)
            σ² = Variance of returns
            r  = Risk-free rate

        Parameters
        ----------
        mean_return : float
            Expected return (e.g., 0.08 for 8%)
        std_return : float
            Standard deviation of returns
        risk_free_rate : float
            Risk-free rate (e.g., 0.04 for 4%)

        Returns
        -------
        float
            Optimal position size as fraction of capital
        """
        if std_return <= 0:
            return 0.0

        # Kelly formula: f* = (μ - r) / σ²
        kelly = (mean_return - risk_free_rate) / (std_return ** 2)

        # Apply fraction and cap
        kelly = kelly * self.kelly_fraction
        kelly = max(0, min(kelly, self.max_position))

        return kelly

    def calculate_from_trades(self, trades: List[float]) -> KellyResult:
        """
        Calculate Kelly from a list of trade P&L values.

        Parameters
        ----------
        trades : list
            List of trade P&L values (positive = win, negative = loss)

        Returns
        -------
        KellyResult
            Comprehensive Kelly calculation results
        """
        trades = np.array(trades)

        if len(trades) < self.min_trades_required:
            return KellyResult(
                kelly=0.0,
                kelly_pct=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                win_loss_ratio=0.0,
                expectancy=0.0,
                recommended_position="Insufficient data (need {self.min_trades_required}+ trades)",
            )

        wins = trades[trades > 0]
        losses = trades[trades < 0]

        if len(wins) == 0 or len(losses) == 0:
            # Edge case: all wins or all losses
            if len(wins) == 0:
                return KellyResult(
                    kelly=0.0,
                    kelly_pct=0.0,
                    win_rate=0.0,
                    avg_win=0.0,
                    avg_loss=abs(np.mean(losses)) if len(losses) > 0 else 0.0,
                    win_loss_ratio=0.0,
                    expectancy=np.mean(trades),
                    recommended_position="No winning trades - do not trade",
                )
            else:
                # All wins - still be conservative
                return KellyResult(
                    kelly=self.max_position,
                    kelly_pct=self.max_position * 100,
                    win_rate=1.0,
                    avg_win=np.mean(wins),
                    avg_loss=0.0,
                    win_loss_ratio=float('inf'),
                    expectancy=np.mean(trades),
                    recommended_position=f"{self.max_position * 100:.1f}% (capped - all wins)",
                )

        win_rate = len(wins) / len(trades)
        avg_win = np.mean(wins)
        avg_loss = abs(np.mean(losses))
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

        kelly = self.binary_kelly(win_rate, avg_win, avg_loss)

        # Expected value per trade
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        return KellyResult(
            kelly=kelly,
            kelly_pct=kelly * 100,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            expectancy=expectancy,
            recommended_position=f"{kelly * 100:.1f}% of capital",
        )

    def get_regime_multiplier(self, regime: str) -> float:
        """
        Get Kelly multiplier based on market regime.

        Renaissance Technologies adjusts position sizing based on regime:
        - BULL: Full Kelly (aggressive, trend following)
        - NEUTRAL: Half Kelly (balanced)
        - BEAR: Quarter Kelly (defensive, preserve capital)

        Parameters
        ----------
        regime : str
            Market regime: 'bull', 'bear', 'neutral', etc.

        Returns
        -------
        float
            Multiplier to apply to base Kelly
        """
        regime = regime.lower()

        multipliers = {
            'bull': 1.0,           # Full Kelly in bull market
            'neutral': 0.5,        # Half Kelly in neutral
            'sideways': 0.5,       # Treat sideways like neutral
            'bear': 0.25,          # Quarter Kelly in bear market
            'high_volatility': 0.25,  # Conservative in high vol
            'unknown': 0.25,       # Conservative when uncertain
        }

        return multipliers.get(regime, 0.5)  # Default to half Kelly

    def calculate_regime_adjusted(
        self,
        trades: List[float],
        regime: str,
    ) -> KellyResult:
        """
        Calculate Kelly with regime adjustment.

        Parameters
        ----------
        trades : list
            List of trade P&L values
        regime : str
            Current market regime

        Returns
        -------
        KellyResult
            Results with regime-adjusted Kelly
        """
        result = self.calculate_from_trades(trades)

        multiplier = self.get_regime_multiplier(regime)
        adjusted_kelly = result.kelly * multiplier

        # Cap at max position
        adjusted_kelly = min(adjusted_kelly, self.max_position)

        # Update result with regime info
        result.regime_multiplier = multiplier
        result.adjusted_kelly = adjusted_kelly
        result.recommended_position = (
            f"{adjusted_kelly * 100:.1f}% of capital "
            f"({regime.upper()} regime, {multiplier}x Kelly)"
        )

        return result

    def calculate_position_size(
        self,
        capital: float,
        price: float,
        trades: List[float],
        regime: str = 'neutral',
    ) -> Dict:
        """
        Calculate recommended position size in shares/units.

        Parameters
        ----------
        capital : float
            Available capital
        price : float
            Current asset price
        trades : list
            Historical trade P&L values
        regime : str
            Current market regime

        Returns
        -------
        dict
            Position sizing recommendation
        """
        result = self.calculate_regime_adjusted(trades, regime)

        if result.adjusted_kelly <= 0 or capital <= 0 or price <= 0:
            return {
                'shares': 0,
                'position_dollars': 0.0,
                'position_pct': 0.0,
                'kelly_result': result,
                'reason': 'Insufficient edge or invalid parameters',
            }

        # Calculate dollar position
        position_dollars = capital * result.adjusted_kelly

        # Calculate shares
        shares = int(position_dollars / price)

        # Recalculate with actual shares
        actual_position_dollars = shares * price
        actual_position_pct = actual_position_dollars / capital

        return {
            'shares': shares,
            'position_dollars': round(actual_position_dollars, 2),
            'position_pct': round(actual_position_pct * 100, 2),
            'base_kelly': round(result.kelly * 100, 2),
            'regime_multiplier': result.regime_multiplier,
            'adjusted_kelly': round(result.adjusted_kelly * 100, 2),
            'win_rate': round(result.win_rate * 100, 2),
            'expectancy': round(result.expectancy, 2),
            'regime': regime,
            'kelly_result': result,
        }


# Convenience functions

def calculate_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.5,
) -> float:
    """
    Quick Kelly calculation.

    Parameters
    ----------
    win_rate : float
        Win probability (0-1)
    avg_win : float
        Average win amount
    avg_loss : float
        Average loss amount (positive value)
    fraction : float
        Kelly fraction (0.5 = half Kelly)

    Returns
    -------
    float
        Optimal position fraction
    """
    calc = KellyCriterion(kelly_fraction=fraction)
    return calc.binary_kelly(win_rate, avg_win, avg_loss)


def kelly_from_trades(trades: List[float], regime: str = 'neutral') -> Dict:
    """
    Calculate Kelly from trade history with regime adjustment.

    Parameters
    ----------
    trades : list
        List of trade P&L values
    regime : str
        Market regime

    Returns
    -------
    dict
        Kelly calculation results
    """
    calc = KellyCriterion()
    result = calc.calculate_regime_adjusted(trades, regime)

    return {
        'kelly': result.kelly,
        'adjusted_kelly': result.adjusted_kelly,
        'win_rate': result.win_rate,
        'expectancy': result.expectancy,
        'regime': regime,
        'regime_multiplier': result.regime_multiplier,
        'recommendation': result.recommended_position,
    }


# Global instance with default settings
default_kelly = KellyCriterion(kelly_fraction=0.5, max_position=0.25)
