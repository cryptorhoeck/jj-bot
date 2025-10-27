// Update status indicators every 30 seconds
setInterval(updateStatus, 30000);

// Update current time every second
setInterval(updateTime, 1000);

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        // Update API status indicator
        const statusEl = document.getElementById('api-status');
        if (status.trading_api.healthy) {
            statusEl.textContent = 'API Running';
            statusEl.className = 'px-2 py-1 rounded text-xs bg-green-100 text-green-800';
        } else {
            statusEl.textContent = 'API Stopped';
            statusEl.className = 'px-2 py-1 rounded text-xs bg-red-100 text-red-800';
        }
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

function updateTime() {
    const timeEl = document.getElementById('current-time');
    if (timeEl) {
        timeEl.textContent = new Date().toLocaleTimeString();
    }
}

// Initialize
updateStatus();
updateTime();
