"""
Regime-Adjusted Thresholds for Babylon + Buffett Capital Management

Adjusts profit harvesting thresholds based on detected market regime.
Inspired by Renaissance Technologies' regime-adaptive position sizing.

Key Principles:
- BULL: Let winners run (higher thresholds)
- NEUTRAL: Standard thresholds
- BEAR: Harvest quickly, preserve capital (lower thresholds)
"""

from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegimeThresholds:
    """Profit harvesting thresholds for a specific regime"""
    regime: str
    harvest_threshold_20: float  # First harvest threshold
    harvest_threshold_50: float  # Second harvest threshold
    harvest_threshold_100: float  # Third harvest threshold
    btc_allocation: float  # BTC allocation (0-1)
    gold_allocation: float  # Gold/MNT allocation (0-1)
    reinvest_pct: float  # Percentage to reinvest vs hold
    description: str


# Regime-specific configurations
REGIME_THRESHOLDS = {
    'bull': RegimeThresholds(
        regime='bull',
        harvest_threshold_20=0.25,   # 25% (let winners run)
        harvest_threshold_50=0.60,   # 60%
        harvest_threshold_100=1.20,  # 120%
        btc_allocation=0.70,         # Aggressive BTC allocation
        gold_allocation=0.30,        # Less defensive
        reinvest_pct=0.50,           # Reinvest half of profits
        description="Bullish regime: Let winners run, aggressive allocation",
    ),
    'neutral': RegimeThresholds(
        regime='neutral',
        harvest_threshold_20=0.20,   # 20% (standard)
        harvest_threshold_50=0.50,   # 50%
        harvest_threshold_100=1.00,  # 100%
        btc_allocation=0.50,         # Balanced
        gold_allocation=0.50,        # Balanced
        reinvest_pct=0.35,           # Moderate reinvestment
        description="Neutral regime: Standard thresholds, balanced allocation",
    ),
    'bear': RegimeThresholds(
        regime='bear',
        harvest_threshold_20=0.10,   # 10% (harvest quickly)
        harvest_threshold_50=0.30,   # 30%
        harvest_threshold_100=0.60,  # 60%
        btc_allocation=0.30,         # Defensive
        gold_allocation=0.70,        # Heavy gold allocation
        reinvest_pct=0.20,           # Save more cash
        description="Bearish regime: Harvest quickly, defensive allocation",
    ),
    'high_volatility': RegimeThresholds(
        regime='high_volatility',
        harvest_threshold_20=0.15,   # 15%
        harvest_threshold_50=0.40,   # 40%
        harvest_threshold_100=0.80,  # 80%
        btc_allocation=0.40,         # Moderate
        gold_allocation=0.60,        # Defensive tilt
        reinvest_pct=0.25,           # Conservative reinvestment
        description="High volatility: Quick harvests, defensive tilt",
    ),
    'sideways': RegimeThresholds(
        regime='sideways',
        harvest_threshold_20=0.20,   # 20%
        harvest_threshold_50=0.50,   # 50%
        harvest_threshold_100=1.00,  # 100%
        btc_allocation=0.50,         # Balanced
        gold_allocation=0.50,        # Balanced
        reinvest_pct=0.30,           # Moderate
        description="Sideways regime: Standard thresholds, wait for breakout",
    ),
}

# Default thresholds when regime is unknown
DEFAULT_THRESHOLDS = REGIME_THRESHOLDS['neutral']


