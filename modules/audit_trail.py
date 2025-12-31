"""
Audit Trail Module
Provides structured logging for compliance and debugging
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    # Trade events
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_FAILED = "order_failed"

    # Risk events
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    TRAILING_STOP_ACTIVATED = "trailing_stop_activated"
    TRAILING_STOP_TRIGGERED = "trailing_stop_triggered"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    POSITION_SYNC = "position_sync"

    # System events
    BOT_START = "bot_start"
    BOT_STOP = "bot_stop"
    EMERGENCY_STOP = "emergency_stop"
    DEAD_MANS_SWITCH = "dead_mans_switch"
    POSITION_RECONCILIATION = "position_reconciliation"
    SESSION_THRESHOLD = "session_threshold"
    CONFIG_CHANGE = "config_change"
    EXCHANGE_CONNECT = "exchange_connect"
    EXCHANGE_DISCONNECT = "exchange_disconnect"
    EXCHANGE_RECONNECT = "exchange_reconnect"
    PRICE_FEED_STALE = "price_feed_stale"
    PRICE_FEED_RESTORED = "price_feed_restored"

    # Signal events
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_REJECTED = "signal_rejected"
    SIGNAL_EXECUTED = "signal_executed"

    # Error events
    ERROR = "error"
    WARNING = "warning"

    # Dead man's switch
    DEAD_MANS_SWITCH = "dead_mans_switch"


class AuditTrail:
    """
    Audit trail logger for trading bot

    Logs all significant events to a JSON-lines file for easy parsing
    and compliance review.
    """

    def __init__(
        self,
        log_dir: str = "logs/audit",
        max_file_size_mb: float = 10.0,
        enabled: bool = True
    ):
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.enabled = enabled
        self._current_file: Optional[str] = None
        self._file_handle = None

        if self.enabled:
            self._setup_log_dir()

    def _setup_log_dir(self):
        """Create log directory if it doesn't exist"""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_log_file(self) -> str:
        """Get current log file path, rotating if needed"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        base_name = f"audit_{date_str}.jsonl"
        file_path = self.log_dir / base_name

        # Check if rotation needed
        if file_path.exists() and file_path.stat().st_size > self.max_file_size:
            # Find next available file number
            i = 1
            while True:
                rotated_name = f"audit_{date_str}_{i:03d}.jsonl"
                rotated_path = self.log_dir / rotated_name
                if not rotated_path.exists():
                    return str(rotated_path)
                i += 1

        return str(file_path)

    def log(
        self,
        event_type: AuditEventType,
        data: Dict[str, Any],
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        severity: str = "INFO"
    ):
        """
        Log an audit event

        Args:
            event_type: Type of event from AuditEventType enum
            data: Event-specific data dictionary
            symbol: Trading symbol if applicable
            order_id: Order ID if applicable
            severity: Log level (INFO, WARNING, ERROR)
        """
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type.value,
            "severity": severity,
            "data": data
        }

        if symbol:
            event["symbol"] = symbol
        if order_id:
            event["order_id"] = order_id

        try:
            log_file = self._get_current_log_file()
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def log_trade_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        signal_source: str,
        order_id: Optional[str] = None,
        slippage_pct: float = 0.0
    ):
        """Log trade entry"""
        self.log(
            AuditEventType.TRADE_ENTRY,
            {
                "side": side,
                "entry_price": entry_price,
                "size": size,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "signal_source": signal_source,
                "slippage_pct": slippage_pct
            },
            symbol=symbol,
            order_id=order_id
        )

    def log_trade_exit(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        size: float,
        pnl: float,
        pnl_pct: float,
        reason: str,
        order_id: Optional[str] = None,
        slippage_pct: float = 0.0
    ):
        """Log trade exit"""
        self.log(
            AuditEventType.TRADE_EXIT,
            {
                "side": side,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "size": size,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": reason,
                "slippage_pct": slippage_pct
            },
            symbol=symbol,
            order_id=order_id
        )

    def log_signal_rejected(
        self,
        symbol: str,
        signal_type: str,
        reason: str,
        details: Optional[Dict] = None
    ):
        """Log rejected signal"""
        data = {
            "signal_type": signal_type,
            "reason": reason
        }
        if details:
            data["details"] = details

        self.log(
            AuditEventType.SIGNAL_REJECTED,
            data,
            symbol=symbol,
            severity="WARNING"
        )

    def log_risk_event(
        self,
        event_type: AuditEventType,
        message: str,
        current_value: float,
        limit_value: float,
        symbol: Optional[str] = None
    ):
        """Log risk management event"""
        self.log(
            event_type,
            {
                "message": message,
                "current_value": current_value,
                "limit_value": limit_value
            },
            symbol=symbol,
            severity="WARNING"
        )

    def log_system_event(
        self,
        event_type: AuditEventType,
        message: str,
        details: Optional[Dict] = None
    ):
        """Log system event"""
        data = {"message": message}
        if details:
            data["details"] = details

        self.log(event_type, data)

    def log_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict] = None,
        symbol: Optional[str] = None
    ):
        """Log error event"""
        data = {
            "error_type": error_type,
            "message": message
        }
        if details:
            data["details"] = details

        self.log(
            AuditEventType.ERROR,
            data,
            symbol=symbol,
            severity="ERROR"
        )

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None,
        symbol: Optional[str] = None
    ) -> list:
        """
        Get recent audit events

        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type
            symbol: Filter by symbol

        Returns:
            List of event dictionaries
        """
        events = []

        # Get all log files sorted by date (newest first)
        log_files = sorted(
            self.log_dir.glob("audit_*.jsonl"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()

                # Read in reverse order (newest first)
                for line in reversed(lines):
                    if len(events) >= limit:
                        break

                    try:
                        event = json.loads(line.strip())

                        # Apply filters
                        if event_type and event.get("event_type") != event_type.value:
                            continue
                        if symbol and event.get("symbol") != symbol:
                            continue

                        events.append(event)
                    except json.JSONDecodeError:
                        continue

                if len(events) >= limit:
                    break

            except Exception as e:
                logger.error(f"Error reading audit log {log_file}: {e}")

        return events


# Global audit trail instance
_audit_trail: Optional[AuditTrail] = None


def get_audit_trail() -> AuditTrail:
    """Get or create global audit trail instance"""
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail()
    return _audit_trail


def init_audit_trail(
    log_dir: str = "logs/audit",
    max_file_size_mb: float = 10.0,
    enabled: bool = True
) -> AuditTrail:
    """Initialize global audit trail with custom settings"""
    global _audit_trail
    _audit_trail = AuditTrail(
        log_dir=log_dir,
        max_file_size_mb=max_file_size_mb,
        enabled=enabled
    )
    return _audit_trail
