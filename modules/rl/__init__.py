"""
Reinforcement Learning Module

PPO and A2C agents for autonomous trading, with Renaissance Technologies-inspired
strategies: HMM regime detection, Kelly Criterion position sizing, and VWAP signals.
"""

from .trading_env import (
    TradingEnvironment,
    Action,
    Position,
    TradeResult,
)

from .ppo_agent import (
    PPOAgent,
    A2CAgent,
    ActorCritic,
    Experience,
    create_agent,
)

from .regime_detector import (
    RegimeDetector,
    MarketRegime,
    RegimeAnalysis,
    detect_regime as sma_detect_regime,
    get_regime_stats,
)

from .hmm_regime_detector import (
    HMMRegimeDetector,
    SMARegimeDetector,
    HMMRegime,
    HMMRegimeResult,
    create_regime_detector,
    detect_regime as hmm_detect_regime,
)

from .kelly_criterion import (
    KellyCriterion,
    KellyFraction,
    KellyResult,
    calculate_kelly,
    kelly_from_trades,
)

from .vwap_calculator import (
    VWAPCalculator,
    VWAPStrategy,
    VWAPSignal,
    VWAPResult,
    Signal,
    calculate_vwap,
    get_vwap_signal,
)

from .jjbot_core import (
    JJBotCore,
    StrategyParams,
    SystemStatus,
    create_jjbot,
    get_default_jjbot,
)

__all__ = [
    # Trading Environment
    "TradingEnvironment",
    "Action",
    "Position",
    "TradeResult",
    # PPO Agent
    "PPOAgent",
    "A2CAgent",
    "ActorCritic",
    "Experience",
    "create_agent",
    # SMA Regime Detection
    "RegimeDetector",
    "MarketRegime",
    "RegimeAnalysis",
    "sma_detect_regime",
    "get_regime_stats",
    # HMM Regime Detection
    "HMMRegimeDetector",
    "SMARegimeDetector",
    "HMMRegime",
    "HMMRegimeResult",
    "create_regime_detector",
    "hmm_detect_regime",
    # Kelly Criterion
    "KellyCriterion",
    "KellyFraction",
    "KellyResult",
    "calculate_kelly",
    "kelly_from_trades",
    # VWAP Calculator
    "VWAPCalculator",
    "VWAPStrategy",
    "VWAPSignal",
    "VWAPResult",
    "Signal",
    "calculate_vwap",
    "get_vwap_signal",
    # JJBot Core
    "JJBotCore",
    "StrategyParams",
    "SystemStatus",
    "create_jjbot",
    "get_default_jjbot",
]