class RegimeThresholdManager:
    """
    Manages profit harvesting thresholds based on market regime.

    Integrates with HMM regime detector to dynamically adjust
    Babylon + Buffett harvesting thresholds.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, RegimeThresholds]] = None,
    ):
        """
        Initialize threshold manager.

        Parameters
        ----------
        thresholds : dict, optional
            Custom regime thresholds (uses defaults if not provided)
        """
        self.thresholds = thresholds or REGIME_THRESHOLDS
        self.current_regime = 'neutral'
        self.current_thresholds = DEFAULT_THRESHOLDS

    def update_regime(self, regime: str):
        """
        Update current regime and thresholds.

        Parameters
        ----------
        regime : str
            Current market regime
        """
        regime = regime.lower()
        self.current_regime = regime
        self.current_thresholds = self.thresholds.get(regime, DEFAULT_THRESHOLDS)

        logger.info(f"Regime updated to '{regime}': {self.current_thresholds.description}")

    def get_thresholds(self, regime: Optional[str] = None) -> RegimeThresholds:
        """
        Get thresholds for a regime.

        Parameters
        ----------
        regime : str, optional
            Regime to get thresholds for (uses current if not specified)

        Returns
        -------
        RegimeThresholds
            Threshold configuration
        """
        if regime:
            return self.thresholds.get(regime.lower(), DEFAULT_THRESHOLDS)
        return self.current_thresholds

    def should_harvest(
        self,
        current_gain_pct: float,
        harvested_20: bool,
        harvested_50: bool,
        harvested_100: bool,
        regime: Optional[str] = None,
    ) -> Dict:
        """
        Determine if a harvest action should be taken.

        Parameters
        ----------
        current_gain_pct : float
            Current position gain percentage (0.20 = 20%)
        harvested_20 : bool
            Whether 20% threshold has been harvested
        harvested_50 : bool
            Whether 50% threshold has been harvested
        harvested_100 : bool
            Whether 100% threshold has been harvested
        regime : str, optional
            Regime to use (uses current if not specified)

        Returns
        -------
        dict
            Harvest decision with trigger and details
        """
        thresholds = self.get_thresholds(regime)

        # Check thresholds in order
        if not harvested_20 and current_gain_pct >= thresholds.harvest_threshold_20:
            return {
                'should_harvest': True,
                'trigger': '20%',
                'threshold': thresholds.harvest_threshold_20,
                'sell_pct': 0.25,  # Sell 25% of position
                'regime': thresholds.regime,
            }

        if not harvested_50 and current_gain_pct >= thresholds.harvest_threshold_50:
            return {
                'should_harvest': True,
                'trigger': '50%',
                'threshold': thresholds.harvest_threshold_50,
                'sell_pct': 0.25,
                'regime': thresholds.regime,
            }

        if not harvested_100 and current_gain_pct >= thresholds.harvest_threshold_100:
            return {
                'should_harvest': True,
                'trigger': '100%',
                'threshold': thresholds.harvest_threshold_100,
                'sell_pct': 0.25,
                'regime': thresholds.regime,
            }

        return {
            'should_harvest': False,
            'trigger': None,
            'next_threshold': self._get_next_threshold(
                harvested_20, harvested_50, harvested_100, thresholds
            ),
            'regime': thresholds.regime,
        }

    def _get_next_threshold(
        self,
        harvested_20: bool,
        harvested_50: bool,
        harvested_100: bool,
        thresholds: RegimeThresholds,
    ) -> Optional[float]:
        """Get the next harvest threshold to watch"""
        if not harvested_20:
            return thresholds.harvest_threshold_20
        if not harvested_50:
            return thresholds.harvest_threshold_50
        if not harvested_100:
            return thresholds.harvest_threshold_100
        return None

    def get_deployment_allocation(self, regime: Optional[str] = None) -> Dict:
        """
        Get deployment allocation for harvested profits.

        Parameters
        ----------
        regime : str, optional
            Regime to use

        Returns
        -------
        dict
            BTC and gold allocation percentages
        """
        thresholds = self.get_thresholds(regime)

        return {
            'btc_allocation': thresholds.btc_allocation,
            'gold_allocation': thresholds.gold_allocation,
            'reinvest_pct': thresholds.reinvest_pct,
            'btc_amount': lambda x: x * thresholds.btc_allocation,
            'gold_amount': lambda x: x * thresholds.gold_allocation,
            'regime': thresholds.regime,
        }

    def get_status(self) -> Dict:
        """Get current threshold manager status"""
        return {
            'current_regime': self.current_regime,
            'thresholds': {
                '20%': self.current_thresholds.harvest_threshold_20 * 100,
                '50%': self.current_thresholds.harvest_threshold_50 * 100,
                '100%': self.current_thresholds.harvest_threshold_100 * 100,
            },
            'allocation': {
                'btc': self.current_thresholds.btc_allocation * 100,
                'gold': self.current_thresholds.gold_allocation * 100,
            },
            'reinvest_pct': self.current_thresholds.reinvest_pct * 100,
            'description': self.current_thresholds.description,
        }


# Convenience functions

def get_thresholds_for_regime(regime: str) -> Dict:
    """
    Get harvest thresholds for a regime.

    Parameters
    ----------
    regime : str
        Market regime

    Returns
    -------
    dict
        Threshold values
    """
    manager = RegimeThresholdManager()
    thresholds = manager.get_thresholds(regime)

    return {
        'harvest_20': thresholds.harvest_threshold_20 * 100,
        'harvest_50': thresholds.harvest_threshold_50 * 100,
        'harvest_100': thresholds.harvest_threshold_100 * 100,
        'btc_allocation': thresholds.btc_allocation * 100,
        'gold_allocation': thresholds.gold_allocation * 100,
        'reinvest_pct': thresholds.reinvest_pct * 100,
    }


def check_harvest_trigger(
    gain_pct: float,
    harvested_20: bool,
    harvested_50: bool,
    harvested_100: bool,
    regime: str = 'neutral',
) -> Dict:
    """
    Check if a harvest should be triggered.

    Parameters
    ----------
    gain_pct : float
        Current gain as decimal (0.20 = 20%)
    harvested_* : bool
        Whether each threshold has been harvested
    regime : str
        Market regime

    Returns
    -------
    dict
        Harvest decision
    """
    manager = RegimeThresholdManager()
    return manager.should_harvest(
        gain_pct, harvested_20, harvested_50, harvested_100, regime
    )


# Global instance
default_threshold_manager = RegimeThresholdManager()
