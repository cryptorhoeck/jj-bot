"""
Strategy Configuration System

Allows users to customize parameters for all strategies:
- RSI periods and thresholds
- Moving average lengths
- MACD parameters
- Indicator-specific settings

Configuration can be saved/loaded per strategy.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, List
import json
import os


@dataclass
class RSIConfig:
    """RSI Strategy Configuration"""
    period: int = 14
    oversold_threshold: float = 30.0
    overbought_threshold: float = 70.0
    smoothing_period: int = 3  # For smoother signals

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RSIConfig':
        return cls(**data)


@dataclass
class SMAConfig:
    """Moving Average Strategy Configuration"""
    short_period: int = 20
    long_period: int = 50
    use_ema: bool = False  # Use EMA instead of SMA

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'SMAConfig':
        return cls(**data)


@dataclass
class MACDConfig:
    """MACD Strategy Configuration"""
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    histogram_threshold: float = 0.0  # Minimum histogram value for signal

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MACDConfig':
        return cls(**data)


@dataclass
class BollingerBandsConfig:
    """Bollinger Bands Strategy Configuration"""
    period: int = 20
    std_dev: float = 2.0
    use_middle_band: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'BollingerBandsConfig':
        return cls(**data)


@dataclass
class StochasticConfig:
    """Stochastic Oscillator Configuration"""
    k_period: int = 14
    d_period: int = 3
    oversold: float = 20.0
    overbought: float = 80.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'StochasticConfig':
        return cls(**data)


@dataclass
class IchimokuConfig:
    """Ichimoku Cloud Configuration"""
    tenkan_period: int = 9
    kijun_period: int = 26
    senkou_b_period: int = 52

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'IchimokuConfig':
        return cls(**data)


@dataclass
class ADXConfig:
    """ADX (Trend Strength) Configuration"""
    period: int = 14
    trend_threshold: float = 25.0  # Above = strong trend

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ADXConfig':
        return cls(**data)


@dataclass
class ATRConfig:
    """Average True Range Configuration"""
    period: int = 14
    multiplier: float = 2.0  # For stop-loss calculation

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ATRConfig':
        return cls(**data)


@dataclass
class StrategyParameters:
    """Complete strategy parameter configuration"""

    # Common indicators
    rsi: RSIConfig = field(default_factory=RSIConfig)
    sma: SMAConfig = field(default_factory=SMAConfig)
    macd: MACDConfig = field(default_factory=MACDConfig)
    bollinger_bands: BollingerBandsConfig = field(default_factory=BollingerBandsConfig)
    stochastic: StochasticConfig = field(default_factory=StochasticConfig)
    ichimoku: IchimokuConfig = field(default_factory=IchimokuConfig)
    adx: ADXConfig = field(default_factory=ADXConfig)
    atr: ATRConfig = field(default_factory=ATRConfig)

    # Strategy-specific overrides
    custom_parameters: Dict[str, Dict] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "rsi": self.rsi.to_dict(),
            "sma": self.sma.to_dict(),
            "macd": self.macd.to_dict(),
            "bollinger_bands": self.bollinger_bands.to_dict(),
            "stochastic": self.stochastic.to_dict(),
            "ichimoku": self.ichimoku.to_dict(),
            "adx": self.adx.to_dict(),
            "atr": self.atr.to_dict(),
            "custom_parameters": self.custom_parameters
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyParameters':
        return cls(
            rsi=RSIConfig.from_dict(data.get("rsi", {})),
            sma=SMAConfig.from_dict(data.get("sma", {})),
            macd=MACDConfig.from_dict(data.get("macd", {})),
            bollinger_bands=BollingerBandsConfig.from_dict(data.get("bollinger_bands", {})),
            stochastic=StochasticConfig.from_dict(data.get("stochastic", {})),
            ichimoku=IchimokuConfig.from_dict(data.get("ichimoku", {})),
            adx=ADXConfig.from_dict(data.get("adx", {})),
            atr=ATRConfig.from_dict(data.get("atr", {})),
            custom_parameters=data.get("custom_parameters", {})
        )

    def save(self, filepath: str):
        """Save configuration to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'StrategyParameters':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def get_default_presets(cls) -> Dict[str, 'StrategyParameters']:
        """Get predefined strategy parameter presets"""
        return {
            "conservative": cls(
                rsi=RSIConfig(period=14, oversold_threshold=25, overbought_threshold=75),
                sma=SMAConfig(short_period=30, long_period=60),
                macd=MACDConfig(fast_period=15, slow_period=30, signal_period=10),
                bollinger_bands=BollingerBandsConfig(period=20, std_dev=2.5),
                atr=ATRConfig(period=14, multiplier=2.5)
            ),

            "moderate": cls(
                rsi=RSIConfig(period=14, oversold_threshold=30, overbought_threshold=70),
                sma=SMAConfig(short_period=20, long_period=50),
                macd=MACDConfig(fast_period=12, slow_period=26, signal_period=9),
                bollinger_bands=BollingerBandsConfig(period=20, std_dev=2.0),
                atr=ATRConfig(period=14, multiplier=2.0)
            ),

            "aggressive": cls(
                rsi=RSIConfig(period=10, oversold_threshold=35, overbought_threshold=65),
                sma=SMAConfig(short_period=10, long_period=30, use_ema=True),
                macd=MACDConfig(fast_period=8, slow_period=21, signal_period=5),
                bollinger_bands=BollingerBandsConfig(period=15, std_dev=1.5),
                atr=ATRConfig(period=10, multiplier=1.5)
            ),

            "scalping": cls(
                rsi=RSIConfig(period=7, oversold_threshold=40, overbought_threshold=60, smoothing_period=2),
                sma=SMAConfig(short_period=5, long_period=15, use_ema=True),
                macd=MACDConfig(fast_period=5, slow_period=13, signal_period=3),
                bollinger_bands=BollingerBandsConfig(period=10, std_dev=1.5),
                atr=ATRConfig(period=7, multiplier=1.0)
            ),

            "swing_trading": cls(
                rsi=RSIConfig(period=21, oversold_threshold=30, overbought_threshold=70),
                sma=SMAConfig(short_period=50, long_period=200),
                macd=MACDConfig(fast_period=19, slow_period=39, signal_period=9),
                bollinger_bands=BollingerBandsConfig(period=30, std_dev=2.5),
                atr=ATRConfig(period=21, multiplier=3.0)
            )
        }


