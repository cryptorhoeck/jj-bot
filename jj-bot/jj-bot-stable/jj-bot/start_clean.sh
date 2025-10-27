#!/bin/bash
cd ~/jj-bot
source .venv/bin/activate

echo "Starting JJ Bot System..."

# Start API
echo "🚀 Starting API..."
nohup python3 -m uvicorn glue.api.main:app --host 127.0.0.1 --port 8000 --reload > logs/api.log 2>&1 &
sleep 5

# Test API
echo "Testing API..."
curl -s http://127.0.0.1:8000/ > /dev/null && echo "✅ API running" || echo "❌ API not responding"

# Start Dashboard
echo "🎨 Starting Dashboard..."
cd dashboard/jj-dashboard
npm install --silent
npm run dev > ../../logs/dashboard.log 2>&1 &

echo ""
echo "✅ System started!"
echo "Dashboard: http://localhost:5173"
echo "API: http://127.0.0.1:8000"
echo ""
echo "Logs:"
echo "  tail -f ~/jj-bot/logs/api.log"
echo "  tail -f ~/jj-bot/logs/dashboard.log"
