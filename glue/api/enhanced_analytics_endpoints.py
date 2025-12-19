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
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import centralized data manager
try:
    from modules.database import data_manager
    DATA_MANAGER_AVAILABLE = True
except ImportError:
    DATA_MANAGER_AVAILABLE = False
    data_manager = None

router = APIRouter(prefix="/api/analytics/enhanced", tags=["enhanced_analytics"])


def get_initial_capital() -> float:
    """Get initial capital from bot config"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'bot_config.json')
        with open(config_path) as f:
            config = json.load(f)
            return config.get('initial_capital', 10000.0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return 10000.0


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
        initial_capital = get_initial_capital()
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


@router.get("/comprehensive", summary="Comprehensive Analytics Data")
async def get_comprehensive_analytics(
    period: str = Query("all", description="Period: 'all', '24h', '7d', '30d', '90d'")
) -> Dict[str, Any]:
    """
    Get comprehensive analytics data for the Analytics tab.

    Includes all-time metrics, time analysis, risk metrics, and AI performance.
    """
    try:
        import numpy as np

        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Build time filter
        # Only count CLOSE records for meaningful P&L stats (OPEN records have pnl=0)
        time_filter = "WHERE signal LIKE 'CLOSE%'"
        if period != "all":
            period_hours = {"24h": 24, "7d": 168, "30d": 720, "90d": 2160}.get(period, 0)
            if period_hours:
                time_threshold = (datetime.now() - timedelta(hours=period_hours)).isoformat()
                time_filter = f"WHERE signal LIKE 'CLOSE%' AND timestamp >= '{time_threshold}'"

        # === OVERVIEW METRICS ===
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(CASE WHEN pnl = 0 THEN 1 ELSE 0 END) as breakeven_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade,
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as gross_loss,
                AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
                MIN(timestamp) as first_trade,
                MAX(timestamp) as last_trade
            FROM trades {time_filter}
        """)

        row = cursor.fetchone()
        total_trades = row[0] or 0
        winning_trades = row[1] or 0
        losing_trades = row[2] or 0
        breakeven_trades = row[3] or 0
        total_pnl = row[4] or 0
        avg_pnl = row[5] or 0
        best_trade = row[6] or 0
        worst_trade = row[7] or 0
        gross_profit = row[8] or 0
        gross_loss = row[9] or 0
        avg_win = row[10] or 0
        avg_loss = row[11] or 0
        first_trade = row[12]
        last_trade = row[13]

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        expectancy = (win_rate/100 * avg_win + (1 - win_rate/100) * avg_loss) if total_trades > 0 else 0

        overview = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "breakeven_trades": breakeven_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2) if avg_win else 0,
            "avg_loss": round(avg_loss, 2) if avg_loss else 0,
            "expectancy": round(expectancy, 2),
            "first_trade": first_trade,
            "last_trade": last_trade
        }

        # === EQUITY CURVE ===
        cursor.execute(f"""
            SELECT timestamp, pnl, symbol, signal
            FROM trades {time_filter}
            ORDER BY timestamp ASC
        """)
        trades = cursor.fetchall()

        initial_capital = get_initial_capital()
        cumulative_pnl = 0
        equity_data = []
        peak_equity = initial_capital
        max_drawdown = 0
        max_drawdown_pct = 0

        for trade in trades:
            timestamp, pnl, symbol, signal = trade
            cumulative_pnl += pnl or 0
            current_equity = initial_capital + cumulative_pnl

            # Track peak and drawdown
            if current_equity > peak_equity:
                peak_equity = current_equity
            drawdown = peak_equity - current_equity
            drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct

            equity_data.append({
                "timestamp": timestamp,
                "pnl": round(pnl or 0, 2),
                "cumulative_pnl": round(cumulative_pnl, 2),
                "equity": round(current_equity, 2),
                "symbol": symbol,
                "signal": signal
            })

        # === RISK METRICS ===
        pnl_values = [t[1] for t in trades if t[1] is not None]

        sharpe_ratio = 0
        sortino_ratio = 0
        calmar_ratio = 0
        volatility = 0

        if len(pnl_values) > 1:
            returns = np.array(pnl_values)
            mean_return = np.mean(returns)
            std_return = np.std(returns)

            # Volatility
            volatility = std_return

            # Sharpe Ratio (annualized, assuming 252 trading days)
            if std_return > 0:
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)

            # Sortino Ratio (downside deviation)
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_std = np.std(negative_returns)
                if downside_std > 0:
                    sortino_ratio = (mean_return / downside_std) * np.sqrt(252)

            # Calmar Ratio
            if max_drawdown > 0:
                total_return_pct = (total_pnl / initial_capital) * 100
                calmar_ratio = total_return_pct / max_drawdown_pct if max_drawdown_pct > 0 else 0

        risk_metrics = {
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "calmar_ratio": round(calmar_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "volatility": round(volatility, 2),
            "current_drawdown": round(peak_equity - (initial_capital + cumulative_pnl), 2) if trades else 0
        }

        # === TIME OF DAY ANALYSIS ===
        cursor.execute(f"""
            SELECT
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl
            FROM trades {time_filter}
            GROUP BY hour
            ORDER BY hour
        """)

        hourly_data = []
        for row in cursor.fetchall():
            hour, trade_count, wins, pnl = row
            hourly_data.append({
                "hour": hour,
                "label": f"{hour:02d}:00",
                "trades": trade_count,
                "wins": wins,
                "win_rate": round(wins / trade_count * 100, 1) if trade_count > 0 else 0,
                "total_pnl": round(pnl or 0, 2),
                "avg_pnl": round((pnl or 0) / trade_count, 2) if trade_count > 0 else 0
            })

        # === DAY OF WEEK ANALYSIS ===
        cursor.execute(f"""
            SELECT
                CAST(strftime('%w', timestamp) AS INTEGER) as dow,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl
            FROM trades {time_filter}
            GROUP BY dow
            ORDER BY dow
        """)

        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        daily_data = []
        for row in cursor.fetchall():
            dow, trade_count, wins, pnl = row
            daily_data.append({
                "day": dow,
                "label": day_names[dow],
                "short_label": day_names[dow][:3],
                "trades": trade_count,
                "wins": wins,
                "win_rate": round(wins / trade_count * 100, 1) if trade_count > 0 else 0,
                "total_pnl": round(pnl or 0, 2)
            })

        # === P&L DISTRIBUTION ===
        pnl_distribution = {"bins": [], "counts": [], "statistics": {}}
        if pnl_values:
            counts, bin_edges = np.histogram(pnl_values, bins=20)
            pnl_distribution = {
                "bins": [round(float(x), 2) for x in bin_edges.tolist()],
                "counts": [int(x) for x in counts.tolist()],
                "statistics": {
                    "min": round(min(pnl_values), 2),
                    "max": round(max(pnl_values), 2),
                    "median": round(float(np.median(pnl_values)), 2),
                    "std": round(float(np.std(pnl_values)), 2),
                    "percentile_25": round(float(np.percentile(pnl_values, 25)), 2),
                    "percentile_75": round(float(np.percentile(pnl_values, 75)), 2),
                    "percentile_95": round(float(np.percentile(pnl_values, 95)), 2),
                    "percentile_5": round(float(np.percentile(pnl_values, 5)), 2)
                }
            }

        # === SYMBOL PERFORMANCE ===
        cursor.execute(f"""
            SELECT
                symbol,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best,
                MIN(pnl) as worst
            FROM trades {time_filter}
            GROUP BY symbol
            ORDER BY total_pnl DESC
        """)

        symbol_data = []
        for row in cursor.fetchall():
            symbol, trades_count, wins, pnl, avg, best, worst = row
            symbol_data.append({
                "symbol": symbol,
                "trades": trades_count,
                "wins": wins,
                "losses": trades_count - wins,
                "win_rate": round(wins / trades_count * 100, 1) if trades_count > 0 else 0,
                "total_pnl": round(pnl or 0, 2),
                "avg_pnl": round(avg or 0, 2),
                "best_trade": round(best or 0, 2),
                "worst_trade": round(worst or 0, 2)
            })

        # === STRATEGY PERFORMANCE ===
        cursor.execute(f"""
            SELECT
                COALESCE(strategy, 'unknown') as strategy,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as gross_loss
            FROM trades {time_filter}
            GROUP BY strategy
            ORDER BY total_pnl DESC
        """)

        strategy_data = []
        for row in cursor.fetchall():
            strategy, trades_count, wins, pnl, avg, gp, gl = row
            pf = (gp / gl) if gl and gl > 0 else 0
            strategy_data.append({
                "strategy": strategy,
                "trades": trades_count,
                "wins": wins,
                "losses": trades_count - wins,
                "win_rate": round(wins / trades_count * 100, 1) if trades_count > 0 else 0,
                "total_pnl": round(pnl or 0, 2),
                "avg_pnl": round(avg or 0, 2),
                "profit_factor": round(pf, 2)
            })

        # === STREAKS ===
        current_streak = 0
        longest_win_streak = 0
        longest_loss_streak = 0
        temp_win = 0
        temp_loss = 0

        for trade in trades:
            pnl = trade[1]
            if pnl and pnl > 0:
                temp_win += 1
                temp_loss = 0
                longest_win_streak = max(longest_win_streak, temp_win)
            elif pnl and pnl < 0:
                temp_loss += 1
                temp_win = 0
                longest_loss_streak = max(longest_loss_streak, temp_loss)

        current_streak = temp_win if temp_win > 0 else -temp_loss

        streaks = {
            "current_streak": current_streak,
            "current_streak_type": "winning" if current_streak > 0 else "losing" if current_streak < 0 else "neutral",
            "longest_win_streak": longest_win_streak,
            "longest_loss_streak": longest_loss_streak
        }

        # === MONTHLY PERFORMANCE ===
        cursor.execute(f"""
            SELECT
                strftime('%Y-%m', timestamp) as month,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl
            FROM trades {time_filter}
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)

        monthly_data = []
        for row in cursor.fetchall():
            month, trades_count, wins, pnl = row
            monthly_data.append({
                "month": month,
                "trades": trades_count,
                "wins": wins,
                "win_rate": round(wins / trades_count * 100, 1) if trades_count > 0 else 0,
                "total_pnl": round(pnl or 0, 2)
            })

        # === BEST/WORST TRADES ===
        cursor.execute(f"""
            SELECT timestamp, symbol, signal, pnl, strategy
            FROM trades {time_filter}
            ORDER BY pnl DESC
            LIMIT 10
        """)
        best_trades = [{"timestamp": r[0], "symbol": r[1], "signal": r[2], "pnl": round(r[3] or 0, 2), "strategy": r[4]} for r in cursor.fetchall()]

        cursor.execute(f"""
            SELECT timestamp, symbol, signal, pnl, strategy
            FROM trades {time_filter}
            ORDER BY pnl ASC
            LIMIT 10
        """)
        worst_trades = [{"timestamp": r[0], "symbol": r[1], "signal": r[2], "pnl": round(r[3] or 0, 2), "strategy": r[4]} for r in cursor.fetchall()]

        # === AI/TRAINING DATA ===
        ai_data = {}
        try:
            # Use data_manager as single source of truth
            if DATA_MANAGER_AVAILABLE:
                bot_state = data_manager.get_bot_state()
                ai_data = {
                    "trading_iq": bot_state.get("trading_iq", 0),
                    "expertise_level": bot_state.get("expertise_level", "Untrained"),
                    "training_sessions": bot_state.get("training_sessions", 0),
                    "total_training_episodes": bot_state.get("total_training_episodes", 0),
                    "total_training_trades": bot_state.get("total_training_trades", 0),
                    "last_training_date": bot_state.get("last_training_date"),
                    "avg_win_rate": bot_state.get("avg_win_rate", 0),
                    "avg_profit_factor": bot_state.get("avg_profit_factor", 0),
                    "best_win_rate": bot_state.get("best_win_rate", 0),
                    "best_profit_factor": bot_state.get("best_profit_factor", 0)
                }
            else:
                # Fallback to JSON file
                state_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'bot_state.json')
                if os.path.exists(state_path):
                    with open(state_path) as f:
                        state = json.load(f)
                        stats = state.get("stats", {})
                        ai_data = {
                            "trading_iq": stats.get("trading_iq", 0),
                            "expertise_level": stats.get("expertise_level", "Untrained"),
                            "training_sessions": stats.get("training_sessions", 0),
                            "total_training_episodes": stats.get("total_training_episodes", 0),
                            "total_training_trades": stats.get("total_training_trades", 0),
                            "last_training_date": stats.get("last_training_date"),
                            "avg_win_rate": stats.get("avg_win_rate", 0),
                            "avg_profit_factor": stats.get("avg_profit_factor", 0),
                            "best_win_rate": stats.get("best_win_rate", 0),
                            "best_profit_factor": stats.get("best_profit_factor", 0)
                        }
        except Exception:
            pass

        conn.close()

        return {
            "success": True,
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "overview": overview,
            "equity_curve": equity_data,
            "risk_metrics": risk_metrics,
            "time_of_day": hourly_data,
            "day_of_week": daily_data,
            "pnl_distribution": pnl_distribution,
            "symbols": symbol_data,
            "strategies": strategy_data,
            "streaks": streaks,
            "monthly": monthly_data,
            "best_trades": best_trades,
            "worst_trades": worst_trades,
            "ai_performance": ai_data
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW ENDPOINTS - Using centralized data_manager (Phase 2)
# ============================================================================

@router.get("/equity-curve-v2", summary="Get Real-Time Equity Curve from Snapshots")
async def get_equity_curve_v2(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours (1-720)"),
    mode: Optional[str] = Query(None, description="Filter by mode: paper, live, backtest")
) -> Dict[str, Any]:
    """
    Get equity curve data from real-time equity snapshots.

    Unlike the original equity-curve endpoint which reconstructs from trades,
    this uses actual equity snapshots recorded periodically during bot operation.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        from datetime import timedelta

        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        snapshots = data_manager.get_equity_curve(since=since, mode=mode, limit=2000)

        if not snapshots:
            return {
                "success": True,
                "data": {
                    "timestamps": [],
                    "equity": [],
                    "daily_pnl": [],
                    "drawdown": [],
                    "drawdown_pct": [],
                    "snapshot_count": 0
                }
            }

        # Extract data for visualization
        timestamps = [s['timestamp'] for s in snapshots]
        equity = [s['equity'] for s in snapshots]
        daily_pnl = [s.get('daily_pnl', 0) or 0 for s in snapshots]
        drawdown = [s.get('drawdown', 0) or 0 for s in snapshots]
        drawdown_pct = [s.get('drawdown_pct', 0) or 0 for s in snapshots]
        peak_equity = [s.get('peak_equity', 0) or 0 for s in snapshots]
        open_positions = [s.get('open_positions', 0) or 0 for s in snapshots]

        # Calculate summary stats
        initial_equity = equity[0] if equity else 10000
        final_equity = equity[-1] if equity else initial_equity
        max_drawdown = max(drawdown) if drawdown else 0
        max_drawdown_pct = max(drawdown_pct) if drawdown_pct else 0

        return {
            "success": True,
            "data": {
                "timestamps": timestamps,
                "equity": equity,
                "daily_pnl": daily_pnl,
                "drawdown": drawdown,
                "drawdown_pct": drawdown_pct,
                "peak_equity": peak_equity,
                "open_positions": open_positions,
                "snapshot_count": len(snapshots),
                "summary": {
                    "initial_equity": round(initial_equity, 2),
                    "final_equity": round(final_equity, 2),
                    "total_return": round((final_equity - initial_equity) / initial_equity * 100, 2) if initial_equity > 0 else 0,
                    "max_drawdown": round(max_drawdown, 2),
                    "max_drawdown_pct": round(max_drawdown_pct, 2),
                    "period_hours": hours,
                    "mode_filter": mode
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-episodes", summary="Get Training Episode History")
async def get_training_episodes(
    session_id: Optional[str] = Query(None, description="Filter by specific session ID"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum episodes to return")
) -> Dict[str, Any]:
    """
    Get training episode metrics for visualization.

    Returns detailed per-episode metrics including rewards, P&L, win rate, etc.
    Perfect for plotting training progression charts.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        episodes = data_manager.get_training_episodes(session_id=session_id, limit=limit)

        if not episodes:
            return {
                "success": True,
                "data": {
                    "episodes": [],
                    "episode_count": 0,
                    "session_id": session_id
                }
            }

        # Format for visualization
        formatted_episodes = []
        for ep in episodes:
            formatted_episodes.append({
                "episode": ep['episode'],
                "session_id": ep['session_id'],
                "timestamp": ep['timestamp'],
                "total_reward": round(ep.get('total_reward', 0) or 0, 4),
                "avg_reward": round(ep.get('avg_reward', 0) or 0, 4),
                "total_pnl": round(ep.get('total_pnl', 0) or 0, 2),
                "trades": ep.get('trades', 0) or 0,
                "wins": ep.get('wins', 0) or 0,
                "losses": ep.get('losses', 0) or 0,
                "win_rate": round(ep.get('win_rate', 0) or 0, 2),
                "profit_factor": round(ep.get('profit_factor', 0) or 0, 2),
                "max_drawdown": round(ep.get('max_drawdown', 0) or 0, 2),
                "sharpe_ratio": round(ep.get('sharpe_ratio', 0) or 0, 2) if ep.get('sharpe_ratio') else None,
                "policy_loss": round(ep.get('policy_loss', 0) or 0, 6) if ep.get('policy_loss') else None,
                "value_loss": round(ep.get('value_loss', 0) or 0, 6) if ep.get('value_loss') else None,
                "entropy": round(ep.get('entropy', 0) or 0, 4) if ep.get('entropy') else None,
                "steps": ep.get('steps', 0) or 0
            })

        # Calculate progression summary
        if formatted_episodes:
            first_ep = formatted_episodes[0]
            last_ep = formatted_episodes[-1]

            progression = {
                "reward_improvement": round(last_ep['total_reward'] - first_ep['total_reward'], 4),
                "win_rate_improvement": round(last_ep['win_rate'] - first_ep['win_rate'], 2),
                "profit_factor_improvement": round(last_ep['profit_factor'] - first_ep['profit_factor'], 2),
                "final_win_rate": last_ep['win_rate'],
                "final_profit_factor": last_ep['profit_factor'],
                "total_training_trades": sum(ep['trades'] for ep in formatted_episodes)
            }
        else:
            progression = {}

        return {
            "success": True,
            "data": {
                "episodes": formatted_episodes,
                "episode_count": len(formatted_episodes),
                "session_id": session_id,
                "progression": progression
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-sessions", summary="Get Training Session Summaries")
async def get_training_sessions_endpoint() -> Dict[str, Any]:
    """
    Get summary of all training sessions.

    Returns aggregated metrics per session for comparing training runs.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        sessions = data_manager.get_training_sessions()

        formatted_sessions = []
        for sess in sessions:
            formatted_sessions.append({
                "session_id": sess['session_id'],
                "started_at": sess['started_at'],
                "ended_at": sess['ended_at'],
                "episodes": sess['episodes'],
                "max_episode": sess['max_episode'],
                "avg_win_rate": round(sess.get('avg_win_rate', 0) or 0, 2),
                "avg_profit_factor": round(sess.get('avg_profit_factor', 0) or 0, 2),
                "total_pnl": round(sess.get('total_pnl', 0) or 0, 2),
                "avg_reward": round(sess.get('avg_reward', 0) or 0, 4)
            })

        return {
            "success": True,
            "data": {
                "sessions": formatted_sessions,
                "session_count": len(formatted_sessions)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-latest", summary="Get Latest Training Session Metrics")
async def get_latest_training() -> Dict[str, Any]:
    """
    Get the most recent training session's final metrics.

    Quick endpoint to show current training state without loading full history.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        latest = data_manager.get_latest_training_metrics()
        bot_state = data_manager.get_bot_state()

        return {
            "success": True,
            "data": {
                "latest_episode": latest if latest else None,
                "bot_state": {
                    "trading_iq": bot_state.get('trading_iq', 0),
                    "expertise_level": bot_state.get('expertise_level', 'Untrained'),
                    "training_sessions": bot_state.get('training_sessions', 0),
                    "total_training_episodes": bot_state.get('total_training_episodes', 0),
                    "total_training_trades": bot_state.get('total_training_trades', 0),
                    "last_training_date": bot_state.get('last_training_date'),
                    "avg_win_rate": bot_state.get('avg_win_rate', 0),
                    "avg_profit_factor": bot_state.get('avg_profit_factor', 0)
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot-state", summary="Get Current Bot State")
async def get_bot_state_endpoint() -> Dict[str, Any]:
    """
    Get current bot state from centralized database.

    Single source of truth for all bot statistics and configuration.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        state = data_manager.get_bot_state()

        return {
            "success": True,
            "data": state
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MODEL VERSIONING ENDPOINTS (Phase 3)
# ============================================================================

@router.get("/model-versions", summary="Get All Model Versions")
async def get_model_versions_endpoint(
    limit: int = Query(20, ge=1, le=100, description="Maximum versions to return")
) -> Dict[str, Any]:
    """
    Get all registered model versions.

    Shows training history and allows comparing different model versions.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        versions = data_manager.get_model_versions(limit=limit)

        formatted_versions = []
        for v in versions:
            formatted_versions.append({
                "version": v['version'],
                "created_at": v['created_at'],
                "file_path": v.get('file_path'),
                "training_episodes": v.get('training_episodes'),
                "training_session_id": v.get('training_session_id'),
                "final_iq": v.get('final_iq'),
                "final_win_rate": round(v.get('final_win_rate', 0) or 0, 2),
                "final_profit_factor": round(v.get('final_profit_factor', 0) or 0, 2),
                "final_sharpe": round(v.get('final_sharpe', 0) or 0, 2) if v.get('final_sharpe') else None,
                "notes": v.get('notes'),
                "is_active": bool(v.get('is_active'))
            })

        return {
            "success": True,
            "data": {
                "versions": formatted_versions,
                "version_count": len(formatted_versions)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-versions/active", summary="Get Active Model Version")
async def get_active_model_endpoint() -> Dict[str, Any]:
    """
    Get the currently active model version.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        active = data_manager.get_active_model_version()

        if not active:
            return {
                "success": True,
                "data": None,
                "message": "No active model version found"
            }

        return {
            "success": True,
            "data": {
                "version": active['version'],
                "created_at": active['created_at'],
                "file_path": active.get('file_path'),
                "training_episodes": active.get('training_episodes'),
                "final_iq": active.get('final_iq'),
                "final_win_rate": round(active.get('final_win_rate', 0) or 0, 2),
                "final_profit_factor": round(active.get('final_profit_factor', 0) or 0, 2),
                "final_sharpe": round(active.get('final_sharpe', 0) or 0, 2) if active.get('final_sharpe') else None,
                "notes": active.get('notes')
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades-by-model", summary="Get Trades by Model Version")
async def get_trades_by_model(
    version: Optional[str] = Query(None, description="Filter by specific model version"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum trades to return")
) -> Dict[str, Any]:
    """
    Get trades grouped by model version.

    Useful for comparing model performance across different versions.
    """
    if not DATA_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Data manager not available")

    try:
        # Get trades with model version info
        with data_manager.get_db() as conn:
            cur = conn.cursor()

            if version:
                cur.execute("""
                    SELECT model_version, COUNT(*) as trades,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                           SUM(pnl) as total_pnl,
                           AVG(pnl) as avg_pnl
                    FROM trades
                    WHERE model_version = ?
                    GROUP BY model_version
                """, (version,))
            else:
                cur.execute("""
                    SELECT model_version, COUNT(*) as trades,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                           SUM(pnl) as total_pnl,
                           AVG(pnl) as avg_pnl
                    FROM trades
                    WHERE model_version IS NOT NULL
                    GROUP BY model_version
                    ORDER BY total_pnl DESC
                    LIMIT ?
                """, (limit,))

            results = cur.fetchall()

        model_stats = []
        for row in results:
            model_version, trades, wins, total_pnl, avg_pnl = row
            model_stats.append({
                "model_version": model_version,
                "trade_count": trades,
                "wins": wins,
                "losses": trades - wins,
                "win_rate": round(wins / trades * 100, 2) if trades > 0 else 0,
                "total_pnl": round(total_pnl or 0, 2),
                "avg_pnl": round(avg_pnl or 0, 2)
            })

        return {
            "success": True,
            "data": {
                "models": model_stats,
                "model_count": len(model_stats)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
