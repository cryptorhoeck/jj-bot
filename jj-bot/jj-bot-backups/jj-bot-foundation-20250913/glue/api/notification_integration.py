import asyncio
import sys
import os
from datetime import datetime

# Fix imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, '..', '..'))

from hands.notifications.notification_manager import notification_manager, alert_triggers
from engine import get_summary

class NotificationIntegration:
    """Integration layer for notifications with trading system"""
    
    def __init__(self):
        self.last_trade_count = 0
        self.monitoring = False
    
    async def start_monitoring(self):
        """Start monitoring for notification triggers"""
        self.monitoring = True
        print("📱 Notification monitoring started")
        
        while self.monitoring:
            try:
                await self.check_trade_alerts()
                await self.check_risk_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                await notification_manager.send_alert(
                    "system_errors", 
                    f"Notification monitoring error: {str(e)}"
                )
                await asyncio.sleep(60)
    
    async def check_trade_alerts(self):
        """Check for new trades and trigger alerts"""
        try:
            summary = get_summary()
            current_trade_count = summary.get("total_trades", 0)
            
            # If new trades detected, check last few trades
            if current_trade_count > self.last_trade_count:
                # In a real implementation, we'd get the actual new trades
                # For now, we'll simulate checking recent trade data
                from hands.analytics.performance_analyzer import PerformanceAnalyzer
                analyzer = PerformanceAnalyzer()
                recent_trades = analyzer.get_trade_data(1)  # Last day
                
                if not recent_trades.empty:
                    latest_trade = recent_trades.iloc[0]
                    trade_dict = {
                        "symbol": latest_trade["symbol"],
                        "signal": latest_trade["signal"],
                        "pnl": latest_trade["pnl"],
                        "timestamp": latest_trade["timestamp"]
                    }
                    
                    await alert_triggers.check_trade_alerts(trade_dict)
                
                self.last_trade_count = current_trade_count
                
        except Exception as e:
            print(f"Error checking trade alerts: {e}")
    
    async def check_risk_alerts(self):
        """Check risk metrics and trigger alerts if needed"""
        try:
            from hands.analytics.performance_analyzer import PerformanceAnalyzer
            analyzer = PerformanceAnalyzer()
            risk_assessment = analyzer.get_risk_assessment()
            
            await alert_triggers.check_risk_alerts(risk_assessment)
            
        except Exception as e:
            print(f"Error checking risk alerts: {e}")
    
    async def send_daily_summary(self):
        """Send daily trading summary"""
        try:
            summary = get_summary()
            
            # Get additional stats
            from hands.analytics.performance_analyzer import PerformanceAnalyzer
            analyzer = PerformanceAnalyzer()
            metrics = analyzer.calculate_performance_metrics(1)  # Today only
            
            summary_data = {
                "total_pnl": metrics.get("total_pnl", 0),
                "total_trades": metrics.get("total_trades", 0),
                "win_rate": metrics.get("win_rate", 0),
                "best_trade": 0,  # Would calculate from trade data
                "worst_trade": 0  # Would calculate from trade data
            }
            
            await alert_triggers.send_daily_summary(summary_data)
            
        except Exception as e:
            await notification_manager.send_alert(
                "system_errors",
                f"Failed to send daily summary: {str(e)}"
            )
    
    def stop_monitoring(self):
        """Stop notification monitoring"""
        self.monitoring = False
        print("📱 Notification monitoring stopped")

# Global notification integration
notification_integration = NotificationIntegration()

async def start_notification_service():
    """Start the notification service"""
    await notification_integration.start_monitoring()

if __name__ == "__main__":
    asyncio.run(start_notification_service())
