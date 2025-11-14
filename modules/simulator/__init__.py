"""
Simulator Module

Realistic market simulation with:
- GBM price generation
- Regime switching
- Market mechanics (slippage, commission)
- Position management
"""

from .price_generator import (
    RealisticPriceGenerator,
    MultiSymbolPriceGenerator,
    MarketRegime,
    PriceTickdata
)

from .market_simulator import (
    MarketSimulator,
    Position,
    Trade,
    OrderSide,
    PositionSide
)

__all__ = [
    "RealisticPriceGenerator",
    "MultiSymbolPriceGenerator",
    "MarketRegime",
    "PriceTickdata",
    "MarketSimulator",
    "Position",
    "Trade",
    "OrderSide",
    "PositionSide",
]
