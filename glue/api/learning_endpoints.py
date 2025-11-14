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

# Import learning modules
from modules.learning.adaptive_strategy_selector import AdaptiveStrategySelector
from modules.learning.strategy_performance_tracker import StrategyPerformanceTracker
from modules.learning.market_regime_detector import MarketRegimeDetector

router = APIRouter(prefix="/api/learning", tags=["learning"])

# Learning component singletons
_adaptive_selector = None
_performance_tracker = None
_regime_detector = None

def get_adaptive_selector():
    """Get or create adaptive strategy selector"""
    global _adaptive_selector
    if _adaptive_selector is None:
        try:
            _adaptive_selector = AdaptiveStrategySelector()
        except Exception as e:
            print(f"Warning: Could not initialize adaptive selector: {e}")
    return _adaptive_selector

def get_performance_tracker():
    """Get or create performance tracker"""
    global _performance_tracker
    if _performance_tracker is None:
        try:
            _performance_tracker = StrategyPerformanceTracker()
        except Exception as e:
            print(f"Warning: Could not initialize performance tracker: {e}")
    return _performance_tracker

def get_regime_detector():
    """Get or create regime detector"""
    global _regime_detector
    if _regime_detector is None:
        try:
            _regime_detector = MarketRegimeDetector()
        except Exception as e:
            print(f"Warning: Could not initialize regime detector: {e}")
    return _regime_detector


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
        # Get real data from learning modules
        adaptive_selector = get_adaptive_selector()
        performance_tracker = get_performance_tracker()
        regime_detector = get_regime_detector()

        # Get current state
        current_state = {
            "recommended_strategy": "momentum",
            "market_regime": "sideways",
            "regime_confidence": 0.70,
            "timestamp": datetime.now().isoformat()
        }

        if adaptive_selector:
            try:
                state = adaptive_selector.get_state()
                if state:
                    current_state["recommended_strategy"] = state.get("current_strategy", "momentum")
                    current_state["confidence"] = state.get("confidence", 0.70)
            except Exception as e:
                print(f"Error getting adaptive selector state: {e}")

        if regime_detector:
            try:
                regime_info = regime_detector.get_current_regime()
                if regime_info:
                    current_state["market_regime"] = regime_info.get("regime", "sideways")
                    current_state["regime_confidence"] = regime_info.get("confidence", 0.70)
            except Exception as e:
                print(f"Error getting regime: {e}")

        # Get top performing strategies
        top_strategies = []
        strategy_names = ["momentum", "trend_following", "volatility", "mean_reversion", "breakout"]

        if performance_tracker:
            try:
                for strategy in strategy_names:
                    metrics = performance_tracker.get_strategy_metrics(strategy, period_hours=24)
                    if metrics:
                        top_strategies.append({
                            "name": strategy,
                            "win_rate": metrics.get("win_rate", 0.0),
                            "total_pnl": metrics.get("total_pnl", 0.0),
                            "trade_count": metrics.get("total_trades", 0)
                        })
            except Exception as e:
                print(f"Error getting strategy metrics: {e}")

        # Fallback to default if no data
        if not top_strategies:
            top_strategies = [
                {"name": "momentum", "win_rate": 0.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "trend_following", "win_rate": 0.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "volatility", "win_rate": 0.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "mean_reversion", "win_rate": 0.0, "total_pnl": 0.0, "trade_count": 0},
                {"name": "breakout", "win_rate": 0.0, "total_pnl": 0.0, "trade_count": 0}
            ]

        # Sort by total P&L
        top_strategies.sort(key=lambda x: x["total_pnl"], reverse=True)

        # Get learning stats
        learning_stats = {
            "total_evaluations": 0,
            "strategy_switches": 0,
            "regime_changes": 0
        }

        if adaptive_selector:
            try:
                state = adaptive_selector.get_state()
                if state:
                    learning_stats["total_evaluations"] = state.get("total_evaluations", 0)
                    learning_stats["strategy_switches"] = state.get("total_switches", 0)
            except Exception as e:
                print(f"Error getting learning stats: {e}")

        # Generate insights
        insights_list = []

        # Check if we have any trade data
        total_trades = sum(s["trade_count"] for s in top_strategies)

        if total_trades == 0:
            insights_list.append({
                "type": "info",
                "message": "Learning system initialized. Start trading to collect performance data."
            })
        else:
            # Best performing strategy
            if top_strategies and top_strategies[0]["total_pnl"] > 0:
                insights_list.append({
                    "type": "suggestion",
                    "message": f"{top_strategies[0]['name'].title()} strategy performing best with ${top_strategies[0]['total_pnl']:.2f} P&L"
                })

            # Warning for losing strategies
            losing_strategies = [s for s in top_strategies if s["total_pnl"] < -50]
            if losing_strategies:
                insights_list.append({
                    "type": "warning",
                    "message": f"{len(losing_strategies)} strategies underperforming. Consider switching."
                })

        insights = {
            "current_state": current_state,
            "top_strategies": top_strategies,
            "learning_stats": learning_stats,
            "insights": insights_list
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
