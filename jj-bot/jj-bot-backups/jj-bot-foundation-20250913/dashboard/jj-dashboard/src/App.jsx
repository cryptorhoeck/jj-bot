import { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

export default function UltimateJJDashboard() {
  const [darkMode, setDarkMode] = useState(false);
  const [summary, setSummary] = useState({});
  const [trades, setTrades] = useState([]);
  const [config, setConfig] = useState({});
  const [analytics, setAnalytics] = useState({});
  const [liveMarketData, setLiveMarketData] = useState({});
  const [systemHealth, setSystemHealth] = useState({});
  const [selectedTab, setSelectedTab] = useState('dashboard');
  const [notifications, setNotifications] = useState([]);
  const [backtestResults, setBacktestResults] = useState(null);
  const [isSimulatorRunning, setIsSimulatorRunning] = useState(false);
  const wsRef = useRef(null);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      wsRef.current = new WebSocket('ws://127.0.0.1:8000/ws');
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'trade_update') {
          setTrades(prev => [data.data, ...prev.slice(0, 99)]);
          showNotification(`New ${data.data.signal} signal for ${data.data.symbol}`, 'trade');
        } else if (data.type === 'summary_update') {
          setSummary(data.data);
        }
      };
      
      wsRef.current.onclose = () => {
        setTimeout(connectWebSocket, 3000);
      };
    };
    
    connectWebSocket();
    return () => wsRef.current?.close();
  }, []);

  // Fetch data periodically
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryRes, tradesRes, configRes, analyticsRes, marketRes, healthRes] = await Promise.all([
          fetch('http://127.0.0.1:8000/api/summary'),
          fetch('http://127.0.0.1:8000/api/trades?limit=50'),
          fetch('http://127.0.0.1:8000/api/config'),
          fetch('http://127.0.0.1:8000/api/analytics/performance'),
          fetch('http://127.0.0.1:8000/api/market/prices'),
          fetch('http://127.0.0.1:8000/api/system/health')
        ]);

        if (summaryRes.ok) setSummary(await summaryRes.json());
        if (tradesRes.ok) setTrades(await tradesRes.json());
        if (configRes.ok) setConfig(await configRes.json());
        if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
        if (marketRes.ok) setLiveMarketData(await marketRes.json());
        if (healthRes.ok) setSystemHealth(await healthRes.json());
      } catch (error) {
        console.error('Failed to fetch data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const showNotification = (message, type = 'info') => {
    const notification = {
      id: Date.now(),
      message,
      type,
      timestamp: new Date().toLocaleTimeString()
    };
    
    setNotifications(prev => [notification, ...prev.slice(0, 4)]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 5000);
  };

  const handleExportData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/data/export');
      const data = await response.json();
      
      if (data.csv_data) {
        const blob = new Blob([data.csv_data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        a.click();
        showNotification(`Exported ${data.total_records} trades to ${data.filename}`, 'success');
      }
    } catch (error) {
      showNotification('Export failed', 'error');
    }
  };

  const handleClearDatabase = async () => {
    if (window.confirm('Are you sure you want to clear all trade data? A backup will be created.')) {
      try {
        const response = await fetch('/api/data/clear', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
          showNotification(`Database cleared. Backup: ${data.backup_created}`, 'success');
          setTrades([]);
          setSummary({});
        }
      } catch (error) {
        showNotification('Clear database failed', 'error');
      }
    }
  };

  const handleToggleSimulator = async () => {
    try {
      const endpoint = isSimulatorRunning ? '/api/simulator/stop' : '/api/simulator/start';
      const response = await fetch(endpoint, { method: 'POST' });
      
      if (response.ok) {
        setIsSimulatorRunning(!isSimulatorRunning);
        showNotification(`Simulator ${isSimulatorRunning ? 'stopped' : 'started'}`, 'info');
      }
    } catch (error) {
      showNotification('Simulator toggle failed', 'error');
    }
  };

  const runBacktest = async () => {
    try {
      const response = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: '2024-01-01',
          end_date: new Date().toISOString().split('T')[0],
          strategy: 'default'
        })
      });
      
      const results = await response.json();
      setBacktestResults(results);
      showNotification('Backtest completed', 'success');
    } catch (error) {
      showNotification('Backtest failed', 'error');
    }
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'dark bg-gray-900' : 'bg-gray-50'}`}>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-lg border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                🦍 JJ-Bot Ultimate
              </h1>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                systemHealth.status === 'healthy' 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                  : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
              }`}>
                {systemHealth.status || 'Unknown'}
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600 dark:text-gray-300">
                {systemHealth.services?.active_connections || 0} connections
              </div>
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="flex space-x-8 pb-4">
            {['dashboard', 'analytics', 'trades', 'market', 'config', 'backtest'].map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`px-3 py-2 text-sm font-medium capitalize transition-colors ${
                  selectedTab === tab
                    ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className={`p-4 rounded-lg shadow-lg max-w-sm transition-all transform ${
              notification.type === 'success' ? 'bg-green-500 text-white' :
              notification.type === 'error' ? 'bg-red-500 text-white' :
              notification.type === 'trade' ? 'bg-blue-500 text-white' :
              'bg-gray-800 text-white'
            }`}
          >
            <div className="font-medium">{notification.message}</div>
            <div className="text-xs opacity-75">{notification.timestamp}</div>
          </div>
        ))}
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Dashboard Tab */}
        {selectedTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard 
                title="Total P&L" 
                value={`$${summary.total_pnl || 0}`}
                change={analytics.total_pnl > 0 ? '+' + analytics.total_pnl : analytics.total_pnl}
                icon="💰"
                darkMode={darkMode}
              />
              <MetricCard 
                title="Win Rate" 
                value={`${analytics.win_rate || 0}%`}
                change={analytics.win_rate > 50 ? 'Good' : 'Needs Work'}
                icon="🎯"
                darkMode={darkMode}
              />
              <MetricCard 
                title="Total Trades" 
                value={summary.total_trades || 0}
                change={`Today: ${summary.today_trades || 0}`}
                icon="📊"
                darkMode={darkMode}
              />
              <MetricCard 
                title="Sharpe Ratio" 
                value={analytics.sharpe_ratio || 0}
                change={analytics.sharpe_ratio > 1 ? 'Excellent' : 'Average'}
                icon="📈"
                darkMode={darkMode}
              />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-semibold mb-4 dark:text-white">Performance Trend</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trades.slice(-20).map((trade, i) => ({
                    index: i,
                    pnl: trade.pnl || 0,
                    cumulative: trades.slice(0, i+1).reduce((sum, t) => sum + (t.pnl || 0), 0)
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? '#374151' : '#e5e7eb'} />
                    <XAxis dataKey="index" stroke={darkMode ? '#9ca3af' : '#6b7280'} />
                    <YAxis stroke={darkMode ? '#9ca3af' : '#6b7280'} />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: darkMode ? '#1f2937' : '#ffffff',
                        border: 'none',
                        borderRadius: '8px',
                        color: darkMode ? '#ffffff' : '#000000'
                      }}
                    />
                    <Line type="monotone" dataKey="cumulative" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-semibold mb-4 dark:text-white">Trade Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Wins', value: analytics.win_rate || 50, fill: '#10b981' },
                        { name: 'Losses', value: 100 - (analytics.win_rate || 50), fill: '#ef4444' }
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      dataKey="value"
                      label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                    />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Control Panel */}
            <ControlPanel 
              onToggleSimulator={handleToggleSimulator}
              onExportData={handleExportData}
              onClearDatabase={handleClearDatabase}
              simulatorRunning={isSimulatorRunning}
              darkMode={darkMode}
            />
          </div>
        )}

        {/* Analytics Tab */}
        {selectedTab === 'analytics' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-semibold mb-6 dark:text-white">📊 Advanced Analytics</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {analytics.profit_factor || 0}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</div>
                </div>
                
                <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    ${analytics.avg_win || 0}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Avg Win</div>
                </div>
                
                <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {analytics.max_drawdown || 0}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Market Tab */}
        {selectedTab === 'market' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-semibold mb-6 dark:text-white">🌍 Live Market Data</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(liveMarketData.prices || {}).map(([symbol, data]) => (
                  <div key={symbol} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <div className="flex justify-between items-center">
                      <div className="font-semibold dark:text-white">{symbol}</div>
                      <div className={`text-sm px-2 py-1 rounded ${
                        data.change_24h > 0 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {data.change_24h > 0 ? '+' : ''}{data.change_24h?.toFixed(2)}%
                      </div>
                    </div>
                    <div className="text-xl font-bold mt-2 dark:text-white">
                      ${data.price?.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Backtest Tab */}
        {selectedTab === 'backtest' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-semibold mb-6 dark:text-white">🔬 Strategy Backtesting</h2>
              
              <button
                onClick={runBacktest}
                className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
              >
                Run Backtest
              </button>
              
              {backtestResults && (
                <div className="mt-6 p-6 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <h3 className="text-lg font-semibold mb-4 dark:text-white">Results</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                        {backtestResults.total_return}%
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Total Return</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                        {backtestResults.win_rate}%
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Win Rate</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                        {backtestResults.sharpe_ratio}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                        {backtestResults.max_drawdown}%
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recent Trades Table */}
        {(selectedTab === 'dashboard' || selectedTab === 'trades') && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h3 className="text-xl font-semibold mb-4 dark:text-white">Recent Trades</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b dark:border-gray-700">
                    <th className="p-3 text-gray-600 dark:text-gray-300">Time</th>
                    <th className="p-3 text-gray-600 dark:text-gray-300">Symbol</th>
                    <th className="p-3 text-gray-600 dark:text-gray-300">Signal</th>
                    <th className="p-3 text-gray-600 dark:text-gray-300">Price</th>
                    <th className="p-3 text-gray-600 dark:text-gray-300">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.slice(0, 10).map((trade, i) => (
                    <tr key={i} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="p-3 dark:text-gray-300">
                        {new Date(trade.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="p-3 font-medium dark:text-white">{trade.symbol}</td>
                      <td className={`p-3 font-bold ${
                        trade.signal === 'LONG' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                      }`}>
                        {trade.signal}
                      </td>
                      <td className="p-3 dark:text-gray-300">${trade.last_price || 'N/A'}</td>
                      <td className={`p-3 font-semibold ${
                        (trade.pnl || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                      }`}>
                        ${trade.pnl?.toFixed(2) || '0.00'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Utility Components
function MetricCard({ title, value, change, icon, darkMode }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 transition-transform hover:scale-105">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold dark:text-white mt-1">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{change}</p>
        </div>
        <div className="text-3xl">{icon}</div>
      </div>
    </div>
  );
}

function ControlPanel({ onToggleSimulator, onExportData, onClearDatabase, simulatorRunning, darkMode }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
      <h3 className="text-xl font-semibold mb-4 dark:text-white">🎮 Control Panel</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <h4 className="font-medium mb-3 dark:text-white">Simulator</h4>
          <button
            onClick={onToggleSimulator}
            className={`w-full px-4 py-2 rounded-lg font-medium text-white transition-colors ${
              simulatorRunning 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-purple-600 hover:bg-purple-700'
            }`}
          >
            {simulatorRunning ? '⏹️ Stop' : '▶️ Start'} Simulator
          </button>
        </div>
        
        <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <h4 className="font-medium mb-3 dark:text-white">Export</h4>
          <button
            onClick={onExportData}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
          >
            📁 Export CSV
          </button>
        </div>
        
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <h4 className="font-medium mb-3 dark:text-white">Reset</h4>
          <button
            onClick={onClearDatabase}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
          >
            🗑️ Clear Data
          </button>
        </div>
      </div>
    </div>
  );
}