# Strategy metadata for UI generation
STRATEGY_METADATA = {
    "rsi_strategy": {
        "name": "RSI Strategy",
        "description": "Relative Strength Index momentum indicator",
        "category": "momentum",
        "parameters": ["rsi"],
        "complexity": "beginner"
    },
    "sma_crossover": {
        "name": "SMA Crossover",
        "description": "Simple/Exponential Moving Average crossover",
        "category": "trend",
        "parameters": ["sma"],
        "complexity": "beginner"
    },
    "macd": {
        "name": "MACD",
        "description": "Moving Average Convergence Divergence",
        "category": "momentum",
        "parameters": ["macd"],
        "complexity": "intermediate"
    },
    "bollinger_bands": {
        "name": "Bollinger Bands",
        "description": "Volatility bands around moving average",
        "category": "volatility",
        "parameters": ["bollinger_bands"],
        "complexity": "intermediate"
    },
    "stochastic": {
        "name": "Stochastic Oscillator",
        "description": "Momentum indicator comparing closing price to price range",
        "category": "momentum",
        "parameters": ["stochastic"],
        "complexity": "intermediate"
    },
    "ichimoku": {
        "name": "Ichimoku Cloud",
        "description": "All-in-one indicator for trend, momentum, and support/resistance",
        "category": "trend",
        "parameters": ["ichimoku"],
        "complexity": "advanced"
    },
    "adx": {
        "name": "ADX (Average Directional Index)",
        "description": "Measures trend strength",
        "category": "trend",
        "parameters": ["adx"],
        "complexity": "intermediate"
    },
    "supertrend": {
        "name": "SuperTrend",
        "description": "Trend-following indicator based on ATR",
        "category": "trend",
        "parameters": ["atr"],
        "complexity": "intermediate"
    },
    "combined_indicators": {
        "name": "Combined Indicators",
        "description": "Combines RSI, SMA, and MACD signals",
        "category": "hybrid",
        "parameters": ["rsi", "sma", "macd"],
        "complexity": "advanced"
    }
}


def get_config_dir() -> str:
    """Get configuration directory"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_dir = os.path.join(project_root, "data", "strategy_configs")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def save_strategy_config(config: StrategyParameters, name: str = "active"):
    """Save strategy configuration"""
    config_dir = get_config_dir()
    filepath = os.path.join(config_dir, f"{name}.json")
    config.save(filepath)


def load_strategy_config(name: str = "active") -> Optional[StrategyParameters]:
    """Load strategy configuration"""
    config_dir = get_config_dir()
    filepath = os.path.join(config_dir, f"{name}.json")

    if not os.path.exists(filepath):
        return None

    return StrategyParameters.load(filepath)


def get_strategy_preset(name: str) -> Optional[StrategyParameters]:
    """Get a preset strategy configuration"""
    presets = StrategyParameters.get_default_presets()
    return presets.get(name)
