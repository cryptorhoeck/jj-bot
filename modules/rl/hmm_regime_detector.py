"""
HMM-Based Market Regime Detection

Uses Hidden Markov Models to classify market regimes (BULL, BEAR, NEUTRAL).
Inspired by Renaissance Technologies' approach, particularly Peter Brown's
application of speech recognition HMM techniques to financial markets.

The Baum-Welch algorithm (used in HMM training) was brought to Renaissance
by Leonard Baum himself, making it foundational to their trading approach.

Dependencies:
    pip install hmmlearn
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import warnings

logger = logging.getLogger(__name__)

# Try to import hmmlearn, fall back gracefully
try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("hmmlearn not installed. HMM regime detection unavailable. "
                   "Install with: pip install hmmlearn")


class HMMRegime(str, Enum):
    """Market regime classifications"""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


@dataclass
class HMMRegimeResult:
    """Result of HMM regime detection"""
    regime: HMMRegime
    probabilities: Dict[str, float]  # Probability of each regime
    confidence: float  # Highest probability
    log_return: float  # Current log return
    volatility: float  # Current volatility
    is_trained: bool


class HMMRegimeDetector:
    """
    Hidden Markov Model regime detector for market state classification.

    Uses log returns and volatility as observable features to infer hidden
    market states (regimes). The model learns transition probabilities between
    regimes and emission distributions for each regime.

    Key Insight from Renaissance:
        Speech recognition and financial markets are structurally similar:
        - Hidden states = phonemes/words ↔ market regimes
        - Observable = sound waves ↔ price/volume
        - Predict next sound ↔ predict next price movement

    Reference:
        Baum, L.E. (1972) "An inequality and associated maximization technique
        in statistical estimation of probabilistic functions of Markov chains"
    """

    def __init__(
        self,
        n_states: int = 3,
        n_iter: int = 500,
        vol_window: int = 20,
        min_data_points: int = 100,
        random_state: int = 42,
    ):
        """
        Initialize the HMM regime detector.

        Parameters
        ----------
        n_states : int
            Number of hidden states:
            - 2 = BULL/BEAR
            - 3 = BULL/BEAR/NEUTRAL (recommended)
        n_iter : int
            Maximum iterations for EM algorithm (Baum-Welch)
        vol_window : int
            Rolling window for volatility calculation
        min_data_points : int
            Minimum data points required for training
        random_state : int
            Random seed for reproducibility
        """
        self.n_states = n_states
        self.n_iter = n_iter
        self.vol_window = vol_window
        self.min_data_points = min_data_points
        self.random_state = random_state

        self.model = None
        self.state_mapping: Dict[int, HMMRegime] = {}
        self.state_means: Dict[int, float] = {}
        self.is_fitted = False

        if not HMM_AVAILABLE:
            logger.warning("HMM functionality disabled - hmmlearn not installed")

    def _prepare_features(
        self,
        prices: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare features for HMM training/prediction.

        Uses log returns and rolling volatility as features.

        Parameters
        ----------
        prices : np.ndarray
            Close prices

        Returns
        -------
        tuple
            (features, log_returns, volatility) arrays
        """
        # Log returns (additive over time, better for modeling)
        log_returns = np.diff(np.log(prices))

        # Pad log returns to match price length
        log_returns = np.concatenate([[0], log_returns])

        # Rolling volatility of log returns (annualized)
        volatility = np.zeros_like(log_returns)
        for i in range(self.vol_window, len(log_returns)):
            window = log_returns[i - self.vol_window:i]
            volatility[i] = np.std(window) * np.sqrt(252)

        # Fill early values with mean volatility
        mean_vol = np.mean(volatility[self.vol_window:])
        volatility[:self.vol_window] = mean_vol

        # Feature matrix: [log_return, volatility]
        features = np.column_stack([log_returns, volatility])

        # Remove any NaN/Inf
        mask = ~(np.isnan(features).any(axis=1) | np.isinf(features).any(axis=1))
        features = features[mask]
        log_returns = log_returns[mask]
        volatility = volatility[mask]

        return features, log_returns, volatility

    def fit(self, prices: np.ndarray) -> "HMMRegimeDetector":
        """
        Fit the HMM model to historical price data.

        Parameters
        ----------
        prices : np.ndarray
            Historical close prices

        Returns
        -------
        self
            Fitted detector
        """
        if not HMM_AVAILABLE:
            logger.error("Cannot fit HMM - hmmlearn not installed")
            return self

        if len(prices) < self.min_data_points:
            logger.warning(f"Insufficient data: {len(prices)} < {self.min_data_points}")
            return self

        features, log_returns, volatility = self._prepare_features(prices)

        if len(features) < self.min_data_points:
            logger.warning(f"Insufficient data after preprocessing")
            return self

        # Initialize and fit HMM
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            self.model = GaussianHMM(
                n_components=self.n_states,
                covariance_type='full',
                n_iter=self.n_iter,
                random_state=self.random_state,
            )

            self.model.fit(features)

        # Identify states by mean return (bear = lowest, bull = highest)
        hidden_states = self.model.predict(features)

        # Calculate mean return for each state
        state_means = {}
        for state in range(self.n_states):
            mask = hidden_states == state
            if np.sum(mask) > 0:
                state_means[state] = np.mean(log_returns[mask])
            else:
                state_means[state] = 0.0

        # Sort states: lowest return = BEAR, highest = BULL
        sorted_states = sorted(state_means.items(), key=lambda x: x[1])

        self.state_mapping = {
            sorted_states[0][0]: HMMRegime.BEAR,
            sorted_states[-1][0]: HMMRegime.BULL,
        }
        if self.n_states >= 3:
            self.state_mapping[sorted_states[1][0]] = HMMRegime.NEUTRAL

        self.state_means = state_means
        self.is_fitted = True

        logger.info(f"HMM fitted with {self.n_states} states on {len(features)} samples")
        logger.debug(f"State means: {state_means}")
        logger.debug(f"State mapping: {self.state_mapping}")

        return self

    def predict_regime(self, prices: np.ndarray) -> HMMRegimeResult:
        """
        Predict the current market regime.

        Parameters
        ----------
        prices : np.ndarray
            Price data (must include recent history for feature calculation)

        Returns
        -------
        HMMRegimeResult
            Regime prediction with probabilities
        """
        if not self.is_fitted or self.model is None:
            return HMMRegimeResult(
                regime=HMMRegime.NEUTRAL,
                probabilities={r.value: 0.33 for r in HMMRegime},
                confidence=0.33,
                log_return=0.0,
                volatility=0.0,
                is_trained=False,
            )

        features, log_returns, volatility = self._prepare_features(prices)

        if len(features) == 0:
            return HMMRegimeResult(
                regime=HMMRegime.NEUTRAL,
                probabilities={r.value: 0.33 for r in HMMRegime},
                confidence=0.33,
                log_return=0.0,
                volatility=0.0,
                is_trained=self.is_fitted,
            )

        # Get state probabilities
        probs = self.model.predict_proba(features)
        current_probs = probs[-1]

        # Get most likely state
        current_state = np.argmax(current_probs)
        regime = self.state_mapping.get(current_state, HMMRegime.NEUTRAL)

        # Build probability dict
        prob_dict = {}
        for state, regime_enum in self.state_mapping.items():
            prob_dict[regime_enum.value] = float(current_probs[state])

        # Fill any missing regimes
        for r in HMMRegime:
            if r.value not in prob_dict:
                prob_dict[r.value] = 0.0

        return HMMRegimeResult(
            regime=regime,
            probabilities=prob_dict,
            confidence=float(current_probs[current_state]),
            log_return=float(log_returns[-1]),
            volatility=float(volatility[-1]),
            is_trained=True,
        )

    def get_regime_history(self, prices: np.ndarray) -> List[HMMRegime]:
        """
        Get historical regime classifications.

        Parameters
        ----------
        prices : np.ndarray
            Price data

        Returns
        -------
        list
            List of regime classifications for each time point
        """
        if not self.is_fitted or self.model is None:
            return [HMMRegime.NEUTRAL] * len(prices)

        features, _, _ = self._prepare_features(prices)
        hidden_states = self.model.predict(features)

        regimes = []
        for state in hidden_states:
            regime = self.state_mapping.get(state, HMMRegime.NEUTRAL)
            regimes.append(regime)

        return regimes

    def get_transition_matrix(self) -> Optional[np.ndarray]:
        """
        Get the learned transition probability matrix.

        Returns
        -------
        np.ndarray or None
            Transition matrix where [i,j] is P(state j | state i)
        """
        if self.model is None:
            return None
        return self.model.transmat_

    def get_regime_statistics(self, prices: np.ndarray) -> Dict:
        """
        Get statistics about regime distribution in historical data.

        Parameters
        ----------
        prices : np.ndarray
            Price data

        Returns
        -------
        dict
            Regime statistics
        """
        regimes = self.get_regime_history(prices)

        counts = {r.value: 0 for r in HMMRegime}
        for r in regimes:
            counts[r.value] += 1

        total = len(regimes)
        percentages = {k: v / total * 100 for k, v in counts.items()}

        return {
            'counts': counts,
            'percentages': percentages,
            'total_periods': total,
            'transition_matrix': self.get_transition_matrix(),
        }


