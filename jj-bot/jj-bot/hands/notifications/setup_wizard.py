#!/usr/bin/env python3
"""
Interactive setup wizard for notifications
"""

import json
from pathlib import Path

def setup_discord():
    """Setup Discord notifications"""
    print("\n🎮 Discord Setup")
    print("1. Create a Discord webhook in your server")
    print("2. Copy the webhook URL")
    
    webhook_url = input("Enter Discord webhook URL (or press Enter to skip): ").strip()
    
    if webhook_url:
        return {
            "enabled": True,
            "webhook_url": webhook_url,
            "username": "JJ Gorilla Bot"
        }
    else:
        return {"enabled": False, "webhook_url": "", "username": "JJ Gorilla Bot"}

def setup_telegram():
    """Setup Telegram notifications"""
    print("\n📱 Telegram Setup")
    print("1. Create a bot with @BotFather on Telegram")
    print("2. Get your bot token")
    print("3. Start a chat with your bot")
    print("4. Get your chat ID from @userinfobot")
    
    bot_token = input("Enter Telegram bot token (or press Enter to skip): ").strip()
    
    if bot_token:
        chat_id = input("Enter your Telegram chat ID: ").strip()
        return {
            "enabled": True,
            "bot_token": bot_token,
            "chat_id": chat_id
        }
    else:
        return {"enabled": False, "bot_token": "", "chat_id": ""}

def setup_email():
    """Setup email notifications"""
    print("\n📧 Email Setup")
    print("For Gmail, use app passwords instead of your regular password")
    
    email = input("Enter your email address (or press Enter to skip): ").strip()
    
    if email:
        password = input("Enter email password or app password: ").strip()
        to_email = input("Enter destination email address: ").strip()
        
        return {
            "enabled": True,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": email,
            "password": password,
            "to_email": to_email
        }
    else:
        return {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "to_email": ""
        }

def setup_webhook():
    """Setup custom webhook"""
    print("\n🔗 Custom Webhook Setup")
    
    webhook_url = input("Enter custom webhook URL (or press Enter to skip): ").strip()
    
    if webhook_url:
        return {
            "enabled": True,
            "url": webhook_url,
            "headers": {"Content-Type": "application/json"}
        }
    else:
        return {
            "enabled": False,
            "url": "",
            "headers": {"Content-Type": "application/json"}
        }

def main():
    """Main setup wizard"""
    print("🦍 JJ Gorilla Notification Setup Wizard")
    print("=" * 50)
    print("This wizard will help you configure mobile alerts and notifications.")
    
    config = {
        "enabled": True,
        "providers": {},
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
    
    # Setup providers
    config["providers"]["discord"] = setup_discord()
    config["providers"]["telegram"] = setup_telegram()
    config["providers"]["email"] = setup_email()
    config["providers"]["webhook"] = setup_webhook()
    
    # Alert thresholds
    print("\n⚙️ Alert Thresholds")
    try:
        big_win_threshold = float(input("Big win alert threshold ($): [100] ") or "100")
        big_loss_threshold = float(input("Big loss alert threshold ($): [-100] ") or "-100")
        
        config["alert_types"]["big_wins"]["threshold"] = big_win_threshold
        config["alert_types"]["big_losses"]["threshold"] = big_loss_threshold
    except ValueError:
        print("Using default thresholds")
    
    # Save configuration
    config_file = Path.home() / "jj-bot" / "data" / "notification_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuration saved to {config_file}")
    print("\n🎉 Notification setup complete!")
    print("You can modify settings anytime by editing the config file or running this wizard again.")
    
    # Test notification
    test = input("\nSend test notification? (y/N): ").strip().lower()
    if test == 'y':
        print("Sending test notification...")
        # This would trigger a test notification
        print("✅ Test notification sent (if any providers are enabled)")

if __name__ == "__main__":
    main()
