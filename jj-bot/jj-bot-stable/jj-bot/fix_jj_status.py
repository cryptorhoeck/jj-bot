import sys

# Read the jj script
with open('jj', 'r') as f:
    content = f.read()

# Fix the status detection logic
# Look for the status function and improve it
if 'status)' in content:
    # This will need to be adjusted based on actual content
    print("Found status function, updating...")
    
# For now, let's create a better status check
better_status = '''
    # Better process detection
    API_PID=$(pgrep -f "uvicorn.*main:app.*8000" | head -1)
    DASH_PID=$(pgrep -f "npm.*dev.*5173" | head -1)
    
    if [ ! -z "$API_PID" ]; then
        echo "✅ API Running (PID: $API_PID)"
    else
        echo "❌ API Not Running"
    fi
    
    if [ ! -z "$DASH_PID" ]; then
        echo "✅ Dashboard Running (PID: $DASH_PID)"
    else
        echo "❌ Dashboard Not Running"
    fi
'''

print("Status detection logic prepared")
