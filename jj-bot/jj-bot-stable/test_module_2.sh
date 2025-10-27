#!/bin/bash
# Test Strategy Engine with Data Feed

cd ~/jj-bot
source .venv/bin/activate

echo "Testing Strategy Engine..."
echo "This will run BOTH modules together:"
echo "  • Data Feed (Module 1) - Gets prices"
echo "  • Strategy Engine (Module 2) - Generates signals"
echo ""

cd modules
python3 test_strategy.py
