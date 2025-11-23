#!/bin/bash
# JJ-Bot Pro - Stop all services

cd "$(dirname "$0")"

# Stop API server
if [ -f logs/api.pid ]; then
    kill $(cat logs/api.pid) 2>/dev/null
    rm logs/api.pid
    echo "API server stopped"
fi

# Stop dashboard
if [ -f logs/dashboard.pid ]; then
    kill $(cat logs/dashboard.pid) 2>/dev/null
    rm logs/dashboard.pid
    echo "Dashboard stopped"
fi

# Also kill any remaining processes
pkill -f "glue/api/main.py" 2>/dev/null
pkill -f "jj-dashboard" 2>/dev/null

echo "JJ-Bot stopped"
