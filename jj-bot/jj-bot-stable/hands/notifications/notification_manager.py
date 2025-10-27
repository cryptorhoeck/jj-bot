import asyncio
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    """Central notification system for trading alerts"""
    
    def __init__(self):
        self.config_file = Path.home() / "jj-bot" / "data" / "notification_config.json"
        self.config = self.load_config()
        self.alert_history = []
        
    def load_config(self):
        """Load notification configuration"""
        default_config = {
            "enabled": True,
            "providers": {
                "discord": {
                    "enabled": False,
                    "webhook_url": "",
                    "username": "JJ Gorilla Bot"
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": ""
                },
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_email": ""
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "headers": {"Content-Type": "application/json"}
                }
            },
            "alert_types": {
                "big_wins": {"enabled": True, "threshold": 100.0},
                "big_losses": {"enabled": True, "threshold": -100.0},
                "daily_summary": {"enabled": True, "time": "18:00"},
                "risk_warnings": {"enabled": True},
                "system_errors": {"enabled": True},
                "strategy_signals": {"enabled": False, "min_confidence": 0.8}
            },
            "rate_limiting": {
                "max_alerts_per_hour": 10,
                "cooldown_minutes": 5
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return default_config
        else:
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Save notification configuration"""
        if config:
            self.config = config
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    async def send_alert(self, alert_type: str, message: str, data: Dict = None):
        """Send alert through configured providers"""
        if not self.config["enabled"]:
            return
        
        # Check rate limiting
        if not self._check_rate_limit():
            logger.warning("Alert rate limit exceeded")
            return
        
        # Check if alert type is enabled
        if alert_type not in self.config["alert_types"] or not self.config["alert_types"][alert_type]["enabled"]:
            return
        
        # Format message
        formatted_message = self._format_message(alert_type, message, data)
        
        # Send through all enabled providers
        providers = self.config["providers"]
        
        tasks = []
        if providers["discord"]["enabled"]:
            tasks.append(self._send_discord(formatted_message))
        if providers["telegram"]["enabled"]:
            tasks.append(self._send_telegram(formatted_message))
        if providers["email"]["enabled"]:
            tasks.append(self._send_email(alert_type, formatted_message))
        if providers["webhook"]["enabled"]:
            tasks.append(self._send_webhook(alert_type, formatted_message, data))
        
        # Execute all notifications concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log alert
        self._log_alert(alert_type, message, data)
    
    def _format_message(self, alert_type: str, message: str, data: Dict = None) -> str:
        """Format message with emojis and context"""
        emoji_map = {
            "big_wins": "🎉",
            "big_losses": "⚠️",
            "daily_summary": "📊",
            "risk_warnings": "🚨",
            "system_errors": "❌",
            "strategy_signals": "🧠"
        }
        
        emoji = emoji_map.get(alert_type, "📢")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted = f"{emoji} **JJ Gorilla Alert** ({timestamp})\n\n{message}"
        
        if data:
            if "pnl" in data:
                formatted += f"\n💰 P&L: ${data['pnl']:+.2f}"
            if "symbol" in data:
                formatted += f"\n📈 Symbol: {data['symbol']}"
            if "confidence" in data:
                formatted += f"\n🎯 Confidence: {data['confidence']:.1%}"
        
        return formatted
    
    async def _send_discord(self, message: str):
        """Send alert to Discord"""
        try:
            webhook_url = self.config["providers"]["discord"]["webhook_url"]
            username = self.config["providers"]["discord"]["username"]
            
            payload = {
                "content": message,
                "username": username
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Discord alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
    
    async def _send_telegram(self, message: str):
        """Send alert to Telegram"""
        try:
            bot_token = self.config["providers"]["telegram"]["bot_token"]
            chat_id = self.config["providers"]["telegram"]["chat_id"]
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    async def _send_email(self, subject: str, message: str):
        """Send alert via email"""
        try:
            config = self.config["providers"]["email"]
            
            msg = MIMEMultipart()
            msg['From'] = config["username"]
            msg['To'] = config["to_email"]
            msg['Subject'] = f"JJ Gorilla Alert: {subject}"
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            server.starttls()
            server.login(config["username"], config["password"])
            text = msg.as_string()
            server.sendmail(config["username"], config["to_email"], text)
            server.quit()
            
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def _send_webhook(self, alert_type: str, message: str, data: Dict = None):
        """Send alert to custom webhook"""
        try:
            config = self.config["providers"]["webhook"]
            
            payload = {
                "alert_type": alert_type,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                config["url"], 
                json=payload, 
                headers=config["headers"],
                timeout=10
            )
            response.raise_for_status()
            logger.info("Webhook alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Count alerts in the last hour
        recent_alerts = [
            alert for alert in self.alert_history
            if alert["timestamp"] > hour_ago
        ]
        
        max_alerts = self.config["rate_limiting"]["max_alerts_per_hour"]
        return len(recent_alerts) < max_alerts
    
    def _log_alert(self, alert_type: str, message: str, data: Dict = None):
        """Log alert to history"""
        alert_record = {
            "timestamp": datetime.now(),
            "type": alert_type,
            "message": message,
            "data": data
        }
        
        self.alert_history.append(alert_record)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """Get recent alert history"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            {
                "timestamp": alert["timestamp"].isoformat(),
                "type": alert["type"],
                "message": alert["message"]
            }
            for alert in self.alert_history
            if alert["timestamp"] > cutoff
        ]

