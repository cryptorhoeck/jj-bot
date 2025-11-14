"""
Price Alert System

Monitor price levels and trigger notifications when conditions are met
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json


class AlertCondition(str, Enum):
    """Alert condition types"""
    ABOVE = "above"
    BELOW = "below"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    PERCENT_CHANGE = "percent_change"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PriceAlert:
    """Individual price alert"""

    def __init__(
        self,
        alert_id: str,
        symbol: str,
        condition: AlertCondition,
        target_price: float,
        current_price: Optional[float] = None,
        message: Optional[str] = None,
        webhook_url: Optional[str] = None,
        repeat: bool = False,
        expires_at: Optional[datetime] = None
    ):
        """
        Initialize price alert

        Args:
            alert_id: Unique alert identifier
            symbol: Trading symbol
            condition: Alert condition type
            target_price: Target price level
            current_price: Current price (for tracking crosses)
            message: Custom alert message
            webhook_url: Webhook URL for notifications
            repeat: Whether to repeat after triggering
            expires_at: Expiration timestamp
        """
        self.alert_id = alert_id
        self.symbol = symbol
        self.condition = AlertCondition(condition)
        self.target_price = target_price
        self.current_price = current_price
        self.message = message or f"{symbol} {condition.value} {target_price}"
        self.webhook_url = webhook_url
        self.repeat = repeat
        self.expires_at = expires_at

        self.status = AlertStatus.ACTIVE
        self.created_at = datetime.now()
        self.triggered_at: Optional[datetime] = None
        self.trigger_count = 0
        self.last_price: Optional[float] = None

    def check(self, price: float) -> bool:
        """
        Check if alert condition is met

        Args:
            price: Current market price

        Returns:
            True if alert should trigger
        """
        if self.status != AlertStatus.ACTIVE:
            return False

        # Check expiration
        if self.expires_at and datetime.now() > self.expires_at:
            self.status = AlertStatus.EXPIRED
            return False

        triggered = False

        if self.condition == AlertCondition.ABOVE:
            triggered = price > self.target_price

        elif self.condition == AlertCondition.BELOW:
            triggered = price < self.target_price

        elif self.condition == AlertCondition.CROSSES_ABOVE:
            if self.last_price is not None:
                triggered = self.last_price <= self.target_price and price > self.target_price

        elif self.condition == AlertCondition.CROSSES_BELOW:
            if self.last_price is not None:
                triggered = self.last_price >= self.target_price and price < self.target_price

        elif self.condition == AlertCondition.PERCENT_CHANGE:
            if self.current_price is not None:
                change_pct = ((price - self.current_price) / self.current_price) * 100
                triggered = abs(change_pct) >= self.target_price

        self.last_price = price

        if triggered:
            self.trigger()

        return triggered

    def trigger(self):
        """Mark alert as triggered"""
        self.triggered_at = datetime.now()
        self.trigger_count += 1

        if not self.repeat:
            self.status = AlertStatus.TRIGGERED

    def cancel(self):
        """Cancel the alert"""
        self.status = AlertStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'symbol': self.symbol,
            'condition': self.condition.value,
            'target_price': self.target_price,
            'current_price': self.current_price,
            'message': self.message,
            'webhook_url': self.webhook_url,
            'repeat': self.repeat,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'trigger_count': self.trigger_count,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class AlertManager:
    """Manage and monitor price alerts"""

    def __init__(self):
        """Initialize alert manager"""
        self.alerts: Dict[str, PriceAlert] = {}
        self.handlers: List[Callable] = []
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

    def create_alert(
        self,
        symbol: str,
        condition: str,
        target_price: float,
        **kwargs
    ) -> PriceAlert:
        """
        Create a new price alert

        Args:
            symbol: Trading symbol
            condition: Alert condition
            target_price: Target price
            **kwargs: Additional alert parameters

        Returns:
            Created alert
        """
        import uuid
        alert_id = str(uuid.uuid4())

        alert = PriceAlert(
            alert_id=alert_id,
            symbol=symbol,
            condition=condition,
            target_price=target_price,
            **kwargs
        )

        self.alerts[alert_id] = alert
        return alert

    def get_alert(self, alert_id: str) -> Optional[PriceAlert]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)

    def get_alerts(
        self,
        symbol: Optional[str] = None,
        status: Optional[AlertStatus] = None
    ) -> List[PriceAlert]:
        """
        Get alerts with optional filtering

        Args:
            symbol: Filter by symbol
            status: Filter by status

        Returns:
            List of matching alerts
        """
        alerts = list(self.alerts.values())

        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol]

        if status:
            alerts = [a for a in alerts if a.status == status]

        return alerts

    def cancel_alert(self, alert_id: str) -> bool:
        """
        Cancel an alert

        Args:
            alert_id: Alert ID to cancel

        Returns:
            True if cancelled successfully
        """
        alert = self.alerts.get(alert_id)
        if alert:
            alert.cancel()
            return True
        return False

    def delete_alert(self, alert_id: str) -> bool:
        """
        Delete an alert

        Args:
            alert_id: Alert ID to delete

        Returns:
            True if deleted successfully
        """
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            return True
        return False

    def check_price(self, symbol: str, price: float) -> List[PriceAlert]:
        """
        Check price against all active alerts for a symbol

        Args:
            symbol: Trading symbol
            price: Current price

        Returns:
            List of triggered alerts
        """
        triggered = []

        for alert in self.get_alerts(symbol=symbol, status=AlertStatus.ACTIVE):
            if alert.check(price):
                triggered.append(alert)
                # Notify handlers
                for handler in self.handlers:
                    try:
                        handler(alert, price)
                    except Exception as e:
                        print(f"Error in alert handler: {e}")

        return triggered

    def add_handler(self, handler: Callable):
        """
        Add alert notification handler

        Args:
            handler: Callback function(alert, price)
        """
        self.handlers.append(handler)

    def remove_handler(self, handler: Callable):
        """Remove alert notification handler"""
        if handler in self.handlers:
            self.handlers.remove(handler)

    async def monitor_prices(self, price_source: Callable):
        """
        Monitor prices from a source

        Args:
            price_source: Async function that returns {symbol: price} dict
        """
        self.monitoring = True

        while self.monitoring:
            try:
                # Get current prices
                prices = await price_source()

                # Check each price
                for symbol, price in prices.items():
                    self.check_price(symbol, price)

                # Wait before next check
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Error monitoring prices: {e}")
                await asyncio.sleep(5)

    def start_monitoring(self, price_source: Callable):
        """Start background price monitoring"""
        if not self.monitoring:
            self.monitor_task = asyncio.create_task(self.monitor_prices(price_source))

    def stop_monitoring(self):
        """Stop background price monitoring"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()

    def get_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        all_alerts = list(self.alerts.values())

        return {
            'total_alerts': len(all_alerts),
            'active': len([a for a in all_alerts if a.status == AlertStatus.ACTIVE]),
            'triggered': len([a for a in all_alerts if a.status == AlertStatus.TRIGGERED]),
            'cancelled': len([a for a in all_alerts if a.status == AlertStatus.CANCELLED]),
            'expired': len([a for a in all_alerts if a.status == AlertStatus.EXPIRED]),
            'monitoring': self.monitoring
        }


# Global alert manager instance
alert_manager = AlertManager()


# Webhook notification handler
async def send_webhook_notification(alert: PriceAlert, price: float):
    """
    Send webhook notification for triggered alert

    Args:
        alert: Triggered alert
        price: Current price
    """
    if not alert.webhook_url:
        return

    try:
        import aiohttp

        payload = {
            'alert_id': alert.alert_id,
            'symbol': alert.symbol,
            'condition': alert.condition.value,
            'target_price': alert.target_price,
            'current_price': price,
            'message': alert.message,
            'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(alert.webhook_url, json=payload) as response:
                if response.status != 200:
                    print(f"Webhook notification failed: {response.status}")

    except Exception as e:
        print(f"Error sending webhook: {e}")


# Console notification handler
def console_notification_handler(alert: PriceAlert, price: float):
    """Print alert to console"""
    print(f"🔔 ALERT TRIGGERED: {alert.message}")
    print(f"   Symbol: {alert.symbol}")
    print(f"   Condition: {alert.condition.value}")
    print(f"   Target: ${alert.target_price}")
    print(f"   Current: ${price}")
    print(f"   Time: {datetime.now()}")


# Add default console handler
alert_manager.add_handler(console_notification_handler)
