import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { DashboardTab } from "./ImprovedDashboard.jsx";
import { TradingTab } from "./TradingTab.jsx";
import { DataTab } from "./DataTab.jsx";
import { MarketChart } from "./MarketChart.jsx";
import { ConfirmModal } from './components';
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
  const [darkMode, setDarkMode] = useState(true); // Default to dark mode for trading
  const [wsConnected, setWsConnected] = useState(false);
  const [realtimeEvents, setRealtimeEvents] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [learningData, setLearningData] = useState(null);
  const [marketDataError, setMarketDataError] = useState(null);
  const [marketDataLoading, setMarketDataLoading] = useState(false);
  const [lastMarketFetch, setLastMarketFetch] = useState(null);
  const [marketRefreshInterval, setMarketRefreshInterval] = useState(120000);
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);

  // Unified Bot Status
  const [botStatus, setBotStatus] = useState({
    running: false,
    mode: 'paper',
    training: null,
    apiConnected: false
  });

  // Apply dark mode to document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // ALL FETCH FUNCTIONS
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

  const fetchMarketData = async (force = false) => {
    if (!force && lastMarketFetch) {
      const timeSinceLastFetch = Date.now() - lastMarketFetch;
      if (timeSinceLastFetch < marketRefreshInterval) {
        return;
      }
    }

    setMarketDataLoading(true);
    setMarketDataError(null);

    try {
      const response = await fetch(`${API_BASE}/api/market/live`);

      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        const waitTime = retryAfter ? parseInt(retryAfter) * 1000 : marketRefreshInterval * 2;
        setMarketDataError(`Rate limited. Waiting ${Math.ceil(waitTime / 1000)}s...`);
        setMarketRefreshInterval(Math.min(waitTime, 300000));
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

          if (marketRefreshInterval > 120000) {
            setMarketRefreshInterval(120000);
          }
        }
      } else {
        setMarketDataError(`Failed to fetch: ${response.status}`);
      }
    } catch (error) {
      setMarketDataError(error.message);
    } finally {
      setMarketDataLoading(false);
    }
  };

  const checkBotStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/bot/status`);
      const data = await response.json();

      setBotStatus({
        running: data.running || false,
        mode: data.mode || 'paper',
        training: data.training || null,
        apiConnected: true
      });

      setSimulatorRunning(data.running || false); // For backward compatibility
    } catch (error) {
      console.error('Error checking bot status:', error);
      setBotStatus(prev => ({ ...prev, apiConnected: false }));
    }
  };

  const checkSimulatorStatus = async () => {
    // Legacy function - now calls unified bot status
    await checkBotStatus();
  };

  const startSimulator = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/start`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'started' || data.status === 'already_running') {
        setSimulatorRunning(true);
        toast.success('Trading bot started successfully!');
        setTimeout(() => {
          fetchTrades();
          fetchSummary();
        }, 3000);
      } else {
        toast.error('Error: ' + data.message);
      }
    } catch (error) {
      toast.error('Error starting simulator: ' + error);
    }
    setLoading(false);
  };

  const stopSimulator = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/simulator/stop`, { method: 'POST' });
      setSimulatorRunning(false);
      toast.success('Trading bot stopped');
    } catch (error) {
      toast.error('Error stopping simulator: ' + error);
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
      toast.success('CSV exported successfully!');
    } catch (error) {
      toast.error('Export failed: ' + error);
    }
  };

  const clearDatabase = async () => {
    setConfirmModalOpen(true);
  };

  const handleClearDatabaseConfirm = async () => {
    try {
      await fetch(`${API_BASE}/api/data/clear`, { method: 'POST' });
      toast.success('Database cleared successfully!');
      setTrades([]);
      setSummary({ total_trades: 0, total_pnl: 0, win_rate: 0, avg_pnl: 0 });
      fetchTrades();
      fetchSummary();
    } catch (error) {
      toast.error('Error clearing database: ' + error);
    }
  };

  const fetchSymbols = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/symbols/list`);
      const data = await response.json();
      if (data.success) setSymbols(data.symbols);
    } catch (error) {
      console.error('Error fetching symbols:', error);
    }
  };

  const fetchLearningData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/learning/insights`);
      const data = await response.json();
      if (data.success) setLearningData(data.insights);
    } catch (error) {
      console.error('Error fetching learning data:', error);
    }
  };

  // WebSocket connection
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
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

        ws.onerror = () => setWsConnected(false);
        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };
      } catch (error) {
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'price_update':
        setMarketData(prev => {
          const updated = [...prev];
          const index = updated.findIndex(item => item.symbol === message.data.symbol);
          if (index !== -1) {
            updated[index] = { ...updated[index], price: message.data.price, change_24h: message.data.change_24h };
          }
          return updated;
        });
        break;
      case 'trade_executed':
        fetchTrades();
        fetchSummary();
        break;
      default:
        break;
    }
  };

  useEffect(() => {
    fetchTrades();
    fetchSummary();
    fetchMarketData();
    checkSimulatorStatus();
    fetchSymbols();
    fetchLearningData();

    const fastInterval = setInterval(() => {
      fetchTrades();
      fetchSummary();
      checkSimulatorStatus();
      fetchLearningData();
    }, 10000);

    const marketInterval = setInterval(() => {
      if (activeTab === 'charts') fetchMarketData();
    }, 120000);

    return () => {
      clearInterval(fastInterval);
      clearInterval(marketInterval);
    };
  }, [activeTab, marketRefreshInterval]);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { id: 'trading', label: 'Trading', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
    { id: 'charts', label: 'Charts', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { id: 'data', label: 'Data', icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4' }
  ];

  return (
    <div className="min-h-screen transition-colors duration-300">
      {/* Premium Header */}
      <header className="header header-glass">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo & Brand */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <h1 className="logo text-xl font-bold">JJ-Bot</h1>
                  <p className="text-xs text-muted">v2.4 Pro</p>
                </div>
              </div>

              {/* Status Badges */}
              <div className="hidden md:flex items-center gap-2 ml-4">
                <span className={`badge ${botStatus.apiConnected ? 'badge-live' : 'badge-danger'}`}>
                  {botStatus.apiConnected ? '🟢 API' : '🔴 API'}
                </span>
                {botStatus.training?.is_training ? (
                  <span className="badge badge-info">
                    🧠 Training ({botStatus.training.trading_iq || 0} IQ)
                  </span>
                ) : botStatus.running ? (
                  <span className="badge badge-success">
                    ▶ Trading
                  </span>
                ) : (
                  <span className="badge badge-warning">
                    ⏹ Stopped
                  </span>
                )}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="hidden lg:flex items-center gap-6">
              <div className="text-right">
                <p className="text-xs text-muted uppercase tracking-wide">Total P&L</p>
                <p className={`text-lg font-bold ${summary.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                  {summary.total_pnl >= 0 ? '+' : ''}${summary.total_pnl?.toFixed(2) || '0.00'}
                </p>
              </div>
              <div className="w-px h-8 bg-[var(--border-color)]" />
              <div className="text-right">
                <p className="text-xs text-muted uppercase tracking-wide">Win Rate</p>
                <p className="text-lg font-bold">{summary.win_rate?.toFixed(1) || '0'}%</p>
              </div>
              <div className="w-px h-8 bg-[var(--border-color)]" />
              <div className="text-right">
                <p className="text-xs text-muted uppercase tracking-wide">Trades</p>
                <p className="text-lg font-bold">{summary.total_trades || 0}</p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-3">
              {/* Dark Mode Toggle */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="btn btn-ghost p-2"
                title="Toggle theme"
              >
                {darkMode ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Navigation Tabs */}
        <div className="nav-tabs mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
              </svg>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="animate-in">
          {activeTab === 'dashboard' && (
            <DashboardTab
              darkMode={darkMode}
              summary={summary}
              trades={trades}
              API_BASE={API_BASE}
            />
          )}

          {activeTab === 'trading' && (
            <TradingTab
              darkMode={darkMode}
              API_BASE={API_BASE}
              learningData={learningData}
            />
          )}

          {activeTab === 'charts' && (
            <MarketChart
              darkMode={darkMode}
              API_BASE={API_BASE}
            />
          )}

          {activeTab === 'data' && (
            <DataTab
              darkMode={darkMode}
              API_BASE={API_BASE}
              trades={trades}
              summary={summary}
            />
          )}
        </div>
      </main>

      {/* Confirm Modal */}
      <ConfirmModal
        isOpen={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        onConfirm={handleClearDatabaseConfirm}
        title="Clear Database"
        message="Are you sure you want to clear all trade data? A backup will be created first."
        confirmText="Clear Database"
        cancelText="Cancel"
        confirmVariant="danger"
        darkMode={darkMode}
      />
    </div>
  );
}

export default App;
