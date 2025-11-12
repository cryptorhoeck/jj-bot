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

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.learning.adaptive_strategy_selector import AdaptiveStrategySelector
from modules.learning.market_regime_detector import MarketRegimeDetector
from modules.learning.strategy_performance_tracker import StrategyPerformanceTracker
from modules.learning.price_history import PriceHistory

router = APIRouter(prefix="/api/learning", tags=["learning"])

# Initialize learning components
selector = AdaptiveStrategySelector()
regime_detector = MarketRegimeDetector()
performance_tracker = StrategyPerformanceTracker()
price_history = PriceHistory()


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
                    "current_strategy": selector.get_current_strategy(),
                    "total_evaluations": selector.get_stats().get("total_evaluations", 0)
                },
                "regime_detector": {
                    "enabled": True,
                    "current_regime": regime_detector.get_current_regime(),
                    "confidence": regime_detector.get_confidence()
                },
                "performance_tracker": {
                    "enabled": True,
                    "strategies_tracked": len(performance_tracker.get_all_strategies()),
                    "total_trades": performance_tracker.get_total_trades()
                },
                "price_history": {
                    "enabled": True,
                    "symbols_tracked": len(price_history.get_symbols()),
                    "total_datapoints": price_history.get_total_datapoints()
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
        strategy = selector.get_current_strategy()
        stats = selector.get_stats()

        return {
            "success": True,
            "data": {
                "strategy": strategy,
                "confidence": stats.get("confidence", 0),
                "reason": stats.get("reason", "Default strategy"),
                "last_update": stats.get("last_update", datetime.now().isoformat())
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
        if strategy:
            # Get specific strategy performance
            perf = performance_tracker.get_strategy_performance(strategy, hours=hours)
            return {
                "success": True,
                "strategy": strategy,
                "performance": perf
            }
        else:
            # Get all strategies performance
            all_perf = performance_tracker.get_all_performance(hours=hours)
            return {
                "success": True,
                "strategies": all_perf
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
        regime = regime_detector.get_current_regime()
        confidence = regime_detector.get_confidence()
        characteristics = regime_detector.get_regime_characteristics()

        return {
            "success": True,
            "regime": {
                "name": regime,
                "confidence": confidence,
                "characteristics": characteristics,
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
        history = regime_detector.get_regime_history(hours=hours)

        return {
            "success": True,
            "history": history,
            "total_changes": len(history)
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
        history = price_history.get_price_history(symbol, hours=hours)

        if not history:
            raise HTTPException(status_code=404, detail=f"No price history for {symbol}")

        return {
            "success": True,
            "symbol": symbol,
            "history": history,
            "datapoints": len(history)
        }
    except HTTPException:
        raise
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
        if symbol:
            patterns = price_history.detect_patterns(symbol, hours=hours)
        else:
            patterns = price_history.detect_all_patterns(hours=hours)

        return {
            "success": True,
            "patterns": patterns,
            "total": len(patterns)
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
        # Get current strategy and performance
        current_strategy = selector.get_current_strategy()
        strategy_stats = selector.get_stats()

        # Get regime
        regime = regime_detector.get_current_regime()
        regime_confidence = regime_detector.get_confidence()

        # Get top performing strategies
        all_perf = performance_tracker.get_all_performance(hours=24)
        sorted_strategies = sorted(
            all_perf.items(),
            key=lambda x: x[1].get("win_rate", 0) * x[1].get("trade_count", 0),
            reverse=True
        )[:5]

        insights = {
            "current_state": {
                "recommended_strategy": current_strategy,
                "market_regime": regime,
                "regime_confidence": regime_confidence,
                "timestamp": datetime.now().isoformat()
            },
            "top_strategies": [
                {
                    "name": name,
                    "win_rate": perf.get("win_rate", 0),
                    "total_pnl": perf.get("total_pnl", 0),
                    "trade_count": perf.get("trade_count", 0)
                }
                for name, perf in sorted_strategies
            ],
            "learning_stats": {
                "total_evaluations": strategy_stats.get("total_evaluations", 0),
                "strategy_switches": strategy_stats.get("strategy_switches", 0),
                "regime_changes": len(regime_detector.get_regime_history(hours=24))
            },
            "insights": []
        }

        # Generate insights
        if regime == "bull" and current_strategy != "trend_following":
            insights["insights"].append({
                "type": "suggestion",
                "message": "Bull market detected. Trend following strategies may perform well."
            })
        elif regime == "bear" and current_strategy != "mean_reversion":
            insights["insights"].append({
                "type": "warning",
                "message": "Bear market detected. Consider defensive strategies."
            })

        if regime_confidence < 0.5:
            insights["insights"].append({
                "type": "info",
                "message": "Market regime uncertain. System will adapt as conditions become clearer."
            })

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
        selector.reset()
        regime_detector.reset()
        performance_tracker.reset()
        price_history.reset()

        return {
            "success": True,
            "message": "Learning system reset successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
