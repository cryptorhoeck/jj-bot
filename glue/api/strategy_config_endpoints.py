"""
Strategy Configuration API Endpoints

Allows users to:
- Get/set strategy parameters
- Load preset configurations
- Customize individual indicator settings
- List available strategies with metadata
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.strategy.strategy_config import (
    StrategyParameters,
    RSIConfig,
    SMAConfig,
    MACDConfig,
    BollingerBandsConfig,
    StochasticConfig,
    IchimokuConfig,
    ADXConfig,
    ATRConfig,
    STRATEGY_METADATA,
    get_strategy_preset,
    save_strategy_config,
    load_strategy_config
)

router = APIRouter(prefix="/api/strategy/config", tags=["strategy_config"])


# Pydantic models for API
class RSISettings(BaseModel):
    period: int = Field(14, ge=2, le=50, description="RSI period (2-50)")
    oversold_threshold: float = Field(30.0, ge=0, le=50, description="Oversold threshold (0-50)")
    overbought_threshold: float = Field(70.0, ge=50, le=100, description="Overbought threshold (50-100)")
    smoothing_period: int = Field(3, ge=1, le=10, description="Smoothing period (1-10)")


class SMASettings(BaseModel):
    short_period: int = Field(20, ge=5, le=100, description="Short period (5-100)")
    long_period: int = Field(50, ge=10, le=300, description="Long period (10-300)")
    use_ema: bool = Field(False, description="Use EMA instead of SMA")


class MACDSettings(BaseModel):
    fast_period: int = Field(12, ge=3, le=50, description="Fast period (3-50)")
    slow_period: int = Field(26, ge=10, le=100, description="Slow period (10-100)")
    signal_period: int = Field(9, ge=2, le=30, description="Signal period (2-30)")
    histogram_threshold: float = Field(0.0, ge=-10, le=10, description="Histogram threshold (-10 to 10)")


class BollingerBandsSettings(BaseModel):
    period: int = Field(20, ge=5, le=100, description="Period (5-100)")
    std_dev: float = Field(2.0, ge=0.5, le=5.0, description="Standard deviations (0.5-5.0)")
    use_middle_band: bool = Field(True, description="Use middle band for signals")


class StochasticSettings(BaseModel):
    k_period: int = Field(14, ge=5, le=50, description="%K period (5-50)")
    d_period: int = Field(3, ge=1, le=10, description="%D period (1-10)")
    oversold: float = Field(20.0, ge=0, le=50, description="Oversold level (0-50)")
    overbought: float = Field(80.0, ge=50, le=100, description="Overbought level (50-100)")


class IchimokuSettings(BaseModel):
    tenkan_period: int = Field(9, ge=5, le=30, description="Tenkan period (5-30)")
    kijun_period: int = Field(26, ge=10, le=50, description="Kijun period (10-50)")
    senkou_b_period: int = Field(52, ge=20, le=100, description="Senkou B period (20-100)")


class ADXSettings(BaseModel):
    period: int = Field(14, ge=5, le=50, description="ADX period (5-50)")
    trend_threshold: float = Field(25.0, ge=10, le=50, description="Trend strength threshold (10-50)")


class ATRSettings(BaseModel):
    period: int = Field(14, ge=5, le=50, description="ATR period (5-50)")
    multiplier: float = Field(2.0, ge=0.5, le=5.0, description="ATR multiplier (0.5-5.0)")


class StrategyConfigModel(BaseModel):
    rsi: RSISettings
    sma: SMASettings
    macd: MACDSettings
    bollinger_bands: BollingerBandsSettings
    stochastic: StochasticSettings
    ichimoku: IchimokuSettings
    adx: ADXSettings
    atr: ATRSettings


# ===== ENDPOINTS =====

@router.get("/", summary="Get Current Strategy Configuration")
async def get_current_strategy_config() -> Dict[str, Any]:
    """
    Get the current strategy parameters configuration.

    Returns all indicator settings that will be used for strategy execution.
    """
    config = load_strategy_config("active") or StrategyParameters()

    return {
        "success": True,
        "config": config.to_dict()
    }


@router.post("/", summary="Update Strategy Configuration")
async def update_strategy_config(config: StrategyConfigModel) -> Dict[str, Any]:
    """
    Update the strategy parameters configuration.

    This will be used for the next trading signals.
    """
    try:
        # Convert API model to internal config
        strategy_params = StrategyParameters(
            rsi=RSIConfig(
                period=config.rsi.period,
                oversold_threshold=config.rsi.oversold_threshold,
                overbought_threshold=config.rsi.overbought_threshold,
                smoothing_period=config.rsi.smoothing_period
            ),
            sma=SMAConfig(
                short_period=config.sma.short_period,
                long_period=config.sma.long_period,
                use_ema=config.sma.use_ema
            ),
            macd=MACDConfig(
                fast_period=config.macd.fast_period,
                slow_period=config.macd.slow_period,
                signal_period=config.macd.signal_period,
                histogram_threshold=config.macd.histogram_threshold
            ),
            bollinger_bands=BollingerBandsConfig(
                period=config.bollinger_bands.period,
                std_dev=config.bollinger_bands.std_dev,
                use_middle_band=config.bollinger_bands.use_middle_band
            ),
            stochastic=StochasticConfig(
                k_period=config.stochastic.k_period,
                d_period=config.stochastic.d_period,
                oversold=config.stochastic.oversold,
                overbought=config.stochastic.overbought
            ),
            ichimoku=IchimokuConfig(
                tenkan_period=config.ichimoku.tenkan_period,
                kijun_period=config.ichimoku.kijun_period,
                senkou_b_period=config.ichimoku.senkou_b_period
            ),
            adx=ADXConfig(
                period=config.adx.period,
                trend_threshold=config.adx.trend_threshold
            ),
            atr=ATRConfig(
                period=config.atr.period,
                multiplier=config.atr.multiplier
            )
        )

        # Save as active config
        save_strategy_config(strategy_params, "active")

        return {
            "success": True,
            "message": "Strategy configuration updated successfully",
            "config": strategy_params.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/strategies", summary="List Available Strategies")
async def list_strategies() -> Dict[str, Any]:
    """
    List all available trading strategies with metadata.

    Returns information about each strategy including:
    - Name and description
    - Category (momentum/trend/volatility/hybrid)
    - Required parameters
    - Complexity level
    """
    return {
        "success": True,
        "strategies": STRATEGY_METADATA
    }


@router.get("/strategies/{strategy_name}", summary="Get Strategy Details")
async def get_strategy_details(strategy_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific strategy.
    """
    if strategy_name not in STRATEGY_METADATA:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_name}' not found"
        )

    metadata = STRATEGY_METADATA[strategy_name]
    config = load_strategy_config("active") or StrategyParameters()

    # Get relevant parameters for this strategy
    relevant_params = {}
    for param_name in metadata["parameters"]:
        param_config = getattr(config, param_name, None)
        if param_config:
            relevant_params[param_name] = param_config.to_dict()

    return {
        "success": True,
        "strategy": strategy_name,
        "metadata": metadata,
        "parameters": relevant_params
    }


