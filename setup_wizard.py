#!/usr/bin/env python3
"""
JJ-Bot Pro Setup Wizard
Interactive setup for first-time users
"""

import os
import sys
import json
import getpass
from pathlib import Path


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print the welcome banner"""
    clear_screen()
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║       ██╗██╗      ██████╗  ██████╗ ████████╗                    ║
║       ██║██║      ██╔══██╗██╔═══██╗╚══██╔══╝                    ║
║       ██║██║█████╗██████╔╝██║   ██║   ██║                       ║
║  ██   ██║██║╚════╝██╔══██╗██║   ██║   ██║                       ║
║  ╚█████╔╝██║      ██████╔╝╚██████╔╝   ██║                       ║
║   ╚════╝ ╚═╝      ╚═════╝  ╚═════╝    ╚═╝                       ║
║                                                                  ║
║                 PRO - Autonomous Trading System                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def get_input(prompt, default=None, secret=False, validator=None):
    """Get validated input from user"""
    while True:
        if default is not None:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "

        if secret:
            value = getpass.getpass(display_prompt)
        else:
            value = input(display_prompt)

        if not value and default is not None:
            value = default

        if validator:
            error = validator(value)
            if error:
                print(f"  Error: {error}")
                continue

        return value


def validate_float(min_val=None, max_val=None):
    """Create float validator"""
    def validator(value):
        try:
            f = float(value)
            if min_val is not None and f < min_val:
                return f"Must be at least {min_val}"
            if max_val is not None and f > max_val:
                return f"Must be at most {max_val}"
            return None
        except ValueError:
            return "Must be a number"
    return validator


def validate_int(min_val=None, max_val=None):
    """Create int validator"""
    def validator(value):
        try:
            i = int(value)
            if min_val is not None and i < min_val:
                return f"Must be at least {min_val}"
            if max_val is not None and i > max_val:
                return f"Must be at most {max_val}"
            return None
        except ValueError:
            return "Must be a whole number"
    return validator


def validate_choice(choices):
    """Create choice validator"""
    def validator(value):
        if value.lower() not in [c.lower() for c in choices]:
            return f"Must be one of: {', '.join(choices)}"
        return None
    return validator


def run_wizard():
    """Run the interactive setup wizard"""
    print_banner()
    print("\nWelcome to JJ-Bot Pro Setup!")
    print("This wizard will help you configure your autonomous trading bot.\n")
    print("Press Enter to accept [default] values.\n")
    input("Press Enter to continue...")

    config = {}

    # Step 1: Trading Mode
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("STEP 1: Trading Mode")
    print("=" * 50)
    print("""
Choose how you want to run the bot:

  paper    - Paper trading with REAL prices (recommended for testing)
  live     - Real money trading (requires API keys)
  training - Train the AI model on historical data
    """)

    mode = get_input(
        "Trading mode",
        default="paper",
        validator=validate_choice(["paper", "live", "training"])
    ).lower()
    config["mode"] = mode

    # Step 2: Exchange Selection
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("STEP 2: Exchange Selection")
    print("=" * 50)
    print("""
Select your exchange:

  binance   - Binance (most popular, best liquidity)
  coinbase  - Coinbase Pro
  kraken    - Kraken
  kucoin    - KuCoin
  bybit     - Bybit
    """)

    exchange = get_input(
        "Exchange",
        default="binance",
        validator=validate_choice(["binance", "coinbase", "kraken", "kucoin", "bybit"])
    ).lower()
    config["exchange"] = exchange

    # Step 3: API Keys (if needed)
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("STEP 3: API Configuration")
    print("=" * 50)

    if mode == "paper":
        print("""
For paper trading, API keys are optional but recommended
for accessing real-time price data.

You can skip this step and the bot will use public APIs.
        """)
        setup_api = get_input("Setup API keys? (y/n)", default="n").lower() == "y"
    else:
        print("""
Live trading requires API keys from your exchange.

IMPORTANT:
- Only provide API keys with TRADE permission
- NEVER use keys with withdrawal permission
- Keep your keys secure - they will be stored locally
        """)
        setup_api = True

    if setup_api:
        api_key = get_input("API Key", secret=False)
        api_secret = get_input("API Secret", secret=True)
        config["api_key"] = api_key
        config["api_secret"] = api_secret
    else:
        config["api_key"] = ""
        config["api_secret"] = ""

    # Always use sandbox for safety unless explicitly live
    config["sandbox"] = mode != "live"

    # Step 4: Trading Symbols
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("STEP 4: Trading Symbols")
    print("=" * 50)
    print("""
Select which cryptocurrencies to trade.
Enter comma-separated pairs (e.g., BTC/USDT,ETH/USDT)

Popular pairs: BTC/USDT, ETH/USDT, SOL/USDT, DOGE/USDT
    """)

    symbols_str = get_input("Trading pairs", default="BTC/USDT,ETH/USDT")
    symbols = [s.strip().upper() for s in symbols_str.split(",")]
    config["symbols"] = symbols

    # Step 5: Capital & Risk
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("STEP 5: Capital & Risk Management")
    print("=" * 50)
    print("""
