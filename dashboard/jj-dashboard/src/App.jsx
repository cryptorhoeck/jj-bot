import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { DashboardTab } from "./DashboardTab.jsx";
import { TradingTab } from "./TradingTab.jsx";
import { TrainingTab } from "./TrainingTab.jsx";
import { DataTab } from "./DataTab.jsx";
import { MarketChart } from "./MarketChart.jsx";
import { ConfirmModal } from './components';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws';

// Currency configuration - CAD is the base currency
// All amounts in the system are stored in CAD
const CURRENCIES = {
  CAD: { symbol: 'C$', name: 'Canadian Dollar', code: 'CAD' },
  USD: { symbol: '$', name: 'US Dollar', code: 'USD' },
  EUR: { symbol: '€', name: 'Euro', code: 'EUR' },
  GBP: { symbol: '£', name: 'British Pound', code: 'GBP' },
  AUD: { symbol: 'A$', name: 'Australian Dollar', code: 'AUD' },
  JPY: { symbol: '¥', name: 'Japanese Yen', code: 'JPY' },
  CHF: { symbol: 'Fr', name: 'Swiss Franc', code: 'CHF' },
};

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
  const [currency, setCurrency] = useState(() => {
    return localStorage.getItem('jjbot_currency') || 'CAD';
  });
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
    apiConnected: false,
    trading_iq: 0,
    expertise_level: 'Untrained'
  });

  // API connection state
  const [apiReady, setApiReady] = useState(false);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [appVersion, setAppVersion] = useState('3.0.4');  // Default, will be fetched from API

  // Check if API is ready
  const checkApiReady = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/summary`, { signal: AbortSignal.timeout(2000) });
      if (response.ok) {
        setApiReady(true);
        setConnectionAttempts(0);
        // Fetch version from API
        try {
          const versionResponse = await fetch(`${API_BASE}/api/system/version`);
          if (versionResponse.ok) {
            const versionData = await versionResponse.json();
            setAppVersion(versionData.version || '3.0.4');
          }
        } catch (e) {
          console.log('Could not fetch version:', e);
        }
        return true;
      }
    } catch (error) {
      console.log('API not ready yet...');
    }
    return false;
  };

  // Wait for API to be ready on mount
  useEffect(() => {
    let interval;
    const waitForApi = async () => {
      const ready = await checkApiReady();
      if (!ready) {
        setConnectionAttempts(prev => prev + 1);
        interval = setTimeout(waitForApi, 2000); // Retry every 2 seconds
      }
    };
    waitForApi();
    return () => clearTimeout(interval);
  }, []);

  // Apply dark mode to document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Save currency preference to localStorage
  useEffect(() => {
    localStorage.setItem('jjbot_currency', currency);
  }, [currency]);

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
      const response = await fetch(`${API_BASE}/api/pro/status`);
      const data = await response.json();

      setBotStatus({
        running: data.running || false,
        mode: data.mode || 'paper',
        training: data.training || null,
        apiConnected: true,
        trading_iq: data.trading_iq || 0,
        expertise_level: data.expertise_level || 'Untrained'
      });

      setSimulatorRunning(data.running || false); // For backward compatibility
    } catch (error) {
      console.error('Error checking bot status:', error);
      setBotStatus(prev => ({ ...prev, apiConnected: false }));
    }
  };

  // Global stop function for bot/training
  const stopBot = async () => {
    const isTraining = botStatus.training?.is_training;
    setLoading(true);

    if (isTraining) {
      toast.loading('Stopping training and saving progress...', { id: 'stopping' });
    }

    try {
      const response = await fetch(`${API_BASE}/api/pro/stop`, { method: 'POST' });
      const data = await response.json();

      if (data.status === 'stopped') {
        setBotStatus(prev => ({ ...prev, running: false, training: null }));
        setSimulatorRunning(false);
        toast.dismiss('stopping');
        toast.success(isTraining ? 'Training stopped - progress saved!' : 'Bot stopped');
        checkBotStatus(); // Refresh status
      } else {
        toast.dismiss('stopping');
        toast.error(data.message || 'Failed to stop');
      }
    } catch (error) {
      toast.dismiss('stopping');
      toast.error('Error stopping: ' + error.message);
    }
    setLoading(false);
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
    if (!apiReady) return; // Don't fetch until API is ready

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
  }, [apiReady, activeTab, marketRefreshInterval]);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { id: 'trading', label: 'Trading', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
    { id: 'training', label: 'Training', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
    { id: 'charts', label: 'Charts', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { id: 'data', label: 'Data', icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4' }
  ];

  // Show loading screen while waiting for API
  if (!apiReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-blue-500/25">
            <svg className="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold mb-2">JJ-Bot</h1>
          <p className="text-muted mb-6">v{appVersion} Pro</p>

          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="spinner w-5 h-5 border-2 border-info border-t-transparent rounded-full animate-spin"></div>
            <p className="text-lg">Connecting to server...</p>
          </div>

          <p className="text-sm text-muted">
            {connectionAttempts > 0 && `Attempt ${connectionAttempts}... `}
            {connectionAttempts > 10 && (
              <span className="text-warning">
                <br />Server is taking longer than expected.
                <br />Make sure start_all.bat is running.
              </span>
            )}
          </p>
        </div>
      </div>
    );
  }

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
                  <p className="text-xs text-muted">v{appVersion} Pro</p>
                </div>
              </div>

              {/* Status Badges */}
              <div className="hidden md:flex items-center gap-2 ml-4">
                <span className={`badge ${botStatus.apiConnected ? 'badge-live' : 'badge-danger'}`}>
                  {botStatus.apiConnected ? '🟢 API' : '🔴 API'}
                </span>
                {/* Persistent IQ Score Badge */}
                <span className="badge" style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', color: 'white' }}>
                  🧠 {botStatus.trading_iq} IQ
                </span>
                {/* Bot Status Badge */}
                {(botStatus.training?.is_training || (botStatus.mode === 'training' && botStatus.running)) ? (
                  <span className="badge badge-info">
                    ⚡ Training {botStatus.training?.progress_pct ? `(${botStatus.training.progress_pct.toFixed(0)}%)` : ''}
                  </span>
                ) : botStatus.running ? (
                  <span className={`badge ${botStatus.mode === 'live' ? 'badge-danger' : 'badge-success'}`}>
                    {botStatus.mode === 'live' ? '🔴 Live Trading' : '▶ Paper Trading'}
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
              {/* Stop Button - Always visible when running */}
              {(botStatus.running || botStatus.training?.is_training) && (
                <button
                  onClick={stopBot}
                  disabled={loading}
                  className="btn btn-danger flex items-center gap-2 px-4 py-2"
                  title={botStatus.training?.is_training ? "Stop training and save progress" : "Stop trading bot"}
                >
                  {loading ? (
                    <div className="spinner w-4 h-4 border-2" />
                  ) : (
                    <>
                      <span>⏹</span>
                      <span className="hidden sm:inline">
                        {botStatus.training?.is_training ? 'Stop Training' : 'Stop Bot'}
                      </span>
                    </>
                  )}
                </button>
              )}

              {/* Currency Selector */}
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="btn btn-ghost px-2 py-1.5 text-sm font-medium cursor-pointer"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '0.375rem',
                  color: 'var(--text-primary)',
                  minWidth: '70px'
                }}
                title="Display currency"
              >
                {Object.entries(CURRENCIES).map(([code, curr]) => (
                  <option key={code} value={code}>
                    {curr.symbol} {code}
                  </option>
                ))}
              </select>

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
              botStatus={botStatus}
              currency={currency}
            />
          )}

          {activeTab === 'trading' && (
            <TradingTab
              darkMode={darkMode}
              API_BASE={API_BASE}
              learningData={learningData}
              sharedBotStatus={botStatus}
              onBotStatusChange={checkBotStatus}
            />
          )}

          {activeTab === 'training' && (
            <TrainingTab
              API_BASE={API_BASE}
              sharedBotStatus={botStatus}
              onBotStatusChange={checkBotStatus}
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
