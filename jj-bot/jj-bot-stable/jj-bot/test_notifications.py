#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

from hands.notifications.notification_manager import notification_manager, alert_triggers

async def test_all_notifications():
    """Test all notification types"""
    print("🧪 Testing JJ-Bot Notifications...")
    
    # Test big win alert
    await notification_manager.send_alert(
        "big_wins",
        "Test big win alert",
        {"symbol": "BTCUSDT", "pnl": 150.0}
    )
    
    # Test risk warning
    await notification_manager.send_alert(
        "risk_warnings", 
        "Test risk warning",
        {"risk_level": "HIGH", "warnings": ["Test warning"]}
    )
    
    # Test daily summary
    summary_data = {
        "total_pnl": 250.50,
        "total_trades": 15,
        "win_rate": 66.7,
        "best_trade": 89.50,
        "worst_trade": -45.20
    }
    await alert_triggers.send_daily_summary(summary_data)
    
    print("✅ All test notifications sent!")

if __name__ == "__main__":
    asyncio.run(test_all_notifications())
