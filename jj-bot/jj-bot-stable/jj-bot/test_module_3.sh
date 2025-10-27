#!/bin/bash
# Test Risk Manager Module

cd ~/jj-bot
source .venv/bin/activate

echo "Testing Risk Manager Module..."
echo ""

cd modules
python3 test_risk.py
