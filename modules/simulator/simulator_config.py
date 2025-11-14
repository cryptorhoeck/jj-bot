"""
Simulator Configuration System

Allows users to customize:
- Price generation parameters (volatility, trend strength)
- Market regime probabilities
- Trading mechanics (commission, slippage, spreads)
- Risk management (stop-loss, take-profit)
- Position sizing

Configuration can be saved/loaded and exposed via API.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional
import json
import os


@dataclass
class PriceGenerationConfig:
    """Configuration for price generation"""

    # Tick settings
    tick_interval_seconds: int = 60  # Time between price updates

    # Volatility settings (multipliers on base volatility)
    volatility_multiplier: float = 1.0  # 1.0 = normal, 2.0 = twice as volatile

    # Trend strength (multipliers on base drift)
    trend_strength: float = 1.0  # 1.0 = normal, 2.0 = stronger trends

    # Regime duration (multiplier on base duration)
    regime_duration_multiplier: float = 1.0  # 1.0 = normal, 0.5 = faster regime changes

    # Correlation between symbols
    inter_symbol_correlation: float = 0.3  # 0 = independent, 1 = perfect correlation

    # Bid-ask spread in basis points
    spread_bps: float = 10.0  # 10 = 0.10% spread

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PriceGenerationConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class TradingMechanicsConfig:
    """Configuration for trading mechanics"""

    # Commission (as decimal)
    commission_rate: float = 0.001  # 0.1%

    # Slippage (as decimal)
    slippage_rate: float = 0.0005  # 0.05%

    # Position sizing (as % of capital)
    position_size_pct: float = 0.10  # 10% per trade

    # Maximum number of open positions
    max_open_positions: int = 5

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingMechanicsConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class RiskManagementConfig:
    """Configuration for risk management"""

    # Stop-loss
    use_stop_loss: bool = True
    stop_loss_pct: float = 0.02  # 2%

    # Take-profit
    use_take_profit: bool = True
    take_profit_pct: float = 0.05  # 5%

    # Trailing stop
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 0.03  # 3%

    # Maximum loss per trade (% of capital)
    max_loss_per_trade_pct: float = 0.02  # 2%

    # Maximum daily loss (% of capital)
    max_daily_loss_pct: float = 0.10  # 10%

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RiskManagementConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class SimulatorConfig:
    """Complete simulator configuration"""

    # Initial capital
    initial_capital: float = 10000.0

    # Trading frequency (attempt trade every N ticks)
    trade_frequency_ticks: int = 5

    # Sub-configurations
    price_generation: PriceGenerationConfig = None
    trading_mechanics: TradingMechanicsConfig = None
    risk_management: RiskManagementConfig = None

    def __post_init__(self):
        """Initialize sub-configurations if not provided"""
        if self.price_generation is None:
            self.price_generation = PriceGenerationConfig()
        if self.trading_mechanics is None:
            self.trading_mechanics = TradingMechanicsConfig()
        if self.risk_management is None:
            self.risk_management = RiskManagementConfig()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "initial_capital": self.initial_capital,
            "trade_frequency_ticks": self.trade_frequency_ticks,
            "price_generation": self.price_generation.to_dict(),
            "trading_mechanics": self.trading_mechanics.to_dict(),
            "risk_management": self.risk_management.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SimulatorConfig':
        """Create from dictionary"""
        return cls(
            initial_capital=data.get("initial_capital", 10000.0),
            trade_frequency_ticks=data.get("trade_frequency_ticks", 5),
            price_generation=PriceGenerationConfig.from_dict(
                data.get("price_generation", {})
            ),
            trading_mechanics=TradingMechanicsConfig.from_dict(
                data.get("trading_mechanics", {})
            ),
            risk_management=RiskManagementConfig.from_dict(
                data.get("risk_management", {})
            )
        )

    def save(self, filepath: str):
        """Save configuration to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'SimulatorConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def get_default_presets(cls) -> Dict[str, 'SimulatorConfig']:
        """Get predefined configuration presets"""
        return {
            "conservative": cls(
                initial_capital=10000.0,
                trade_frequency_ticks=10,  # Trade less frequently
                price_generation=PriceGenerationConfig(
                    volatility_multiplier=0.7,  # Lower volatility
                    trend_strength=0.8,
                    regime_duration_multiplier=1.5  # Longer regimes
                ),
                trading_mechanics=TradingMechanicsConfig(
                    position_size_pct=0.05,  # Smaller positions (5%)
                    max_open_positions=3
                ),
                risk_management=RiskManagementConfig(
                    stop_loss_pct=0.015,  # Tighter stop-loss (1.5%)
                    take_profit_pct=0.03,  # Lower target (3%)
                    max_loss_per_trade_pct=0.01,
                    max_daily_loss_pct=0.05
                )
            ),

            "moderate": cls(
                initial_capital=10000.0,
                trade_frequency_ticks=5,
                price_generation=PriceGenerationConfig(
                    volatility_multiplier=1.0,
                    trend_strength=1.0,
                    regime_duration_multiplier=1.0
                ),
                trading_mechanics=TradingMechanicsConfig(
                    position_size_pct=0.10,  # 10% positions
                    max_open_positions=5
                ),
                risk_management=RiskManagementConfig(
                    stop_loss_pct=0.02,  # 2% stop-loss
                    take_profit_pct=0.05,  # 5% target
                    max_loss_per_trade_pct=0.02,
                    max_daily_loss_pct=0.10
                )
            ),

            "aggressive": cls(
                initial_capital=10000.0,
                trade_frequency_ticks=3,  # Trade more frequently
                price_generation=PriceGenerationConfig(
                    volatility_multiplier=1.5,  # Higher volatility
                    trend_strength=1.3,
                    regime_duration_multiplier=0.7  # Faster regime changes
                ),
                trading_mechanics=TradingMechanicsConfig(
                    position_size_pct=0.15,  # Larger positions (15%)
                    max_open_positions=7
                ),
                risk_management=RiskManagementConfig(
                    stop_loss_pct=0.03,  # Wider stop-loss (3%)
                    take_profit_pct=0.08,  # Higher target (8%)
                    max_loss_per_trade_pct=0.03,
                    max_daily_loss_pct=0.15
                )
            ),

            "scalping": cls(
                initial_capital=10000.0,
                trade_frequency_ticks=1,  # Trade every tick
                price_generation=PriceGenerationConfig(
                    tick_interval_seconds=30,  # Faster ticks
                    volatility_multiplier=0.8,
                    trend_strength=0.6,
                    regime_duration_multiplier=2.0
                ),
                trading_mechanics=TradingMechanicsConfig(
                    position_size_pct=0.20,  # Large positions
                    max_open_positions=3,  # But fewer at once
                    commission_rate=0.0005,  # Assume maker rebates
                    slippage_rate=0.0003
                ),
                risk_management=RiskManagementConfig(
                    stop_loss_pct=0.01,  # Very tight stop (1%)
                    take_profit_pct=0.015,  # Small target (1.5%)
                    max_loss_per_trade_pct=0.01,
                    max_daily_loss_pct=0.10
                )
            ),

            "swing_trading": cls(
                initial_capital=10000.0,
                trade_frequency_ticks=20,  # Trade infrequently
                price_generation=PriceGenerationConfig(
                    tick_interval_seconds=300,  # 5-minute ticks
                    volatility_multiplier=1.2,
                    trend_strength=1.5,
                    regime_duration_multiplier=2.0  # Long-lasting trends
                ),
                trading_mechanics=TradingMechanicsConfig(
                    position_size_pct=0.12,
                    max_open_positions=4
                ),
                risk_management=RiskManagementConfig(
                    stop_loss_pct=0.05,  # Wide stop (5%)
                    take_profit_pct=0.15,  # Large target (15%)
                    use_trailing_stop=True,
                    trailing_stop_pct=0.03,
                    max_loss_per_trade_pct=0.05,
                    max_daily_loss_pct=0.15
                )
            )
        }


# Global default configuration
DEFAULT_CONFIG = SimulatorConfig()


def get_config_dir() -> str:
    """Get configuration directory"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    config_dir = os.path.join(project_root, "data", "simulator_configs")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def save_user_config(config: SimulatorConfig, name: str = "user_config"):
    """Save user configuration"""
    config_dir = get_config_dir()
    filepath = os.path.join(config_dir, f"{name}.json")
    config.save(filepath)


def load_user_config(name: str = "user_config") -> Optional[SimulatorConfig]:
    """Load user configuration"""
    config_dir = get_config_dir()
    filepath = os.path.join(config_dir, f"{name}.json")

    if not os.path.exists(filepath):
        return None

    return SimulatorConfig.load(filepath)


def get_preset(name: str) -> Optional[SimulatorConfig]:
    """Get a preset configuration by name"""
    presets = SimulatorConfig.get_default_presets()
    return presets.get(name)
