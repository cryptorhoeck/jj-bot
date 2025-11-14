"""
ML Feature Engineering API Endpoints

Provides RESTful endpoints for extracting ML features from market data
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.ml import feature_engineer
from modules.data import cached_market_data_service

router = APIRouter(prefix="/api/ml", tags=["machine_learning"])


# === Request/Response Models ===

class FeatureExtractionRequest(BaseModel):
    """Request model for feature extraction"""
    symbol: str
    timeframe: str = "1h"
    num_candles: int = 200
    source: str = "auto"
    include_labels: bool = False
    normalize: bool = False
    normalization_method: str = "standardize"  # or "minmax"


# === Endpoints ===

@router.post("/features/extract")
async def extract_features(request: FeatureExtractionRequest):
    """
    Extract ML features from market data

    Fetches real market data and extracts comprehensive feature set including:
    - Price-based features (returns, momentum, volatility)
    - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - Volume features
    - Time-based features
    - Market regime features

    Request body:
    {
        "symbol": "BTC",
        "timeframe": "1h",
        "num_candles": 200,
        "source": "auto",
        "include_labels": true,
        "normalize": true,
        "normalization_method": "standardize"
    }

    Returns:
        Feature matrix with feature names and optional labels
    """
    try:
        # Fetch market data
        data_result = cached_market_data_service.get_ohlcv(
            symbol=request.symbol,
            source=request.source,
            timeframe=request.timeframe,
            num_candles=request.num_candles
        )

        if not data_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch market data: {data_result.get('error')}"
            )

        candles = data_result["candles"]

        # Extract features
        result = feature_engineer.extract_all_features(
            candles=candles,
            include_labels=request.include_labels
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Feature extraction failed")
            )

        # Normalize if requested
        if request.normalize:
            normalized_features, norm_params = feature_engineer.normalize_features(
                result["features"],
                method=request.normalization_method
            )
            result["features"] = normalized_features
            result["normalization_params"] = norm_params
            result["normalized"] = True
        else:
            result["normalized"] = False

        # Add metadata
        result["data_source"] = data_result.get("source")
        result["symbol"] = request.symbol
        result["timeframe"] = request.timeframe

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/extract/{symbol}")
async def extract_features_get(
    symbol: str,
    timeframe: str = Query("1h", description="Candle timeframe"),
    num_candles: int = Query(200, description="Number of candles"),
    source: str = Query("auto", description="Data source"),
    include_labels: bool = Query(False, description="Include labels for supervised learning"),
    normalize: bool = Query(False, description="Normalize features"),
    normalization_method: str = Query("standardize", description="Normalization method")
):
    """
    Extract ML features (GET version)

    Simpler endpoint for quick feature extraction

    Examples:
    - /api/ml/features/extract/BTC?timeframe=1h&num_candles=100
    - /api/ml/features/extract/ETH?include_labels=true&normalize=true
    """
    request = FeatureExtractionRequest(
        symbol=symbol,
        timeframe=timeframe,
        num_candles=num_candles,
        source=source,
        include_labels=include_labels,
        normalize=normalize,
        normalization_method=normalization_method
    )

    return await extract_features(request)


@router.get("/features/info")
async def get_feature_info():
    """
    Get information about available features

    Returns detailed description of all feature categories and individual features

    Example:
    - GET /api/ml/features/info
    """
    return {
        "success": True,
        "feature_categories": {
            "price_based": {
                "description": "Features derived from OHLC price data",
                "features": [
                    "return_1", "return_5", "return_10", "return_20",
                    "log_return_1", "hl_range", "oc_range", "price_position",
                    "gap", "momentum_5", "momentum_10", "volatility_10", "volatility_20"
                ],
                "count": 13
            },
            "technical_indicators": {
                "description": "Technical analysis indicators",
                "features": [
                    "rsi_14", "rsi_normalized", "sma_20", "sma_50",
                    "price_to_sma20", "price_to_sma50", "sma20_to_sma50",
                    "macd", "macd_signal", "macd_histogram",
                    "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_position",
                    "atr_14"
                ],
                "count": 16
            },
            "volume": {
                "description": "Volume-based features",
                "features": [
                    "volume", "volume_sma_20", "volume_ratio",
                    "volume_change", "price_volume_trend"
                ],
                "count": 5
            },
            "time_based": {
                "description": "Time and seasonality features",
                "features": [
                    "hour", "day_of_week", "day_of_month", "month",
                    "is_weekend", "hour_sin", "hour_cos", "dow_sin", "dow_cos"
                ],
                "count": 9
            },
            "market_regime": {
                "description": "Market state and regime features",
                "features": [
                    "trend_strength", "volatility_regime",
                    "volume_regime", "market_phase"
                ],
                "count": 4
            }
        },
        "total_features": 47,
        "normalization_methods": ["standardize", "minmax"],
        "label_classes": {
            "1": "Price up (> 0.5%)",
            "-1": "Price down (< -0.5%)",
            "0": "Neutral (between -0.5% and 0.5%)"
        }
    }


@router.get("/features/sample")
async def get_sample_features():
    """
    Get a sample feature extraction to understand the output format

    Returns example feature extraction with all metadata

    Example:
    - GET /api/ml/features/sample
    """
    return {
        "success": True,
        "sample": {
            "features": [
                [0.02, 0.05, 0.08, 0.12, 0.019, 0.015, 0.01, 0.75, 0.001, 5.2, 8.1, 0.012, 0.018],
                # ... more feature vectors
            ],
            "feature_names": [
                "return_1", "return_5", "return_10", "return_20", "log_return_1",
                "hl_range", "oc_range", "price_position", "gap",
                "momentum_5", "momentum_10", "volatility_10", "volatility_20",
                # ... more feature names
            ],
            "labels": [1, 1, -1, 0, 1],  # Optional, if include_labels=true
            "num_features": 47,
            "num_samples": 200
        },
        "usage": "Use POST /api/ml/features/extract with your desired parameters",
        "note": "This is example data only. Use the extract endpoint for real features."
    }


@router.post("/features/normalize")
async def normalize_features_endpoint(
    features: list,
    method: str = "standardize"
):
    """
    Normalize a feature matrix

    Useful for normalizing features extracted separately

    Request body:
    {
        "features": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        "method": "standardize"
    }

    Methods:
    - "standardize": Z-score normalization (mean=0, std=1)
    - "minmax": Min-max scaling (range 0-1)

    Example:
    - POST /api/ml/features/normalize
    """
    try:
        if not features:
            raise HTTPException(status_code=400, detail="No features provided")

        normalized, params = feature_engineer.normalize_features(features, method)

        return {
            "success": True,
            "normalized_features": normalized,
            "normalization_params": params,
            "method": method
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ml_status():
    """
    Get ML module status and capabilities

    Returns information about the ML feature engineering system

    Example:
    - GET /api/ml/status
    """
    return {
        "success": True,
        "status": "operational",
        "capabilities": {
            "feature_extraction": True,
            "feature_normalization": True,
            "label_generation": True,
            "real_time_data_integration": True
        },
        "supported_markets": ["crypto", "stocks"],
        "supported_timeframes": ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"],
        "feature_count": 47,
        "endpoints": [
            "POST /api/ml/features/extract",
            "GET /api/ml/features/extract/{symbol}",
            "GET /api/ml/features/info",
            "GET /api/ml/features/sample",
            "POST /api/ml/features/normalize",
            "GET /api/ml/status"
        ]
    }
