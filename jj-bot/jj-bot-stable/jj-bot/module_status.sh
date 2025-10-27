#!/bin/bash
# Check status of all modules

cd ~/jj-bot

echo "MODULE STATUS CHECK"
echo "=================="
echo ""
echo "Existing System:"
ps aux | grep -E "main.py|npm" | grep -v grep && echo "✅ Running" || echo "❌ Not running"
echo ""
echo "Module System:"
ls -la modules/ 2>/dev/null | grep -E "data_feed|strategy|risk" || echo "No modules yet"
