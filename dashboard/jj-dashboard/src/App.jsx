import React, { useState, useEffect } from 'react';
import { ControlPanel } from "./ControlPanel.jsx";
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState({
    total_trades: 0,
    total_pnl: 0,
    win_rate: 0,
    avg_pnl: 0
  });
  const [marketData, setMarketData] = useState([]);
  const [simulatorRunning, setSimulatorRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [realtimeEvents, setRealtimeEvents] = useState([]);

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
    yellow: darkMode ? '#fbbf24' : '#eab308',
    gray: darkMode ? '#4b5563' : '#6b7280'
  };

  // ALL YOUR ORIGINAL FETCH FUNCTIONS
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

  // NEW: Fetch real market data
  const fetchMarketData = async () => {
    try {
      // First try the live endpoint if it exists
      const response = await fetch(`${API_BASE}/api/market/live`);
      if (response.ok) {
        const data = await response.json();
        // Convert object to array
        if (data.data && typeof data.data === 'object') {
          const marketArray = Object.values(data.data).map(coin => ({
            symbol: coin.symbol,
            price: coin.usd,
            change_24h: coin.usd_24h_change || 0,
            market_cap: coin.usd_market_cap || 0,
            volume_24h: coin.usd_24h_vol || 0
          }));
          setMarketData(marketArray);
        } else {
          setMarketData([]);
        }
      } else {
        // Fallback to mock data for now
        setMarketData([]);
      }
    } catch (error) {
      console.error('Error fetching market data:', error);
      setMarketData([]);
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

  // ALL YOUR ORIGINAL CONTROL FUNCTIONS
  const startSimulator = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/start`, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.status === 'started' || data.status === 'already_running') {
        setSimulatorRunning(true);
        alert('Trade simulator started! Trades will appear in a few seconds.');
        setTimeout(() => {
          fetchTrades();
          fetchSummary();
        }, 3000);
      } else {
        alert('Error: ' + data.message);
      }
    } catch (error) {
      alert('Error starting simulator: ' + error);
    }
    setLoading(false);
  };

  const stopSimulator = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/stop`, {
        method: 'POST'
      });
      const data = await response.json();
      setSimulatorRunning(false);
      alert('Simulator stopped');
    } catch (error) {
      alert('Error stopping simulator: ' + error);
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
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert('Error exporting data: ' + error);
    }
  };

  const clearDatabase = async () => {
    if (confirm('Are you sure you want to clear all trade data? This will backup first.')) {
      try {
        const response = await fetch(`${API_BASE}/api/data/clear`, {
          method: 'POST'
        });
        const data = await response.json();
        alert('Database cleared and backed up!');
        setTrades([]);
        setSummary({
          total_trades: 0,
          total_pnl: 0,
          win_rate: 0,
          avg_pnl: 0
        });
        fetchTrades();
        fetchSummary();
      } catch (error) {
        alert('Error clearing database: ' + error);
      }
    }
  };

  // WebSocket connection for real-time updates
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
          console.log('✅ WebSocket connected');
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setWsConnected(false);
        };

        ws.onclose = () => {
          console.log('🔌 WebSocket disconnected');
          setWsConnected(false);
          // Reconnect after 3 seconds
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };
      } catch (error) {
        console.error('WebSocket connection error:', error);
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
    };
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'price_update':
        updateMarketPrice(message.data);
        break;
      case 'trading_signal':
        addRealtimeEvent({ type: 'signal', ...message.data });
        break;
      case 'trade_executed':
        addRealtimeEvent({ type: 'trade', ...message.data });
        fetchTrades(); // Refresh trade list
        fetchSummary(); // Refresh summary
        break;
      case 'connection':
        console.log('Connected:', message.message);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  };

  // Update market price in real-time
  const updateMarketPrice = (priceData) => {
    setMarketData(prev => {
      const updated = [...prev];
      const index = updated.findIndex(item => item.symbol === priceData.symbol);
      if (index !== -1) {
        updated[index] = {
          ...updated[index],
          price: priceData.price,
          change_24h: priceData.change_24h
        };
      } else {
        updated.push({
          symbol: priceData.symbol,
          price: priceData.price,
          change_24h: priceData.change_24h
        });
      }
      return updated;
    });
  };

  // Add real-time event notification
  const addRealtimeEvent = (event) => {
    setRealtimeEvents(prev => [event, ...prev].slice(0, 10)); // Keep last 10 events
  };

  // Initial data fetch and periodic refresh (less frequent now with WebSocket)
  useEffect(() => {
    fetchTrades();
    fetchSummary();
    fetchMarketData();
    checkSimulatorStatus();

    const interval = setInterval(() => {
      fetchSummary();
      checkSimulatorStatus();
    }, 10000); // Reduced to every 10 seconds instead of 5

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: colors.bg, 
      color: colors.text,
      fontFamily: 'system-ui',
      transition: 'background-color 0.3s, color 0.3s'
    }}>
      {/* HEADER WITH DARK MODE TOGGLE */}
      <div style={{ 
        backgroundColor: colors.card, 
        boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)',
        transition: 'background-color 0.3s'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: colors.text }}>
                JJ-Bot Trading Dashboard v2.3
              </h1>
              <div style={{ fontSize: '0.875rem', color: colors.textMuted, marginTop: '0.5rem' }}>
                {wsConnected ? '🟢 Live' : '🔴 Offline'} |
                Simulator: {simulatorRunning ? '🟢 Running' : '🔴 Stopped'} |
                Trades: {summary.total_trades} |
                P&L: ${summary.total_pnl?.toFixed(2)}
              </div>
            </div>
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
              title="Toggle dark mode"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        {/* NAVIGATION TABS - NOW WITH MARKET TAB */}
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
                  textTransform: 'capitalize',
                  transition: 'color 0.3s'
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* OVERVIEW TAB - YOUR ORIGINAL WITH DARK MODE SUPPORT */}
        {activeTab === 'overview' && (
          <div>
            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
              <div style={{ 
                backgroundColor: colors.card, 
                padding: '1rem', 
                borderRadius: '0.5rem', 
                boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Total Trades</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: colors.text }}>{summary.total_trades}</div>
              </div>
              <div style={{ 
                backgroundColor: colors.card, 
                padding: '1rem', 
                borderRadius: '0.5rem', 
                boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Total P&L</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: summary.total_pnl >= 0 ? colors.green : colors.red }}>
                  ${summary.total_pnl?.toFixed(2)}
                </div>
              </div>
              <div style={{ 
                backgroundColor: colors.card, 
                padding: '1rem', 
                borderRadius: '0.5rem', 
                boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Win Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: colors.text }}>{summary.win_rate?.toFixed(1)}%</div>
              </div>
              <div style={{ 
                backgroundColor: colors.card, 
                padding: '1rem', 
                borderRadius: '0.5rem', 
                boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Avg P&L</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: summary.avg_pnl >= 0 ? colors.green : colors.red }}>
                  ${summary.avg_pnl?.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div style={{ 
              backgroundColor: colors.card, 
              borderRadius: '0.5rem', 
              padding: '1.5rem', 
              boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <h3 style={{ fontWeight: '600', marginBottom: '1rem', color: colors.text }}>Recent Activity</h3>
              {trades.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {trades.slice(0, 5).map((trade, index) => (
                    <div key={index} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      padding: '0.5rem', 
                      backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                      borderRadius: '0.25rem'
                    }}>
                      <span>{new Date(trade.timestamp).toLocaleTimeString()}</span>
                      <span>{trade.symbol}</span>
                      <span>{trade.signal}</span>
                      <span>${trade.last_price}</span>
                      <span style={{ color: trade.pnl >= 0 ? colors.green : colors.red, fontWeight: 'bold' }}>
                        ${trade.pnl?.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: colors.textMuted }}>No trades yet. Start the simulator to generate trades.</p>
              )}
            </div>
          </div>
        )}

        {/* NEW MARKET TAB WITH REAL DATA */}
        {activeTab === 'market' && (
          <div style={{ 
            backgroundColor: colors.card, 
            borderRadius: '0.5rem', 
            padding: '1.5rem', 
            boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              🌐 Live Market Data
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem' }}>
              {marketData.map((coin, index) => (
                <div key={index} style={{ 
                  border: `1px solid ${colors.border}`, 
                  borderRadius: '0.5rem', 
                  padding: '0.75rem',
                  backgroundColor: darkMode ? '#1a1a1a' : 'white'
                }}>
                  <h3 style={{ fontWeight: '600', marginBottom: '0.25rem', color: colors.text, fontSize: '0.875rem' }}>{coin.symbol}</h3>
                  <p style={{ fontSize: '1.125rem', fontWeight: 'bold', color: colors.text, marginBottom: '0.25rem' }}>
                    ${coin.price?.toLocaleString(undefined, { 
                      minimumFractionDigits: coin.price < 1 ? 4 : 2,
                      maximumFractionDigits: coin.price < 1 ? 4 : 2
                    })}
                  </p>
                  <p style={{ 
                    fontSize: '0.75rem', 
                    color: coin.change_24h >= 0 ? colors.green : colors.red,
                    fontWeight: 'bold'
                  }}>
                    {coin.change_24h >= 0 ? '↑' : '↓'} {Math.abs(coin.change_24h).toFixed(2)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CONTROL TAB - YOUR COMPLETE ORIGINAL WITH DARK MODE */}
        {activeTab === 'control' && (
          <ControlPanel colors={colors} API_BASE={API_BASE} />
        )}
        {/* TRADES TAB - YOUR COMPLETE ORIGINAL WITH DARK MODE */}
        {activeTab === 'trades' && (
          <div style={{ 
            backgroundColor: colors.card, 
            borderRadius: '0.5rem', 
            padding: '1.5rem', 
            boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              Recent Trades ({trades.length})
            </h2>
            {trades.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                      <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Time</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Symbol</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Signal</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Price</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>VWAP</th>
                      <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade, index) => (
                      <tr key={index} style={{ 
                        borderBottom: `1px solid ${colors.border}`,
                        backgroundColor: index % 2 === 0 ? 'transparent' : (darkMode ? '#1a1a1a' : '#f9fafb')
                      }}>
                        <td style={{ padding: '0.5rem', color: colors.text }}>{new Date(trade.timestamp).toLocaleTimeString()}</td>
                        <td style={{ padding: '0.5rem', color: colors.text }}>{trade.symbol}</td>
                        <td style={{ padding: '0.5rem', color: colors.text }}>{trade.signal}</td>
                        <td style={{ padding: '0.5rem', color: colors.text }}>${trade.last_price}</td>
                        <td style={{ padding: '0.5rem', color: colors.text }}>${trade.vwap}</td>
                        <td style={{ padding: '0.5rem', color: trade.pnl >= 0 ? colors.green : colors.red, fontWeight: 'bold' }}>
                          ${trade.pnl?.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: colors.textMuted, textAlign: 'center', padding: '2rem' }}>
                No trades yet. Go to Control tab and start the simulator.
              </p>
            )}
          </div>
        )}
      </div>
      </div>
  );
}

export default App;
