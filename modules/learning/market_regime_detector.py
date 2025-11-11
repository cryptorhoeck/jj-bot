"""
Market Regime Detector

Detects current market regime: BULL, BEAR, SIDEWAYS, or VOLATILE.
Uses trend strength, volatility, and momentum indicators.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.learning.price_history import PriceHistory
from modules.database.connection import get_db_connection, LEARNING_DB_PATH


class MarketRegime(Enum):
    """Market regime types"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class MarketRegimeDetector:
    """
    Detects current market regime based on price action.

    Regimes:
    - BULL: Strong uptrend, positive momentum
    - BEAR: Strong downtrend, negative momentum
    - SIDEWAYS: Range-bound, low trend strength
    - VOLATILE: High volatility, unclear direction
    """

    def __init__(self):
        """Initialize market regime detector."""
        self.price_history = PriceHistory()
        self.learning_db = LEARNING_DB_PATH

    def detect_regime(
        self,
        symbol: str,
        lookback_periods: int = 100
    ) -> Dict:
        """
        Detect current market regime for a symbol.

        Args:
            symbol: Trading symbol
            lookback_periods: Number of price periods to analyze

        Returns:
            Dict with regime, confidence, and metrics
        """
        # Get recent prices
        prices = self.price_history.get_price_array(symbol, lookback_periods)

        if len(prices) < 20:  # Need minimum data
            return {
                'regime': MarketRegime.UNKNOWN.value,
                'confidence': 0.0,
                'trend_strength': 0.0,
                'volatility': 0.0,
                'momentum': 0.0
            }

        # Calculate indicators
        trend_strength = self._calculate_trend_strength(prices)
        volatility = self._calculate_volatility(prices)
        momentum = self._calculate_momentum(prices)

        # Determine regime based on indicators
        regime, confidence = self._classify_regime(
            trend_strength,
            volatility,
            momentum
        )

        return {
            'regime': regime.value,
            'confidence': round(confidence, 2),
            'trend_strength': round(trend_strength, 2),
            'volatility': round(volatility, 2),
            'momentum': round(momentum, 2),
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }

    def save_regime(self, symbol: str):
        """
        Detect and save current regime to database.

        Args:
            symbol: Trading symbol
        """
        regime_data = self.detect_regime(symbol)

        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO market_regime (
                    timestamp, regime, trend_strength, volatility, momentum
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                regime_data['timestamp'],
                regime_data['regime'],
                regime_data['trend_strength'],
                regime_data['volatility'],
                regime_data['momentum']
            ))
            conn.commit()

    def get_regime_history(
        self,
        hours: int = 24
    ) -> List[Dict]:
        """
        Get historical regime data.

        Args:
            hours: Hours of history to retrieve

        Returns:
            List of regime snapshots
        """
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, regime, trend_strength, volatility, momentum
                FROM market_regime
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (start_time,))

            rows = cur.fetchall()
            return [
                {
                    'timestamp': row[0],
                    'regime': row[1],
                    'trend_strength': row[2],
                    'volatility': row[3],
                    'momentum': row[4]
                }
                for row in rows
            ]

    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """
        Calculate trend strength using linear regression slope.

        Returns:
            Trend strength (-1 to +1, negative = downtrend, positive = uptrend)
        """
        if len(prices) < 2:
            return 0.0

        n = len(prices)
        x = list(range(n))
        y = prices

        # Calculate linear regression slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalize slope to -1 to +1 range
        # Scale by price range
        price_range = max(prices) - min(prices)
        if price_range == 0:
            return 0.0

        normalized_slope = slope / (price_range / n)

        # Clamp to -1 to +1
        return max(min(normalized_slope, 1.0), -1.0)

    def _calculate_volatility(self, prices: List[float]) -> float:
        """
        Calculate price volatility (standard deviation of returns).

        Returns:
            Volatility (0 to 1, higher = more volatile)
        """
        if len(prices) < 2:
            return 0.0

        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns:
            return 0.0

        # Standard deviation of returns
        import statistics
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0

        # Normalize to 0-1 range (typical crypto volatility is 0-0.1 per period)
        normalized_vol = min(volatility * 10, 1.0)

        return normalized_vol

    def _calculate_momentum(self, prices: List[float]) -> float:
        """
        Calculate price momentum (rate of change).

        Returns:
            Momentum (-1 to +1, negative = losing momentum, positive = gaining)
        """
        if len(prices) < 20:
            return 0.0

        # Calculate ROC (Rate of Change) over last 20 periods
        current_price = prices[-1]
        past_price = prices[-20]

        if past_price == 0:
            return 0.0

        roc = (current_price - past_price) / past_price

        # Normalize to -1 to +1 (typical crypto ROC is -0.2 to +0.2)
        normalized_roc = max(min(roc * 5, 1.0), -1.0)

        return normalized_roc

    def _classify_regime(
        self,
        trend_strength: float,
        volatility: float,
        momentum: float
    ) -> tuple:
        """
        Classify market regime based on indicators.

        Args:
            trend_strength: -1 to +1
            volatility: 0 to 1
            momentum: -1 to +1

        Returns:
            (MarketRegime, confidence)
        """
        # High volatility → VOLATILE regime
        if volatility > 0.7:
            return MarketRegime.VOLATILE, volatility

        # Strong positive trend + positive momentum → BULL
        if trend_strength > 0.3 and momentum > 0.2:
            confidence = (trend_strength + momentum) / 2
            return MarketRegime.BULL, confidence

        # Strong negative trend + negative momentum → BEAR
        if trend_strength < -0.3 and momentum < -0.2:
            confidence = abs((trend_strength + momentum) / 2)
            return MarketRegime.BEAR, confidence

        # Weak trend + low volatility → SIDEWAYS
        if abs(trend_strength) < 0.2 and volatility < 0.4:
            confidence = 1.0 - (abs(trend_strength) + volatility) / 2
            return MarketRegime.SIDEWAYS, confidence

        # Moderate volatility, unclear direction → VOLATILE
        if volatility > 0.4:
            return MarketRegime.VOLATILE, volatility

        # Default: SIDEWAYS with low confidence
        return MarketRegime.SIDEWAYS, 0.3
