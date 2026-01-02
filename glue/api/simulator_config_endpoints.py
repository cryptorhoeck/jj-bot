"""
Simulator Configuration API Endpoints

Allows users to:
- Get/set simulator configuration
- Load preset configurations
- Create custom configurations
- Save/load user configurations
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel, Field

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.simulator.simulator_config import (
    SimulatorConfig,
    PriceGenerationConfig,
    TradingMechanicsConfig,
    RiskManagementConfig,
    get_preset,
    save_user_config,
    load_user_config
)

router = APIRouter(prefix="/api/simulator/config", tags=["simulator_config"])


# Pydantic models for API requests/responses
class PriceGenerationSettings(BaseModel):
    """Price generation settings"""
    tick_interval_seconds: int = Field(60, ge=1, le=3600, description="Time between price updates (1-3600 seconds)")
    volatility_multiplier: float = Field(1.0, ge=0.1, le=5.0, description="Volatility multiplier (0.1-5.0)")
    trend_strength: float = Field(1.0, ge=0.0, le=3.0, description="Trend strength multiplier (0-3.0)")
    regime_duration_multiplier: float = Field(1.0, ge=0.1, le=5.0, description="Regime duration multiplier (0.1-5.0)")
    inter_symbol_correlation: float = Field(0.3, ge=0.0, le=1.0, description="Inter-symbol correlation (0-1)")
    spread_bps: float = Field(10.0, ge=1.0, le=100.0, description="Bid-ask spread in basis points (1-100)")


class TradingMechanicsSettings(BaseModel):
    """Trading mechanics settings - REALISTIC VALUES"""
    commission_rate: float = Field(0.002, ge=0.0, le=0.01, description="Commission rate (default 0.2% realistic)")
    slippage_rate: float = Field(0.005, ge=0.0, le=0.02, description="Slippage rate (default 0.5% realistic)")
    position_size_pct: float = Field(0.10, ge=0.01, le=1.0, description="Position size as % of capital (1-100%)")
    max_open_positions: int = Field(5, ge=1, le=20, description="Maximum open positions (1-20)")


class RiskManagementSettings(BaseModel):
    """Risk management settings"""
    use_stop_loss: bool = Field(True, description="Enable stop-loss")
    stop_loss_pct: float = Field(0.02, ge=0.001, le=0.50, description="Stop-loss percentage (0.1-50%)")
    use_take_profit: bool = Field(True, description="Enable take-profit")
    take_profit_pct: float = Field(0.05, ge=0.001, le=1.0, description="Take-profit percentage (0.1-100%)")
    use_trailing_stop: bool = Field(False, description="Enable trailing stop")
    trailing_stop_pct: float = Field(0.03, ge=0.001, le=0.50, description="Trailing stop percentage (0.1-50%)")
    max_loss_per_trade_pct: float = Field(0.02, ge=0.001, le=0.50, description="Max loss per trade (0.1-50%)")
    max_daily_loss_pct: float = Field(0.10, ge=0.01, le=1.0, description="Max daily loss (1-100%)")


class SimulatorConfigModel(BaseModel):
    """Complete simulator configuration"""
    initial_capital: float = Field(10000.0, ge=100.0, le=1000000.0, description="Initial capital ($100-$1M)")
    trade_frequency_ticks: int = Field(5, ge=1, le=100, description="Trade frequency in ticks (1-100)")
    price_generation: PriceGenerationSettings
    trading_mechanics: TradingMechanicsSettings
    risk_management: RiskManagementSettings


# ===== ENDPOINTS =====

@router.get("/", summary="Get Current Configuration")
async def get_current_config() -> Dict[str, Any]:
    """
    Get the current simulator configuration.

    Returns the active configuration with all parameters.
    """
    # Try to load user config, fall back to default
    config = load_user_config("active") or SimulatorConfig()

    return {
        "success": True,
        "config": config.to_dict()
    }


@router.post("/", summary="Update Configuration")
async def update_config(config: SimulatorConfigModel) -> Dict[str, Any]:
    """
    Update the simulator configuration.

    This will be used for the next simulation run.
    """
    try:
        # Convert API model to internal config
        simulator_config = SimulatorConfig(
            initial_capital=config.initial_capital,
            trade_frequency_ticks=config.trade_frequency_ticks,
            price_generation=PriceGenerationConfig(
                tick_interval_seconds=config.price_generation.tick_interval_seconds,
                volatility_multiplier=config.price_generation.volatility_multiplier,
                trend_strength=config.price_generation.trend_strength,
                regime_duration_multiplier=config.price_generation.regime_duration_multiplier,
                inter_symbol_correlation=config.price_generation.inter_symbol_correlation,
                spread_bps=config.price_generation.spread_bps
            ),
            trading_mechanics=TradingMechanicsConfig(
                commission_rate=config.trading_mechanics.commission_rate,
                slippage_rate=config.trading_mechanics.slippage_rate,
                position_size_pct=config.trading_mechanics.position_size_pct,
                max_open_positions=config.trading_mechanics.max_open_positions
            ),
            risk_management=RiskManagementConfig(
                use_stop_loss=config.risk_management.use_stop_loss,
                stop_loss_pct=config.risk_management.stop_loss_pct,
                use_take_profit=config.risk_management.use_take_profit,
                take_profit_pct=config.risk_management.take_profit_pct,
                use_trailing_stop=config.risk_management.use_trailing_stop,
                trailing_stop_pct=config.risk_management.trailing_stop_pct,
                max_loss_per_trade_pct=config.risk_management.max_loss_per_trade_pct,
                max_daily_loss_pct=config.risk_management.max_daily_loss_pct
            )
        )

        # Save as active config
        save_user_config(simulator_config, "active")

        return {
            "success": True,
            "message": "Configuration updated successfully",
            "config": simulator_config.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/presets", summary="List Available Presets")
async def list_presets() -> Dict[str, Any]:
    """
    List all available preset configurations.

    Presets include: conservative, moderate, aggressive, scalping, swing_trading
    """
    presets = SimulatorConfig.get_default_presets()

    return {
        "success": True,
        "presets": {
            name: {
                "name": name,
                "description": _get_preset_description(name),
                "config": config.to_dict()
            }
            for name, config in presets.items()
        }
    }


@router.get("/presets/{preset_name}", summary="Get Preset Configuration")
async def get_preset_config(preset_name: str) -> Dict[str, Any]:
    """
    Get a specific preset configuration by name.

    Available presets:
    - conservative: Low risk, small positions, tight stops
    - moderate: Balanced risk/reward
    - aggressive: Higher risk, larger positions, wider stops
    - scalping: Very short-term, tight stops, frequent trades
    - swing_trading: Longer-term, wide stops, infrequent trades
    """
    config = get_preset(preset_name)

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_name}' not found"
        )

    return {
        "success": True,
        "preset_name": preset_name,
        "description": _get_preset_description(preset_name),
        "config": config.to_dict()
    }


@router.post("/presets/{preset_name}/activate", summary="Activate Preset")
async def activate_preset(preset_name: str) -> Dict[str, Any]:
    """
    Activate a preset configuration.

    This will replace the current configuration with the selected preset.
    """
    config = get_preset(preset_name)

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_name}' not found"
        )

    # Save as active config
    save_user_config(config, "active")

    return {
        "success": True,
        "message": f"Preset '{preset_name}' activated",
        "config": config.to_dict()
    }


@router.post("/reset", summary="Reset to Default")
async def reset_to_default() -> Dict[str, Any]:
    """
    Reset configuration to default (moderate preset).
    """
    config = get_preset("moderate") or SimulatorConfig()
    save_user_config(config, "active")

    return {
        "success": True,
        "message": "Configuration reset to default",
        "config": config.to_dict()
    }


@router.get("/parameter-ranges", summary="Get Parameter Ranges")
async def get_parameter_ranges() -> Dict[str, Any]:
    """
    Get valid ranges for all configuration parameters.

    Useful for building UI sliders and validation.
    """
    return {
        "success": True,
        "ranges": {
            "initial_capital": {
                "min": 100.0,
                "max": 1000000.0,
                "default": 10000.0,
                "step": 100.0,
                "description": "Starting capital in USD"
            },
            "trade_frequency_ticks": {
                "min": 1,
                "max": 100,
                "default": 5,
                "step": 1,
                "description": "Attempt trade every N ticks"
            },
            "tick_interval_seconds": {
                "min": 1,
                "max": 3600,
                "default": 60,
                "step": 1,
                "description": "Time between price updates (seconds)"
            },
            "volatility_multiplier": {
                "min": 0.1,
                "max": 5.0,
                "default": 1.0,
                "step": 0.1,
                "description": "Volatility multiplier (1.0 = normal)"
            },
            "trend_strength": {
                "min": 0.0,
                "max": 3.0,
                "default": 1.0,
                "step": 0.1,
                "description": "Trend strength (1.0 = normal)"
            },
            "commission_rate": {
                "min": 0.0,
                "max": 0.01,
                "default": 0.001,
                "step": 0.0001,
                "description": "Commission rate (0.001 = 0.1%)"
            },
            "slippage_rate": {
                "min": 0.0,
                "max": 0.01,
                "default": 0.0005,
                "step": 0.0001,
                "description": "Slippage rate (0.0005 = 0.05%)"
            },
            "position_size_pct": {
                "min": 0.01,
                "max": 1.0,
                "default": 0.10,
                "step": 0.01,
                "description": "Position size as fraction (0.10 = 10%)"
            },
            "stop_loss_pct": {
                "min": 0.001,
                "max": 0.50,
                "default": 0.02,
                "step": 0.001,
                "description": "Stop-loss as fraction (0.02 = 2%)"
            },
            "take_profit_pct": {
                "min": 0.001,
                "max": 1.0,
                "default": 0.05,
                "step": 0.001,
                "description": "Take-profit as fraction (0.05 = 5%)"
            }
        }
    }


def _get_preset_description(preset_name: str) -> str:
    """Get description for a preset"""
    descriptions = {
        "conservative": "Low-risk strategy with small positions (5%), tight stops (1.5%), and lower volatility. Best for preserving capital.",
        "moderate": "Balanced approach with medium positions (10%), standard stops (2%), and normal volatility. Good default for most users.",
        "aggressive": "High-risk strategy with large positions (15%), wide stops (3%), and higher volatility. Aims for bigger gains with more risk.",
        "scalping": "Very short-term strategy with tight stops (1%), small targets (1.5%), and frequent trades. Requires fast execution.",
        "swing_trading": "Long-term strategy with wide stops (5%), large targets (15%), and infrequent trades. Captures major trends."
    }
    return descriptions.get(preset_name, "Custom configuration")