# Fallback SMA-based detector when HMM not available
class SMARegimeDetector:
    """
    Simple SMA-based regime detector (fallback when HMM unavailable).

    Uses SMA crossover and volatility for regime classification.
    Less sophisticated than HMM but doesn't require additional dependencies.
    """

    def __init__(
        self,
        short_window: int = 20,
        long_window: int = 50,
        vol_window: int = 20,
        trend_threshold: float = 0.02,
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.vol_window = vol_window
        self.trend_threshold = trend_threshold
        self.is_fitted = True  # Always "fitted"

    def fit(self, prices: np.ndarray) -> "SMARegimeDetector":
        """SMA detector doesn't need training"""
        return self

    def predict_regime(self, prices: np.ndarray) -> HMMRegimeResult:
        """Predict regime using SMA crossover"""
        if len(prices) < self.long_window:
            return HMMRegimeResult(
                regime=HMMRegime.NEUTRAL,
                probabilities={r.value: 0.33 for r in HMMRegime},
                confidence=0.5,
                log_return=0.0,
                volatility=0.0,
                is_trained=True,
            )

        short_sma = np.mean(prices[-self.short_window:])
        long_sma = np.mean(prices[-self.long_window:])

        trend = (short_sma - long_sma) / long_sma if long_sma > 0 else 0

        if trend > self.trend_threshold:
            regime = HMMRegime.BULL
            probs = {HMMRegime.BULL.value: 0.7, HMMRegime.NEUTRAL.value: 0.2, HMMRegime.BEAR.value: 0.1}
        elif trend < -self.trend_threshold:
            regime = HMMRegime.BEAR
            probs = {HMMRegime.BEAR.value: 0.7, HMMRegime.NEUTRAL.value: 0.2, HMMRegime.BULL.value: 0.1}
        else:
            regime = HMMRegime.NEUTRAL
            probs = {HMMRegime.NEUTRAL.value: 0.6, HMMRegime.BULL.value: 0.2, HMMRegime.BEAR.value: 0.2}

        # Calculate log return and volatility
        log_return = np.log(prices[-1] / prices[-2]) if len(prices) > 1 else 0
        returns = np.diff(np.log(prices[-self.vol_window:])) if len(prices) > self.vol_window else np.array([0])
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0

        return HMMRegimeResult(
            regime=regime,
            probabilities=probs,
            confidence=max(probs.values()),
            log_return=log_return,
            volatility=volatility,
            is_trained=True,
        )


def create_regime_detector(use_hmm: bool = True, **kwargs) -> "HMMRegimeDetector | SMARegimeDetector":
    """
    Factory function to create appropriate regime detector.

    Parameters
    ----------
    use_hmm : bool
        Prefer HMM if available
    **kwargs
        Arguments passed to detector constructor

    Returns
    -------
    Detector instance
    """
    if use_hmm and HMM_AVAILABLE:
        return HMMRegimeDetector(**kwargs)
    else:
        if use_hmm and not HMM_AVAILABLE:
            logger.warning("HMM requested but hmmlearn not installed. Using SMA fallback.")
        return SMARegimeDetector(**kwargs)


# Convenience function
def detect_regime(prices: np.ndarray, use_hmm: bool = True) -> str:
    """
    Quick regime detection.

    Parameters
    ----------
    prices : np.ndarray
        Price data
    use_hmm : bool
        Use HMM if available

    Returns
    -------
    str
        Regime string: 'bull', 'bear', or 'neutral'
    """
    detector = create_regime_detector(use_hmm=use_hmm)
    detector.fit(prices)
    result = detector.predict_regime(prices)
    return result.regime.value


# Global detector instance (SMA fallback if HMM unavailable)
default_hmm_detector = create_regime_detector(use_hmm=True)
