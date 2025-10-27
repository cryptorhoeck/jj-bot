#!/bin/bash
# Test Complete Integration

cd ~/jj-bot
source .venv/bin/activate

echo "🔗 Testing Complete Integration"
echo "This runs all 3 modules together:"
echo "  • Data Feed → Strategy → Risk Manager"
echo ""

cd modules
python3 orchestrator.py
