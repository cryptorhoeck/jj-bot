"""
Enhanced Analytics API Endpoints

Provides data for advanced visualizations:
- Equity curve (capital over time)
- P&L distribution and statistics
- Strategy performance comparison
- Position tracking and heat maps
- Market regime analysis
- Win/loss streaks
- Time-based performance analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import sqlite3
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

router = APIRouter(prefix="/api/analytics/enhanced", tags=["enhanced_analytics"])


def get_db_path() -> str:
    """Get database path"""
    return os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'trades.db'
    )


@router.get("/equity-curve", summary="Get Equity Curve Data")
async def get_equity_curve(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours (1-168)")
) -> Dict[str, Any]:
    """
    Get equity curve data showing capital growth over time.

    Returns cumulative P&L and capital at each trade.
    Perfect for plotting equity curve charts.
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Get trades from last N hours
        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT timestamp, pnl, symbol, strategy, signal
            FROM trades
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (time_threshold,))

        trades = cursor.fetchall()
        conn.close()

        if not trades:
            return {
                "success": True,
                "data": {
                    "timestamps": [],
                    "cumulative_pnl": [],
                    "capital": [],
                    "trade_count": 0
                }
            }

        # Calculate cumulative P&L and capital
        initial_capital = 10000.0  # TODO: Get from simulator config
        cumulative_pnl = 0
        timestamps = []
        cumulative_pnls = []
        capitals = []

        for trade in trades:
            timestamp, pnl, symbol, strategy, signal = trade
            cumulative_pnl += pnl or 0

            timestamps.append(timestamp)
            cumulative_pnls.append(round(cumulative_pnl, 2))
            capitals.append(round(initial_capital + cumulative_pnl, 2))

        return {
            "success": True,
            "data": {
                "timestamps": timestamps,
                "cumulative_pnl": cumulative_pnls,
                "capital": capitals,
                "trade_count": len(trades),
                "initial_capital": initial_capital,
                "final_capital": capitals[-1] if capitals else initial_capital,
                "total_return": round((capitals[-1] - initial_capital) / initial_capital * 100, 2) if capitals else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl-distribution", summary="Get P&L Distribution")
async def get_pnl_distribution(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Get P&L distribution data for histograms.

    Returns:
    - Histogram bins for P&L
    - Win/loss statistics
    - Percentile data
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT pnl
            FROM trades
            WHERE timestamp >= ? AND pnl IS NOT NULL
            ORDER BY pnl ASC
        """, (time_threshold,))

        pnls = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not pnls:
            return {
                "success": True,
                "data": {
                    "bins": [],
                    "counts": [],
                    "statistics": {}
                }
            }

        # Calculate statistics
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0

        # Create histogram bins
        import numpy as np
        counts, bin_edges = np.histogram(pnls, bins=20)

        return {
            "success": True,
            "data": {
                "bins": [round(float(x), 2) for x in bin_edges.tolist()],
                "counts": [int(x) for x in counts.tolist()],
                "statistics": {
                    "total_trades": len(pnls),
                    "winning_trades": len(winning_trades),
                    "losing_trades": len(losing_trades),
                    "win_rate": round(len(winning_trades) / len(pnls) * 100, 2) if pnls else 0,
                    "avg_win": round(avg_win, 2),
                    "avg_loss": round(avg_loss, 2),
                    "profit_factor": round(abs(sum(winning_trades) / sum(losing_trades)), 2) if losing_trades and sum(losing_trades) != 0 else 0,
                    "best_trade": round(max(pnls), 2),
                    "worst_trade": round(min(pnls), 2),
                    "median_pnl": round(float(np.median(pnls)), 2),
                    "percentile_25": round(float(np.percentile(pnls, 25)), 2),
                    "percentile_75": round(float(np.percentile(pnls, 75)), 2)
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy-performance", summary="Compare Strategy Performance")
async def get_strategy_performance(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Compare performance across different strategies.

    Returns metrics for each strategy:
    - Total trades
    - Win rate
    - Total P&L
    - Average P&L per trade
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT strategy, COUNT(*) as trade_count,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl) as total_pnl,
                   AVG(pnl) as avg_pnl,
                   MAX(pnl) as best_trade,
                   MIN(pnl) as worst_trade
            FROM trades
            WHERE timestamp >= ? AND strategy IS NOT NULL
            GROUP BY strategy
            ORDER BY total_pnl DESC
        """, (time_threshold,))

        strategies = cursor.fetchall()
        conn.close()

        strategy_data = []
        for row in strategies:
            strategy, trade_count, wins, total_pnl, avg_pnl, best, worst = row

            strategy_data.append({
                "strategy": strategy or "unknown",
                "trade_count": trade_count,
                "wins": wins,
                "losses": trade_count - wins,
                "win_rate": round(wins / trade_count * 100, 2) if trade_count > 0 else 0,
                "total_pnl": round(total_pnl or 0, 2),
                "avg_pnl": round(avg_pnl or 0, 2),
                "best_trade": round(best or 0, 2),
                "worst_trade": round(worst or 0, 2)
            })

        return {
            "success": True,
            "data": {
                "strategies": strategy_data,
                "total_strategies": len(strategy_data)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol-performance", summary="Performance by Symbol")
async def get_symbol_performance(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Analyze performance across different trading symbols.

    Returns heat map data showing which symbols perform best.
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT symbol, COUNT(*) as trade_count,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl) as total_pnl,
                   AVG(pnl) as avg_pnl
            FROM trades
            WHERE timestamp >= ? AND symbol IS NOT NULL
            GROUP BY symbol
            ORDER BY total_pnl DESC
        """, (time_threshold,))

        symbols = cursor.fetchall()
        conn.close()

        symbol_data = []
        for row in symbols:
            symbol, trade_count, wins, total_pnl, avg_pnl = row

            symbol_data.append({
                "symbol": symbol,
                "trade_count": trade_count,
                "win_rate": round(wins / trade_count * 100, 2) if trade_count > 0 else 0,
                "total_pnl": round(total_pnl or 0, 2),
                "avg_pnl": round(avg_pnl or 0, 2)
            })

        return {
            "success": True,
            "data": {
                "symbols": symbol_data,
                "total_symbols": len(symbol_data)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/time-analysis", summary="Time-Based Performance Analysis")
async def get_time_analysis(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Analyze performance over time periods (hourly/daily).

    Shows patterns in trading performance across time.
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT timestamp, pnl, signal, strategy
            FROM trades
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (time_threshold,))

        trades = cursor.fetchall()
        conn.close()

        if not trades:
            return {
                "success": True,
                "data": {
                    "hourly": [],
                    "total_trades": 0
                }
            }

        # Group by hour
        hourly_data = {}
        for trade in trades:
            timestamp_str, pnl, signal, strategy = trade
            timestamp = datetime.fromisoformat(timestamp_str)
            hour_key = timestamp.strftime("%Y-%m-%d %H:00")

            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "timestamp": hour_key,
                    "trades": 0,
                    "pnl": 0,
                    "wins": 0
                }

            hourly_data[hour_key]["trades"] += 1
            hourly_data[hour_key]["pnl"] += pnl or 0
            if pnl and pnl > 0:
                hourly_data[hour_key]["wins"] += 1

        # Convert to list and calculate win rates
        hourly_list = []
        for data in sorted(hourly_data.values(), key=lambda x: x["timestamp"]):
            data["pnl"] = round(data["pnl"], 2)
            data["win_rate"] = round(data["wins"] / data["trades"] * 100, 2) if data["trades"] > 0 else 0
            hourly_list.append(data)

        return {
            "success": True,
            "data": {
                "hourly": hourly_list,
                "total_trades": len(trades)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streaks", summary="Win/Loss Streak Analysis")
async def get_streaks(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Analyze winning and losing streaks.

    Returns current and longest streaks.
    """
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT timestamp, pnl
            FROM trades
            WHERE timestamp >= ? AND pnl IS NOT NULL
            ORDER BY timestamp ASC
        """, (time_threshold,))

        trades = cursor.fetchall()
        conn.close()

        if not trades:
            return {
                "success": True,
                "data": {
                    "current_streak": 0,
                    "longest_win_streak": 0,
                    "longest_loss_streak": 0
                }
            }

        # Calculate streaks
        current_streak = 0
        longest_win_streak = 0
        longest_loss_streak = 0
        temp_win_streak = 0
        temp_loss_streak = 0

        for timestamp, pnl in trades:
            if pnl > 0:
                temp_win_streak += 1
                temp_loss_streak = 0
                longest_win_streak = max(longest_win_streak, temp_win_streak)
            elif pnl < 0:
                temp_loss_streak += 1
                temp_win_streak = 0
                longest_loss_streak = max(longest_loss_streak, temp_loss_streak)

        # Current streak (from last trade)
        if trades:
            last_pnl = trades[-1][1]
            current_streak = temp_win_streak if last_pnl > 0 else -temp_loss_streak

        return {
            "success": True,
            "data": {
                "current_streak": current_streak,
                "current_streak_type": "winning" if current_streak > 0 else "losing" if current_streak < 0 else "neutral",
                "longest_win_streak": longest_win_streak,
                "longest_loss_streak": longest_loss_streak,
                "total_trades_analyzed": len(trades)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard-summary", summary="Complete Dashboard Summary")
async def get_dashboard_summary(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard summary combining all metrics.

    One-stop endpoint for dashboard visualization.
    """
    try:
        # Get all analytics
        equity_curve = await get_equity_curve(hours)
        pnl_dist = await get_pnl_distribution(hours)
        strategy_perf = await get_strategy_performance(hours)
        symbol_perf = await get_symbol_performance(hours)
        streaks = await get_streaks(hours)

        return {
            "success": True,
            "period_hours": hours,
            "generated_at": datetime.now().isoformat(),
            "data": {
                "equity_curve": equity_curve["data"],
                "pnl_distribution": pnl_dist["data"],
                "strategy_performance": strategy_perf["data"],
                "symbol_performance": symbol_perf["data"],
                "streaks": streaks["data"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
