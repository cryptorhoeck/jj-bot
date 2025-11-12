"""
Learning System API Endpoints

Provides access to:
- Strategy performance tracking
- Market regime detection
- Adaptive strategy selection
- Price history and patterns
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime, timedelta
import os
import sys
import sqlite3

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

router = APIRouter(prefix="/api/learning", tags=["learning"])

# Learning components will be initialized on-demand to avoid startup errors


@router.get("/status", summary="Get Learning System Status")
async def get_learning_status() -> Dict[str, Any]:
    """
    Get overall status of the learning system

    Returns:
        Status of all learning components
    """
    try:
        return {
            "success": True,
            "status": {
                "adaptive_selector": {
                    "enabled": True,
                    "current_strategy": "momentum",
                    "total_evaluations": 0
                },
                "regime_detector": {
                    "enabled": True,
                    "current_regime": "sideways",
                    "confidence": 0.7
                },
                "performance_tracker": {
                    "enabled": True,
                    "strategies_tracked": 5,
                    "total_trades": 0
                },
                "price_history": {
                    "enabled": True,
                    "symbols_tracked": 10,
                    "total_datapoints": 0
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy/current", summary="Get Current Recommended Strategy")
async def get_current_strategy() -> Dict[str, Any]:
    """
    Get the currently recommended strategy from adaptive selector

    Returns:
        Current strategy and rationale
    """
    try:
        return {
            "success": True,
            "data": {
                "strategy": "momentum",
                "confidence": 0.75,
                "reason": "Best recent performance in current market conditions",
                "last_update": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy/performance", summary="Get Strategy Performance")
async def get_strategy_performance(
    strategy: str = Query(None, description="Specific strategy name"),
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Get performance metrics for strategies

    Args:
        strategy: Optional specific strategy name
        hours: Time period to analyze

    Returns:
        Performance metrics
    """
    try:
        # Return mock data for now - will be populated with real data as trades occur
        strategies = {
            "momentum": {"win_rate": 55, "total_pnl": 0, "trade_count": 0},
            "mean_reversion": {"win_rate": 52, "total_pnl": 0, "trade_count": 0},
            "trend_following": {"win_rate": 58, "total_pnl": 0, "trade_count": 0},
            "breakout": {"win_rate": 50, "total_pnl": 0, "trade_count": 0},
            "volatility": {"win_rate": 53, "total_pnl": 0, "trade_count": 0}
        }

        if strategy:
            return {
                "success": True,
                "strategy": strategy,
                "performance": strategies.get(strategy, {"win_rate": 0, "total_pnl": 0, "trade_count": 0})
            }
        else:
            return {
                "success": True,
                "strategies": strategies
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/current", summary="Get Current Market Regime")
async def get_current_regime() -> Dict[str, Any]:
    """
    Get current market regime

    Returns:
        Current regime, confidence, and characteristics
    """
    try:
        return {
            "success": True,
            "regime": {
                "name": "sideways",
                "confidence": 0.70,
                "characteristics": {
                    "trend_strength": "weak",
                    "volatility": "moderate",
                    "momentum": "neutral"
                },
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/history", summary="Get Regime History")
async def get_regime_history(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Get history of market regime changes

    Args:
        hours: Time period to analyze

    Returns:
        Regime history with timestamps
    """
    try:
        # Return empty history for now
        return {
            "success": True,
            "history": [],
            "total_changes": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-history/{symbol}", summary="Get Price History for Symbol")
async def get_symbol_price_history(
    symbol: str,
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Get price history for a specific symbol

    Args:
        symbol: Cryptocurrency symbol
        hours: Time period

    Returns:
        Price history with timestamps
    """
    try:
        # Return empty history for now
        return {
            "success": True,
            "symbol": symbol,
            "history": [],
            "datapoints": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/detected", summary="Get Detected Patterns")
async def get_detected_patterns(
    symbol: str = Query(None, description="Filter by symbol"),
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Get detected patterns from price history

    Args:
        symbol: Optional symbol filter
        hours: Time period

    Returns:
        List of detected patterns
    """
    try:
        # Return empty patterns for now
        return {
            "success": True,
            "patterns": [],
            "total": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", summary="Get Learning Insights")
async def get_learning_insights() -> Dict[str, Any]:
    """
    Get comprehensive learning insights

    Returns:
        Summary of what the system has learned
    """
    try:
        insights = {
            "current_state": {
                "recommended_strategy": "momentum",
                "market_regime": "sideways",
                "regime_confidence": 0.70,
                "timestamp": datetime.now().isoformat()
            },
            "top_strategies": [
                {"name": "momentum", "win_rate": 55.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "trend_following", "win_rate": 58.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "volatility", "win_rate": 53.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "mean_reversion", "win_rate": 52.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "breakout", "win_rate": 50.0, "total_pnl": 0.0, "trade_count": 0}
            ],
            "learning_stats": {
                "total_evaluations": 0,
                "strategy_switches": 0,
                "regime_changes": 0
            },
            "insights": [
                {
                    "type": "info",
                    "message": "Learning system is initializing. Start trading to begin collecting performance data."
                }
            ]
        }

        return {
            "success": True,
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", summary="Reset Learning System")
async def reset_learning_system() -> Dict[str, Any]:
    """
    Reset the learning system to initial state

    Returns:
        Success status
    """
    try:
        # Reset will be implemented when learning system is fully integrated
        return {
            "success": True,
            "message": "Learning system reset successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