@router.get("/presets", summary="List Parameter Presets")
async def list_parameter_presets() -> Dict[str, Any]:
    """
    List all available parameter presets.

    Presets include: conservative, moderate, aggressive, scalping, swing_trading
    """
    presets = StrategyParameters.get_default_presets()

    return {
        "success": True,
        "presets": {
            name: {
                "name": name,
                "description": _get_preset_description(name),
                "config": params.to_dict()
            }
            for name, params in presets.items()
        }
    }


@router.get("/presets/{preset_name}", summary="Get Preset Parameters")
async def get_preset_parameters(preset_name: str) -> Dict[str, Any]:
    """
    Get a specific parameter preset by name.
    """
    params = get_strategy_preset(preset_name)

    if not params:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_name}' not found"
        )

    return {
        "success": True,
        "preset_name": preset_name,
        "description": _get_preset_description(preset_name),
        "config": params.to_dict()
    }


@router.post("/presets/{preset_name}/activate", summary="Activate Parameter Preset")
async def activate_preset_parameters(preset_name: str) -> Dict[str, Any]:
    """
    Activate a parameter preset.

    This will replace current strategy parameters with the selected preset.
    """
    params = get_strategy_preset(preset_name)

    if not params:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_name}' not found"
        )

    # Save as active config
    save_strategy_config(params, "active")

    return {
        "success": True,
        "message": f"Parameter preset '{preset_name}' activated",
        "config": params.to_dict()
    }