Configure your capital and risk parameters.
These settings protect your account from large losses.
    """)

    initial_capital = float(get_input(
        "Initial capital (USD)",
        default="10000",
        validator=validate_float(100, 10000000)
    ))
    config["initial_capital"] = initial_capital

    print("\nPosition sizing (% of capital per trade):")
    max_position = float(get_input(
        "Max position size (%)",
        default="10",
        validator=validate_float(1, 50)
    )) / 100
    config["max_position_pct"] = max_position

    max_positions = int(get_input(
        "Max simultaneous positions",
        default="3",
        validator=validate_int(1, 10)
    ))
    config["max_positions"] = max_positions

    print("\nRisk limits:")
    stop_loss = float(get_input(
        "Stop loss (%)",
        default="2",
        validator=validate_float(0.5, 20)
    )) / 100
    config["stop_loss_pct"] = stop_loss

    take_profit = float(get_input(
        "Take profit (%)",
        default="4",
        validator=validate_float(1, 50)
    )) / 100
    config["take_profit_pct"] = take_profit

    max_daily_loss = float(get_input(
        "Max daily loss (%)",
        default="5",
        validator=validate_float(1, 25)
    )) / 100
    config["max_daily_loss_pct"] = max_daily_loss

    max_drawdown = float(get_input(
        "Max drawdown (%)",
        default="10",
        validator=validate_float(5, 50)
    )) / 100
    config["max_drawdown_pct"] = max_drawdown

    # Step 6: AI & Strategy
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("STEP 6: AI & Strategy Configuration")
    print("=" * 50)
    print("""
Configure the AI trading components.
All features are enabled by default for best performance.
    """)

    use_rl = get_input(
        "Enable AI agent (reinforcement learning)?",
        default="y",
        validator=validate_choice(["y", "n"])
    ).lower() == "y"
    config["use_rl_agent"] = use_rl

    use_edge = get_input(
        "Enable edge strategies (funding, sentiment)?",
        default="y",
        validator=validate_choice(["y", "n"])
    ).lower() == "y"
    config["use_edge_strategies"] = use_edge

    use_alt = get_input(
        "Enable alternative data (fear/greed, on-chain)?",
        default="y",
        validator=validate_choice(["y", "n"])
    ).lower() == "y"
    config["use_alternative_data"] = use_alt

    min_confidence = float(get_input(
        "Minimum signal confidence to trade (%)",
        default="60",
        validator=validate_float(30, 95)
    )) / 100
    config["min_signal_confidence"] = min_confidence

    # Step 7: Additional Settings
    config["rl_model_path"] = "models/ppo_agent.pt"
    config["train_episodes"] = 100
    config["analysis_interval_seconds"] = 60
    config["log_level"] = "INFO"
    config["log_trades"] = True

    # Summary & Save
    clear_screen()
    print_banner()
    print("\n" + "=" * 50)
    print("CONFIGURATION SUMMARY")
    print("=" * 50)
    print(f"""
Mode:               {config['mode'].upper()}
Exchange:           {config['exchange'].capitalize()}
API Keys:           {'Configured' if config['api_key'] else 'Not set'}
Trading Pairs:      {', '.join(config['symbols'])}
Initial Capital:    ${config['initial_capital']:,.2f}

Position Settings:
  - Max per trade:  {config['max_position_pct']*100:.0f}%
  - Max positions:  {config['max_positions']}

Risk Settings:
  - Stop Loss:      {config['stop_loss_pct']*100:.1f}%
  - Take Profit:    {config['take_profit_pct']*100:.1f}%
  - Daily Loss Max: {config['max_daily_loss_pct']*100:.1f}%
  - Max Drawdown:   {config['max_drawdown_pct']*100:.1f}%

AI Features:
  - RL Agent:       {'Enabled' if config['use_rl_agent'] else 'Disabled'}
  - Edge Strategies:{'Enabled' if config['use_edge_strategies'] else 'Disabled'}
  - Alt Data:       {'Enabled' if config['use_alternative_data'] else 'Disabled'}
  - Min Confidence: {config['min_signal_confidence']*100:.0f}%
    """)

    save = get_input(
        "\nSave this configuration?",
        default="y",
        validator=validate_choice(["y", "n"])
    ).lower() == "y"

    if save:
        # Create directories
        os.makedirs("config", exist_ok=True)
        os.makedirs("models", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

        # Save config
        config_path = "config/bot_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        print(f"\n Configuration saved to {config_path}")
        print("""
┌──────────────────────────────────────────────────────────────────┐
│                     SETUP COMPLETE!                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  To start the bot, run one of these commands:                   │
│                                                                  │
│  Windows:    start_bot.bat                                       │
│  Linux/Mac:  ./start_bot.sh                                      │
│  Python:     python jjbot_pro.py                                 │
│                                                                  │
│  To train the AI first:                                         │
│  python jjbot_pro.py --train                                     │
│                                                                  │
│  To view the dashboard:                                          │
│  cd dashboard/jj-dashboard && npm run dev                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
        """)
    else:
        print("\n Configuration not saved. Run setup_wizard.py again to configure.")

    return config


def quick_setup(mode="paper", exchange="binance"):
    """Quick setup with defaults"""
    config = {
        "mode": mode,
        "exchange": exchange,
        "api_key": "",
        "api_secret": "",
        "sandbox": True,
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "initial_capital": 10000.0,
        "max_position_pct": 0.10,
        "max_positions": 3,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "max_daily_loss_pct": 0.05,
        "max_drawdown_pct": 0.10,
        "use_rl_agent": True,
        "use_edge_strategies": True,
        "use_alternative_data": True,
        "min_signal_confidence": 0.6,
        "rl_model_path": "models/ppo_agent.pt",
        "train_episodes": 100,
        "analysis_interval_seconds": 60,
        "log_level": "INFO",
        "log_trades": True,
    }

    os.makedirs("config", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    with open("config/bot_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("Quick setup complete! Config saved to config/bot_config.json")
    return config


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_setup()
    else:
        run_wizard()
