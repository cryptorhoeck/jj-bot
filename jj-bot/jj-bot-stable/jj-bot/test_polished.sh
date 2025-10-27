#!/bin/bash
cd ~/jj-bot
source .venv/bin/activate
echo "🚀 Starting Polished Trading System"
echo "Tracking Top 20 Cryptocurrencies"
echo ""
cd modules
python3 polished_system.py