@router.post("/reset", summary="Reset to Default Parameters")
async def reset_to_default_parameters() -> Dict[str, Any]:
    """
    Reset strategy parameters to default (moderate preset).
    """
    params = get_strategy_preset("moderate") or StrategyParameters()
    save_strategy_config(params, "active")

    return {
        "success": True,
        "message": "Strategy parameters reset to default",
        "config": params.to_dict()
    }


@router.get("/parameter-ranges", summary="Get Parameter Ranges")
async def get_strategy_parameter_ranges() -> Dict[str, Any]:
    """
    Get valid ranges for all strategy parameters.

    Useful for building UI sliders and validation.
    """
    return {
        "success": True,
        "ranges": {
            "rsi": {
                "period": {"min": 2, "max": 50, "default": 14, "step": 1},
                "oversold_threshold": {"min": 0, "max": 50, "default": 30, "step": 1},
                "overbought_threshold": {"min": 50, "max": 100, "default": 70, "step": 1},
                "smoothing_period": {"min": 1, "max": 10, "default": 3, "step": 1}
            },
            "sma": {
                "short_period": {"min": 5, "max": 100, "default": 20, "step": 1},
                "long_period": {"min": 10, "max": 300, "default": 50, "step": 5},
                "use_ema": {"type": "boolean", "default": False}
            },
            "macd": {
                "fast_period": {"min": 3, "max": 50, "default": 12, "step": 1},
                "slow_period": {"min": 10, "max": 100, "default": 26, "step": 1},
                "signal_period": {"min": 2, "max": 30, "default": 9, "step": 1},
                "histogram_threshold": {"min": -10, "max": 10, "default": 0, "step": 0.1}
            },
            "bollinger_bands": {
                "period": {"min": 5, "max": 100, "default": 20, "step": 1},
                "std_dev": {"min": 0.5, "max": 5.0, "default": 2.0, "step": 0.1},
                "use_middle_band": {"type": "boolean", "default": True}
            },
            "stochastic": {
                "k_period": {"min": 5, "max": 50, "default": 14, "step": 1},
                "d_period": {"min": 1, "max": 10, "default": 3, "step": 1},
                "oversold": {"min": 0, "max": 50, "default": 20, "step": 1},
                "overbought": {"min": 50, "max": 100, "default": 80, "step": 1}
            },
            "ichimoku": {
                "tenkan_period": {"min": 5, "max": 30, "default": 9, "step": 1},
                "kijun_period": {"min": 10, "max": 50, "default": 26, "step": 1},
                "senkou_b_period": {"min": 20, "max": 100, "default": 52, "step": 1}
            },
            "adx": {
                "period": {"min": 5, "max": 50, "default": 14, "step": 1},
                "trend_threshold": {"min": 10, "max": 50, "default": 25, "step": 1}
            },
            "atr": {
                "period": {"min": 5, "max": 50, "default": 14, "step": 1},
                "multiplier": {"min": 0.5, "max": 5.0, "default": 2.0, "step": 0.1}
            }
        }
    }


def _get_preset_description(preset_name: str) -> str:
    """Get description for a parameter preset"""
    descriptions = {
        "conservative": "Conservative parameters: longer periods, wider thresholds, less sensitive to noise",
        "moderate": "Balanced parameters: standard periods and thresholds, good for most markets",
        "aggressive": "Aggressive parameters: shorter periods, tighter thresholds, more responsive to price action",
        "scalping": "Ultra-short-term parameters: very short periods for quick trades",
        "swing_trading": "Long-term parameters: longer periods for capturing major trends"
    }
    return descriptions.get(preset_name, "Custom parameter configuration")
