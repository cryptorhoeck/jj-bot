import React, { useState, useEffect } from 'react';
import { DashboardTab } from "./DashboardTab.jsx";
import { TradingTab } from "./TradingTab.jsx";
import { DataTab } from "./DataTab.jsx";
import { MarketChart } from "./MarketChart.jsx";
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState({
    total_trades: 0,
    total_pnl: 0,
    win_rate: 0,
    avg_pnl: 0
  });
  const [marketData, setMarketData] = useState([]);
  const [lastMarketUpdate, setLastMarketUpdate] = useState(null);
  const [simulatorRunning, setSimulatorRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [realtimeEvents, setRealtimeEvents] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [learningData, setLearningData] = useState(null);
  const [marketDataError, setMarketDataError] = useState(null);
  const [marketDataLoading, setMarketDataLoading] = useState(false);
  const [lastMarketFetch, setLastMarketFetch] = useState(null);
  const [marketRefreshInterval, setMarketRefreshInterval] = useState(120000); // 2 minutes default

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

  // Fetch real market data with rate limiting and error handling
  const fetchMarketData = async (force = false) => {
    // Rate limit check - don't fetch more than once per interval (unless forced)
    if (!force && lastMarketFetch) {
      const timeSinceLastFetch = Date.now() - lastMarketFetch;
      if (timeSinceLastFetch < marketRefreshInterval) {
        console.log(`⏸️  Rate limit: ${Math.ceil((marketRefreshInterval - timeSinceLastFetch) / 1000)}s until next fetch`);
        return;
      }
    }

    setMarketDataLoading(true);
    setMarketDataError(null);

    try {
      const response = await fetch(`${API_BASE}/api/market/live`);

      // Handle 429 Too Many Requests
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        const waitTime = retryAfter ? parseInt(retryAfter) * 1000 : marketRefreshInterval * 2;

        setMarketDataError(`Rate limited. Waiting ${Math.ceil(waitTime / 1000)}s before retry...`);
        setMarketRefreshInterval(Math.min(waitTime, 300000)); // Cap at 5 minutes
        console.warn(`⚠️  Rate limited! Increasing interval to ${waitTime / 1000}s`);
        return;
      }

      if (response.ok) {
        const data = await response.json();
        if (data.data && typeof data.data === 'object') {
          const marketArray = Object.values(data.data).map(coin => ({
            symbol: coin.symbol,
            price: coin.usd,
            change_24h: coin.usd_24h_change || 0,
            market_cap: coin.usd_market_cap || 0,
            volume_24h: coin.usd_24h_vol || 0
          }));
          setMarketData(marketArray);
          setLastMarketUpdate(new Date());
          setLastMarketFetch(Date.now());
          setMarketDataError(null);

          // Success - reset interval to default if it was increased
          if (marketRefreshInterval > 120000) {
            setMarketRefreshInterval(120000);
          }
        } else {
          setMarketData([]);
        }
      } else {
        setMarketDataError(`Failed to fetch: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error fetching market data:', error);
      setMarketDataError(error.message);
    } finally {
      setMarketDataLoading(false);
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

  const archiveData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/archive`, {
        method: 'POST'
      });
      const data = await response.json();
      alert(data.message);
    } catch (error) {
      alert('Error archiving data: ' + error);
    }
  };

  const fetchSymbols = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/symbols/list`);
      const data = await response.json();
      if (data.success) {
        setSymbols(data.symbols);
      }
    } catch (error) {
      console.error('Error fetching symbols:', error);
    }
  };

  const toggleSymbol = async (symbol, enabled) => {
    try {
      const response = await fetch(`${API_BASE}/api/symbols/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, enabled })
      });
      const data = await response.json();
      if (data.success) {
        fetchSymbols();
        fetchMarketData();
      }
    } catch (error) {
      console.error('Error toggling symbol:', error);
    }
  };

  const fetchLearningData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/learning/insights`);
      const data = await response.json();
      if (data.success) {
        setLearningData(data.insights);
      }
    } catch (error) {
      console.error('Error fetching learning data:', error);
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

  // Initial data fetch and periodic refresh with smart rate limiting
  useEffect(() => {
    fetchTrades();
    fetchSummary();
    fetchMarketData();
    checkSimulatorStatus();
    fetchSymbols();
    fetchLearningData();

    // Fast interval for trades/summary (10 seconds)
    const fastInterval = setInterval(() => {
      fetchTrades();
      fetchSummary();
      checkSimulatorStatus();
      fetchLearningData();
    }, 10000);

    // Slow interval for market data only when on Charts tab (120 seconds = 2 minutes)
    const marketInterval = setInterval(() => {
      // Only fetch market data if on Charts tab
      if (activeTab === 'charts') {
        fetchMarketData();
      }
    }, 120000);

    return () => {
      clearInterval(fastInterval);
      clearInterval(marketInterval);
    };
  }, [activeTab, marketRefreshInterval]); // Re-run if active tab or interval changes

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
        {/* NAVIGATION TABS */}
        <div style={{ borderBottom: `2px solid ${colors.border}`, marginBottom: '2rem' }}>
          <div style={{ display: 'flex', gap: '2rem' }}>
            {[
              { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
              { id: 'trading', label: '🤖 Trading', icon: '🤖' },
              { id: 'charts', label: '📈 Charts', icon: '📈' },
              { id: 'data', label: '📁 Data', icon: '📁' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: activeTab === tab.id ? colors.blue : 'none',
                  border: 'none',
                  borderRadius: '0.5rem 0.5rem 0 0',
                  color: activeTab === tab.id ? 'white' : colors.textMuted,
                  fontWeight: '600',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  transition: 'all 0.3s'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <DashboardTab
            colors={colors}
            darkMode={darkMode}
            summary={summary}
            trades={trades}
            botRunning={simulatorRunning}
            learningData={learningData}
            onNavigate={setActiveTab}
          />
        )}

        {/* TRADING TAB */}
        {activeTab === 'trading' && (
          <TradingTab
            colors={colors}
            darkMode={darkMode}
            API_BASE={API_BASE}
            learningData={learningData}
          />
        )}

        {/* CHARTS TAB */}
        {activeTab === 'charts' && (
          <MarketChart
            colors={colors}
            darkMode={darkMode}
            API_BASE={API_BASE}
          />
        )}

        {/* DATA & ANALYTICS TAB */}
        {activeTab === 'data' && (
          <DataTab
            colors={colors}
            darkMode={darkMode}
            API_BASE={API_BASE}
            trades={trades}
            summary={summary}
          />
        )}
      </div>
      </div>
  );
}

export default App;

