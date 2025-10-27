// Simple Module Status Component
import React, { useState, useEffect } from 'react';

export function ModuleStatus({ API_BASE }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/module-status`);
        const data = await res.json();
        setStatus(data);
      } catch (e) {
        setStatus({ running: false });
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [API_BASE]);

  return (
    <div style={{
      position: 'fixed',
      bottom: '1rem',
      right: '1rem',
      padding: '0.5rem 1rem',
      backgroundColor: status?.running ? '#10b981' : '#6b7280',
      color: 'white',
      borderRadius: '0.5rem',
      fontSize: '0.875rem',
      opacity: 0.9
    }}>
      Modules: {status?.running ? '🟢 Running' : '⭕ Stopped'}
      {status?.coins_tracked && ` (${status.coins_tracked} coins)`}
    </div>
  );
}
