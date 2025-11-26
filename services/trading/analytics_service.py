"""
Analytics Service - Tracks and analyzes trading performance
"""

import sys
import os
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.base.service import BaseService
from modules.event_bus import event_bus


class AnalyticsService(BaseService):
    """Service that analyzes trading performance and generates statistics"""

    def __init__(self):
        super().__init__(name="analytics", auto_start=True)

        # Configuration
        self.config = {
            "update_interval": 60,  # seconds - how often to recalculate stats
            "db_path": "data/trades.db"
        }

        # Stats tracking
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "last_analysis": None,
            "trades_by_symbol": {},
            "performance_by_day": {},
            "recent_trades": []
        }

        # Real-time tracking
        self.trade_events = []
        self.equity_curve = []

        # Subscribe to trade events
        event_bus.subscribe("TRADE_EXECUTED", self._on_trade_executed)

    def _run(self):
        """Analyze trading performance in a loop"""
        print(f"📊 Analytics Service starting (update every {self.config['update_interval']}s)...")

        while self.status == "running":
            try:
                # Analyze trades from database
                self._analyze_trades()

                # Calculate advanced metrics
                self._calculate_metrics()

                # Update last analysis time
                self.stats["last_analysis"] = datetime.now().isoformat()

                # Log summary every 10 analyses
                if len(self.equity_curve) > 0 and len(self.equity_curve) % 10 == 0:
                    print(f"📈 Analytics: {self.stats['total_trades']} trades | "
                          f"Win Rate: {self.stats['win_rate']:.1f}% | "
                          f"PnL: ${self.stats['total_pnl']:.2f}")

            except Exception as e:
                print(f"❌ Analytics error: {e}")

            # Wait before next analysis
            time.sleep(self.config["update_interval"])

    def _analyze_trades(self):
        """Analyze all trades from the database"""
        try:
            # Check if database exists
            db_path = self.config["db_path"]
            if not os.path.exists(db_path):
                return

            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all trades
            cursor.execute("""
                SELECT timestamp, symbol, signal, last_price, vwap, pnl
                FROM trades
                ORDER BY id ASC
            """)

            trades = cursor.fetchall()
            conn.close()

            if not trades:
                return

            # Reset stats
            total_wins = 0
            total_losses = 0
            total_pnl = 0.0
            wins = []
            losses = []
            trades_by_symbol = defaultdict(lambda: {"count": 0, "pnl": 0.0})
            trades_by_day = defaultdict(lambda: {"count": 0, "pnl": 0.0})

            # Analyze each trade
            for trade in trades:
                timestamp, symbol, signal, last_price, vwap, pnl = trade

                # Overall stats
                total_pnl += pnl
                if pnl > 0:
                    total_wins += 1
                    wins.append(pnl)
                elif pnl < 0:
                    total_losses += 1
                    losses.append(abs(pnl))

                # By symbol
                trades_by_symbol[symbol]["count"] += 1
                trades_by_symbol[symbol]["pnl"] += pnl

                # By day
                try:
                    day = timestamp.split('T')[0]
                    trades_by_day[day]["count"] += 1
                    trades_by_day[day]["pnl"] += pnl
                except (AttributeError, IndexError, KeyError):
                    # Skip trades with invalid timestamp format
                    pass

            # Calculate metrics
            total_trades = len(trades)
            win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
            avg_win = (sum(wins) / len(wins)) if wins else 0.0
            avg_loss = (sum(losses) / len(losses)) if losses else 0.0

            # Profit factor
            total_win_amount = sum(wins) if wins else 0.0
            total_loss_amount = sum(losses) if losses else 0.0
            profit_factor = (total_win_amount / total_loss_amount) if total_loss_amount > 0 else 0.0

            # Update stats
            self.stats.update({
                "total_trades": total_trades,
                "winning_trades": total_wins,
                "losing_trades": total_losses,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "trades_by_symbol": dict(trades_by_symbol),
                "performance_by_day": dict(trades_by_day)
            })

            # Store recent trades
            self.stats["recent_trades"] = [
                {
                    "timestamp": t[0],
                    "symbol": t[1],
                    "signal": t[2],
                    "price": t[3],
                    "vwap": t[4],
                    "pnl": t[5]
                }
                for t in trades[-20:]  # Last 20 trades
            ]

        except Exception as e:
            print(f"⚠️ Analytics database error: {e}")

    def _calculate_metrics(self):
        """Calculate advanced trading metrics"""
        try:
            # Calculate max drawdown from equity curve
            if self.equity_curve:
                peak = self.equity_curve[0]
                max_dd = 0.0

                for equity in self.equity_curve:
                    if equity > peak:
                        peak = equity
                    drawdown = (peak - equity) / peak if peak > 0 else 0
                    max_dd = max(max_dd, drawdown)

                self.stats["max_drawdown"] = max_dd * 100  # Convert to percentage

            # Calculate Sharpe ratio (simplified)
            # In a real system, this would use returns and risk-free rate
            if self.stats["total_trades"] > 10:
                win_rate = self.stats["win_rate"] / 100
                avg_return = self.stats["avg_win"] * win_rate - self.stats["avg_loss"] * (1 - win_rate)
                volatility = (self.stats["avg_win"] + self.stats["avg_loss"]) / 2

                if volatility > 0:
                    self.stats["sharpe_ratio"] = avg_return / volatility
                else:
                    self.stats["sharpe_ratio"] = 0.0

        except Exception as e:
            print(f"⚠️ Analytics metrics error: {e}")

    def _on_trade_executed(self, event: Dict):
        """Handle trade execution events"""
        try:
            trade_data = event["data"]
            self.trade_events.append(trade_data)

            # Update equity curve
            pnl = trade_data.get("pnl", 0.0)
            if self.equity_curve:
                new_equity = self.equity_curve[-1] + pnl
            else:
                new_equity = 10000.0 + pnl  # Assume starting with $10k

            self.equity_curve.append(new_equity)

            # Keep only last 1000 points
            if len(self.equity_curve) > 1000:
                self.equity_curve = self.equity_curve[-1000:]

        except Exception as e:
            print(f"⚠️ Analytics event error: {e}")

    def _cleanup(self):
        """Cleanup when stopping"""
        # Unsubscribe from events
        event_bus.unsubscribe("TRADE_EXECUTED", self._on_trade_executed)
        print("🛑 Analytics Service stopped")

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive performance report

        Returns:
            Dictionary with performance metrics
        """
        return {
            "overview": {
                "total_trades": self.stats["total_trades"],
                "win_rate": self.stats["win_rate"],
                "total_pnl": self.stats["total_pnl"],
                "profit_factor": self.stats["profit_factor"]
            },
            "trade_metrics": {
                "winning_trades": self.stats["winning_trades"],
                "losing_trades": self.stats["losing_trades"],
                "avg_win": self.stats["avg_win"],
                "avg_loss": self.stats["avg_loss"]
            },
            "risk_metrics": {
                "max_drawdown": self.stats["max_drawdown"],
                "sharpe_ratio": self.stats["sharpe_ratio"]
            },
            "by_symbol": self.stats["trades_by_symbol"],
            "by_day": self.stats["performance_by_day"],
            "recent_trades": self.stats["recent_trades"][-10:],
            "last_analysis": self.stats["last_analysis"]
        }

    def get_equity_curve(self) -> List[float]:
        """
        Get the equity curve (account balance over time)

        Returns:
            List of equity values
        """
        return self.equity_curve.copy()
