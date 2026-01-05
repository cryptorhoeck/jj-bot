"""
JJBotCore - Unified Trading System

Integrates Renaissance Technologies-inspired strategies:
- HMM Regime Detection (market state classification)
- Kelly Criterion (optimal position sizing)
- VWAP Signal Generation (entry/exit signals)
- Babylon + Buffett (regime-adjusted profit harvesting)

This is the central entry point for the integrated trading system.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .hmm_regime_detector import (
    HMMRegimeDetector,
    SMARegimeDetector,
    HMMRegime,
    HMMRegimeResult,
    create_regime_detector,
)
from .kelly_criterion import (
    KellyCriterion,
    KellyResult,
)
from .vwap_calculator import (
    VWAPCalculator,
    VWAPStrategy,
    VWAPSignal,
    Signal,
)

logger = logging.getLogger(__name__)


@dataclass
class StrategyParams:
    """Trading parameters for a specific regime"""
    regime: str
    vwap_strategy: VWAPStrategy
    kelly_fraction: float
    stop_loss_pct: float
    take_profit_pct: float
    position_bias: str  # 'LONG', 'SHORT', 'NEUTRAL'
    max_leverage: float


# Regime-specific parameters
REGIME_PARAMS = {
    'bull': StrategyParams(
        regime='bull',
        vwap_strategy=VWAPStrategy.TREND_FOLLOWING,
        kelly_fraction=1.0,  # Full Kelly
        stop_loss_pct=0.02,
        take_profit_pct=0.05,
        position_bias='LONG',
        max_leverage=1.5,
    ),
    'bear': StrategyParams(
        regime='bear',
        vwap_strategy=VWAPStrategy.MEAN_REVERSION,
        kelly_fraction=0.25,  # Quarter Kelly
        stop_loss_pct=0.01,
        take_profit_pct=0.03,
        position_bias='SHORT',
        max_leverage=0.5,
    ),
    'neutral': StrategyParams(
        regime='neutral',
        vwap_strategy=VWAPStrategy.MEAN_REVERSION,
        kelly_fraction=0.5,  # Half Kelly
        stop_loss_pct=0.015,
        take_profit_pct=0.04,
        position_bias='NEUTRAL',
        max_leverage=1.0,
    ),
    'high_volatility': StrategyParams(
        regime='high_volatility',
        vwap_strategy=VWAPStrategy.MEAN_REVERSION,
        kelly_fraction=0.25,  # Quarter Kelly
        stop_loss_pct=0.01,
        take_profit_pct=0.03,
        position_bias='NEUTRAL',
        max_leverage=0.5,
    ),
    'sideways': StrategyParams(
        regime='sideways',
        vwap_strategy=VWAPStrategy.MEAN_REVERSION,
        kelly_fraction=0.5,  # Half Kelly
        stop_loss_pct=0.015,
        take_profit_pct=0.04,
        position_bias='NEUTRAL',
        max_leverage=1.0,
    ),
}


@dataclass
class SystemStatus:
    """Complete system status"""
    timestamp: str
    regime: Dict[str, Any]
    signal: Dict[str, Any]
    position_sizing: Dict[str, Any]
    strategy_params: Dict[str, Any]
    capital: float
    trade_count: int


class JJBotCore:
    """
    Silverback Intelligence - JJ-Bot Core Trading System

    Integrates:
    - Hidden Markov Model regime detection
    - Kelly Criterion position sizing
    - VWAP-based signal generation

    Usage:
        >>> bot = JJBotCore(capital=100000)
        >>> bot.fit(historical_prices)
        >>> status = bot.get_system_status(current_prices, current_volumes)
        >>> print(status['signal']['signal_type'])  # BUY, SELL, HOLD
    """

    def __init__(
        self,
        capital: float = 10000,
        max_position_pct: float = 0.25,
        use_hmm: bool = True,
        kelly_fraction: float = 0.5,
    ):
        """
        Initialize JJ-Bot.

        Parameters
        ----------
        capital : float
            Starting capital
        max_position_pct : float
            Maximum position as fraction of capital
        use_hmm : bool
            Use HMM for regime detection (falls back to SMA if unavailable)
        kelly_fraction : float
            Base Kelly fraction (0.5 = half Kelly)
        """
        self.capital = capital
        self.max_position_pct = max_position_pct

        # Initialize components
        self.regime_detector = create_regime_detector(use_hmm=use_hmm)
        self.kelly_calc = KellyCriterion(
            kelly_fraction=kelly_fraction,
            max_position=max_position_pct,
        )
        self.vwap_calc = VWAPCalculator()

        # Trade history for Kelly calculation
        self.trade_history: List[float] = []

        # Current state
        self.current_regime: str = 'neutral'
        self.current_regime_result: Optional[HMMRegimeResult] = None
        self.current_position: float = 0.0
        self.entry_price: Optional[float] = None

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        logger.info(f"JJBotCore initialized with capital=${capital:,.2f}, "
                    f"HMM={'enabled' if use_hmm else 'disabled'}")

    def fit(self, prices: np.ndarray) -> "JJBotCore":
        """
        Fit the regime detection model on historical data.

        Parameters
        ----------
        prices : np.ndarray
            Historical close prices

        Returns
        -------
        self
            Fitted bot instance
        """
        self.regime_detector.fit(prices)
        logger.info(f"JJBotCore fitted on {len(prices)} price points")
        return self

    def update_regime(self, prices: np.ndarray) -> str:
        """
        Update current market regime.

        Parameters
        ----------
        prices : np.ndarray
            Recent price data (at least 100 points recommended)

        Returns
        -------
        str
            Current regime: 'bull', 'bear', 'neutral'
        """
        self.current_regime_result = self.regime_detector.predict_regime(prices)
        self.current_regime = self.current_regime_result.regime.value
        return self.current_regime

    def get_strategy_params(self, regime: Optional[str] = None) -> StrategyParams:
        """
        Get trading parameters based on current regime.

        Parameters
        ----------
        regime : str, optional
            Regime to use (uses current if not specified)

        Returns
        -------
        StrategyParams
            Strategy configuration for the regime
        """
        regime = regime or self.current_regime
        return REGIME_PARAMS.get(regime, REGIME_PARAMS['neutral'])

    def calculate_position_size(
        self,
        price: float,
        regime: Optional[str] = None,
    ) -> Dict:
        """
        Calculate optimal position size using Kelly Criterion.

        Parameters
        ----------
        price : float
            Current asset price
        regime : str, optional
            Market regime (uses current if not specified)

        Returns
        -------
        dict
            Position sizing recommendation
        """
        regime = regime or self.current_regime
        params = self.get_strategy_params(regime)

        # Get base Kelly from trade history
        if len(self.trade_history) >= 10:
            kelly_result = self.kelly_calc.calculate_from_trades(self.trade_history)
            base_kelly = kelly_result.kelly
        else:
            # Default conservative sizing until we have history
            base_kelly = 0.05

        # Adjust by regime
        adjusted_kelly = base_kelly * params.kelly_fraction

        # Cap at max position
        adjusted_kelly = min(adjusted_kelly, self.max_position_pct)

        # Calculate dollar position
        position_dollars = self.capital * adjusted_kelly

        # Calculate shares/units
        shares = int(position_dollars / price) if price > 0 else 0

        return {
            'shares': shares,
            'position_dollars': round(shares * price, 2),
            'position_pct': round((shares * price) / self.capital * 100, 2) if self.capital > 0 else 0,
            'base_kelly': round(base_kelly * 100, 2),
            'adjusted_kelly': round(adjusted_kelly * 100, 2),
            'regime_multiplier': params.kelly_fraction,
            'regime': regime,
        }

    def generate_signal(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        regime: Optional[str] = None,
    ) -> Dict:
        """
        Generate trading signal from VWAP analysis.

        Parameters
        ----------
        high, low, close, volume : np.ndarray
            OHLCV data
        regime : str, optional
            Market regime (uses current if not specified)

        Returns
        -------
        dict
            Signal information
        """
        regime = regime or self.current_regime
        params = self.get_strategy_params(regime)

        # Get VWAP signal
        vwap_signal = self.vwap_calc.generate_signal(
            high, low, close, volume,
            strategy=params.vwap_strategy,
            regime=regime,
        )

        return {
            'signal': vwap_signal.signal.value,
            'signal_type': vwap_signal.signal_type,
            'vwap_distance_pct': round(vwap_signal.vwap_distance_pct, 2),
            'current_price': round(vwap_signal.current_price, 2),
            'current_vwap': round(vwap_signal.current_vwap, 2),
            'strategy': params.vwap_strategy.value,
            'regime': regime,
            'position_bias': params.position_bias,
            'confidence': round(vwap_signal.confidence, 2),
        }

    def process_trade_result(
        self,
        entry_price: float,
        exit_price: float,
        shares: float,
    ) -> float:
        """
        Record trade result for Kelly calculation.

        Parameters
        ----------
        entry_price : float
            Entry price
        exit_price : float
            Exit price
        shares : float
            Number of shares traded

        Returns
        -------
        float
            Trade P&L
        """
        pnl = (exit_price - entry_price) * shares
        self.trade_history.append(pnl)

        # Update statistics
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Keep last 100 trades for rolling calculation
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]

        logger.debug(f"Trade recorded: P&L=${pnl:.2f}, "
                     f"Win rate={self.winning_trades}/{self.total_trades}")

        return pnl

    def update_capital(self, new_capital: float):
        """Update available capital"""
        self.capital = new_capital

    def get_system_status(
        self,
        prices: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        volume: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Get complete system status.

        Parameters
        ----------
        prices : np.ndarray
            Close prices
        high, low, volume : np.ndarray, optional
            Additional OHLCV data for VWAP (estimates if not provided)

        Returns
        -------
        dict
            Complete system status
        """
        # Update regime
        self.update_regime(prices)
        params = self.get_strategy_params()

        # Estimate high/low/volume if not provided
        if high is None:
            high = prices * 1.005  # Estimate 0.5% above close
        if low is None:
            low = prices * 0.995  # Estimate 0.5% below close
        if volume is None:
            volume = np.ones_like(prices) * 1000  # Default volume

        # Get signal
        signal = self.generate_signal(high, low, prices, volume)

        # Get position sizing
        current_price = prices[-1]
        position_info = self.calculate_position_size(current_price)

        return {
            'timestamp': datetime.now().isoformat(),
            'regime': {
                'current': self.current_regime,
                'probabilities': self.current_regime_result.probabilities if self.current_regime_result else {},
                'confidence': self.current_regime_result.confidence if self.current_regime_result else 0.5,
                'bias': params.position_bias,
            },
            'signal': signal,
            'position_sizing': position_info,
            'strategy_params': {
                'vwap_strategy': params.vwap_strategy.value,
                'kelly_fraction': params.kelly_fraction,
                'stop_loss_pct': params.stop_loss_pct * 100,
                'take_profit_pct': params.take_profit_pct * 100,
                'max_leverage': params.max_leverage,
            },
            'capital': self.capital,
            'trade_count': self.total_trades,
            'statistics': {
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0,
            },
        }

    def get_trading_recommendation(
        self,
        prices: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        volume: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Get a simple trading recommendation.

        Returns a clear action recommendation with all necessary details.

        Parameters
        ----------
        prices : np.ndarray
            Close prices
        high, low, volume : np.ndarray, optional
            Additional OHLCV data

        Returns
        -------
        dict
            Trading recommendation
        """
        status = self.get_system_status(prices, high, low, volume)

        signal_type = status['signal']['signal_type']
        regime = status['regime']['current']
        confidence = status['signal']['confidence']

        if signal_type == 'BUY':
            action = 'OPEN_LONG'
            shares = status['position_sizing']['shares']
            position_value = status['position_sizing']['position_dollars']
        elif signal_type == 'SELL' and self.current_position > 0:
            action = 'CLOSE_LONG'
            shares = int(self.current_position)
            position_value = shares * prices[-1]
        elif signal_type == 'SELL':
            action = 'OPEN_SHORT' if status['regime']['bias'] != 'LONG' else 'HOLD'
            shares = status['position_sizing']['shares'] if action == 'OPEN_SHORT' else 0
            position_value = status['position_sizing']['position_dollars'] if action == 'OPEN_SHORT' else 0
        else:
            action = 'HOLD'
            shares = 0
            position_value = 0

        return {
            'action': action,
            'shares': shares,
            'position_value': position_value,
            'current_price': status['signal']['current_price'],
            'regime': regime,
            'confidence': confidence,
            'vwap_distance': status['signal']['vwap_distance_pct'],
            'strategy': status['strategy_params']['vwap_strategy'],
            'stop_loss_pct': status['strategy_params']['stop_loss_pct'],
            'take_profit_pct': status['strategy_params']['take_profit_pct'],
        }


# Convenience function
def create_jjbot(
    capital: float = 10000,
    use_hmm: bool = True,
) -> JJBotCore:
    """
    Create and return a JJBotCore instance.

    Parameters
    ----------
    capital : float
        Starting capital
    use_hmm : bool
        Use HMM for regime detection

    Returns
    -------
    JJBotCore
        Configured bot instance
    """
    return JJBotCore(capital=capital, use_hmm=use_hmm)


# Global instance (lazy initialization)
_default_jjbot: Optional[JJBotCore] = None


def get_default_jjbot() -> JJBotCore:
    """Get or create the default JJBotCore instance"""
    global _default_jjbot
    if _default_jjbot is None:
        _default_jjbot = create_jjbot()
    return _default_jjbot
