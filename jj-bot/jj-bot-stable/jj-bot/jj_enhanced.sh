#!/bin/bash

# Enhanced JJ Command System
# Ensures virtual environment and proper execution

# Always activate venv first
cd ~/jj-bot
source .venv/bin/activate

# Function to check if API is really running
check_api() {
    if pgrep -f "uvicorn.*main:app.*8000" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if dashboard is really running
check_dashboard() {
    if pgrep -f "npm.*dev" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Enhanced status function
status() {
    echo "=== JJ Bot System Status ==="
    
    # Check API
    if check_api; then
        PID=$(pgrep -f "uvicorn.*main:app.*8000" | head -1)
        echo "✅ API Running (PID: $PID)"
    else
        echo "❌ API Not Running"
    fi
    
    # Check Dashboard
    if check_dashboard; then
        PID=$(pgrep -f "npm.*dev" | head -1)
        echo "✅ Dashboard Running (PID: $PID)"
    else
        echo "❌ Dashboard Not Running"
    fi
    
    # Check API health
    echo -n "API Health: "
    if curl -s http://127.0.0.1:8000/api/system/health > /dev/null 2>&1; then
        echo "✅ Responding"
    else
        echo "❌ Not Responding"
    fi
    
    # Check Dashboard health
    echo -n "Dashboard Health: "
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "✅ Responding"
    else
        echo "❌ Not Responding"
    fi
    
    # Show URLs
    echo ""
    echo "Access URLs:"
    echo "  API: http://127.0.0.1:8000"
    echo "  Dashboard: http://127.0.0.1:8000/dashboard/"
    echo "  API Docs: http://127.0.0.1:8000/docs"
    
    # Backup info
    echo ""
    echo "Backups:"
    BACKUP_COUNT=$(ls -1 ~/jj-bot-backups/*/*.tar.gz 2>/dev/null | wc -l)
    LATEST_BACKUP=$(ls -t ~/jj-bot-backups/*/*.tar.gz 2>/dev/null | head -1 | xargs basename 2>/dev/null)
    echo "  Total: $BACKUP_COUNT"
    echo "  Latest: $LATEST_BACKUP"
}

# Start function
start() {
    echo "🚀 Starting JJ-Bot services..."
    
    # Start API if not running
    if ! check_api; then
        echo "Starting API..."
        cd ~/jj-bot/glue/api
        nohup uvicorn main:app --host 127.0.0.1 --port 8000 > ~/jj-bot/logs/api.log 2>&1 &
        sleep 2
    else
        echo "API already running"
    fi
    
    # Start Dashboard if not running
    if ! check_dashboard; then
        echo "Starting Dashboard..."
        cd ~/jj-bot/dashboard/jj-dashboard
        nohup npm run dev > ~/jj-bot/logs/dashboard.log 2>&1 &
        sleep 3
    else
        echo "Dashboard already running"
    fi
    
    status
}

# Stop function
stop() {
    echo "🛑 Stopping JJ-Bot services..."
    
    # Stop API
    pkill -f "uvicorn.*main:app.*8000"
    
    # Stop Dashboard
    pkill -f "npm.*dev"
    
    sleep 2
    status
}

# Main command handler
case "$1" in
    status)
        status
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    *)
        # Pass through to original jj script
        ./jj.original "$@"
        ;;
esac
