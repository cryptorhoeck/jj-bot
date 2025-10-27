#!/bin/bash
cd ~/jj-bot
source .venv/bin/activate
echo "🚀 Starting WORKING Trading System"
echo "This version bypasses event bus issues"
echo ""
cd modules
python3 working_system.py
