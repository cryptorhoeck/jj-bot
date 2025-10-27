import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState({
    total_trades: 0,
    total_pnl: 0,
    win_rate: 0,
    avg_pnl: 0
  });
  const [marketData, setMarketData] = useState({});
  const [simulatorRunning, setSimulatorRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // Dark mode colors
  const colors = {
    bg: darkMode ? '#1a1a1a' : '#f3f4f6',
    card: darkMode ? '#2d2d2d' : 'white',
    text: darkMode ? '#e0e0e0' : '#111827',
    textMuted: darkMode ? '#a0a0a0' : '#6b7280',
    border: darkMode ? '#404040' : '#e5e7eb',
    green: '#10b981',
    red: '#ef4444',
    blue: darkMode ? '#60a5fa' : '#3b82f6',
    yellow: darkMode ? '#fbbf24' : '#eab308'
  };

  // Test function for market data
  const fetchMarketData = async () => {
    try {
      // For now, use mock data to test
      setMarketData({
        "BTCUSDT": { "price": 45000, "change_24h": 2.5 },
        "ETHUSDT": { "price": 2500, "change_24h": -1.2 },
        "BNBUSDT": { "price": 300, "change_24h": 0.8 },
        "timestamp": new Date().toISOString(),
        "source": "Test Data"
      });
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchTrades = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/trades?limit=50`);
      const data = await response.json();
      setTrades(data.trades || []);
    } catch (error) {
      console.error('Error fetching trades:', error);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/summary`);
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  };

  const checkSimulatorStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulator/status`);
      const data = await response.json();
      setSimulatorRunning(data.running);
    } catch (error) {
      console.error('Error checking simulator:', error);
    }
  };

  const startSimulator = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/start`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'started' || data.status === 'already_running') {
        setSimulatorRunning(true);
        alert('Trade simulator started!');
      }
    } catch (error) {
      alert('Error: ' + error);
    }
    setLoading(false);
  };

  const stopSimulator = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/simulator/stop`, { method: 'POST' });
      setSimulatorRunning(false);
      alert('Simulator stopped');
    } catch (error) {
      alert('Error: ' + error);
    }
    setLoading(false);
  };

  const exportCSV = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/export`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      alert('Error: ' + error);
    }
  };

  const clearDatabase = async () => {
    if (confirm('Clear all trade data?')) {
      try {
        await fetch(`${API_BASE}/api/data/clear`, { method: 'POST' });
        alert('Database cleared!');
        setTrades([]);
        fetchTrades();
        fetchSummary();
      } catch (error) {
        alert('Error: ' + error);
      }
    }
  };

  useEffect(() => {
    fetchTrades();
    fetchSummary();
    fetchMarketData();
    checkSimulatorStatus();

    const interval = setInterval(() => {
      fetchTrades();
      fetchSummary();
      fetchMarketData();
      checkSimulatorStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: colors.bg, 
      color: colors.text,
      fontFamily: 'system-ui',
      transition: 'all 0.3s'
    }}>
      <div style={{ 
        backgroundColor: colors.card, 
        boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: colors.text }}>
            JJ-Bot Dashboard v2.2
          </h1>
          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: colors.border,
              color: colors.text,
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '1.5rem'
            }}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        {/* Navigation */}
        <div style={{ borderBottom: `2px solid ${colors.border}`, marginBottom: '2rem' }}>
          <div style={{ display: 'flex', gap: '2rem' }}>
            {['overview', 'market', 'control', 'trades'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: '0.5rem 0',
                  background: 'none',
                  border: 'none',
                  borderBottom: activeTab === tab ? `2px solid ${colors.blue}` : '2px solid transparent',
                  color: activeTab === tab ? colors.blue : colors.textMuted,
                  fontWeight: '500',
                  cursor: 'pointer',
                  textTransform: 'capitalize'
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Market Tab */}
        {activeTab === 'market' && (
          <div style={{ 
            backgroundColor: colors.card, 
            borderRadius: '0.5rem', 
            padding: '1.5rem',
            boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              📈 Market Data
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              {Object.entries(marketData).filter(([key]) => key.includes('USDT')).map(([symbol, data]) => (
                <div key={symbol} style={{ 
                  border: `1px solid ${colors.border}`, 
                  borderRadius: '0.5rem', 
                  padding: '1rem',
                  backgroundColor: darkMode ? '#1a1a1a' : 'white'
                }}>
                  <h3 style={{ fontWeight: '600', color: colors.text }}>{symbol}</h3>
                  <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: colors.text }}>
                    ${data.price?.toLocaleString()}
                  </p>
                  <p style={{ color: data.change_24h >= 0 ? colors.green : colors.red }}>
                    {data.change_24h >= 0 ? '↑' : '↓'} {Math.abs(data.change_24h).toFixed(2)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Other tabs - simplified for space */}
        {activeTab === 'overview' && (
          <div style={{ backgroundColor: colors.card, padding: '1rem', borderRadius: '0.5rem' }}>
            <h2 style={{ color: colors.text }}>Overview</h2>
            <p style={{ color: colors.textMuted }}>Trades: {summary.total_trades} | P&L: ${summary.total_pnl?.toFixed(2)}</p>
          </div>
        )}

        {activeTab === 'control' && (
          <div style={{ backgroundColor: colors.card, padding: '1rem', borderRadius: '0.5rem' }}>
            <h2 style={{ color: colors.text }}>Control Panel</h2>
            <button
              onClick={simulatorRunning ? stopSimulator : startSimulator}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: simulatorRunning ? colors.red : colors.green,
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer'
              }}
            >
              {simulatorRunning ? 'Stop' : 'Start'} Simulator
            </button>
          </div>
        )}

        {activeTab === 'trades' && (
          <div style={{ backgroundColor: colors.card, padding: '1rem', borderRadius: '0.5rem' }}>
            <h2 style={{ color: colors.text }}>Trades</h2>
            <p style={{ color: colors.textMuted }}>{trades.length} trades</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
