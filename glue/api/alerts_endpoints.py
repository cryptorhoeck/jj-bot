"""
Alerts API Endpoints

Provides RESTful endpoints for price alert management
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.alerts import alert_manager, AlertCondition, AlertStatus

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# === Request/Response Models ===

class CreateAlertRequest(BaseModel):
    """Request to create a new alert"""
    symbol: str
    condition: str  # AlertCondition
    target_price: float
    current_price: Optional[float] = None
    message: Optional[str] = None
    webhook_url: Optional[str] = None
    repeat: bool = False
    expires_in_hours: Optional[int] = None


class UpdateAlertRequest(BaseModel):
    """Request to update an alert"""
    target_price: Optional[float] = None
    message: Optional[str] = None
    webhook_url: Optional[str] = None


# === Endpoints ===

@router.post("/create")
async def create_alert(request: CreateAlertRequest):
    """
    Create a new price alert

    Monitors price levels and triggers notifications when conditions are met.

    Supported conditions:
    - above: Trigger when price goes above target
    - below: Trigger when price goes below target
    - crosses_above: Trigger when price crosses above target
    - crosses_below: Trigger when price crosses below target
    - percent_change: Trigger when price changes by target percentage

    Request body:
    {
        "symbol": "BTC",
        "condition": "above",
        "target_price": 50000,
        "message": "BTC reached $50k!",
        "webhook_url": "https://hooks.slack.com/...",
        "repeat": false,
        "expires_in_hours": 24
    }

    Returns:
        Created alert details

    Example:
    - POST /api/alerts/create
    """
    try:
        # Validate condition
        try:
            AlertCondition(request.condition)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid condition. Must be one of: {[c.value for c in AlertCondition]}"
            )

        # Calculate expiration
        expires_at = None
        if request.expires_in_hours:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(hours=request.expires_in_hours)

        # Create alert
        alert = alert_manager.create_alert(
            symbol=request.symbol,
            condition=request.condition,
            target_price=request.target_price,
            current_price=request.current_price,
            message=request.message,
            webhook_url=request.webhook_url,
            repeat=request.repeat,
            expires_at=expires_at
        )

        return {
            'success': True,
            'alert': alert.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_alerts(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: Optional[str] = Query(None, description="Filter by status (active, triggered, cancelled, expired)")
):
    """
    List all alerts with optional filtering

    Query parameters:
    - symbol: Filter by trading symbol
    - status: Filter by alert status

    Examples:
    - /api/alerts/list
    - /api/alerts/list?symbol=BTC
    - /api/alerts/list?status=active
    - /api/alerts/list?symbol=ETH&status=triggered
    """
    try:
        # Validate status
        alert_status = None
        if status:
            try:
                alert_status = AlertStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {[s.value for s in AlertStatus]}"
                )

        # Get alerts
        alerts = alert_manager.get_alerts(symbol=symbol, status=alert_status)

        return {
            'success': True,
            'alerts': [alert.to_dict() for alert in alerts],
            'count': len(alerts)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """
    Get alert by ID

    Args:
        alert_id: Alert identifier

    Returns:
        Alert details

    Example:
    - GET /api/alerts/abc-123-def-456
    """
    try:
        alert = alert_manager.get_alert(alert_id)

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            'success': True,
            'alert': alert.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, request: UpdateAlertRequest):
    """
    Update an existing alert

    Args:
        alert_id: Alert identifier

    Request body:
    {
        "target_price": 55000,
        "message": "Updated message"
    }

    Returns:
        Updated alert details

    Example:
    - PATCH /api/alerts/abc-123-def-456
    """
    try:
        alert = alert_manager.get_alert(alert_id)

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Update fields
        if request.target_price is not None:
            alert.target_price = request.target_price

        if request.message is not None:
            alert.message = request.message

        if request.webhook_url is not None:
            alert.webhook_url = request.webhook_url

        return {
            'success': True,
            'alert': alert.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/cancel")
async def cancel_alert(alert_id: str):
    """
    Cancel an active alert

    Args:
        alert_id: Alert identifier

    Returns:
        Success status

    Example:
    - POST /api/alerts/abc-123-def-456/cancel
    """
    try:
        success = alert_manager.cancel_alert(alert_id)

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            'success': True,
            'message': 'Alert cancelled'
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """
    Delete an alert

    Args:
        alert_id: Alert identifier

    Returns:
        Success status

    Example:
    - DELETE /api/alerts/abc-123-def-456
    """
    try:
        success = alert_manager.delete_alert(alert_id)

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            'success': True,
            'message': 'Alert deleted'
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-price")
async def check_price(symbol: str, price: float):
    """
    Manually check a price against all active alerts

    Useful for testing alerts or manual price updates.

    Request body (as query params):
    - symbol: Trading symbol
    - price: Current price

    Returns:
        List of triggered alerts

    Example:
    - POST /api/alerts/check-price?symbol=BTC&price=50000
    """
    try:
        triggered = alert_manager.check_price(symbol, price)

        return {
            'success': True,
            'symbol': symbol,
            'price': price,
            'triggered_alerts': [alert.to_dict() for alert in triggered],
            'count': len(triggered)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get alert system statistics

    Returns overall statistics about the alert system.

    Example:
    - GET /api/alerts/stats
    """
    try:
        stats = alert_manager.get_stats()

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conditions")
async def get_conditions():
    """
    Get available alert conditions

    Returns list of supported alert conditions with descriptions.

    Example:
    - GET /api/alerts/conditions
    """
    return {
        'success': True,
        'conditions': [
            {
                'value': AlertCondition.ABOVE.value,
                'description': 'Trigger when price goes above target level'
            },
            {
                'value': AlertCondition.BELOW.value,
                'description': 'Trigger when price goes below target level'
            },
            {
                'value': AlertCondition.CROSSES_ABOVE.value,
                'description': 'Trigger when price crosses above target level'
            },
            {
                'value': AlertCondition.CROSSES_BELOW.value,
                'description': 'Trigger when price crosses below target level'
            },
            {
                'value': AlertCondition.PERCENT_CHANGE.value,
                'description': 'Trigger when price changes by target percentage'
            }
        ]
    }


@router.post("/test-webhook")
async def test_webhook(webhook_url: str):
    """
    Test a webhook URL

    Sends a test notification to verify webhook is working.

    Request body (as query param):
    - webhook_url: URL to test

    Returns:
        Test result

    Example:
    - POST /api/alerts/test-webhook?webhook_url=https://hooks.slack.com/...
    """
    try:
        from modules.alerts import send_webhook_notification, PriceAlert

        # Create a test alert
        test_alert = PriceAlert(
            alert_id="test",
            symbol="BTC",
            condition=AlertCondition.ABOVE,
            target_price=50000,
            message="Test notification from JJ-Bot",
            webhook_url=webhook_url
        )
        test_alert.trigger()

        # Send notification
        await send_webhook_notification(test_alert, 50100)

        return {
            'success': True,
            'message': 'Test webhook sent',
            'webhook_url': webhook_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook test failed: {str(e)}")
