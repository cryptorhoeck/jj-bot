#!/bin/bash

echo "🔍 JJ Bot System Status"
echo "======================="
echo ""

# Check API
echo -n "API Status: "
curl -s http://127.0.0.1:8000/ > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"

# Check Dashboard
echo -n "Dashboard Status: "
curl -s http://localhost:5173/ > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"

# Check processes
echo ""
echo "Running Processes:"
ps aux | grep -E "uvicorn|npm" | grep -v grep | wc -l | xargs -I {} echo "  {} processes found"

# Backup info
echo ""
echo "Backup Information:"
echo "  Foundation: ~/jj-bot-backups/jj-bot-foundation-*"
echo "  Total backups: $(ls -1 ~/jj-bot-backups/*.tar.gz 2>/dev/null | wc -l)"
echo "  Latest backup: $(ls -t ~/jj-bot-backups/*.tar.gz 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo 'None')"

# Changelog
echo ""
echo "Latest Changelog Entry:"
tail -n 5 ~/jj-bot/CHANGELOG.md | grep -v "^$" | head -3
