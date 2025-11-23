#!/bin/bash
# JJ-Bot Pro - Silent Startup
# Runs everything in background, opens dashboard in browser

cd "$(dirname "$0")"

# Create required directories
mkdir -p logs models config

# Start API server in background
nohup python3 glue/api/main.py > logs/api.log 2>&1 &
echo $! > logs/api.pid

# Wait for API to start
sleep 3

# Start dashboard dev server in background
cd dashboard/jj-dashboard
nohup npm run dev > ../../logs/dashboard.log 2>&1 &
echo $! > ../../logs/dashboard.pid
cd ../..

# Open dashboard in browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
elif command -v open &> /dev/null; then
    open http://localhost:5173
fi

echo "JJ-Bot started. Dashboard opening in browser..."
echo "To stop: ./stop_bot.sh"
