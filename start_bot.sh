#!/bin/bash
# JJ-Bot Pro - Linux/Mac Startup Script
# ======================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "  =========================================="
    echo "   JJ-Bot Pro - Autonomous Trading System"
    echo "  =========================================="
    echo -e "${NC}"
}

print_banner

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed${NC}"
    echo "Please install Python 3.9+ using your package manager"
    exit 1
fi

PYTHON=python3

# Check Python version
PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Python version: ${GREEN}$PY_VERSION${NC}"

# Change to script directory
cd "$(dirname "$0")"

# Check if config exists
if [ ! -f "config/bot_config.json" ]; then
    echo -e "${YELLOW}Configuration not found. Running setup wizard...${NC}"
    echo ""
    $PYTHON setup_wizard.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}Setup failed. Please check errors above.${NC}"
        exit 1
    fi
fi

# Create required directories
mkdir -p logs models

# Handle command line arguments
case "$1" in
    --setup)
        $PYTHON setup_wizard.py
        exit 0
        ;;
    --quick-setup)
        $PYTHON setup_wizard.py --quick
        exit 0
        ;;
    --train)
        echo -e "${YELLOW}Starting AI Training Mode...${NC}"
        $PYTHON -c "
from jjbot_pro import BotConfig, JJBotPro
c = BotConfig.load()
c.mode = 'training'
bot = JJBotPro(c)
bot.run()
"
        exit 0
        ;;
    --dashboard)
        echo -e "${YELLOW}Starting Dashboard...${NC}"
        cd dashboard/jj-dashboard
        npm run dev
        exit 0
        ;;
    --status)
        # Show bot status from API if running
        curl -s http://localhost:5000/api/bot/status 2>/dev/null || echo "Bot API not running"
        exit 0
        ;;
    --help)
        echo ""
        echo "Usage: ./start_bot.sh [option]"
        echo ""
        echo "Options:"
        echo "  (none)        Start the trading bot"
        echo "  --setup       Run the interactive setup wizard"
        echo "  --quick-setup Quick setup with defaults"
        echo "  --train       Run AI training mode"
        echo "  --dashboard   Start the web dashboard"
        echo "  --status      Check bot status"
        echo "  --help        Show this help message"
        echo ""
        exit 0
        ;;
esac

# Display current configuration
echo ""
echo "Current Configuration:"
echo "----------------------"
$PYTHON -c "
import json
try:
    c = json.load(open('config/bot_config.json'))
    print(f\"  Mode: {c['mode'].upper()}\")
    print(f\"  Exchange: {c['exchange'].capitalize()}\")
    print(f\"  Symbols: {', '.join(c['symbols'])}\")
    print(f\"  Capital: \${c['initial_capital']:,.2f}\")
except Exception as e:
    print(f'  Error reading config: {e}')
"

# Warning for live mode
MODE=$($PYTHON -c "import json; print(json.load(open('config/bot_config.json'))['mode'])" 2>/dev/null)
if [ "$MODE" == "live" ]; then
    echo ""
    echo -e "${RED}WARNING: Bot is configured for LIVE trading!${NC}"
    echo -e "${RED}Real money will be at risk.${NC}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
else
    echo ""
    echo -e "Press Enter to start the bot... (Ctrl+C to cancel)"
    read
fi

echo ""
echo -e "${GREEN}Starting JJ-Bot Pro...${NC}"
echo ""
echo "=========================================="
echo "  Bot is running. Press Ctrl+C to stop."
echo "=========================================="
echo ""

# Handle shutdown gracefully
trap 'echo ""; echo "Shutting down..."; exit 0' SIGINT SIGTERM

# Run the bot
$PYTHON jjbot_pro.py

echo ""
echo "Bot stopped."
