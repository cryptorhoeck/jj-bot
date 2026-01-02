"""
Market Regime Detector

Identifies current market conditions to enable regime-specific trading strategies.
Detects: Bull, Bear, Sideways, and High Volatility regimes.

Used by the Ensemble Agent to select the appropriate expert model for current conditions.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime classifications"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    UNKNOWN = "unknown"


@dataclass
class RegimeAnalysis:
    """Detailed regime analysis result"""
    regime: MarketRegime
    confidence: float  # 0-1 confidence in the classification
    trend_strength: float  # Absolute trend strength
    volatility: float  # Current volatility level
    volatility_percentile: float  # Volatility relative to history
    momentum: float  # Recent price momentum
    details: Dict  # Additional metrics


class RegimeDetector:
    """
    Detects market regime from price data.

    Uses multiple indicators:
    - Trend: SMA crossovers and price momentum
    - Volatility: ATR and rolling std deviation
    - Regime classification: Combines trend and volatility signals
    """

    def __init__(
        self,
        lookback_short: int = 20,
        lookback_long: int = 50,
        volatility_lookback: int = 20,
        volatility_threshold_high: float = 1.5,  # 1.5x average = high volatility
        volatility_threshold_low: float = 0.5,   # 0.5x average = low volatility
        trend_threshold: float = 0.02,  # 2% move for trend confirmation
        min_data_points: int = 100,
    ):
        """
        Initialize regime detector.

        Args:
            lookback_short: Short-term SMA period
            lookback_long: Long-term SMA period
            volatility_lookback: Period for volatility calculation
            volatility_threshold_high: Multiplier for high volatility classification
            volatility_threshold_low: Multiplier for low/sideways classification
            trend_threshold: Minimum trend magnitude for bull/bear classification
            min_data_points: Minimum data points needed for detection
        """
        self.lookback_short = lookback_short
        self.lookback_long = lookback_long
        self.volatility_lookback = volatility_lookback
        self.volatility_threshold_high = volatility_threshold_high
        self.volatility_threshold_low = volatility_threshold_low
        self.trend_threshold = trend_threshold
        self.min_data_points = min_data_points

        # Historical volatility for percentile calculation
        self.volatility_history: List[float] = []
        self.max_volatility_history = 1000

    def detect(
        self,
        prices: np.ndarray,
        high_prices: Optional[np.ndarray] = None,
        low_prices: Optional[np.ndarray] = None,
    ) -> RegimeAnalysis:
        """
        Detect market regime from price data.

        Args:
            prices: Close prices (most recent at end)
            high_prices: High prices (optional, for ATR)
            low_prices: Low prices (optional, for ATR)

        Returns:
            RegimeAnalysis with detected regime and metrics
        """
        if len(prices) < self.min_data_points:
            return RegimeAnalysis(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                trend_strength=0.0,
                volatility=0.0,
                volatility_percentile=0.5,
                momentum=0.0,
                details={"reason": "Insufficient data"}
            )

        # Calculate indicators
        sma_short = self._sma(prices, self.lookback_short)
        sma_long = self._sma(prices, self.lookback_long)

        # Trend strength: normalized difference between SMAs
        current_price = prices[-1]
        trend_strength = (sma_short - sma_long) / sma_long if sma_long > 0 else 0

        # Momentum: recent price change
        momentum_period = min(10, len(prices) - 1)
        momentum = (prices[-1] - prices[-momentum_period - 1]) / prices[-momentum_period - 1]

        # Volatility calculation
        if high_prices is not None and low_prices is not None:
            volatility = self._atr(prices, high_prices, low_prices)
        else:
            volatility = self._rolling_volatility(prices)

        # Update volatility history
        self.volatility_history.append(volatility)
        if len(self.volatility_history) > self.max_volatility_history:
            self.volatility_history.pop(0)

        # Calculate volatility percentile
        if len(self.volatility_history) >= 20:
            volatility_percentile = np.mean([v <= volatility for v in self.volatility_history])
        else:
            volatility_percentile = 0.5  # Neutral if not enough history

        # Average volatility for comparison
        avg_volatility = np.mean(self.volatility_history) if self.volatility_history else volatility
        volatility_ratio = volatility / avg_volatility if avg_volatility > 0 else 1.0

        # Determine regime
        regime, confidence = self._classify_regime(
            trend_strength=trend_strength,
            volatility_ratio=volatility_ratio,
            momentum=momentum,
            volatility_percentile=volatility_percentile,
        )

        return RegimeAnalysis(
            regime=regime,
            confidence=confidence,
            trend_strength=trend_strength,
            volatility=volatility,
            volatility_percentile=volatility_percentile,
            momentum=momentum,
            details={
                "sma_short": sma_short,
                "sma_long": sma_long,
                "volatility_ratio": volatility_ratio,
                "price": current_price,
                "avg_volatility": avg_volatility,
            }
        )

    def _classify_regime(
        self,
        trend_strength: float,
        volatility_ratio: float,
        momentum: float,
        volatility_percentile: float,
    ) -> Tuple[MarketRegime, float]:
        """
        Classify market regime based on indicators.

        Returns:
            Tuple of (regime, confidence)
        """
        # Check for high volatility first (overrides trend signals)
        if volatility_ratio >= self.volatility_threshold_high or volatility_percentile >= 0.85:
            # High volatility regime
            confidence = min(1.0, (volatility_ratio - 1.0) / (self.volatility_threshold_high - 1.0))
            confidence = max(0.5, confidence)  # Minimum 50% confidence
            return MarketRegime.HIGH_VOLATILITY, confidence

        # Check trend direction
        abs_trend = abs(trend_strength)

        if abs_trend < self.trend_threshold * 0.5:
            # Very weak trend - sideways
            confidence = 1.0 - (abs_trend / (self.trend_threshold * 0.5))
            confidence = max(0.5, min(1.0, confidence))
            return MarketRegime.SIDEWAYS, confidence

        elif abs_trend >= self.trend_threshold:
            # Strong trend
            if trend_strength > 0 and momentum >= 0:
                # Bull market: uptrend with positive momentum
                confidence = min(1.0, abs_trend / (self.trend_threshold * 2))
                confidence = max(0.6, confidence)
                return MarketRegime.BULL, confidence

            elif trend_strength < 0 and momentum <= 0:
                # Bear market: downtrend with negative momentum
                confidence = min(1.0, abs_trend / (self.trend_threshold * 2))
                confidence = max(0.6, confidence)
                return MarketRegime.BEAR, confidence

            else:
                # Conflicting signals - trend and momentum disagree
                # Classify based on trend but with lower confidence
                if trend_strength > 0:
                    return MarketRegime.BULL, 0.5
                else:
                    return MarketRegime.BEAR, 0.5

        else:
            # Weak trend - leaning towards sideways
            if volatility_ratio < self.volatility_threshold_low:
                # Low volatility + weak trend = sideways
                return MarketRegime.SIDEWAYS, 0.7
            else:
                # Normal volatility, weak trend - classify by direction
                if trend_strength > 0:
                    return MarketRegime.BULL, 0.5
                elif trend_strength < 0:
                    return MarketRegime.BEAR, 0.5
                else:
                    return MarketRegime.SIDEWAYS, 0.5

    def _sma(self, prices: np.ndarray, period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        return np.mean(prices[-period:])

    def _rolling_volatility(self, prices: np.ndarray) -> float:
        """Calculate rolling volatility (annualized std of returns)"""
        if len(prices) < 2:
            return 0.0

        returns = np.diff(prices) / prices[:-1]
        period = min(self.volatility_lookback, len(returns))
        rolling_std = np.std(returns[-period:])

        # Annualize (assuming daily data, 252 trading days)
        return rolling_std * np.sqrt(252)

    def _atr(
        self,
        close: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
    ) -> float:
        """Calculate Average True Range"""
        if len(close) < 2:
            return 0.0

        # True Range components
        tr1 = high[1:] - low[1:]  # High - Low
        tr2 = np.abs(high[1:] - close[:-1])  # High - Previous Close
        tr3 = np.abs(low[1:] - close[:-1])  # Low - Previous Close

        true_range = np.maximum(tr1, np.maximum(tr2, tr3))

        period = min(self.volatility_lookback, len(true_range))
        atr = np.mean(true_range[-period:])

        # Normalize by price
        return atr / close[-1] if close[-1] > 0 else 0.0

    def get_regime_for_training(
        self,
        prices: np.ndarray,
        window_size: int = 100,
    ) -> List[str]:
        """
        Get regime labels for each step in a training sequence.

        Args:
            prices: Price data for entire episode
            window_size: Lookback window for regime detection

        Returns:
            List of regime strings, one per timestep
        """
        regimes = []

        for i in range(len(prices)):
            # Use available data up to this point
            start_idx = max(0, i - window_size)
            window = prices[start_idx:i + 1]

            if len(window) >= self.min_data_points:
                analysis = self.detect(window)
                regimes.append(analysis.regime.value)
            else:
                regimes.append(MarketRegime.UNKNOWN.value)

        return regimes

    def reset(self):
        """Reset volatility history"""
        self.volatility_history = []


# Convenience functions

def detect_regime(prices: np.ndarray) -> str:
    """
    Quick regime detection for a price series.

    Args:
        prices: Close prices (most recent at end)

    Returns:
        Regime string: 'bull', 'bear', 'sideways', 'high_volatility', or 'unknown'
    """
    detector = RegimeDetector()
    analysis = detector.detect(prices)
    return analysis.regime.value


def get_regime_stats(prices: np.ndarray) -> Dict:
    """
    Get detailed regime analysis.

    Args:
        prices: Close prices

    Returns:
        Dictionary with regime, confidence, and all metrics
    """
    detector = RegimeDetector()
    analysis = detector.detect(prices)

    return {
        "regime": analysis.regime.value,
        "confidence": analysis.confidence,
        "trend_strength": analysis.trend_strength,
        "volatility": analysis.volatility,
        "volatility_percentile": analysis.volatility_percentile,
        "momentum": analysis.momentum,
        **analysis.details,
    }


# Global detector instance
default_detector = RegimeDetector()
