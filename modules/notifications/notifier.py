"""
Trade Notification System
Sends alerts via Telegram, Discord, or generic webhooks
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notifications"""
    # Telegram settings
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Discord settings
    discord_enabled: bool = False
    discord_webhook_url: str = ""

    # Generic webhook
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_headers: Dict[str, str] = field(default_factory=dict)

    # Notification preferences
    notify_on_entry: bool = True
    notify_on_exit: bool = True
    notify_on_stop_loss: bool = True
    notify_on_error: bool = True
    notify_on_daily_summary: bool = True

    # Rate limiting
    min_notification_interval_seconds: float = 1.0  # Prevent spam

    def __post_init__(self):
        """Load from environment variables if not set"""
        if not self.telegram_bot_token:
            self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not self.telegram_chat_id:
            self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not self.discord_webhook_url:
            self.discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
        if not self.webhook_url:
            self.webhook_url = os.environ.get("NOTIFICATION_WEBHOOK_URL", "")

        # Auto-enable based on config presence
        if self.telegram_bot_token and self.telegram_chat_id:
            self.telegram_enabled = True
        if self.discord_webhook_url:
            self.discord_enabled = True
        if self.webhook_url:
            self.webhook_enabled = True


class BaseNotifier(ABC):
    """Abstract base class for notification providers"""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self._last_notification_time: datetime = datetime.min
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _rate_limit_check(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        elapsed = (now - self._last_notification_time).total_seconds()
        if elapsed < self.config.min_notification_interval_seconds:
            return False
        self._last_notification_time = now
        return True

    @abstractmethod
    async def send(self, message: str, **kwargs) -> bool:
        """Send a notification"""
        pass

    @abstractmethod
    def format_trade_entry(self, trade_data: Dict[str, Any]) -> str:
        """Format trade entry notification"""
        pass

    @abstractmethod
    def format_trade_exit(self, trade_data: Dict[str, Any]) -> str:
        """Format trade exit notification"""
        pass


class TelegramNotifier(BaseNotifier):
    """Telegram notification provider"""

    API_BASE = "https://api.telegram.org/bot"

    async def send(self, message: str, parse_mode: str = "HTML", **kwargs) -> bool:
        """Send a Telegram message"""
        if not self.config.telegram_enabled:
            return False

        if not self._rate_limit_check():
            logger.debug("Telegram notification rate limited")
            return False

        try:
            session = await self._get_session()
            url = f"{self.API_BASE}{self.config.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }

            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    logger.debug("Telegram notification sent successfully")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Telegram error {resp.status}: {error_text}")
                    return False

        except asyncio.TimeoutError:
            logger.error("Telegram notification timed out")
            return False
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def format_trade_entry(self, trade_data: Dict[str, Any]) -> str:
        """Format trade entry for Telegram"""
        symbol = trade_data.get("symbol", "???")
        action = trade_data.get("action", "OPEN")
        price = trade_data.get("price", 0)
        quantity = trade_data.get("quantity", 0)

        direction = "LONG" if "LONG" in action.upper() else "SHORT"
        emoji = "\U0001F7E2" if direction == "LONG" else "\U0001F534"  # Green/Red circle

        return (
            f"{emoji} <b>Trade Opened</b>\n"
            f"<code>{symbol}</code> {direction}\n"
            f"Entry: <b>${price:,.2f}</b>\n"
            f"Size: ${quantity:,.2f}"
        )

    def format_trade_exit(self, trade_data: Dict[str, Any]) -> str:
        """Format trade exit for Telegram"""
        symbol = trade_data.get("symbol", "???")
        action = trade_data.get("action", "CLOSE")
        price = trade_data.get("price", 0)
        pnl = trade_data.get("pnl", 0)
        pnl_pct = trade_data.get("pnl_pct", 0)
        reason = trade_data.get("reason", "manual")

        emoji = "\U00002705" if pnl >= 0 else "\U0000274C"  # Checkmark/X
        pnl_emoji = "\U0001F4B0" if pnl >= 0 else "\U0001F4B8"  # Money bag/Flying money

        return (
            f"{emoji} <b>Trade Closed</b>\n"
            f"<code>{symbol}</code> @ ${price:,.2f}\n"
            f"{pnl_emoji} P&L: <b>${pnl:+,.2f}</b> ({pnl_pct:+.2f}%)\n"
            f"Reason: {reason}"
        )

    def format_error(self, error_data: Dict[str, Any]) -> str:
        """Format error notification"""
        error_type = error_data.get("type", "Unknown")
        message = error_data.get("message", "No details")

        return (
            f"\U000026A0 <b>Bot Alert</b>\n"
            f"Type: {error_type}\n"
            f"<code>{message}</code>"
        )

    def format_daily_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format daily summary"""
        total_trades = summary_data.get("total_trades", 0)
        winning_trades = summary_data.get("winning_trades", 0)
        daily_pnl = summary_data.get("daily_pnl", 0)
        equity = summary_data.get("equity", 0)
        open_positions = summary_data.get("open_positions", 0)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        emoji = "\U0001F4C8" if daily_pnl >= 0 else "\U0001F4C9"  # Chart up/down

        return (
            f"\U0001F4CA <b>Daily Summary</b>\n"
            f"Trades: {total_trades} ({win_rate:.1f}% win)\n"
            f"{emoji} P&L: <b>${daily_pnl:+,.2f}</b>\n"
            f"Equity: ${equity:,.2f}\n"
            f"Open Positions: {open_positions}"
        )


class DiscordNotifier(BaseNotifier):
    """Discord webhook notification provider"""

    async def send(self, message: str, **kwargs) -> bool:
        """Send a Discord webhook message"""
        if not self.config.discord_enabled:
            return False

        if not self._rate_limit_check():
            logger.debug("Discord notification rate limited")
            return False

        try:
            session = await self._get_session()

            # Discord webhook payload
            payload = {
                "content": message,
                "username": "JJ-Bot",
            }

            # Support for embeds
            if "embed" in kwargs:
                payload["embeds"] = [kwargs["embed"]]
                payload.pop("content", None)

            async with session.post(
                self.config.discord_webhook_url,
                json=payload,
                timeout=10
            ) as resp:
                if resp.status in (200, 204):
                    logger.debug("Discord notification sent successfully")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Discord error {resp.status}: {error_text}")
                    return False

        except asyncio.TimeoutError:
            logger.error("Discord notification timed out")
            return False
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    def _create_embed(self, title: str, description: str, color: int, fields: List[Dict] = None) -> Dict:
        """Create Discord embed"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }
        if fields:
            embed["fields"] = fields
        return embed

    def format_trade_entry(self, trade_data: Dict[str, Any]) -> str:
        """Format trade entry for Discord (returns embed dict as string for send())"""
        symbol = trade_data.get("symbol", "???")
        action = trade_data.get("action", "OPEN")
        price = trade_data.get("price", 0)
        quantity = trade_data.get("quantity", 0)

        direction = "LONG" if "LONG" in action.upper() else "SHORT"
        color = 0x00FF00 if direction == "LONG" else 0xFF0000  # Green/Red

        return (
            f"**Trade Opened**\n"
            f"`{symbol}` {direction}\n"
            f"Entry: **${price:,.2f}**\n"
            f"Size: ${quantity:,.2f}"
        )

    def format_trade_exit(self, trade_data: Dict[str, Any]) -> str:
        """Format trade exit for Discord"""
        symbol = trade_data.get("symbol", "???")
        price = trade_data.get("price", 0)
        pnl = trade_data.get("pnl", 0)
        pnl_pct = trade_data.get("pnl_pct", 0)
        reason = trade_data.get("reason", "manual")

        emoji = ":white_check_mark:" if pnl >= 0 else ":x:"

        return (
            f"{emoji} **Trade Closed**\n"
            f"`{symbol}` @ ${price:,.2f}\n"
            f"P&L: **${pnl:+,.2f}** ({pnl_pct:+.2f}%)\n"
            f"Reason: {reason}"
        )

    def format_error(self, error_data: Dict[str, Any]) -> str:
        """Format error notification"""
        error_type = error_data.get("type", "Unknown")
        message = error_data.get("message", "No details")

        return f":warning: **Bot Alert**\nType: {error_type}\n```{message}```"

    def format_daily_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format daily summary"""
        total_trades = summary_data.get("total_trades", 0)
        winning_trades = summary_data.get("winning_trades", 0)
        daily_pnl = summary_data.get("daily_pnl", 0)
        equity = summary_data.get("equity", 0)
        open_positions = summary_data.get("open_positions", 0)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        emoji = ":chart_with_upwards_trend:" if daily_pnl >= 0 else ":chart_with_downwards_trend:"

        return (
            f":bar_chart: **Daily Summary**\n"
            f"Trades: {total_trades} ({win_rate:.1f}% win)\n"
            f"{emoji} P&L: **${daily_pnl:+,.2f}**\n"
            f"Equity: ${equity:,.2f}\n"
            f"Open Positions: {open_positions}"
        )


class WebhookNotifier(BaseNotifier):
    """Generic webhook notification provider"""

    async def send(self, message: str, **kwargs) -> bool:
        """Send a generic webhook notification"""
        if not self.config.webhook_enabled:
            return False

        if not self._rate_limit_check():
            logger.debug("Webhook notification rate limited")
            return False

        try:
            session = await self._get_session()

            payload = {
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "jj-bot",
                **kwargs
            }

            headers = {"Content-Type": "application/json"}
            headers.update(self.config.webhook_headers)

            async with session.post(
                self.config.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            ) as resp:
                if resp.status in (200, 201, 204):
                    logger.debug("Webhook notification sent successfully")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Webhook error {resp.status}: {error_text}")
                    return False

        except asyncio.TimeoutError:
            logger.error("Webhook notification timed out")
            return False
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    def format_trade_entry(self, trade_data: Dict[str, Any]) -> str:
        """Format trade entry (simple text)"""
        symbol = trade_data.get("symbol", "???")
        action = trade_data.get("action", "OPEN")
        price = trade_data.get("price", 0)
        return f"Trade Opened: {symbol} {action} @ ${price:,.2f}"

    def format_trade_exit(self, trade_data: Dict[str, Any]) -> str:
        """Format trade exit (simple text)"""
        symbol = trade_data.get("symbol", "???")
        price = trade_data.get("price", 0)
        pnl = trade_data.get("pnl", 0)
        return f"Trade Closed: {symbol} @ ${price:,.2f}, P&L: ${pnl:+,.2f}"

    def format_error(self, error_data: Dict[str, Any]) -> str:
        """Format error"""
        return f"Bot Error: {error_data.get('type', 'Unknown')} - {error_data.get('message', '')}"

    def format_daily_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format daily summary"""
        return f"Daily P&L: ${summary_data.get('daily_pnl', 0):+,.2f}, Equity: ${summary_data.get('equity', 0):,.2f}"


class NotificationManager:
    """
    Manages multiple notification providers
    Usage:
        notifier = NotificationManager(config)
        await notifier.notify_trade_entry(trade_data)
        await notifier.notify_trade_exit(trade_data)
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._notifiers: List[BaseNotifier] = []
        self._setup_notifiers()

    def _setup_notifiers(self):
        """Initialize enabled notifiers"""
        if self.config.telegram_enabled:
            self._notifiers.append(TelegramNotifier(self.config))
            logger.info("Telegram notifications enabled")

        if self.config.discord_enabled:
            self._notifiers.append(DiscordNotifier(self.config))
            logger.info("Discord notifications enabled")

        if self.config.webhook_enabled:
            self._notifiers.append(WebhookNotifier(self.config))
            logger.info("Webhook notifications enabled")

        if not self._notifiers:
            logger.info("No notification providers configured")

    @property
    def is_enabled(self) -> bool:
        """Check if any notifier is enabled"""
        return len(self._notifiers) > 0

    async def close(self):
        """Close all notifier sessions"""
        for notifier in self._notifiers:
            await notifier.close()

    async def _send_to_all(self, messages: List[str]) -> int:
        """Send message to all providers, return success count"""
        if not messages or not self._notifiers:
            return 0

        success_count = 0
        for notifier, message in zip(self._notifiers, messages):
            if await notifier.send(message):
                success_count += 1
        return success_count

    async def notify_trade_entry(self, trade_data: Dict[str, Any]) -> bool:
        """Notify about trade entry"""
        if not self.config.notify_on_entry:
            return False

        messages = [n.format_trade_entry(trade_data) for n in self._notifiers]
        results = await asyncio.gather(
            *[n.send(msg) for n, msg in zip(self._notifiers, messages)],
            return_exceptions=True
        )
        return any(r is True for r in results)

    async def notify_trade_exit(self, trade_data: Dict[str, Any]) -> bool:
        """Notify about trade exit"""
        if not self.config.notify_on_exit:
            return False

        # Always notify on stop loss regardless of setting
        is_stop_loss = trade_data.get("reason", "").lower() in ("stop_loss", "stop_loss_exchange")
        if is_stop_loss and not self.config.notify_on_stop_loss:
            return False

        messages = [n.format_trade_exit(trade_data) for n in self._notifiers]
        results = await asyncio.gather(
            *[n.send(msg) for n, msg in zip(self._notifiers, messages)],
            return_exceptions=True
        )
        return any(r is True for r in results)

    async def notify_error(self, error_type: str, message: str) -> bool:
        """Notify about an error"""
        if not self.config.notify_on_error:
            return False

        error_data = {"type": error_type, "message": message}
        messages = [n.format_error(error_data) for n in self._notifiers]
        results = await asyncio.gather(
            *[n.send(msg) for n, msg in zip(self._notifiers, messages)],
            return_exceptions=True
        )
        return any(r is True for r in results)

    async def notify_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Send daily summary"""
        if not self.config.notify_on_daily_summary:
            return False

        messages = [n.format_daily_summary(summary_data) for n in self._notifiers]
        results = await asyncio.gather(
            *[n.send(msg) for n, msg in zip(self._notifiers, messages)],
            return_exceptions=True
        )
        return any(r is True for r in results)

    async def send_raw(self, message: str) -> bool:
        """Send a raw message to all providers"""
        results = await asyncio.gather(
            *[n.send(message) for n in self._notifiers],
            return_exceptions=True
        )
        return any(r is True for r in results)


def create_notifier(config: Optional[NotificationConfig] = None) -> NotificationManager:
    """Factory function to create notification manager"""
    return NotificationManager(config)