class AlertTriggers:
    """Automatic alert triggers based on trading events"""
    
    def __init__(self, notification_manager: NotificationManager):
        self.notifier = notification_manager
        self.last_daily_summary = None
        
    async def check_trade_alerts(self, trade: Dict):
        """Check if trade triggers any alerts"""
        pnl = trade.get("pnl", 0)
        symbol = trade.get("symbol", "")
        
        # Big win alert
        win_threshold = self.notifier.config["alert_types"]["big_wins"]["threshold"]
        if pnl >= win_threshold:
            message = f"🎉 Big Win Alert!\n\nSymbol: {symbol}\nP&L: ${pnl:+.2f}"
            await self.notifier.send_alert("big_wins", message, trade)
        
        # Big loss alert
        loss_threshold = self.notifier.config["alert_types"]["big_losses"]["threshold"]
        if pnl <= loss_threshold:
            message = f"⚠️ Big Loss Alert!\n\nSymbol: {symbol}\nP&L: ${pnl:+.2f}"
            await self.notifier.send_alert("big_losses", message, trade)
    
    async def check_risk_alerts(self, risk_assessment: Dict):
        """Check if risk metrics trigger alerts"""
        risk_level = risk_assessment.get("risk_level", "UNKNOWN")
        warnings = risk_assessment.get("warnings", [])
        
        if risk_level in ["HIGH", "EXTREME"] and warnings:
            message = f"🚨 Risk Warning!\n\nRisk Level: {risk_level}\nWarnings:\n"
            for warning in warnings[:3]:  # Limit to 3 warnings
                message += f"• {warning}\n"
            
            await self.notifier.send_alert("risk_warnings", message, risk_assessment)
    
    async def check_strategy_alerts(self, analysis: Dict):
        """Check if strategy signals trigger alerts"""
        signal = analysis.get("consensus_signal", "HOLD")
        confidence = analysis.get("consensus_confidence", 0)
        min_confidence = self.notifier.config["alert_types"]["strategy_signals"]["min_confidence"]
        
        if signal != "HOLD" and confidence >= min_confidence:
            message = f"🧠 Strong Strategy Signal!\n\nSignal: {signal}\nConfidence: {confidence:.1%}\n\n{analysis.get('recommendation', '')}"
            await self.notifier.send_alert("strategy_signals", message, analysis)
    
    async def send_daily_summary(self, summary_data: Dict):
        """Send daily trading summary"""
        message = f"""📊 Daily Trading Summary

💰 Total P&L: ${summary_data.get('total_pnl', 0):+.2f}
📈 Total Trades: {summary_data.get('total_trades', 0)}
🎯 Win Rate: {summary_data.get('win_rate', 0):.1f}%
📊 Best Trade: ${summary_data.get('best_trade', 0):+.2f}
📉 Worst Trade: ${summary_data.get('worst_trade', 0):+.2f}

Keep grinding! 🦍
"""
        await self.notifier.send_alert("daily_summary", message, summary_data)

# Global notification manager
notification_manager = NotificationManager()
alert_triggers = AlertTriggers(notification_manager)
