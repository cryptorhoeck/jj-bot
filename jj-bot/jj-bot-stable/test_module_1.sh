#!/bin/bash
# Test Data Feed Module Independently

cd ~/jj-bot
source .venv/bin/activate

echo "Testing Data Feed Module..."
echo "This runs completely separately from your main system"
echo ""

cd modules
python3 test_data_feed.py
